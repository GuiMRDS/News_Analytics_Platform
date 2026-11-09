import json

import pytest

from agente import ferramentas_mercado as fm


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("petr4", "PETR4.SA"),
        (" VALE3 ", "VALE3.SA"),
        ("MXRF11", "MXRF11.SA"),  # FII
        ("TAEE11", "TAEE11.SA"),  # unit
        ("AAPL34", "AAPL34.SA"),  # BDR
        ("AAPL", "AAPL"),  # ação dos EUA
        ("ibov", "^BVSP"),
        ("dólar", "BRL=X"),
        ("bitcoin", "BTC-USD"),
        ("PETR4.SA", "PETR4.SA"),
    ],
)
def test_normalizar_ticker(entrada, esperado):
    assert fm.normalizar_ticker(entrada) == esperado


@pytest.mark.parametrize(
    ("dias", "aliquota"),
    [(1, 0.225), (180, 0.225), (181, 0.20), (360, 0.20), (361, 0.175), (720, 0.175), (721, 0.15)],
)
def test_tabela_regressiva_ir(dias, aliquota):
    assert fm.aliquota_ir(dias) == aliquota


def test_simular_renda_fixa_12_meses_com_ir():
    r = fm.simular_renda_fixa(10_000, 12.0, 12)
    assert r["valor_bruto"] == 11_200.00
    assert r["rendimento_bruto"] == 1_200.00
    assert r["aliquota_ir_pct"] == 20.0  # 360 dias
    assert r["imposto_renda"] == 240.00
    assert r["valor_liquido"] == 10_960.00
    assert r["rentabilidade_liquida_pct"] == 9.6


def test_simular_renda_fixa_isento():
    r = fm.simular_renda_fixa(10_000, 12.0, 12, isento_ir=True)
    assert r["imposto_renda"] == 0
    assert r["valor_liquido"] == r["valor_bruto"]


def test_simular_renda_fixa_valores_invalidos():
    with pytest.raises(ValueError):
        fm.simular_renda_fixa(0, 10, 12)
    with pytest.raises(ValueError):
        fm.simular_renda_fixa(1000, 10, 0)


def test_resumir_historico():
    # 21 pregões atrás o preço era 100; ontem, 110; hoje, 121
    r = fm.resumir_historico([100.0] * 231 + [110.0] * 20 + [121.0])
    assert r["preco"] == 121.0
    assert r["variacao_dia_pct"] == 10.0
    assert r["variacao_mes_pct"] == 21.0
    assert r["variacao_12m_pct"] == 21.0
    assert r["maxima_periodo"] == 121.0
    assert r["minima_periodo"] == 100.0


def test_resumir_historico_curto_e_vazio():
    r = fm.resumir_historico([10.0, 11.0])
    assert r["variacao_dia_pct"] == 10.0
    assert r["variacao_mes_pct"] is None
    assert r["variacao_12m_pct"] is None
    with pytest.raises(ValueError):
        fm.resumir_historico([])


def test_obter_cotacao_b3():
    c = fm.obter_cotacao("petr4")
    assert c["ticker"] == "PETR4.SA"
    assert c["moeda"] == "BRL"
    assert c["preco"] == 125.1
    assert c["fonte"] == "Yahoo Finance"


def test_obter_cotacao_sem_dados_nao_levanta():
    c = fm.obter_cotacao("INEXISTENTE")
    assert "erro" in c


def test_obter_indicadores():
    ind = fm.obter_indicadores()
    assert ind["selic_meta_aa"]["valor"] == 13.75
    assert ind["cdi_aa"]["valor"] == 13.65
    assert ind["ipca_12m"]["valor"] == 4.58
    assert ind["dolar_ptax"]["valor"] == 5.5013
    assert "Banco Central" in ind["fonte"]


def test_obter_indicadores_com_falha_parcial(monkeypatch):
    def falha_no_ipca(codigo):
        if codigo == 13522:
            raise TimeoutError("BCB fora do ar")
        return {"valor": 1.0, "data": "01/01/2026"}

    monkeypatch.setattr(fm, "_buscar_serie_bcb", falha_no_ipca)
    ind = fm.obter_indicadores()
    assert "erro" in ind["ipca_12m"]
    assert ind["selic_meta_aa"]["valor"] == 1.0


def test_obter_panorama():
    p = fm.obter_panorama()
    assert set(p) == set(fm.PANORAMA)
    assert p["Ibovespa"]["ticker"] == "^BVSP"
    assert p["Ibovespa"]["preco"] == 125.1


def test_toolkit_registra_ferramentas_e_retorna_json():
    tk = fm.MercadoFinanceiroTools()
    assert set(tk.functions) == {
        "cotacao_ativo",
        "indicadores_economicos",
        "panorama_mercado",
        "simular_investimento_renda_fixa",
    }
    assert json.loads(tk.cotacao_ativo("VALE3"))["ticker"] == "VALE3.SA"
    assert json.loads(tk.indicadores_economicos())["selic_meta_aa"]["valor"] == 13.75
    assert "erro" in json.loads(tk.simular_investimento_renda_fixa(-1, 10, 12))
