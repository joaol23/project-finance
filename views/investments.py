import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import Investment, Transaction, Category, InvestmentType, TransactionType, Account, CategoryType

st.title("📈 Investimentos")
st.caption("Acompanhe sua carteira de investimentos")

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
if "inv_sold" not in st.session_state:
    st.session_state.inv_sold = False

if st.session_state.inv_linked:
    st.toast("✅ Transação vinculada ao investimento!", icon="✅")
    st.session_state.inv_linked = False

if st.session_state.prices_updated:
    st.toast("✅ Cotações atualizadas!", icon="✅")
    st.session_state.prices_updated = False

if st.session_state.inv_sold:
    st.toast("✅ Venda registrada com sucesso!", icon="✅")
    st.session_state.inv_sold = False

tab_portfolio, tab_sell, tab_pending, tab_history = st.tabs([
    "📊 Portfólio", "💰 Vender Ativo", "⏳ Transações Pendentes", "📋 Histórico"
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
                purple_palette = ['#9333ea', '#a855f7', '#7c3aed', '#8b5cf6', '#6366f1', '#818cf8']
                fig = px.pie(
                    values=list(type_values.values()),
                    names=list(type_values.keys()),
                    hole=0.4,
                    color_discrete_sequence=purple_palette
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    legend=dict(font=dict(color='#9ca3af'))
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
                gray_purple_palette = ['#4b5563', '#6b7280', '#9ca3af', '#7c3aed', '#9333ea', '#a855f7']
                fig = px.pie(
                    values=list(asset_values.values()),
                    names=list(asset_values.keys()),
                    hole=0.4,
                    color_discrete_sequence=gray_purple_palette
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    legend=dict(font=dict(color='#9ca3af'))
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        col_perf1, col_perf2 = st.columns(2)
        
        with col_perf1:
            st.markdown("### Performance por Ativo (%)")
            perf_data = []
            for inv in investments:
                gain_pct = float(inv.gain_loss_percent)
                perf_data.append({
                    "Ativo": inv.ticker,
                    "Rentabilidade": gain_pct,
                    "Cor": "#22c55e" if gain_pct >= 0 else "#ef4444"
                })
            
            if perf_data:
                perf_data = sorted(perf_data, key=lambda x: x["Rentabilidade"], reverse=True)
                fig_perf = go.Figure()
                fig_perf.add_trace(go.Bar(
                    y=[d["Ativo"] for d in perf_data],
                    x=[d["Rentabilidade"] for d in perf_data],
                    orientation='h',
                    marker_color=[d["Cor"] for d in perf_data],
                    text=[f"{d['Rentabilidade']:+.1f}%" for d in perf_data],
                    textposition='outside'
                ))
                fig_perf.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af', title='Rentabilidade (%)'),
                    yaxis=dict(showgrid=False, color='#9ca3af', autorange="reversed"),
                    showlegend=False,
                    height=max(300, len(perf_data) * 40)
                )
                fig_perf.add_vline(x=0, line_dash="dash", line_color="#9ca3af")
                st.plotly_chart(fig_perf, use_container_width=True)
        
        with col_perf2:
            st.markdown("### Preço Médio vs Cotação Atual")
            price_data = []
            for inv in investments:
                avg_price = float(inv.average_price)
                current = float(inv.current_price or 0)
                if avg_price > 0 or current > 0:
                    price_data.append({
                        "Ativo": inv.ticker,
                        "Preço Médio": avg_price,
                        "Cotação Atual": current
                    })
            
            if price_data:
                df_prices = pd.DataFrame(price_data)
                fig_prices = go.Figure()
                fig_prices.add_trace(go.Bar(
                    name='Preço Médio',
                    x=df_prices['Ativo'],
                    y=df_prices['Preço Médio'],
                    marker_color='#6b7280'
                ))
                fig_prices.add_trace(go.Bar(
                    name='Cotação Atual',
                    x=df_prices['Ativo'],
                    y=df_prices['Cotação Atual'],
                    marker_color='#9333ea'
                ))
                fig_prices.update_layout(
                    barmode='group',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    xaxis=dict(showgrid=False, color='#9ca3af'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af', title='R$'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#9ca3af')),
                    height=350
                )
                st.plotly_chart(fig_prices, use_container_width=True)
        
        st.markdown("---")
        
        st.markdown("### Indicador de Ação por Ativo")
        st.caption("⚠️ Não é recomendação de investimento. Baseado apenas na diferença entre PM e cotação atual.")
        
        action_cols = st.columns(min(4, len(investments)) if investments else 1)
        for idx, inv in enumerate(investments):
            col_idx = idx % len(action_cols)
            with action_cols[col_idx]:
                avg_price = float(inv.average_price)
                current = float(inv.current_price or 0)
                gain_pct = float(inv.gain_loss_percent)
                
                if current == 0:
                    action = "⏸️ Atualizar"
                    action_color = "gray"
                    reason = "Cotação não disponível"
                elif gain_pct > 20:
                    action = "💰 Realizar Lucro"
                    action_color = "green"
                    reason = f"+{gain_pct:.1f}% de ganho"
                elif gain_pct > 5:
                    action = "📈 No Lucro"
                    action_color = "green"
                    reason = f"+{gain_pct:.1f}% acima do PM"
                elif gain_pct < -15:
                    action = "🔻 Avaliar"
                    action_color = "red"
                    reason = f"{gain_pct:.1f}% de perda"
                elif gain_pct < -5:
                    action = "⚠️ Atenção"
                    action_color = "orange"
                    reason = f"{gain_pct:.1f}% abaixo do PM"
                else:
                    action = "➡️ Manter"
                    action_color = "blue"
                    reason = "Próximo ao PM"
                
                st.markdown(f"**{inv.ticker}**")
                st.markdown(f":{action_color}[{action}]")
                st.caption(reason)
        
        st.markdown("---")
        
        st.markdown("### Evolução do Portfólio")
        all_inv_transactions = session.query(Transaction).filter(
            Transaction.investment_id != None
        ).order_by(Transaction.date).all()
        
        if all_inv_transactions:
            portfolio_evolution = {}
            running_invested = Decimal(0)
            
            for t in all_inv_transactions:
                date_key = t.date.strftime("%Y-%m-%d")
                if t.transaction_type == TransactionType.EXPENSE:
                    running_invested += t.amount
                else:
                    running_invested -= t.amount
                portfolio_evolution[date_key] = float(running_invested)
            
            if portfolio_evolution:
                dates = list(portfolio_evolution.keys())
                values = list(portfolio_evolution.values())
                
                df_evolution = pd.DataFrame({
                    "Data": pd.to_datetime(dates),
                    "Valor Investido": values
                })
                
                current_total = sum(float(inv.current_value) for inv in investments if inv.current_value > 0)
                if current_total > 0:
                    df_evolution["Valor Atual"] = [current_total] * len(df_evolution)
                
                fig_evolution = go.Figure()
                fig_evolution.add_trace(go.Scatter(
                    x=df_evolution["Data"],
                    y=df_evolution["Valor Investido"],
                    mode='lines+markers',
                    name='Valor Investido',
                    line=dict(color='#6b7280', width=2),
                    marker=dict(size=6)
                ))
                
                if current_total > 0:
                    fig_evolution.add_hline(
                        y=current_total, 
                        line_dash="dash", 
                        line_color="#9333ea",
                        annotation_text=f"Valor Atual: R$ {current_total:,.2f}",
                        annotation_position="top right"
                    )
                
                fig_evolution.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    xaxis=dict(showgrid=False, color='#9ca3af', title='Data'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af', title='R$'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#9ca3af')),
                    height=400
                )
                st.plotly_chart(fig_evolution, use_container_width=True)
        else:
            st.info("Registre transações de investimento para ver a evolução do portfólio.")
        
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
                        key=f"inv_price_{inv.id}"
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

