# ui/app.py
"""Interface de chat: notícias e análise do mercado financeiro para investidores.

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
from agente import ferramentas_mercado  # noqa: E402
from agente.comum import mensagem_erro_amigavel, obter_api_key  # noqa: E402
from components.sidebar import render_sidebar  # noqa: E402

SUGESTOES = [
    "Como a decisão mais recente do Copom afeta a renda fixa e a bolsa?",
    "Por que a Petrobras (PETR4) oscilou hoje?",
    "Fundos imobiliários (FIIs) ainda valem a pena com a Selic atual?",
    "Como o dólar e os juros dos EUA afetam o Ibovespa?",
]

st.set_page_config(
    page_title="News Analytics — Investidores",
    page_icon="📈",
    layout="wide",
)


@st.cache_data(ttl=900, show_spinner=False)
def carregar_painel() -> tuple[dict | None, dict | None]:
    """Panorama e indicadores (cache de 15 min). Nunca derruba a página."""
    try:
        panorama = ferramentas_mercado.obter_panorama()
    except Exception:  # noqa: BLE001
        panorama = None
    try:
        indicadores = ferramentas_mercado.obter_indicadores()
    except Exception:  # noqa: BLE001
        indicadores = None
    return panorama, indicadores


def _usar_sugestao(texto: str) -> None:
    st.session_state.tema_sugerido = texto


if "mensagens" not in st.session_state:
    st.session_state.mensagens = []

st.title("📈 Notícias para Investidores")
st.caption(
    "Ações, renda fixa, renda variável, fundos, câmbio, cripto e economia: notícias apuradas, "
    "checadas e explicadas com dados reais de mercado. Outros temas também são bem-vindos."
)

# Seletor de versão dentro da área do chat
chave_versao = st.segmented_control(
    "Versão dos agentes",
    options=list(registry.VERSOES.keys()),
    default=registry.VERSAO_PADRAO,
    format_func=lambda chave: registry.VERSOES[chave].rotulo,
    key="versao",
) or registry.VERSAO_PADRAO

versao = registry.VERSOES[chave_versao]

panorama, indicadores = carregar_painel()
if render_sidebar(versao, panorama, indicadores):
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
    st.info("Pergunte sobre um ativo, indicador ou notícia do mercado, ou escolha uma sugestão:")
    colunas = st.columns(2)
    for i, sugestao in enumerate(SUGESTOES):
        colunas[i % 2].button(
            sugestao,
            key=f"sugestao_{i}",
            on_click=_usar_sugestao,
            args=(sugestao,),
            use_container_width=True,
        )

tema = st.chat_input(f"Pergunte sobre o mercado ({chave_versao})…") or st.session_state.pop(
    "tema_sugerido", None
)

if tema:
    st.session_state.mensagens.append({"papel": "user", "conteudo": tema})
    with st.chat_message("user"):
        st.markdown(tema)

    with st.chat_message("assistant"):
        st.caption(f"🤖 {versao.rotulo}")
        try:
            with st.spinner(f"Executando {versao.rotulo}… (pode levar alguns minutos)"):
                workflow = registry.carregar_workflow(chave_versao)
                resultado = workflow.run(tema)
            status = str(getattr(resultado, "status", "") or "")
            conteudo = str(getattr(resultado, "content", None) or "")
            if "ERROR" in status.upper() or not conteudo:
                conteudo = f"❌ Erro ao executar {versao.rotulo}: {mensagem_erro_amigavel(conteudo or 'sem conteúdo')}"
        except Exception as erro:  # noqa: BLE001 - mostrar qualquer falha ao usuário
            conteudo = f"❌ Erro ao executar {versao.rotulo}: {mensagem_erro_amigavel(str(erro))}"
        st.markdown(conteudo)

    st.session_state.mensagens.append(
        {"papel": "assistant", "conteudo": conteudo, "versao": versao.rotulo}
    )
