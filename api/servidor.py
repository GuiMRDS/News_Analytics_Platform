"""Servidor HTTP: API JSON + front-end Quantum Terminal (HTML/CSS/JS puro).

Execute a partir da raiz:  uv run python -m api   →  http://127.0.0.1:8000
"""

import asyncio
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agente import ferramentas_mercado as mercado
from agente.comum import (
    BASE_DIR,
    OUTPUT_DIR,
    modelo_disponivel,
    modelos_configurados,
    obter_api_key,
    resumo_cota_esgotada,
    situacao_cota,
)
from api import registry
from api.execucao import GerenciadorDeTarefas, etapas_do_executor

WEB_DIR = BASE_DIR / "web"
MAX_TICKERS = 20
TTL_PAINEL = 900  # 15 min
TTL_COTACAO = 300  # 5 min
TTL_HISTORICO = 300

app = FastAPI(title="News Analytics Platform", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
tarefas = GerenciadorDeTarefas()


# ---------------------------------------------------------------------------
# Cache simples em memória (dados de mercado não precisam ser instantâneos)
# ---------------------------------------------------------------------------

def _tem_erro(valor: Any) -> bool:
    """True se o dicionário (ou algum dicionário aninhado) traz a chave 'erro'."""
    if isinstance(valor, dict):
        return "erro" in valor or any(_tem_erro(v) for v in valor.values())
    return False


class Cache:
    def __init__(self) -> None:
        self._dados: dict[str, tuple[float, Any]] = {}
        self._trava = threading.Lock()

    def consultar(self, chave: str, ttl: int) -> Any:
        with self._trava:
            item = self._dados.get(chave)
        return item[1] if item and time.time() - item[0] < ttl else None

    def guardar(self, chave: str, valor: Any) -> None:
        # Não guarda respostas com erro (nem parciais), para tentar de novo na próxima chamada
        if not _tem_erro(valor):
            with self._trava:
                self._dados[chave] = (time.time(), valor)

    def obter(self, chave: str, ttl: int, produzir: Callable[[], Any]) -> Any:
        valor = self.consultar(chave, ttl)
        if valor is None:
            valor = produzir()
            self.guardar(chave, valor)
        return valor

    def limpar(self) -> None:
        with self._trava:
            self._dados.clear()


cache = Cache()


# ---------------------------------------------------------------------------
# Sistema
# ---------------------------------------------------------------------------

@app.get("/api/status")
def status() -> dict:
    return {
        "api_key_configurada": bool(obter_api_key()),
        "modelo": modelo_disponivel() or modelos_configurados()[0],
        "cota": situacao_cota(),
        "busca_backend": os.getenv("BUSCA_BACKEND", "auto"),
        "versao_padrao": registry.VERSAO_PADRAO,
        "tarefas_em_andamento": tarefas.em_andamento(),
    }


@app.get("/api/versoes")
def versoes() -> dict:
    return {"padrao": registry.VERSAO_PADRAO, "versoes": [v.publico() for v in registry.VERSOES.values()]}


# ---------------------------------------------------------------------------
# Mercado
# ---------------------------------------------------------------------------

@app.get("/api/mercado")
def painel_mercado() -> dict:
    return {
        "panorama": cache.obter("panorama", TTL_PAINEL, mercado.obter_panorama),
        "indicadores": cache.obter("indicadores", TTL_PAINEL, mercado.obter_indicadores),
        "atualizado_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


@app.get("/api/mercado/cotacoes")
def cotacoes(tickers: str = Query(..., description="Lista separada por vírgula, ex.: PETR4,VALE3")) -> dict:
    lista = [t.strip() for t in tickers.split(",") if t.strip()]
    if not lista:
        raise HTTPException(400, "Informe ao menos um ticker.")
    if len(lista) > MAX_TICKERS:
        raise HTTPException(400, f"Máximo de {MAX_TICKERS} tickers por consulta.")
    entradas = [t.upper() for t in lista]
    em_cache = {t: cache.consultar(f"cot:{t}", TTL_COTACAO) for t in entradas}
    faltantes = [t for t, v in em_cache.items() if v is None]
    if faltantes:  # uma única consulta ao Yahoo para todos os que faltam
        for t, cotacao in zip(faltantes, mercado.obter_cotacoes(faltantes)):
            em_cache[t] = cotacao
            cache.guardar(f"cot:{t}", cotacao)
    return {"cotacoes": [{"entrada": t, **em_cache[t]} for t in entradas]}


@app.get("/api/mercado/historico/{ticker}")
def historico(ticker: str, periodo: str = "1mo") -> dict:
    if periodo not in mercado.PERIODOS_GRAFICO:
        raise HTTPException(400, f"Período inválido. Use: {', '.join(mercado.PERIODOS_GRAFICO)}.")
    return cache.obter(f"hist:{ticker.upper()}:{periodo}", TTL_HISTORICO, lambda: mercado.obter_historico(ticker, periodo))


class Simulacao(BaseModel):
    valor: float = Field(gt=0, le=1_000_000_000)
    taxa_anual_pct: float = Field(gt=0, le=100)
    meses: int = Field(gt=0, le=600)
    isento_ir: bool = False


@app.post("/api/simulacao/renda-fixa")
def simulacao_renda_fixa(dados: Simulacao) -> dict:
    return mercado.simular_renda_fixa(dados.valor, dados.taxa_anual_pct, dados.meses, dados.isento_ir)


# ---------------------------------------------------------------------------
# Perguntas aos agentes (execução em segundo plano + Server-Sent Events)
# ---------------------------------------------------------------------------

class Pergunta(BaseModel):
    tema: str = Field(min_length=3, max_length=500)
    versao: str = registry.VERSAO_PADRAO


@app.post("/api/perguntas", status_code=202)
def criar_pergunta(pergunta: Pergunta) -> dict:
    if pergunta.versao not in registry.VERSOES:
        raise HTTPException(400, f"Versão desconhecida: {pergunta.versao}")
    if not obter_api_key():
        raise HTTPException(503, "GROQ_API_KEY não configurada. Crie o arquivo .env (veja .env.example).")
    if modelo_disponivel() is None:
        # Todos os modelos sem cota diária: avisa na hora em vez de rodar um pipeline que vai falhar
        raise HTTPException(429, resumo_cota_esgotada())
    executor = registry.carregar_workflow(pergunta.versao)
    tarefa = tarefas.criar(pergunta.tema.strip(), pergunta.versao, executor)
    return {"id": tarefa.id, "versao": tarefa.versao, "etapas": etapas_do_executor(executor)}


@app.get("/api/perguntas/{tarefa_id}")
def estado_pergunta(tarefa_id: str) -> dict:
    tarefa = tarefas.obter(tarefa_id)
    if not tarefa:
        raise HTTPException(404, "Pergunta não encontrada.")
    return tarefa.resumo()


@app.post("/api/perguntas/{tarefa_id}/cancelar")
def cancelar_pergunta(tarefa_id: str) -> dict:
    """Cancela a pesquisa: interrompe os agentes em execução e não avança para as próximas etapas."""
    tarefa = tarefas.obter(tarefa_id)
    if not tarefa:
        raise HTTPException(404, "Pergunta não encontrada.")
    if not tarefa.cancelar():
        raise HTTPException(409, "Esta pergunta já terminou ou já foi cancelada.")
    return {"id": tarefa.id, "cancelada": True}


@app.get("/api/perguntas/{tarefa_id}/eventos")
async def eventos_pergunta(tarefa_id: str) -> StreamingResponse:
    tarefa = tarefas.obter(tarefa_id)
    if not tarefa:
        raise HTTPException(404, "Pergunta não encontrada.")

    async def fluxo():
        indice, ultimo_envio = 0, time.time()
        while True:
            novos = tarefa.eventos_desde(indice)
            for evento in novos:
                yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"
            indice += len(novos)
            if novos:
                ultimo_envio = time.time()
            if tarefa.concluida and not tarefa.eventos_desde(indice):
                break
            if time.time() - ultimo_envio > 15:
                yield ": ping\n\n"  # mantém a conexão viva durante etapas longas
                ultimo_envio = time.time()
            await asyncio.sleep(0.25)

    return StreamingResponse(fluxo(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------------------------------------------------------------------
# Matérias salvas em output/
# ---------------------------------------------------------------------------

_VERSAO_OK = re.compile(r"^V\d+$")
_ARQUIVO_OK = re.compile(r"^[\w.\-]+\.md$")


def _titulo(caminho: Path) -> str:
    try:
        with caminho.open(encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith(("⚠️", "---", ">")):
                    return linha.lstrip("#").strip().strip("*")[:160]
    except OSError:
        pass
    return caminho.stem


@app.get("/api/materias")
def listar_materias(limite: int = Query(50, ge=1, le=200)) -> dict:
    arquivos = [p for p in OUTPUT_DIR.glob("V*/*.md") if p.is_file()] if OUTPUT_DIR.exists() else []
    arquivos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "materias": [
            {
                "versao": p.parent.name,
                "arquivo": p.name,
                "titulo": _titulo(p),
                "modificado_em": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(p.stat().st_mtime)),
                "tamanho": p.stat().st_size,
            }
            for p in arquivos[:limite]
        ]
    }


@app.get("/api/materias/{versao}/{arquivo}")
def ler_materia(versao: str, arquivo: str) -> dict:
    if not _VERSAO_OK.match(versao) or not _ARQUIVO_OK.match(arquivo):
        raise HTTPException(400, "Caminho inválido.")
    caminho = (OUTPUT_DIR / versao / arquivo).resolve()
    if OUTPUT_DIR.resolve() not in caminho.parents or not caminho.is_file():
        raise HTTPException(404, "Matéria não encontrada.")
    return {"versao": versao, "arquivo": arquivo, "titulo": _titulo(caminho), "markdown": caminho.read_text(encoding="utf-8")}


# ---------------------------------------------------------------------------
# Front-end
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
