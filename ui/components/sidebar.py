import streamlit as st


def render_sidebar(versao) -> bool:
    """Mostra detalhes da versão ativa. Retorna True se pediram nova conversa."""

    with st.sidebar:
        st.title("📰 News Curator")

        st.subheader(versao.rotulo)
        st.write(versao.descricao)
        st.caption(versao.pipeline)

        st.divider()

        nova_conversa = st.button(
            "🗑️ Nova conversa",
            use_container_width=True,
            key="nova_conversa",
        )

        st.caption(
            "Troque a versão dos agentes a qualquer momento pelo seletor acima do chat. "
            "Cada resposta indica qual versão a gerou."
        )

    return nova_conversa
