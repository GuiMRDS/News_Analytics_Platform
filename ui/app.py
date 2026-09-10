# ui/app.py

import streamlit as st
from components.sidebar import render_sidebar
import sys
from pathlib import Path
from registry import WORKFLOWS

BASE_DIR = Path(__file__).resolve().parent.parent

if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

st.set_page_config(
    page_title="News Curator",
    page_icon="📰",
    layout="wide"
)

versao = render_sidebar(WORKFLOWS)

workflow = WORKFLOWS[versao]

st.title("📰 Curadoria de Notícias")

tema = st.text_input(
    "Tema da matéria",
    placeholder="Ex: Inteligência Artificial no Brasil"
)

if st.button(
    "Gerar Matéria",
    use_container_width=True
):

    if tema:

        with st.spinner(
            "Executando workflow..."
        ):

            resultado = workflow.run(tema)

        st.success(
            "Matéria gerada com sucesso!"
        )

        st.markdown(resultado.content)