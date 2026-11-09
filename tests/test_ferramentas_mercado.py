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


def test_parsing_spark_em_lote(monkeypatch, funcoes_reais):
    """Formato real do endpoint spark (valores None são descartados)."""
    urls = []

    def resposta(url):
        urls.append(url)
        return {"PETR4.SA": {"timestamp": [1, 2, 3], "close": [44.1, None, 45.18]}, "^BVSP": {"timestamp": [1], "close": [171119.6]}}

    monkeypatch.setattr(fm, "_yahoo_json", resposta)
    series = funcoes_reais["_historicos_lote"](["PETR4.SA", "^BVSP"], "1y")
    assert series == {"PETR4.SA": [44.1, 45.18], "^BVSP": [171119.6]}
    assert len(urls) == 1 and "symbols=PETR4.SA,%5EBVSP" in urls[0] and "range=1y" in urls[0]


def test_spark_divide_em_lotes_de_20(monkeypatch, funcoes_reais):
    chamadas = []
    monkeypatch.setattr(fm, "_yahoo_json", lambda url: chamadas.append(url) or {})
    funcoes_reais["_historicos_lote"]([f"T{i}" for i in range(45)], "1y")
    assert len(chamadas) == 3


def test_parsing_chart_intradiario(monkeypatch, funcoes_reais):
    """Formato real do endpoint chart; horários convertidos para o fuso da bolsa."""
    monkeypatch.setattr(fm, "_yahoo_json", lambda url: {"chart": {"result": [{
        "meta": {"gmtoffset": -10800, "currency": "BRL"},
        "timestamp": [1794229200, 1794229500, 1794229800],
        "indicators": {"quote": [{"close": [170966.0, None, 171119.6]}]},
    }]}})
    serie = funcoes_reais["_serie"]("^BVSP", "1d", "5m")
    assert [v for _, v in serie] == [170966.0, 171119.6]
    assert serie[0][0].endswith("-03:00")


def test_chart_sem_resultado(monkeypatch, funcoes_reais):
    monkeypatch.setattr(fm, "_yahoo_json", lambda url: {"chart": {"result": None, "error": {"code": "Not Found"}}})
    assert funcoes_reais["_serie"]("XXXX", "1d", "5m") == []


def test_obter_cotacoes_em_lote_preserva_ordem_e_erros():
    cot = fm.obter_cotacoes(["vale3", "INEXISTENTE", "petr4"])
    assert [c["ticker"] for c in cot] == ["VALE3.SA", "INEXISTENTE", "PETR4.SA"]
    assert "erro" in cot[1] and cot[0]["preco"] == 125.1


def test_obter_cotacoes_falha_de_rede(monkeypatch):
    def falha(tickers, periodo="1y"):
        raise TimeoutError("Yahoo fora do ar")

    monkeypatch.setattr(fm, "_historicos_lote", falha)
    cot = fm.obter_cotacoes(["PETR4", "VALE3"])
    assert all("Yahoo fora do ar" in c["erro"] for c in cot)


def test_bcb_usa_intervalo_quando_ultimos_falha():
    """A série 4389 (CDI) responde 304 no endpoint ultimos/1; o fallback usa o intervalo de datas."""
    urls = []

    def falso(url):
        urls.append(url)
        if "/ultimos/1" in url:
            raise OSError("HTTP Error 304: Not Modified")
        return [{"data": "06/11/2026", "valor": "13.60"}, {"data": "09/11/2026", "valor": "13.65"}]

    assert fm.ultimo_valor_sgs(4389, falso) == {"valor": 13.65, "data": "09/11/2026"}
    assert "dataInicial=" in urls[1] and "dataFinal=" in urls[1]


def test_bcb_usa_ultimos_quando_funciona():
    assert fm.ultimo_valor_sgs(432, lambda url: [{"data": "09/11/2026", "valor": "13.75"}]) == {"valor": 13.75, "data": "09/11/2026"}


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
