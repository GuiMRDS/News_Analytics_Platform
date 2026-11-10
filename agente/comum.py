"""Configuração e utilitários compartilhados entre as versões do curador."""

import json
import os
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from agno.models.groq import Groq
from agno.utils.log import log_warning
from agno.skills import Skills, LocalSkills
from agno.tools.file import FileTools
from agno.tools.websearch import WebSearchTools

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"
OUTPUT_DIR = BASE_DIR / "output"

load_dotenv(BASE_DIR / ".env")

MODELO_ID = "openai/gpt-oss-20b"

# O plano gratuito do Groq limita o gpt-oss-20b a 8.000 tokens por minuto (TPM).
# Poucos resultados por busca e poucas chamadas de ferramenta por agente mantêm
# cada requisição abaixo desse limite.
MAX_RESULTADOS_BUSCA = 5
LIMITE_CHAMADAS_FERRAMENTAS = 4
TENTATIVAS_API = 2  # retries do SDK do Groq para 429 por minuto (respeita o retry-after)


def obter_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")


def verificar_api_key() -> None:
    """Falha com mensagem clara se a GROQ_API_KEY não estiver configurada."""
    if not obter_api_key():
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. Crie um arquivo .env na raiz do projeto "
            "(veja .env.example) com GROQ_API_KEY=sua_chave."
        )


# ---------------------------------------------------------------------------
# Cota diária do Groq (TPD) e modelos reserva
# ---------------------------------------------------------------------------
# No plano gratuito, cada modelo tem a sua própria cota diária (200 mil tokens,
# janela móvel de 24 h). Quando um modelo esgota, os agentes passam para o
# próximo da lista. Configure com GROQ_MODEL_ID (principal) e
# GROQ_MODELOS_RESERVA (separados por vírgula; vazio desativa a reserva).
MODELOS_RESERVA_PADRAO = "openai/gpt-oss-120b"

_cota_trava = threading.Lock()
_cota_esgotada_ate: dict[str, float] = {}  # modelo -> timestamp em que a cota libera


def modelos_configurados() -> list[str]:
    principal = os.getenv("GROQ_MODEL_ID", MODELO_ID)
    reserva = os.getenv("GROQ_MODELOS_RESERVA", MODELOS_RESERVA_PADRAO)
    modelos = [principal] + [m.strip() for m in reserva.split(",") if m.strip()]
    return list(dict.fromkeys(modelos))


def segundos_ate_liberar(texto: str) -> float | None:
    """Lê o 'Please try again in 1h2m4.5s' das mensagens do Groq."""
    m = re.search(r"try again in ((?:\d+h)?(?:\d+m)?(?:[\d.]+s)?)", texto)
    if not m or not m.group(1):
        return None
    total = 0.0
    for valor, unidade in re.findall(r"([\d.]+)([hms])", m.group(1)):
        total += float(valor) * {"h": 3600, "m": 60, "s": 1}[unidade]
    return total


def registrar_cota_esgotada(modelo: str, segundos: float | None) -> None:
    with _cota_trava:
        _cota_esgotada_ate[modelo] = time.time() + (segundos if segundos is not None else 600)


def modelo_disponivel() -> str | None:
    """Primeiro modelo configurado com cota diária disponível (ou None)."""
    agora = time.time()
    with _cota_trava:
        return next((m for m in modelos_configurados() if _cota_esgotada_ate.get(m, 0) <= agora), None)


def situacao_cota() -> list[dict]:
    agora = time.time()
    with _cota_trava:
        return [
            {"modelo": m, "disponivel": _cota_esgotada_ate.get(m, 0) <= agora,
             "libera_em_s": max(0, round(_cota_esgotada_ate.get(m, 0) - agora))}
            for m in modelos_configurados()
        ]


def cota_diaria_esgotada(texto: str) -> bool:
    return "tokens per day" in texto or "(TPD)" in texto


