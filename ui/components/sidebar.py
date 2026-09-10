import streamlit as st

def render_sidebar(workflows):

    with st.sidebar:

        st.title("📰 News Curator")

        versao = st.selectbox(
            "Versão",
            list(workflows.keys())
        )

        st.divider()

        st.caption(
            "Workflow de Curadoria de Notícias"
        )

    return versao