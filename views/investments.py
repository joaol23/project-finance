import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import Investment, Transaction, Category, InvestmentType, TransactionType

st.title("📈 Investimentos")

session = get_session()

try:
    from services.stock_service import get_stock_price, extract_ticker_from_description, detect_investment_type, YFINANCE_AVAILABLE
except ImportError:
    YFINANCE_AVAILABLE = False
    def get_stock_price(ticker): return None
    def extract_ticker_from_description(desc): return None
    def detect_investment_type(ticker): return "stock"

investments = session.query(Investment).all()
investment_categories = session.query(Category).filter(Category.is_investment == True).all()
investment_category_ids = [c.id for c in investment_categories]

pending_transactions = session.query(Transaction).filter(
    Transaction.category_id.in_(investment_category_ids),
    Transaction.investment_id == None
).order_by(Transaction.date.desc()).all()

type_labels = {
    InvestmentType.STOCK: "Ação",
    InvestmentType.FII: "FII",
    InvestmentType.CRYPTO: "Crypto",
    InvestmentType.OTHER: "Outro"
}

if "inv_linked" not in st.session_state:
    st.session_state.inv_linked = False
if "prices_updated" not in st.session_state:
    st.session_state.prices_updated = False

if st.session_state.inv_linked:
    st.toast("✅ Transação vinculada ao investimento!", icon="✅")
    st.session_state.inv_linked = False

if st.session_state.prices_updated:
    st.toast("✅ Cotações atualizadas!", icon="✅")
    st.session_state.prices_updated = False

tab_portfolio, tab_pending, tab_history = st.tabs([
    "📊 Portfólio", "⏳ Transações Pendentes", "📋 Histórico"
])

