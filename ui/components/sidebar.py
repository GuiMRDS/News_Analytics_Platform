import streamlit as st


def _formatar(valor, casas=2):
    if valor is None:
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def render_painel_mercado(panorama: dict | None, indicadores: dict | None) -> None:
    """Painel com dados reais de mercado (Yahoo Finance e Banco Central)."""
    st.subheader("📊 Mercado agora")

    if not panorama and not indicadores:
        st.caption("Dados de mercado indisponíveis no momento.")
        return

    if panorama:
        colunas = st.columns(2)
        for i, (nome, dados) in enumerate(panorama.items()):
            with colunas[i % 2]:
                if dados.get("preco") is None:
                    st.metric(nome, "—")
                    continue
                variacao = dados.get("variacao_dia_pct")
                st.metric(
                    nome,
                    _formatar(dados["preco"], 0 if dados["preco"] > 10_000 else 2),
                    f"{_formatar(variacao)}%" if variacao is not None else None,
                )

    if indicadores:
        linhas = []
        for chave, rotulo, sufixo in (
            ("selic_meta_aa", "Selic", "% a.a."),
            ("cdi_aa", "CDI", "% a.a."),
            ("ipca_12m", "IPCA 12m", "%"),
            ("dolar_ptax", "Dólar PTAX", ""),
        ):
            dado = indicadores.get(chave) or {}
            if "valor" in dado:
                prefixo = "R$ " if chave == "dolar_ptax" else ""
                casas = 4 if chave == "dolar_ptax" else 2
                linhas.append(f"**{rotulo}:** {prefixo}{_formatar(dado['valor'], casas)}{sufixo} _({dado['data']})_")
        if linhas:
            st.markdown("  \n".join(linhas))

    st.caption("Fontes: Yahoo Finance e Banco Central (SGS). Atualiza a cada 15 min.")


def render_sidebar(versao, panorama: dict | None = None, indicadores: dict | None = None) -> bool:
    """Mostra o painel de mercado e a versão ativa. Retorna True se pediram nova conversa."""

    with st.sidebar:
        st.title("📈 News Analytics")
        st.caption("Notícias e dados para investidores")

        render_painel_mercado(panorama, indicadores)

        st.divider()

        st.subheader(versao.rotulo)
        st.write(versao.descricao)
        st.caption(versao.pipeline)

        nova_conversa = st.button(
            "🗑️ Nova conversa",
            use_container_width=True,
            key="nova_conversa",
        )

        st.caption(
            "Troque a versão dos agentes pelo seletor acima do chat. "
            "Conteúdo informativo; não constitui recomendação de investimento."
        )

    return nova_conversa
