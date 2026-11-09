"""Configuração e utilitários compartilhados entre as versões do curador."""

import os
import re
from pathlib import Path

from dotenv import load_dotenv
from agno.models.groq import Groq
from agno.skills import Skills, LocalSkills
from agno.tools.file import FileTools

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"
OUTPUT_DIR = BASE_DIR / "output"

load_dotenv(BASE_DIR / ".env")

MODELO_ID = "openai/gpt-oss-20b"


def obter_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")


def verificar_api_key() -> None:
    """Falha com mensagem clara se a GROQ_API_KEY não estiver configurada."""
    if not obter_api_key():
        raise RuntimeError(
            "GROQ_API_KEY não encontrada. Crie um arquivo .env na raiz do projeto "
            "(veja .env.example) com GROQ_API_KEY=sua_chave."
        )


def criar_modelo() -> Groq:
    return Groq(id=MODELO_ID, api_key=obter_api_key())


def carregar_skills() -> Skills:
    if not SKILLS_DIR.exists():
        raise FileNotFoundError(f"Skills não encontradas: {SKILLS_DIR}")
    return Skills(loaders=[LocalSkills(str(SKILLS_DIR))])


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
