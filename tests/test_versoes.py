"""Testes de estrutura das versões e das funções determinísticas."""

import re

import pytest
from agno.tools.websearch import WebSearchTools
from agno.workflow.types import StepInput, StepOutput

from agente import agente_curador, agente_curador_v2
from agente import agente_curador_v3 as v3
from agente import agente_curador_v4 as v4
from agente import agente_curador_v5 as v5
from agente.comum import MAX_RESULTADOS_BUSCA, SKILLS_DIR
from agente.ferramentas_mercado import MercadoFinanceiroTools

DOSSIE_OK = "## FONTES COLETADAS\n- **A**: x\n- **B**: y\n- **C**: z\n"
DOSSIE_FRACO = "## FONTES COLETADAS\n- **A**: x\n"

TODOS_OS_AGENTES = [
    agente_curador.agente_noticias,
    agente_curador_v2.pesquisador, agente_curador_v2.apurador,
    agente_curador_v2.verificador, agente_curador_v2.redator,
    v3.pesquisador, v3.apurador, v3.verificador, v3.redator,
    v4.pesquisador_nacional, v4.pesquisador_internacional,
    v4.apurador, v4.verificador, v4.redator,
    v5.pesquisador_mercado_nacional, v5.pesquisador_mercado_global,
    v5.apurador, v5.verificador, v5.analista_mercado, v5.redator,
]


def _nomes(workflow):
    return [s.name for s in workflow.steps]


# --- Estrutura -------------------------------------------------------------

def test_v2_estrutura():
    assert _nomes(agente_curador_v2.workflow) == ["pesquisa", "apuracao", "verificacao", "redacao"]


def test_v3_estrutura():
    assert _nomes(v3.news_curator_workflow) == ["pesquisa", "apuracao_loop", "verificacao", "redacao"]


def test_v4_estrutura():
    assert _nomes(v4.research_pipeline_workflow) == [
        "pesquisa", "apuracao_loop", "validacao_fontes", "verificacao", "redacao", "exportacao",
    ]
    assert len(v4.research_team.members) == 2


def test_v5_estrutura():
    assert _nomes(v5.investor_workflow) == [
        "pesquisa", "apuracao_loop", "validacao_fontes", "verificacao",
        "analise_mercado", "consolidacao", "redacao", "exportacao",
    ]
    assert len(v5.research_team.members) == 2


def test_v5_injeta_a_skill_nas_instrucoes_sem_tool_de_skills():
    """Economia de tokens: sem get_skill_instructions; o texto da skill vai no prompt."""
    from agente.comum import ler_skill

    esperado = [
        (v5.pesquisador_mercado_nacional, "pesquisa-noticias"),
        (v5.apurador, "apuracao-fontes"),
        (v5.verificador, "verificacao-factual"),
        (v5.analista_mercado, "analise-mercado"),
        (v5.redator, "redacao-jornalistica"),
    ]
    for agente, skill in esperado:
        assert agente.skills is None, agente.name
        prompt = "\n".join(agente.instructions)
        assert ler_skill(skill) in prompt, agente.name
        assert "name:" not in ler_skill(skill)  # frontmatter removido


def test_v5_agentes_com_dados_de_mercado():
    for agente in (v5.verificador, v5.analista_mercado):
        assert any(isinstance(t, MercadoFinanceiroTools) for t in agente.tools)


@pytest.mark.parametrize("modulo", [v3, v4, v5])
def test_loop_de_apuracao_configurado(modulo):
    assert [s.name for s in modulo.apuracao_loop.steps] == ["apuracao"]
    assert modulo.apuracao_loop.max_iterations == modulo.MAX_TENTATIVAS_APURACAO
    assert modulo.apuracao_loop.end_condition is modulo.fontes_suficientes


# --- Busca e limites (causa do erro 413 do Groq) ---------------------------

