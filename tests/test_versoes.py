"""Testes de estrutura das versões e das funções determinísticas."""

import re

import pytest
from agno.workflow.types import StepInput, StepOutput

from agente import agente_curador_v3 as v3
from agente import agente_curador_v4 as v4
from agente.comum import SKILLS_DIR

DOSSIE_OK = "## FONTES COLETADAS\n- **A**: x\n- **B**: y\n- **C**: z\n"
DOSSIE_FRACO = "## FONTES COLETADAS\n- **A**: x\n"


# --- V3 -------------------------------------------------------------------

def test_v3_estrutura():
    assert [s.name for s in v3.news_curator_workflow.steps] == [
        "pesquisa", "apuracao_loop", "verificacao", "redacao",
    ]


@pytest.mark.parametrize("modulo", [v3, v4])
def test_fontes_suficientes(modulo):
    assert modulo.fontes_suficientes([]) is False
    assert modulo.fontes_suficientes([StepOutput(content=DOSSIE_FRACO)]) is False
    assert modulo.fontes_suficientes([StepOutput(content=DOSSIE_OK)]) is True
    # Só a última iteração do loop importa
    saidas = [StepOutput(content=DOSSIE_OK), StepOutput(content=DOSSIE_FRACO)]
    assert modulo.fontes_suficientes(saidas) is False


@pytest.mark.parametrize("modulo", [v3, v4])
def test_loop_de_apuracao_configurado(modulo):
    assert [s.name for s in modulo.apuracao_loop.steps] == ["apuracao"]
    assert modulo.apuracao_loop.max_iterations == modulo.MAX_TENTATIVAS_APURACAO
    assert modulo.apuracao_loop.end_condition is modulo.fontes_suficientes


# --- V4 -------------------------------------------------------------------

def test_v4_estrutura():
    assert [s.name for s in v4.research_pipeline_workflow.steps] == [
        "pesquisa", "apuracao_loop", "validacao_fontes",
        "verificacao", "redacao", "exportacao",
    ]
    assert v4.pesquisa_step.team is v4.research_team
    assert len(v4.research_team.members) == 2


def test_validar_fontes_aprovado():
    saida = v4.validar_fontes(StepInput(previous_step_content=DOSSIE_OK))
    assert saida.content.startswith("## VALIDAÇÃO DE FONTES")
    assert "APROVADO" in saida.content
    assert DOSSIE_OK in saida.content  # o dossiê é repassado adiante


def test_validar_fontes_insuficiente():
    saida = v4.validar_fontes(StepInput(previous_step_content=DOSSIE_FRACO))
    assert "INSUFICIENTE" in saida.content
    assert "apenas 1" in saida.content


@pytest.mark.parametrize(
    ("tema", "esperado"),
    [
        ("Inteligência Artificial no Brasil?", "inteligencia_artificial_no_brasil"),
        ("  !!!  ", "materia"),
        ("a" * 80, "a" * 50),
    ],
)
def test_slug(tema, esperado):
    assert v4._slug(tema) == esperado


def test_exportar_markdown(monkeypatch, tmp_path):
    monkeypatch.setattr(v4, "output_dir", tmp_path)
    saida = v4.exportar_markdown(
        StepInput(input="Economia brasileira", previous_step_content="# Matéria\n\nTexto.")
    )
    arquivos = list(tmp_path.glob("materia_economia_brasileira_*.md"))
    assert len(arquivos) == 1
    assert re.fullmatch(r"materia_economia_brasileira_\d{4}-\d{2}-\d{2}\.md", arquivos[0].name)
    assert arquivos[0].read_text(encoding="utf-8") == "# Matéria\n\nTexto.\n"
    assert saida.content.startswith("# Matéria")
    assert "Matéria salva em" in saida.content


# --- Todas as versões ----------------------------------------------------

def test_skills_citadas_nas_instrucoes_existem():
    """Toda skill citada como skill 'nome' nas instruções dos agentes deve existir."""
    from agente import agente_curador, agente_curador_v2

    existentes = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    agentes = [
        agente_curador.agente_noticias,
        agente_curador_v2.pesquisador, agente_curador_v2.apurador,
        agente_curador_v2.verificador, agente_curador_v2.redator,
        v3.pesquisador, v3.apurador, v3.verificador, v3.redator,
        v4.pesquisador_nacional, v4.pesquisador_internacional,
        v4.apurador, v4.verificador, v4.redator,
    ]
    citadas = set()
    for agente in agentes:
        for linha in agente.instructions:
            citadas |= set(re.findall(r"skill '([a-z-]+)'", linha))
    assert citadas, "nenhuma skill citada nas instruções"
    assert citadas <= existentes
