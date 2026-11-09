"""Configuração e utilitários compartilhados entre as versões do curador."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from agno.models.groq import Groq
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
TENTATIVAS_API = 5  # retries do cliente Groq para erros 429 (respeita o retry-after)


def obter_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")


def verificar_api_key() -> None:
    """Falha com mensagem clara se a GROQ_API_KEY não estiver configurada."""
    if not obter_api_key():
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. Crie um arquivo .env na raiz do projeto "
            "(veja .env.example) com GROQ_API_KEY=sua_chave."
        )


class GroqTolerante(Groq):
    """Groq que repete a requisição quando o modelo gera uma chamada de ferramenta inválida.

    O gpt-oss às vezes chama ferramentas com argumentos fora do schema (ex.:
    web_search com {"id": "<url>"} em vez de "query"). O Groq responde 400
    `tool_use_failed` e o Agno trata todo 400 como não repetível, o que derruba
    o agente. A geração é aleatória: repetir quase sempre resolve.
    """

    def _is_retryable_error(self, error) -> bool:  # type: ignore[override]
        if "tool_use_failed" in str(error):
            return True
        return super()._is_retryable_error(error)


def criar_modelo() -> Groq:
    """Modelo Groq. Pode ser trocado com a variável de ambiente GROQ_MODEL_ID."""
    return GroqTolerante(
        id=os.getenv("GROQ_MODEL_ID", MODELO_ID),
        api_key=obter_api_key(),
        max_retries=TENTATIVAS_API,  # erros 429 (SDK do Groq)
        retries=2,  # chamadas de ferramenta inválidas (Agno)
        delay_between_retries=2,
    )


def criar_busca() -> WebSearchTools:
    """Busca web/notícias via ddgs.

    O backend "duckduckgo" (usado pelo DuckDuckGoTools) parou de retornar
    resultados; "auto" alterna entre os backends disponíveis (bing, yahoo...).
    Pode ser trocado com a variável de ambiente BUSCA_BACKEND.
    """
    return WebSearchTools(
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
    if "tokens per day" in texto or "(TPD)" in texto:
        espera = re.search(r"try again in ([\dhms.]+)", texto)
        return (
            "Cota diária de tokens do Groq esgotada para este modelo"
            + (f"; libera em {espera.group(1)}" if espera else "")
            + ". Como a cota é por modelo, dá para trocar GROQ_MODEL_ID no .env "
            "(ex.: openai/gpt-oss-120b) ou usar um plano maior."
        )
    if "429" in texto or "rate_limit" in texto:
        return (
            "Limite de uso da API do Groq atingido (tokens/requisições por minuto ou por dia). "
            f"Aguarde um pouco e tente novamente. Detalhe: {texto[:200]}"
        )
    if "401" in texto or "invalid_api_key" in texto.lower():
        return "GROQ_API_KEY inválida. Confira a chave no arquivo .env."
    return texto