def resumo_cota_esgotada() -> str:
    """Mensagem para quando todos os modelos estão sem cota."""
    estado = situacao_cota()
    proximo = min((e["libera_em_s"] for e in estado), default=0)
    minutos = max(1, round(proximo / 60))
    nomes = ", ".join(e["modelo"] for e in estado)
    return (
        f"Cota diária de tokens do Groq esgotada em todos os modelos configurados ({nomes}). "
        f"A próxima libera em ~{minutos} min. Adicione outros modelos em GROQ_MODELOS_RESERVA "
        "no .env ou use um plano maior do Groq."
    )


class CotaEsgotada(RuntimeError):
    """Todos os modelos configurados estão sem cota diária."""


class GroqTolerante(Groq):
    """Groq resiliente a dois problemas do plano gratuito.

    1. Cota diária (429 TPD): marca o modelo como esgotado (para todos os
       agentes) e troca para o próximo modelo reserva, sem esperar. Se não
       houver nenhum disponível, falha na hora em vez de insistir.
    2. Chamada de ferramenta inválida (400 `tool_use_failed`, ex.: web_search
       com {"id": "<url>"}): o Agno trata todo 400 como não repetível, mas a
       geração é aleatória e repetir quase sempre resolve.
    """

    def _escolher_modelo(self) -> None:
        if _cota_esgotada_ate.get(self.id, 0) > time.time():
            proximo = modelo_disponivel()
            if proximo is None:
                raise CotaEsgotada(resumo_cota_esgotada())
            self.id = proximo

    def invoke(self, *args, **kwargs):  # type: ignore[override]
        self._escolher_modelo()
        return super().invoke(*args, **kwargs)

    def invoke_stream(self, *args, **kwargs):  # type: ignore[override]
        self._escolher_modelo()
        return super().invoke_stream(*args, **kwargs)

    def _is_retryable_error(self, error) -> bool:  # type: ignore[override]
        texto = str(error)
        if cota_diaria_esgotada(texto):
            registrar_cota_esgotada(self.id, segundos_ate_liberar(texto))
            proximo = modelo_disponivel()
            if proximo is None:
                return False  # nenhuma reserva: não adianta insistir
            log_warning(f"Cota diária esgotada em {self.id}; trocando para {proximo}.")
            self.id = proximo
            return True
        if "tool_use_failed" in texto:
            return True
        return super()._is_retryable_error(error)


def criar_modelo() -> Groq:
    """Modelo Groq: o primeiro com cota disponível (GROQ_MODEL_ID + GROQ_MODELOS_RESERVA)."""
    return GroqTolerante(
        id=modelo_disponivel() or modelos_configurados()[0],
        api_key=obter_api_key(),
        max_retries=TENTATIVAS_API,  # erros 429 por minuto (SDK do Groq, respeita o retry-after)
        retries=len(modelos_configurados()) + 1,  # troca de modelo + chamadas de ferramenta inválidas
        delay_between_retries=2,
    )


class BuscaTolerante(WebSearchTools):
    """Busca que devolve uma mensagem em vez de levantar exceção.

    O ddgs levanta `DDGSException: No results found.` quando uma consulta não
    acha nada; o Agno registra o traceback inteiro e o agente perde a chamada.
    Aqui o agente recebe uma orientação para tentar outros termos.
    """

    def web_search(self, query: str, max_results: int = 5) -> str:
        """Use this function to search the web for a query.

        Args:
            query(str): The query to search for.
            max_results (optional, default=5): The maximum number of results to return.

        Returns:
            The search results from the web.
        """
        try:
            return super().web_search(query, max_results)
        except Exception as erro:  # noqa: BLE001
            return _sem_resultados(query, erro)

    def search_news(self, query: str, max_results: int = 5) -> str:
        """Use this function to get the latest news from the web.

        Args:
            query(str): The query to search for.
            max_results (optional, default=5): The maximum number of results to return.

        Returns:
            The latest news from the web.
        """
        try:
            return super().search_news(query, max_results)
        except Exception as erro:  # noqa: BLE001
            return _sem_resultados(query, erro)


def _sem_resultados(query: str, erro: Exception) -> str:
    return json.dumps(
        {"resultados": [], "aviso": f"Nenhum resultado para '{query}' ({erro}). Tente termos mais curtos, "
                                    "em outro idioma ou a outra ferramenta de busca."},
        ensure_ascii=False,
    )


