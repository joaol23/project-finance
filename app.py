import streamlit as st
import os
from database import init_db

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(
    page_title="Organizador Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

st.markdown("""
<style>
    .stApp {
        background-color: #1a1a2e;
    }
    .stSidebar {
        background-color: #16213e;
    }
    .stMetric {
        background-color: #16213e;
        padding: 15px;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #e94560;
    }
    .positive {
        color: #22c55e;
    }
    .negative {
        color: #ef4444;
    }
    /* Esconder menu de páginas padrão do Streamlit */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:nth-child(2) {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("💰 Organizador Financeiro")

page = st.sidebar.radio(
    "Menu",
    ["📊 Painel", "💸 Transações", "📁 Categorias", "📋 Orçamentos", 
     "💳 Cartões de Crédito", "📈 Investimentos", "📥 Importar Dados"],
    label_visibility="collapsed"
)

exec_globals = {"PROJECT_ROOT": PROJECT_ROOT}

if page == "📊 Painel":
    exec(open(os.path.join(PROJECT_ROOT, "views/dashboard.py"), encoding="utf-8").read(), exec_globals)
elif page == "💸 Transações":
    exec(open(os.path.join(PROJECT_ROOT, "views/transactions.py"), encoding="utf-8").read(), exec_globals)
elif page == "📁 Categorias":
    exec(open(os.path.join(PROJECT_ROOT, "views/categories.py"), encoding="utf-8").read(), exec_globals)
elif page == "📋 Orçamentos":
    exec(open(os.path.join(PROJECT_ROOT, "views/budgets.py"), encoding="utf-8").read(), exec_globals)
elif page == "💳 Cartões de Crédito":
    exec(open(os.path.join(PROJECT_ROOT, "views/credit_cards.py"), encoding="utf-8").read(), exec_globals)
elif page == "📈 Investimentos":
    exec(open(os.path.join(PROJECT_ROOT, "views/investments.py"), encoding="utf-8").read(), exec_globals)
elif page == "📥 Importar Dados":
    exec(open(os.path.join(PROJECT_ROOT, "views/import_data.py"), encoding="utf-8").read(), exec_globals)
