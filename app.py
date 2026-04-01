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
    /* === Base === */
    .stApp {
        background-color: #0d0d0d;
    }
    
    /* === Sidebar === */
    .stSidebar, [data-testid="stSidebar"] {
        background-color: #1a1a1a !important;
        border-right: 1px solid #2d2d2d;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #f5f5f5;
    }
    
    /* === Headings === */
    h1, h2, h3 {
        color: #a855f7 !important;
    }
    h1 {
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* === Metrics Cards === */
    [data-testid="stMetric"] {
        background-color: #1a1a1a;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #2d2d2d;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    [data-testid="stMetric"] label {
        color: #9ca3af !important;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f5f5f5 !important;
    }
    
    /* === Buttons === */
    .stButton > button {
        background-color: #9333ea;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #a855f7;
        border: none;
    }
    .stButton > button:focus {
        box-shadow: 0 0 0 3px rgba(147, 51, 234, 0.3);
    }
    
    /* === Inputs === */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        color: #f5f5f5;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #9333ea;
        box-shadow: 0 0 0 2px rgba(147, 51, 234, 0.2);
    }
    
    /* === Tabs === */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #9ca3af;
        border-radius: 8px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #9333ea !important;
        color: white !important;
    }
    
    /* === Expanders === */
    .streamlit-expanderHeader {
        background-color: #1a1a1a;
        border-radius: 8px;
        border: 1px solid #2d2d2d;
    }
    .streamlit-expanderContent {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-top: none;
        border-radius: 0 0 8px 8px;
    }
    
    /* === Data containers / Cards === */
    .element-container .stMarkdown hr {
        border-color: #2d2d2d;
    }
    
    /* === Positive/Negative colors === */
    .positive {
        color: #22c55e !important;
    }
    .negative {
        color: #ef4444 !important;
    }
    
    /* === Hide default Streamlit page nav === */
    [data-testid="stSidebarNav"] {
        display: none;
    }
    section[data-testid="stSidebar"] > div:first-child > div:first-child > div:nth-child(2) {
        display: none;
    }
    
    /* === Custom card class === */
    .card {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .card-header {
        color: #a855f7;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 12px;
    }
    
    /* === Filter bar === */
    .filter-bar {
        background-color: #1a1a1a;
        border: 1px solid #2d2d2d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
    }
    
    /* === Toast customization === */
    [data-testid="stToast"] {
        background-color: #1a1a1a;
        border: 1px solid #9333ea;
    }
    
    /* === Radio buttons in sidebar === */
    [data-testid="stSidebar"] .stRadio label {
        color: #f5f5f5 !important;
    }
    [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] {
        color: #f5f5f5;
    }
</style>
""", unsafe_allow_html=True)

st.sidebar.title("💰 Organizador Financeiro")

page = st.sidebar.radio(
    "Menu",
    ["📊 Painel", "💸 Transações", "📁 Categorias", "📋 Orçamentos", 
     "💳 Cartões de Crédito", "📈 Investimentos", "📉 Análises", "📥 Importar/Exportar"],
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
elif page == "📉 Análises":
    exec(open(os.path.join(PROJECT_ROOT, "views/analytics.py"), encoding="utf-8").read(), exec_globals)
elif page == "📥 Importar/Exportar":
    exec(open(os.path.join(PROJECT_ROOT, "views/import_data.py"), encoding="utf-8").read(), exec_globals)
