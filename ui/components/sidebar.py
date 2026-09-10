# ui/components/sidebar.py

import streamlit as st
from ui.registry import WORKFLOWS

def render_sidebar():

    with st.sidebar:

        st.title("📰 News Curator")

        versao = st.selectbox(
            "Versão",
            list(WORKFLOWS.keys())
        )

        st.divider()

        st.caption(
            "Workflow de Curadoria de Notícias"
        )

    return versao