# ui/app.py

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Precisa vir antes dos imports de `registry`, que importam o pacote `agente`.
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st  # noqa: E402

from agente.comum import obter_api_key  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402
from registry import WORKFLOWS  # noqa: E402

st.set_page_config(
    page_title="News Curator",
    page_icon="📰",
    layout="wide"
)

versao = render_sidebar(WORKFLOWS)

workflow = WORKFLOWS[versao]

st.title("📰 Curadoria de Notícias")

if not obter_api_key():
    st.error(
        "GROQ_API_KEY não encontrada. Crie um arquivo `.env` na raiz do projeto "
        "com `GROQ_API_KEY=sua_chave` (veja `.env.example`)."
    )
    st.stop()

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