with tab_sell:
    st.markdown("### Registrar Venda de Ativo")
    st.markdown("Registre a venda total ou parcial de um investimento.")
    
    all_investments = session.query(Investment).all()
    investments_with_qty = [inv for inv in all_investments if float(inv.total_quantity) > 0]
    
    if investments_with_qty:
        account = session.query(Account).first()
        if not account:
            account = Account(name="Conta Principal", initial_balance=Decimal("0"))
            session.add(account)
            session.commit()
        
        sold_stocks_category = session.query(Category).filter(
            Category.name.ilike("%vendid%")
        ).first()
        if not sold_stocks_category:
            sold_stocks_category = session.query(Category).filter(
                Category.category_type == CategoryType.INCOME,
                Category.is_investment == True
            ).first()
        
        ticker_to_inv = {inv.ticker: inv for inv in investments_with_qty}
        ticker_list = list(ticker_to_inv.keys())
        
        selected_ticker = st.selectbox(
            "Selecione o Ativo",
            ticker_list,
            format_func=lambda x: f"{x} ({float(ticker_to_inv[x].total_quantity):,.2f} unidades)",
            key="sell_ticker_select"
        )
        
        if selected_ticker:
            selected_inv = ticker_to_inv[selected_ticker]
            available_qty = float(selected_inv.total_quantity)
            avg_price = float(selected_inv.average_price)
            
            st.markdown("---")
            st.markdown(f"**{selected_inv.ticker}** - {selected_inv.name or type_labels[selected_inv.investment_type]}")
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Quantidade Disponível", f"{available_qty:,.2f}")
            with col_info2:
                st.metric("Preço Médio de Compra", f"R$ {avg_price:,.2f}")
            with col_info3:
                current = float(selected_inv.current_price or 0)
                st.metric("Cotação Atual", f"R$ {current:,.2f}" if current > 0 else "N/A")
            
            st.markdown("---")
            
            with st.form(key="sell_form"):
                col_date, col_qty, col_price = st.columns(3)
                
                with col_date:
                    sell_date = st.date_input(
                        "Data da Venda",
                        value=date.today()
                    )
                
                with col_qty:
                    sell_qty = st.number_input(
                        "Quantidade a Vender",
                        min_value=0.01,
                        max_value=available_qty,
                        value=min(1.0, available_qty),
                        step=1.0,
                        format="%.2f"
                    )
                
                with col_price:
                    suggested_price = float(selected_inv.current_price or selected_inv.average_price or 0)
                    sell_price = st.number_input(
                        "Preço de Venda por Unidade",
                        min_value=0.01,
                        value=max(0.01, suggested_price),
                        step=0.01,
                        format="%.2f"
                    )
                
                total_sale = sell_qty * sell_price
                cost_basis = sell_qty * avg_price
                realized_profit = total_sale - cost_basis
                profit_pct = (realized_profit / cost_basis * 100) if cost_basis > 0 else 0
                
                st.markdown("---")
                st.markdown("### Resumo da Venda")
                
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)
                with col_res1:
                    st.metric("Valor Total da Venda", f"R$ {total_sale:,.2f}")
                with col_res2:
                    st.metric("Custo de Aquisição", f"R$ {cost_basis:,.2f}")
                with col_res3:
                    profit_color = "green" if realized_profit >= 0 else "red"
                    st.markdown("**Lucro/Prejuízo Realizado**")
                    st.markdown(f":{profit_color}[**R$ {realized_profit:+,.2f}**]")
                with col_res4:
                    st.markdown("**Rentabilidade**")
                    st.markdown(f":{profit_color}[**{profit_pct:+.1f}%**]")
                
                remaining_qty = available_qty - sell_qty
                st.caption(f"Após a venda, restará **{remaining_qty:,.2f}** unidade(s) de {selected_inv.ticker}")
                
                if realized_profit >= 0:
                    st.success(f"✅ Você terá um lucro de R$ {realized_profit:,.2f} ({profit_pct:+.1f}%)")
                else:
                    st.warning(f"⚠️ Você terá um prejuízo de R$ {abs(realized_profit):,.2f} ({profit_pct:+.1f}%)")
                
                st.markdown("---")
                
                submitted = st.form_submit_button("💰 Confirmar Venda", type="primary", use_container_width=True)
                
                if submitted:
                    if sell_qty > 0 and sell_qty <= available_qty:
                        try:
                            sale_transaction = Transaction(
                                date=sell_date,
                                amount=Decimal(str(total_sale)),
                                description=f"Venda de {sell_qty:,.2f} {selected_inv.ticker} a R$ {sell_price:,.2f}",
                                transaction_type=TransactionType.INCOME,
                                category_id=sold_stocks_category.id if sold_stocks_category else None,
                                account_id=account.id,
                                investment_id=selected_inv.id,
                                quantity=Decimal(str(sell_qty)),
                                price_per_unit=Decimal(str(sell_price))
                            )
                            session.add(sale_transaction)
                            session.commit()
                            
                            st.success(f"✅ Venda registrada! {sell_qty:,.2f} unidades de {selected_inv.ticker} vendidas por R$ {total_sale:,.2f}")
                            st.session_state.inv_sold = True
                            st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"❌ Erro ao registrar venda: {str(e)}")
                    else:
                        st.error("❌ Quantidade inválida! Verifique se a quantidade é maior que zero e não excede o disponível.")
    else:
        st.info("Nenhum investimento com quantidade disponível para venda.")
        st.markdown("Vincule transações de compra na aba **Transações Pendentes** para começar.")

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
                        key=f"pending_price_{t.id}",
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
    
    buy_transactions = [t for t in linked_transactions if t.transaction_type == TransactionType.EXPENSE]
    sell_transactions = [t for t in linked_transactions if t.transaction_type == TransactionType.INCOME]
    
    total_bought = sum(float(t.amount) for t in buy_transactions)
    total_sold = sum(float(t.amount) for t in sell_transactions)
    
    total_realized_profit = Decimal(0)
    for t in sell_transactions:
        if t.investment and t.quantity:
            avg_price = t.investment.average_price
            sale_price = t.price_per_unit or Decimal(0)
            qty = t.quantity
            cost_basis = qty * avg_price
            sale_value = qty * sale_price
            total_realized_profit += (sale_value - cost_basis)
    
    col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)
    with col_sum1:
        st.metric("Total Comprado", f"R$ {total_bought:,.2f}", delta=f"{len(buy_transactions)} compras", delta_color="off")
    with col_sum2:
        st.metric("Total Vendido", f"R$ {total_sold:,.2f}", delta=f"{len(sell_transactions)} vendas", delta_color="off")
    with col_sum3:
        profit_color = "normal" if total_realized_profit >= 0 else "inverse"
        st.metric("Lucro Realizado", f"R$ {float(total_realized_profit):,.2f}", 
                 delta="vendas concluídas" if total_realized_profit >= 0 else "prejuízo",
                 delta_color=profit_color)
    with col_sum4:
        unrealized = sum(float(inv.gain_loss) for inv in investments)
        unrealized_color = "normal" if unrealized >= 0 else "inverse"
        st.metric("Lucro Não Realizado", f"R$ {unrealized:,.2f}",
                 delta="posições abertas",
                 delta_color=unrealized_color)
    
    st.markdown("---")
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        if investments:
            filter_options = {"Todos": None} | {inv.ticker: inv.id for inv in investments}
            selected_filter = st.selectbox("Filtrar por Ativo", list(filter_options.keys()), key="filter_inv_hist")
        else:
            selected_filter = "Todos"
            filter_options = {"Todos": None}
    
    with col_filter2:
        type_filter = st.selectbox("Filtrar por Tipo", ["Todos", "Compras", "Vendas"], key="filter_type_hist")
    
    filtered_transactions = linked_transactions
    
    if investments and filter_options.get(selected_filter):
        filtered_transactions = [t for t in filtered_transactions if t.investment_id == filter_options[selected_filter]]
    
    if type_filter == "Compras":
        filtered_transactions = [t for t in filtered_transactions if t.transaction_type == TransactionType.EXPENSE]
    elif type_filter == "Vendas":
        filtered_transactions = [t for t in filtered_transactions if t.transaction_type == TransactionType.INCOME]
    
    if filtered_transactions:
        pagination_sig = (selected_filter if investments else None, type_filter)
        if st.session_state.get("inv_hist_pagination_sig") != pagination_sig:
            st.session_state.inv_hist_pagination_sig = pagination_sig
            st.session_state.inv_hist_page = 1

        page_size = st.session_state.get("inv_hist_page_size", 20)
        total = len(filtered_transactions)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current_page = int(st.session_state.get("inv_hist_page", 1))
        current_page = max(1, min(current_page, total_pages))
        st.session_state.inv_hist_page = current_page

        start_idx = (st.session_state.inv_hist_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)

        page_linked_transactions = filtered_transactions[start_idx:end_idx]

        header_cols = st.columns([1.2, 1, 0.9, 0.8, 1.1, 1.1, 2.0, 0.5])
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
            st.markdown("**Resultado**")
        with header_cols[7]:
            st.markdown("**Ação**")
        st.markdown("---")
        
        for t in page_linked_transactions:
            with st.container():
                qty = float(t.quantity or 0)
                price_unit = float(t.price_per_unit or 0)
                total_value = qty * price_unit
                is_sale = t.transaction_type == TransactionType.INCOME
                
                col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1.2, 1, 0.9, 0.8, 1.1, 1.1, 2.0, 0.5])
                with col1:
                    st.write(t.date.strftime("%d/%m/%Y"))
                with col2:
                    st.write(t.investment.ticker if t.investment else "-")
                with col3:
                    if is_sale:
                        st.markdown(":green[💰 Venda]")
                    else:
                        st.markdown(":blue[🛒 Compra]")
                with col4:
                    st.write(f"{qty:,.2f}")
                with col5:
                    st.write(f"R$ {price_unit:,.2f}")
                with col6:
                    st.write(f"R$ {total_value:,.2f}")
                with col7:
                    if is_sale:
                        if t.investment:
                            avg_price = float(t.investment.average_price)
                            cost_basis = qty * avg_price
                            realized_profit = total_value - cost_basis
                            profit_pct = (realized_profit / cost_basis * 100) if cost_basis > 0 else 0
                            color = "green" if realized_profit >= 0 else "red"
                            st.markdown(f":{color}[**Lucro: R$ {realized_profit:+,.2f}** ({profit_pct:+.1f}%)]")
                        else:
                            st.write("-")
                    else:
                        current_price = float(t.investment.current_price or 0) if t.investment else 0
                        if current_price > 0:
                            current_value = qty * current_price
                            variation = current_value - total_value
                            variation_pct = (variation / total_value * 100) if total_value > 0 else 0
                            color = "green" if variation >= 0 else "red"
                            st.markdown(f":{color}[Var: R$ {variation:+,.2f} ({variation_pct:+.1f}%)]")
                        else:
                            st.caption("Atualizar cotação")
                with col8:
                    if st.button("🗑️", key=f"delete_{t.id}", help="Excluir transação"):
                        session.delete(t)
                        session.commit()
                        st.toast("🗑️ Transação excluída!", icon="🗑️")
                        st.rerun()
        
        col_pag1, col_pag2, col_pag3 = st.columns([2, 2, 2])
        with col_pag1:
            new_page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="inv_hist_page_input",
            )
            if new_page != current_page:
                st.session_state.inv_hist_page = int(new_page)
                st.rerun()
        with col_pag2:
            new_page_size = st.selectbox(
                "Itens por página",
                [10, 20, 50, 100],
                index=[10, 20, 50, 100].index(page_size) if page_size in [10, 20, 50, 100] else 1,
                key="inv_hist_page_size_select",
            )
            if new_page_size != page_size:
                st.session_state.inv_hist_page_size = new_page_size
                st.session_state.inv_hist_page = 1
                st.rerun()
        with col_pag3:
            st.markdown(f"Mostrando **{start_idx + 1}–{end_idx}** de **{total}**")
    else:
        st.info("Nenhuma transação de investimento registrada")

session.close()
