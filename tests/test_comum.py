import pytest

from agente import comum

DOSSIE_3_FONTES = """## FONTES COLETADAS
- **Folha**: Título A (https://folha.com/a)
- **G1**: Título B (https://g1.com/b)
- **Reuters**: Título C (https://reuters.com/c)

## LINHA DO TEMPO
- **Evento fora da seção** (https://ignorado.com)
"""


def test_contar_fontes_conta_apenas_secao_de_fontes():
    assert comum.contar_fontes(DOSSIE_3_FONTES) == 3


def test_contar_fontes_ignora_duplicatas_e_maiusculas():
    texto = "## FONTES COLETADAS\n- **Folha**: x\n- **folha**: y\n- **G1**: z\n"
    assert comum.contar_fontes(texto) == 2


def test_contar_fontes_usa_urls_quando_nao_ha_negrito():
    texto = "Fontes: https://a.com/1 https://b.com/2 https://c.com/3 https://a.com/1"
    assert comum.contar_fontes(texto) == 3


def test_contar_fontes_texto_vazio():
    assert comum.contar_fontes("") == 0


def test_verificar_api_key_sem_chave(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        comum.verificar_api_key()


def test_verificar_api_key_com_chave(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "x")
    comum.verificar_api_key()


def test_caminhos_apontam_para_raiz_do_repositorio():
    assert (comum.BASE_DIR / "pyproject.toml").exists()
    assert comum.SKILLS_DIR == comum.BASE_DIR / "skills"
    assert comum.SKILLS_DIR.is_dir()


def test_diretorio_saida_cria_pasta(monkeypatch, tmp_path):
    monkeypatch.setattr(comum, "OUTPUT_DIR", tmp_path)
    pasta = comum.diretorio_saida("VX")
    assert pasta == tmp_path / "VX"
    assert pasta.is_dir()