def test_nenhum_agente_usa_backend_duckduckgo_e_buscas_sao_limitadas():
    for agente in TODOS_OS_AGENTES:
        for tool in agente.tools or []:
            if isinstance(tool, WebSearchTools):
                assert tool.backend != "duckduckgo", agente.name
                assert tool.fixed_max_results == MAX_RESULTADOS_BUSCA, agente.name


@pytest.mark.parametrize("modulo", [v4, v5])
def test_agentes_com_ferramentas_tem_limite_de_chamadas(modulo):
    for nome in dir(modulo):
        agente = getattr(modulo, nome)
        if type(agente).__name__ == "Agent" and agente.tools:
            assert agente.tool_call_limit, agente.name


# --- Funções determinísticas -----------------------------------------------

@pytest.mark.parametrize("modulo", [v3, v4, v5])
def test_fontes_suficientes(modulo):
    assert modulo.fontes_suficientes([]) is False
    assert modulo.fontes_suficientes([StepOutput(content=DOSSIE_FRACO)]) is False
    assert modulo.fontes_suficientes([StepOutput(content=DOSSIE_OK)]) is True
    # Só a última iteração do loop importa
    saidas = [StepOutput(content=DOSSIE_OK), StepOutput(content=DOSSIE_FRACO)]
    assert modulo.fontes_suficientes(saidas) is False


@pytest.mark.parametrize("modulo", [v4, v5])
def test_validar_fontes(modulo):
    ok = modulo.validar_fontes(StepInput(previous_step_content=DOSSIE_OK))
    assert ok.content.startswith("## VALIDAÇÃO DE FONTES")
    assert "APROVADO" in ok.content
    assert DOSSIE_OK in ok.content  # o dossiê é repassado adiante

    fraco = modulo.validar_fontes(StepInput(previous_step_content=DOSSIE_FRACO))
    assert "INSUFICIENTE" in fraco.content
    assert "apenas 1" in fraco.content


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


@pytest.mark.parametrize("modulo", [v4, v5])
def test_exportar_markdown(modulo, monkeypatch, tmp_path):
    monkeypatch.setattr(modulo, "output_dir", tmp_path)
    saida = modulo.exportar_markdown(
        StepInput(input="Selic e renda fixa", previous_step_content="# Matéria\n\nTexto.")
    )
    arquivos = list(tmp_path.glob("materia_selic_e_renda_fixa_*.md"))
    assert len(arquivos) == 1
    assert re.fullmatch(r"materia_selic_e_renda_fixa_\d{4}-\d{2}-\d{2}\.md", arquivos[0].name)
    assert arquivos[0].read_text(encoding="utf-8") == "# Matéria\n\nTexto.\n"
    assert saida.content.startswith("# Matéria")
    assert "Matéria salva em" in saida.content


def test_v5_consolidacao_junta_verificacao_e_analise():
    entrada = StepInput(
        input="tema",
        previous_step_content="## PAINEL DE MERCADO\nPETR4 R$ 44,84",
        previous_step_outputs={"verificacao": StepOutput(step_name="verificacao", content="## FATOS CONFIRMADOS\nX")},
    )
    saida = v5.consolidar_para_redacao(entrada).content
    assert "# RELATÓRIO DE VERIFICAÇÃO" in saida and "## FATOS CONFIRMADOS" in saida
    assert "# ANÁLISE DE MERCADO" in saida and "PETR4 R$ 44,84" in saida
    assert saida.index("VERIFICAÇÃO") < saida.index("ANÁLISE")


# --- Skills ----------------------------------------------------------------

def test_skills_citadas_nas_instrucoes_existem():
    """Toda skill citada como skill 'nome' nas instruções dos agentes deve existir."""
    existentes = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    citadas = set()
    for agente in TODOS_OS_AGENTES:
        for linha in agente.instructions:
            citadas |= set(re.findall(r"skill '([a-z-]+)'", linha))
    assert "analise-mercado" in citadas
    assert citadas <= existentes
