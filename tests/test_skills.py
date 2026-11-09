import re

import pytest

from agente.comum import SKILLS_DIR

SKILLS_ESPERADAS = {
    "pesquisa-noticias",
    "apuracao-fontes",
    "verificacao-factual",
    "redacao-jornalistica",
    "analise-mercado",
}


def _frontmatter(texto: str) -> str:
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", texto, re.DOTALL)
    assert match, "SKILL.md sem frontmatter YAML"
    return match.group(1)


def test_todas_as_skills_existem():
    pastas = {p.name for p in SKILLS_DIR.iterdir() if p.is_dir()}
    assert SKILLS_ESPERADAS <= pastas


@pytest.mark.parametrize("nome", sorted(SKILLS_ESPERADAS))
def test_frontmatter_da_skill(nome):
    texto = (SKILLS_DIR / nome / "SKILL.md").read_text(encoding="utf-8")
    fm = _frontmatter(texto)
    assert re.search(rf"^name:\s*{re.escape(nome)}\s*$", fm, re.MULTILINE)
    assert re.search(r"^description:\s*\S", fm, re.MULTILINE)
    assert re.search(r'version:\s*"\d+\.\d+\.\d+"', fm)


def test_apuracao_define_secao_usada_por_contar_fontes():
    texto = (SKILLS_DIR / "apuracao-fontes" / "SKILL.md").read_text(encoding="utf-8")
    assert "## FONTES COLETADAS" in texto


def test_analise_mercado_cita_ferramentas_que_existem():
    from agente.ferramentas_mercado import MercadoFinanceiroTools

    texto = (SKILLS_DIR / "analise-mercado" / "SKILL.md").read_text(encoding="utf-8")
    citadas = set(re.findall(r"`([a-z_]+)`", texto))
    assert citadas, "a skill deve citar as ferramentas pelo nome"
    assert citadas <= set(MercadoFinanceiroTools().functions)


def test_redacao_tem_secao_do_investidor_e_aviso():
    texto = (SKILLS_DIR / "redacao-jornalistica" / "SKILL.md").read_text(encoding="utf-8")
    assert "O que isso significa para o investidor" in texto
    assert "não constitui recomendação de investimento" in texto