with tab_portfolio:
    st.markdown("### Visão Geral do Portfólio")
    
    total_invested = sum(float(inv.total_invested) for inv in investments)
    total_current = sum(float(inv.current_value) for inv in investments)
    total_gain = total_current - total_invested
    gain_percent = (total_gain / total_invested * 100) if total_invested > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Investido", f"R$ {total_invested:,.2f}")
    with col2:
        st.metric("Valor Atual", f"R$ {total_current:,.2f}")
    with col3:
        delta_color = "normal" if total_gain >= 0 else "inverse"
        st.metric("Ganho/Perda", f"R$ {total_gain:,.2f}", 
                 delta=f"{gain_percent:.1f}%" if total_invested > 0 else None,
                 delta_color=delta_color)
    with col4:
        st.metric("Ativos", len(investments))
    
    st.markdown("---")
    
    if YFINANCE_AVAILABLE:
        if investments:
            if st.button("🔄 Atualizar Cotações", type="primary", use_container_width=True):
                progress_bar = st.progress(0, text="Buscando cotações...")
                updated = 0
                errors = []
                total = len(investments)
                
                for i, inv in enumerate(investments):
                    progress_bar.progress((i + 1) / total, text=f"Buscando {inv.ticker}...")
                    price = get_stock_price(inv.ticker)
                    if price:
                        inv.current_price = Decimal(str(price))
                        updated += 1
                    else:
                        errors.append(inv.ticker)
                
                session.commit()
                progress_bar.empty()
                
                if errors:
                    st.warning(f"⚠️ Não foi possível obter cotação para: {', '.join(errors)}. A API pode estar temporariamente indisponível.")
                if updated > 0:
                    st.success(f"✅ {updated} cotação(ões) atualizada(s)!")
                st.session_state.prices_updated = True
                st.rerun()
        else:
            st.info("📊 Cadastre investimentos para atualizar cotações automaticamente")
    else:
        st.warning("⚠️ Biblioteca yfinance não disponível. Execute: `pip install yfinance`")
    
    st.markdown("---")
    
    if investments:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("### Distribuição por Tipo")
            type_values = {}
            for inv in investments:
                type_name = type_labels[inv.investment_type]
                value = float(inv.current_value) if inv.current_value > 0 else float(inv.total_invested)
                type_values[type_name] = type_values.get(type_name, 0) + value
            
            if type_values and sum(type_values.values()) > 0:
                fig = px.pie(
                    values=list(type_values.values()),
                    names=list(type_values.keys()),
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set2
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            st.markdown("### Distribuição por Ativo")
            asset_values = {}
            for inv in investments:
                value = float(inv.current_value) if inv.current_value > 0 else float(inv.total_invested)
                if value > 0:
                    asset_values[inv.ticker] = value
            
            if asset_values:
                fig = px.pie(
                    values=list(asset_values.values()),
                    names=list(asset_values.keys()),
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### Meus Investimentos")
        
        for inv in investments:
            gain = float(inv.gain_loss)
            gain_pct = float(inv.gain_loss_percent)
            gain_color = "🟢" if gain >= 0 else "🔴"
            
            with st.expander(f"{gain_color} {inv.ticker} - {inv.name or type_labels[inv.investment_type]}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Quantidade", f"{float(inv.total_quantity):,.2f}")
                with col2:
                    st.metric("Preço Médio", f"R$ {float(inv.average_price):,.2f}")
                with col3:
                    st.metric("Total Investido", f"R$ {float(inv.total_invested):,.2f}")
                with col4:
                    st.metric("Cotação Atual", f"R$ {float(inv.current_price or 0):,.2f}")
                
                col5, col6, col7, col8 = st.columns(4)
                with col5:
                    st.metric("Valor Atual", f"R$ {float(inv.current_value):,.2f}")
                with col6:
                    delta_str = f"{gain_pct:+.1f}%"
                    st.metric("Ganho/Perda", f"R$ {gain:,.2f}", delta=delta_str)
                with col7:
                    new_price = st.number_input(
                        "Atualizar Cotação",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        value=float(inv.current_price) if inv.current_price else 0.0,
                        key=f"price_{inv.id}"
                    )
                with col8:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("💾 Salvar", key=f"save_price_{inv.id}"):
                        inv.current_price = Decimal(str(new_price))
                        session.commit()
                        st.toast("✅ Cotação atualizada!", icon="✅")
                        st.rerun()
    else:
        st.info("Nenhum investimento cadastrado. Vincule transações na aba 'Transações Pendentes'.")

with tab_pending:
    st.markdown("### Transações Pendentes de Vinculação")
    st.markdown("Transações com categorias de investimento que ainda não foram vinculadas a um ativo.")
    
    if pending_transactions:
        st.warning(f"📋 {len(pending_transactions)} transações pendentes")
        
        for t in pending_transactions:
            suggested_ticker = extract_ticker_from_description(t.description)
            
            with st.container():
                st.markdown(f"**{t.date.strftime('%d/%m/%Y')}** - {t.description}")
                st.markdown(f"Valor: **R$ {float(t.amount):,.2f}** | Categoria: {t.category.name if t.category else 'N/A'}")
                
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    ticker = st.text_input(
                        "Ticker",
                        value=suggested_ticker or "",
                        key=f"ticker_{t.id}",
                        placeholder="Ex: PETR4"
                    ).upper()
                
                with col2:
                    qty = st.number_input(
                        "Quantidade",
                        min_value=0.0,
                        step=1.0,
                        format="%.2f",
                        key=f"qty_{t.id}",
                        value=0.0
                    )
                
                with col3:
                    if qty > 0:
                        suggested_price = float(t.amount) / qty
                    else:
                        suggested_price = 0.0
                    
                    price = st.number_input(
                        "Preço por Unidade",
                        min_value=0.0,
                        step=0.01,
                        format="%.2f",
                        key=f"price_{t.id}",
                        value=suggested_price
                    )
                
                with col4:
                    st.markdown("&nbsp;", unsafe_allow_html=True)
                    if st.button("✅ Vincular", key=f"link_{t.id}", type="primary"):
                        if ticker and qty > 0:
                            investment = session.query(Investment).filter(Investment.ticker == ticker).first()
                            
                            if not investment:
                                inv_type_str = detect_investment_type(ticker)
                                inv_type_map = {
                                    "stock": InvestmentType.STOCK,
                                    "fii": InvestmentType.FII,
                                    "crypto": InvestmentType.CRYPTO,
                                    "other": InvestmentType.OTHER
                                }
                                investment = Investment(
                                    ticker=ticker,
                                    investment_type=inv_type_map.get(inv_type_str, InvestmentType.STOCK)
                                )
                                session.add(investment)
                                session.flush()
                            
                            t.investment_id = investment.id
                            t.quantity = Decimal(str(qty))
                            t.price_per_unit = Decimal(str(price))
                            session.commit()
                            
                            st.session_state.inv_linked = True
                            st.rerun()
                        else:
                            st.error("Preencha o ticker e a quantidade")
                
                st.markdown("---")
    else:
        st.success("✅ Nenhuma transação pendente!")
        st.markdown("Crie transações com as categorias **Ações**, **FIIs** ou **Criptomoedas** para vê-las aqui.")

with tab_history:
    st.markdown("### Histórico de Transações de Investimento")
    
    linked_transactions = session.query(Transaction).filter(
        Transaction.investment_id != None
    ).order_by(Transaction.date.desc()).all()
    
    if investments:
        filter_options = {"Todos": None} | {inv.ticker: inv.id for inv in investments}
        selected_filter = st.selectbox("Filtrar por Ativo", list(filter_options.keys()), key="filter_inv_hist")
        
        if filter_options[selected_filter]:
            linked_transactions = [t for t in linked_transactions if t.investment_id == filter_options[selected_filter]]
    
    if linked_transactions:
        header_cols = st.columns([1.3, 1, 0.8, 0.8, 1.1, 1.2, 1.8, 0.5])
        with header_cols[0]:
            st.markdown("**Data**")
        with header_cols[1]:
            st.markdown("**Ticker**")
        with header_cols[2]:
            st.markdown("**Tipo**")
        with header_cols[3]:
            st.markdown("**Qtd**")
        with header_cols[4]:
            st.markdown("**Preço Unit.**")
        with header_cols[5]:
            st.markdown("**Valor Total**")
        with header_cols[6]:
            st.markdown("**Variação**")
        with header_cols[7]:
            st.markdown("**Ação**")
        st.markdown("---")
        
        for t in linked_transactions:
            with st.container():
                qty = float(t.quantity or 0)
                price_paid = float(t.price_per_unit or 0)
                total_paid = qty * price_paid
                current_price = float(t.investment.current_price or 0) if t.investment else 0
                current_value = qty * current_price
                variation = current_value - total_paid
                variation_pct = (variation / total_paid * 100) if total_paid > 0 else 0
                
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.3, 1, 0.8, 0.8, 1.1, 1.2, 1.8, 0.5])
                with col1:
                    st.write(t.date.strftime("%d/%m/%Y"))
                with col2:
                    st.write(t.investment.ticker if t.investment else "-")
                with col3:
                    tipo = "Compra" if t.transaction_type == TransactionType.EXPENSE else "Venda"
                    st.write(tipo)
                with col4:
                    st.write(f"{qty:,.2f}")
                with col5:
                    st.write(f"R$ {price_paid:,.2f}")
                with col6:
                    st.write(f"R$ {total_paid:,.2f}")
                with col7:
                    if current_price > 0:
                        color = "green" if variation >= 0 else "red"
                        st.markdown(f":{color}[R$ {variation:+,.2f} ({variation_pct:+.1f}%)]")
                    else:
                        st.write("Atualizar cotação")
                with col8:
                    if st.button("🔓", key=f"unlink_{t.id}", help="Desvincular"):
                        t.investment_id = None
                        t.quantity = None
                        t.price_per_unit = None
                        session.commit()
                        st.toast("🔓 Transação desvinculada!", icon="🔓")
                        st.rerun()
    else:
        st.info("Nenhuma transação de investimento registrada")

session.close()
