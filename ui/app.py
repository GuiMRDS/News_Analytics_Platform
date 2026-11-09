# ui/app.py
"""Interface de chat do curador de notícias.

Execute a partir da raiz:  uv run python -m streamlit run ui/app.py
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = Path(__file__).resolve().parent

# Precisa vir antes dos imports de `registry`, que importa o pacote `agente`.
for caminho in (BASE_DIR, UI_DIR):
    if str(caminho) not in sys.path:
        sys.path.insert(0, str(caminho))

import streamlit as st  # noqa: E402

import registry  # noqa: E402
from agente.comum import obter_api_key  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402

st.set_page_config(
    page_title="News Curator",
    page_icon="📰",
    layout="wide",
)

if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

st.title("📰 Curadoria de Notícias")

# Seletor de versão dentro da área do chat
chave_versao = st.segmented_control(
    "Versão dos agentes",
    options=list(registry.VERSOES.keys()),
    default=registry.VERSAO_PADRAO,
    format_func=lambda chave: registry.VERSOES[chave].rotulo,
    key="versao",
) or registry.VERSAO_PADRAO

versao = registry.VERSOES[chave_versao]

if render_sidebar(versao):
    st.session_state.mensagens = []

if not obter_api_key():
    st.error(
        "GROQ_API_KEY não encontrada. Crie um arquivo `.env` na raiz do projeto "
        "com `GROQ_API_KEY=sua_chave` (veja `.env.example`)."
    )
    st.stop()

# Histórico
for mensagem in st.session_state.mensagens:
    with st.chat_message(mensagem["papel"]):
        if mensagem["papel"] == "assistant":
            st.caption(f"🤖 {mensagem['versao']}")
        st.markdown(mensagem["conteudo"])

if not st.session_state.mensagens:
    st.info("Digite um tema abaixo para gerar uma matéria jornalística.")

tema = st.chat_input(f"Tema da matéria ({chave_versao})…")

if tema:
    st.session_state.mensagens.append({"papel": "user", "conteudo": tema})
    with st.chat_message("user"):
        st.markdown(tema)

    with st.chat_message("assistant"):
        st.caption(f"🤖 {versao.rotulo}")
        try:
            with st.spinner(f"Executando {versao.rotulo}…"):
                workflow = registry.carregar_workflow(chave_versao)
                resultado = workflow.run(tema)
            conteudo = str(getattr(resultado, "content", None) or "_O workflow não retornou conteúdo._")
        except Exception as erro:  # noqa: BLE001 - mostrar qualquer falha ao usuário
            conteudo = f"❌ Erro ao executar {versao.rotulo}: `{erro}`"
        st.markdown(conteudo)

    st.session_state.mensagens.append(
        {"papel": "assistant", "conteudo": conteudo, "versao": versao.rotulo}
    )