def criar_busca() -> WebSearchTools:
    """Busca web/notícias via ddgs.

    O backend "duckduckgo" (usado pelo DuckDuckGoTools) parou de retornar
    resultados; "auto" alterna entre os backends disponíveis (bing, yahoo...).
    Pode ser trocado com a variável de ambiente BUSCA_BACKEND.
    """
    return BuscaTolerante(
        backend=os.getenv("BUSCA_BACKEND", "auto"),
        fixed_max_results=MAX_RESULTADOS_BUSCA,
        instructions=INSTRUCOES_BUSCA,
        add_instructions=True,
    )


INSTRUCOES_BUSCA = (
    "Ferramentas de busca: chame web_search ou search_news SEMPRE com o argumento "
    '"query" (texto da busca). Não é possível abrir URLs: para saber mais sobre um link, '
    "busque pelo título da matéria."
)


def carregar_skills() -> Skills:
    if not SKILLS_DIR.exists():
        raise FileNotFoundError(f"Skills não encontradas: {SKILLS_DIR}")
    return Skills(loaders=[LocalSkills(str(SKILLS_DIR))])


def ler_skill(nome: str) -> str:
    """Corpo de skills/<nome>/SKILL.md, sem o frontmatter YAML.

    Injetar só a skill que o agente usa economiza a requisição extra de
    get_skill_instructions e o catálogo de skills no prompt (tokens/minuto).
    """
    texto = (SKILLS_DIR / nome / "SKILL.md").read_text(encoding="utf-8")
    partes = re.split(r"^---\s*$", texto, maxsplit=2, flags=re.MULTILINE)
    corpo = partes[2] if len(partes) == 3 else texto
    return corpo.strip()


def diretorio_saida(versao: str) -> Path:
    caminho = OUTPUT_DIR / versao
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def criar_file_tools(versao: str) -> FileTools:
    return FileTools(
        base_dir=diretorio_saida(versao),
        enable_save_file=True,
        enable_read_file=True,
        enable_list_files=True,
    )


def contar_fontes(texto: str) -> int:
    """Conta fontes distintas em um dossiê de apuração.

    Usa a seção '## FONTES COLETADAS' (se existir) e retorna o maior valor entre
    veículos únicos em **negrito** e URLs únicas.
    """
    secao = texto

    match = re.search(
        r"##\s*FONTES COLETADAS(.*?)(##|$)",
        texto,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        secao = match.group(1)

    fontes_unicas = {f.strip().lower() for f in re.findall(r"\*\*(.*?)\*\*", secao)}
    urls_unicas = set(re.findall(r"https?://[^\s)]+", secao))

    return max(len(fontes_unicas), len(urls_unicas))


def mensagem_erro_amigavel(erro: str) -> str:
    """Traduz erros comuns da API do Groq para uma explicação acionável."""
    texto = str(erro)
    if "413" in texto or "Request too large" in texto:
        return (
            "A requisição ficou maior que o limite de tokens por minuto do plano do Groq "
            f"({texto[:200]}). Reduza o tema, use outro modelo (GROQ_MODEL_ID) ou um plano maior."
        )
    if texto.startswith("Cota diária de tokens do Groq esgotada"):
        return texto  # já é a mensagem amigável (CotaEsgotada)
    if cota_diaria_esgotada(texto):
        if modelo_disponivel() is None:
            return resumo_cota_esgotada()
        segundos = segundos_ate_liberar(texto)
        return (
            "Cota diária de tokens do Groq esgotada para este modelo"
            + (f"; libera em ~{max(1, round(segundos / 60))} min" if segundos else "")
            + ". Como a cota é por modelo, configure modelos reserva em GROQ_MODELOS_RESERVA no .env "
            "ou use um plano maior."
        )
    if "429" in texto or "rate_limit" in texto:
        return (
            "Limite de uso da API do Groq atingido (tokens/requisições por minuto ou por dia). "
            f"Aguarde um pouco e tente novamente. Detalhe: {texto[:200]}"
        )
    if "401" in texto or "invalid_api_key" in texto.lower():
        return "GROQ_API_KEY inválida. Confira a chave no arquivo .env."
    return texto
