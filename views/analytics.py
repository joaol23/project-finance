import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from decimal import Decimal
from database import get_session
from database.models import Transaction, TransactionType, Category, CategoryType, Budget, CreditCardTransaction, CreditCard

st.title("📊 Análises")
st.caption("Insights detalhados sobre seus gastos")

session = get_session()

today = date.today()

col_filter1, col_filter2, col_filter3 = st.columns(3)
with col_filter1:
    analysis_type = st.selectbox(
        "Analisar",
        ["💸 Transações", "💳 Cartão de Crédito", "📊 Ambos"],
        key="analytics_type"
    )
with col_filter2:
    period_type = st.selectbox(
        "Período",
        ["Último mês", "Últimos 3 meses", "Últimos 6 meses", "Último ano", "Personalizado"],
        key="analytics_period"
    )

if period_type == "Último mês":
    end_date = today
    start_date = date(today.year, today.month, 1)
elif period_type == "Últimos 3 meses":
    end_date = today
    start_date = date(today.year, today.month, 1) - timedelta(days=90)
elif period_type == "Últimos 6 meses":
    end_date = today
    start_date = date(today.year, today.month, 1) - timedelta(days=180)
elif period_type == "Último ano":
    end_date = today
    start_date = date(today.year - 1, today.month, 1)
else:
    with col_filter3:
        date_range = st.date_input(
            "Selecione o período",
            value=(date(today.year, 1, 1), today),
            key="analytics_date_range"
        )
        if len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = date_range[0], today

transactions = session.query(Transaction).filter(
    Transaction.date >= start_date,
    Transaction.date <= end_date
).all()

cc_transactions = session.query(CreditCardTransaction).filter(
    CreditCardTransaction.date >= start_date,
    CreditCardTransaction.date <= end_date
).all()

expense_transactions = [t for t in transactions if t.transaction_type == TransactionType.EXPENSE]
income_transactions = [t for t in transactions if t.transaction_type == TransactionType.INCOME]

total_expense = sum(float(t.amount) for t in expense_transactions)
total_income = sum(float(t.amount) for t in income_transactions)
total_cc = sum(float(t.amount) for t in cc_transactions)

if analysis_type == "💸 Transações":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Entradas", f"R$ {total_income:,.2f}")
    with col2:
        st.metric("Total Saídas", f"R$ {total_expense:,.2f}")
    with col3:
        balance = total_income - total_expense
        st.metric("Saldo", f"R$ {balance:,.2f}", delta=f"R$ {balance:,.2f}", delta_color="normal" if balance >= 0 else "inverse")
    with col4:
        st.metric("Transações", len(transactions))
    analysis_transactions = expense_transactions
    total_for_analysis = total_expense
elif analysis_type == "💳 Cartão de Crédito":
    cards = session.query(CreditCard).all()
    card_totals = {}
    for t in cc_transactions:
        card_name = t.credit_card.name if t.credit_card else "Sem cartão"
        card_totals[card_name] = card_totals.get(card_name, 0) + float(t.amount)
    
    cols = st.columns(len(cards) + 2) if cards else st.columns(3)
    with cols[0]:
        st.metric("Total Cartões", f"R$ {total_cc:,.2f}")
    with cols[1]:
        st.metric("Transações", len(cc_transactions))
    for i, card in enumerate(cards):
        with cols[i + 2]:
            card_total = card_totals.get(card.name, 0)
            st.metric(f"💳 {card.name}", f"R$ {card_total:,.2f}")
    analysis_transactions = cc_transactions
    total_for_analysis = total_cc
else:
    combined_expense = total_expense + total_cc
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Entradas", f"R$ {total_income:,.2f}")
    with col2:
        st.metric("Saídas (Trans.)", f"R$ {total_expense:,.2f}")
    with col3:
        st.metric("Saídas (Cartão)", f"R$ {total_cc:,.2f}")
    with col4:
        st.metric("Total Saídas", f"R$ {combined_expense:,.2f}")
    with col5:
        balance = total_income - combined_expense
        st.metric("Saldo", f"R$ {balance:,.2f}", delta_color="normal" if balance >= 0 else "inverse")
    
    class CombinedTransaction:
        def __init__(self, t, source):
            self.date = t.date
            self.amount = t.amount
            self.description = t.description
            self.category = t.category
            self.source = source
    
    analysis_transactions = [CombinedTransaction(t, "Transação") for t in expense_transactions]
    analysis_transactions += [CombinedTransaction(t, "Cartão") for t in cc_transactions]
    total_for_analysis = combined_expense

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏆 Top Gastos",
    "📈 Evolução Mensal",
    "🎯 Orçamento vs Real",
    "⚠️ Gastos Anômalos",
    "📊 Análise Pareto",
    "💳 Por Cartão",
    "💰 Análise de Receitas"
])

with tab1:
    st.markdown("### Top 10 Categorias com Maior Gasto")
    
    expense_by_cat = {}
    for t in analysis_transactions:
        if t.category:
            cat_name = t.category.name
            expense_by_cat[cat_name] = expense_by_cat.get(cat_name, 0) + float(t.amount)
        else:
            expense_by_cat["Sem categoria"] = expense_by_cat.get("Sem categoria", 0) + float(t.amount)
    
    if expense_by_cat:
        sorted_cats = sorted(expense_by_cat.items(), key=lambda x: x[1], reverse=True)[:10]
        df_top = pd.DataFrame(sorted_cats, columns=["Categoria", "Valor"])
        
        fig = px.bar(
            df_top,
            x="Valor",
            y="Categoria",
            orientation="h",
            color="Valor",
            color_continuous_scale=[[0, '#4b5563'], [0.5, '#7c3aed'], [1, '#9333ea']]
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f5f5f5',
            yaxis={'categoryorder': 'total ascending', 'color': '#9ca3af'},
            xaxis={'color': '#9ca3af'},
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Detalhamento")
        for cat, value in sorted_cats:
            pct = (value / total_for_analysis * 100) if total_for_analysis > 0 else 0
            st.markdown(f"**{cat}:** R$ {value:,.2f} ({pct:.1f}%)")
    else:
        st.info("Nenhuma despesa encontrada no período")

with tab2:
    st.markdown("### Evolução Mensal de Gastos por Categoria")
    
    if analysis_transactions:
        monthly_data = {}
        for t in analysis_transactions:
            month_key = t.date.strftime("%Y-%m")
            cat_name = t.category.name if t.category else "Sem categoria"
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {}
            monthly_data[month_key][cat_name] = monthly_data[month_key].get(cat_name, 0) + float(t.amount)
        
        all_cats = set()
        for month_cats in monthly_data.values():
            all_cats.update(month_cats.keys())
        
        rows = []
        for month, cats in sorted(monthly_data.items()):
            for cat in all_cats:
                rows.append({
                    "Mês": month,
                    "Categoria": cat,
                    "Valor": cats.get(cat, 0)
                })
        
        df_monthly = pd.DataFrame(rows)
        
        top_cats = list(expense_by_cat.keys())[:5] if expense_by_cat else []
        selected_cats = st.multiselect(
            "Selecione categorias para visualizar",
            sorted(all_cats),
            default=top_cats,
            key="monthly_cats"
        )
        
        if selected_cats:
            df_filtered = df_monthly[df_monthly["Categoria"].isin(selected_cats)]
            
            purple_sequence = ['#9333ea', '#a855f7', '#7c3aed', '#8b5cf6', '#6366f1', '#818cf8', '#c084fc', '#a78bfa']
            fig = px.line(
                df_filtered,
                x="Mês",
                y="Valor",
                color="Categoria",
                markers=True,
                color_discrete_sequence=purple_sequence
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f5f5f5',
                xaxis=dict(showgrid=False, color='#9ca3af'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
                legend=dict(font=dict(color='#9ca3af'))
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma despesa encontrada no período")

with tab3:
    st.markdown("### Orçamento vs Realizado")
    
    months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1
    months_diff = max(1, months_diff)
    
    if months_diff > 1:
        st.caption(f"📅 Período de **{months_diff} meses** - orçamento multiplicado pelo número de meses")
    
    budgets = session.query(Budget).all()
    budget_dict = {b.category_id: float(b.planned_amount) for b in budgets}
    
    if analysis_type == "💸 Transações":
        expense_categories = session.query(Category).filter(
            Category.category_type == CategoryType.EXPENSE
        ).all()
    elif analysis_type == "💳 Cartão de Crédito":
        expense_categories = session.query(Category).filter(
            Category.category_type == CategoryType.CREDIT_CARD
        ).all()
    else:
        expense_categories = session.query(Category).filter(
            Category.category_type.in_([CategoryType.EXPENSE, CategoryType.CREDIT_CARD])
        ).all()
    
    budget_comparison = []
    for cat in expense_categories:
        monthly_planned = budget_dict.get(cat.id, 0)
        planned = monthly_planned * months_diff
        actual = expense_by_cat.get(cat.name, 0)
        
        if planned > 0 or actual > 0:
            diff = planned - actual
            pct_used = (actual / planned * 100) if planned > 0 else 0
            status = "🟢 OK" if actual <= planned else "🔴 Estourado"
            
            budget_comparison.append({
                "Categoria": cat.name,
                "Planejado": planned,
                "Realizado": actual,
                "Diferença": diff,
                "% Usado": pct_used,
                "Status": status
            })
    
    if budget_comparison:
        df_budget = pd.DataFrame(budget_comparison)
        df_budget = df_budget.sort_values("Realizado", ascending=False)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='Planejado',
            x=df_budget['Categoria'],
            y=df_budget['Planejado'],
            marker_color='#9333ea'
        ))
        fig.add_trace(go.Bar(
            name='Realizado',
            x=df_budget['Categoria'],
            y=df_budget['Realizado'],
            marker_color=df_budget['Diferença'].apply(lambda x: '#22c55e' if x >= 0 else '#ef4444')
        ))
        fig.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f5f5f5',
            xaxis=dict(showgrid=False, color='#9ca3af'),
            yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#9ca3af'))
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("#### Resumo")
        estourados = [b for b in budget_comparison if b["Diferença"] < 0]
        if estourados:
            st.error(f"**{len(estourados)} categoria(s) estourada(s):**")
            for b in sorted(estourados, key=lambda x: x["Diferença"]):
                st.markdown(f"- **{b['Categoria']}:** R$ {abs(b['Diferença']):,.2f} acima do orçamento ({b['% Usado']:.1f}%)")
        else:
            st.success("✅ Todos os orçamentos estão dentro do planejado!")
    else:
        st.info("Nenhum orçamento definido ou sem gastos no período")

with tab4:
    st.markdown("### Gastos Anômalos")
    st.markdown("Transações significativamente acima da média da categoria.")
    
    if analysis_transactions and expense_by_cat:
        cat_transactions = {}
        for t in analysis_transactions:
            cat_name = t.category.name if t.category else "Sem categoria"
            if cat_name not in cat_transactions:
                cat_transactions[cat_name] = []
            cat_transactions[cat_name].append(t)
        
        anomalies = []
        for cat_name, trans_list in cat_transactions.items():
            if len(trans_list) >= 3:
                values = [float(t.amount) for t in trans_list]
                mean = sum(values) / len(values)
                
                for t in trans_list:
                    value = float(t.amount)
                    if value > mean * 2:
                        anomalies.append({
                            "Data": t.date,
                            "Categoria": cat_name,
                            "Descrição": t.description,
                            "Valor": value,
                            "Média Cat.": mean,
                            "Desvio": value / mean
                        })
        
        if anomalies:
            anomalies = sorted(anomalies, key=lambda x: x["Desvio"], reverse=True)[:20]
            st.warning(f"**{len(anomalies)} transação(ões) anômala(s) encontrada(s)**")
            
            for a in anomalies:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{a['Data'].strftime('%d/%m/%Y')}** - {a['Descrição']}")
                        st.caption(f"Categoria: {a['Categoria']}")
                    with col2:
                        st.markdown(f":red[R$ {a['Valor']:,.2f}]")
                        st.caption(f"Média: R$ {a['Média Cat.']:,.2f} ({a['Desvio']:.1f}x)")
                    st.markdown("---")
        else:
            st.success("✅ Nenhuma transação anômala encontrada")
    else:
        st.info("Dados insuficientes para análise de anomalias")

with tab5:
    st.markdown("### Análise de Pareto (80/20)")
    st.markdown("Identificando os gastos que representam 80% do total.")
    
    if expense_by_cat:
        sorted_cats = sorted(expense_by_cat.items(), key=lambda x: x[1], reverse=True)
        
        cumulative = 0
        pareto_data = []
        for cat, value in sorted_cats:
            cumulative += value
            pct_individual = (value / total_for_analysis * 100) if total_for_analysis > 0 else 0
            pct_cumulative = (cumulative / total_for_analysis * 100) if total_for_analysis > 0 else 0
            pareto_data.append({
                "Categoria": cat,
                "Valor": value,
                "% Individual": pct_individual,
                "% Acumulado": pct_cumulative
            })
        
        df_pareto = pd.DataFrame(pareto_data)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_pareto['Categoria'],
            y=df_pareto['Valor'],
            name='Valor',
            marker_color='#9333ea'
        ))
        fig.add_trace(go.Scatter(
            x=df_pareto['Categoria'],
            y=df_pareto['% Acumulado'],
            name='% Acumulado',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='#c084fc', width=2),
            marker=dict(size=8, color='#c084fc')
        ))
        fig.add_hline(y=80, line_dash="dash", line_color="#9ca3af", annotation_text="80%", yref="y2")
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f5f5f5',
            yaxis=dict(title='Valor (R$)', showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
            yaxis2=dict(title='% Acumulado', overlaying='y', side='right', range=[0, 105], color='#9ca3af'),
            xaxis=dict(showgrid=False, color='#9ca3af'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#9ca3af'))
        )
        st.plotly_chart(fig, use_container_width=True)
        
        cats_80 = [p for p in pareto_data if p["% Acumulado"] <= 80]
        if not cats_80 and pareto_data:
            cats_80 = [pareto_data[0]]
        
        st.markdown("#### Categorias que representam 80% dos gastos:")
        for p in cats_80:
            st.markdown(f"- **{p['Categoria']}:** R$ {p['Valor']:,.2f} ({p['% Individual']:.1f}%)")
        
        remaining = len(pareto_data) - len(cats_80)
        if remaining > 0:
            st.caption(f"As demais {remaining} categorias representam os outros 20% dos gastos.")
    else:
        st.info("Nenhuma despesa encontrada no período")

with tab6:
    st.markdown("### Resumo por Cartão")
    
    if cc_transactions:
        card_data = {}
        card_monthly = {}
        
        for t in cc_transactions:
            card_name = t.credit_card.name if t.credit_card else "Sem cartão"
            month_key = t.date.strftime("%Y-%m")
            
            card_data[card_name] = card_data.get(card_name, 0) + float(t.amount)
            
            if card_name not in card_monthly:
                card_monthly[card_name] = {}
            card_monthly[card_name][month_key] = card_monthly[card_name].get(month_key, 0) + float(t.amount)
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### Total por Cartão")
            for card, total in sorted(card_data.items(), key=lambda x: x[1], reverse=True):
                pct = (total / total_cc * 100) if total_cc > 0 else 0
                st.metric(f"💳 {card}", f"R$ {total:,.2f}", delta=f"{pct:.1f}%", delta_color="off")
        
        with col2:
            st.markdown("#### Evolução Mensal")
            monthly_rows = []
            for card, months in card_monthly.items():
                for month, value in months.items():
                    monthly_rows.append({"Cartão": card, "Mês": month, "Valor": value})
            
            if monthly_rows:
                df_card_monthly = pd.DataFrame(monthly_rows)
                purple_sequence = ['#9333ea', '#a855f7', '#7c3aed', '#8b5cf6', '#6366f1']
                fig_monthly = px.line(
                    df_card_monthly,
                    x="Mês",
                    y="Valor",
                    color="Cartão",
                    markers=True,
                    color_discrete_sequence=purple_sequence
                )
                fig_monthly.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    xaxis=dict(showgrid=False, color='#9ca3af'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
                    legend=dict(font=dict(color='#9ca3af')),
                    height=300
                )
                st.plotly_chart(fig_monthly, use_container_width=True)
        
        st.info("💡 Para análise detalhada por categoria, selecione **💳 Cartão de Crédito** no filtro acima e veja as outras abas.")
    else:
        st.info("Nenhuma transação de cartão de crédito encontrada no período")

with tab7:
    st.markdown("### Análise de Receitas (Entradas)")
    st.markdown("Insights detalhados sobre suas fontes de renda.")
    
    if income_transactions:
        income_by_cat = {}
        for t in income_transactions:
            if t.category:
                cat_name = t.category.name
                income_by_cat[cat_name] = income_by_cat.get(cat_name, 0) + float(t.amount)
            else:
                income_by_cat["Sem categoria"] = income_by_cat.get("Sem categoria", 0) + float(t.amount)
        
        col_inc1, col_inc2, col_inc3, col_inc4 = st.columns(4)
        with col_inc1:
            st.metric("Total de Entradas", f"R$ {total_income:,.2f}")
        with col_inc2:
            avg_income = total_income / len(income_transactions) if income_transactions else 0
            st.metric("Média por Transação", f"R$ {avg_income:,.2f}")
        with col_inc3:
            st.metric("Qtd. Transações", len(income_transactions))
        with col_inc4:
            num_sources = len(income_by_cat)
            st.metric("Fontes de Receita", num_sources)
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.markdown("#### Top Fontes de Receita")
            if income_by_cat:
                sorted_income = sorted(income_by_cat.items(), key=lambda x: x[1], reverse=True)[:10]
                df_income = pd.DataFrame(sorted_income, columns=["Categoria", "Valor"])
                
                fig_income = px.bar(
                    df_income,
                    x="Valor",
                    y="Categoria",
                    orientation="h",
                    color="Valor",
                    color_continuous_scale=[[0, '#059669'], [0.5, '#10b981'], [1, '#34d399']]
                )
                fig_income.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    yaxis={'categoryorder': 'total ascending', 'color': '#9ca3af'},
                    xaxis={'color': '#9ca3af'},
                    showlegend=False,
                    coloraxis_showscale=False,
                    height=350
                )
                st.plotly_chart(fig_income, use_container_width=True)
        
        with col_chart2:
            st.markdown("#### Distribuição por Fonte")
            if income_by_cat:
                green_palette = ['#22c55e', '#4ade80', '#86efac', '#10b981', '#34d399', '#6ee7b7']
                fig_pie = px.pie(
                    values=list(income_by_cat.values()),
                    names=list(income_by_cat.keys()),
                    hole=0.4,
                    color_discrete_sequence=green_palette
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    legend=dict(font=dict(color='#9ca3af')),
                    height=350
                )
                st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### Evolução Mensal das Receitas")
        
        monthly_income = {}
        for t in income_transactions:
            month_key = t.date.strftime("%Y-%m")
            cat_name = t.category.name if t.category else "Sem categoria"
            
            if month_key not in monthly_income:
                monthly_income[month_key] = {}
            monthly_income[month_key][cat_name] = monthly_income[month_key].get(cat_name, 0) + float(t.amount)
        
        if monthly_income:
            all_income_cats = set()
            for month_cats in monthly_income.values():
                all_income_cats.update(month_cats.keys())
            
            income_rows = []
            for month, cats in sorted(monthly_income.items()):
                for cat in all_income_cats:
                    income_rows.append({
                        "Mês": month,
                        "Categoria": cat,
                        "Valor": cats.get(cat, 0)
                    })
            
            df_income_monthly = pd.DataFrame(income_rows)
            
            top_income_cats = list(income_by_cat.keys())[:5] if income_by_cat else []
            selected_income_cats = st.multiselect(
                "Selecione categorias para visualizar",
                sorted(all_income_cats),
                default=top_income_cats,
                key="income_monthly_cats"
            )
            
            if selected_income_cats:
                df_filtered_income = df_income_monthly[df_income_monthly["Categoria"].isin(selected_income_cats)]
                
                green_sequence = ['#22c55e', '#10b981', '#059669', '#047857', '#065f46', '#064e3b']
                fig_income_line = px.line(
                    df_filtered_income,
                    x="Mês",
                    y="Valor",
                    color="Categoria",
                    markers=True,
                    color_discrete_sequence=green_sequence
                )
                fig_income_line.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='#f5f5f5',
                    xaxis=dict(showgrid=False, color='#9ca3af'),
                    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
                    legend=dict(font=dict(color='#9ca3af')),
                    height=350
                )
                st.plotly_chart(fig_income_line, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### Receitas vs Despesas")
        
        monthly_totals = {}
        for t in transactions:
            month_key = t.date.strftime("%Y-%m")
            if month_key not in monthly_totals:
                monthly_totals[month_key] = {"Receitas": 0, "Despesas": 0}
            
            if t.transaction_type == TransactionType.INCOME:
                monthly_totals[month_key]["Receitas"] += float(t.amount)
            else:
                monthly_totals[month_key]["Despesas"] += float(t.amount)
        
        if monthly_totals:
            comparison_rows = []
            for month in sorted(monthly_totals.keys()):
                data = monthly_totals[month]
                comparison_rows.append({
                    "Mês": month,
                    "Receitas": data["Receitas"],
                    "Despesas": data["Despesas"],
                    "Saldo": data["Receitas"] - data["Despesas"]
                })
            
            df_comparison = pd.DataFrame(comparison_rows)
            
            fig_comparison = go.Figure()
            fig_comparison.add_trace(go.Bar(
                name='Receitas',
                x=df_comparison['Mês'],
                y=df_comparison['Receitas'],
                marker_color='#22c55e'
            ))
            fig_comparison.add_trace(go.Bar(
                name='Despesas',
                x=df_comparison['Mês'],
                y=df_comparison['Despesas'],
                marker_color='#ef4444'
            ))
            fig_comparison.add_trace(go.Scatter(
                name='Saldo',
                x=df_comparison['Mês'],
                y=df_comparison['Saldo'],
                mode='lines+markers',
                line=dict(color='#9333ea', width=3),
                marker=dict(size=8)
            ))
            
            fig_comparison.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#f5f5f5',
                xaxis=dict(showgrid=False, color='#9ca3af'),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af', title='R$'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color='#9ca3af')),
                height=400
            )
            fig_comparison.add_hline(y=0, line_dash="dash", line_color="#9ca3af")
            st.plotly_chart(fig_comparison, use_container_width=True)
            
            positive_months = sum(1 for row in comparison_rows if row["Saldo"] > 0)
            negative_months = sum(1 for row in comparison_rows if row["Saldo"] < 0)
            total_months = len(comparison_rows)
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Meses Positivos", f"{positive_months}/{total_months}", 
                         delta=f"{positive_months/total_months*100:.0f}%" if total_months > 0 else "0%",
                         delta_color="normal")
            with col_stat2:
                st.metric("Meses Negativos", f"{negative_months}/{total_months}",
                         delta=f"{negative_months/total_months*100:.0f}%" if total_months > 0 else "0%",
                         delta_color="inverse")
            with col_stat3:
                avg_monthly_balance = sum(row["Saldo"] for row in comparison_rows) / total_months if total_months > 0 else 0
                balance_color = "normal" if avg_monthly_balance >= 0 else "inverse"
                st.metric("Saldo Médio Mensal", f"R$ {avg_monthly_balance:,.2f}",
                         delta_color=balance_color)
        
        st.markdown("---")
        st.markdown("#### Detalhamento por Fonte de Receita")
        
        for cat, value in sorted(income_by_cat.items(), key=lambda x: x[1], reverse=True):
            pct = (value / total_income * 100) if total_income > 0 else 0
            cat_transactions = [t for t in income_transactions if (t.category.name if t.category else "Sem categoria") == cat]
            avg_value = value / len(cat_transactions) if cat_transactions else 0
            
            with st.expander(f"💵 {cat} - R$ {value:,.2f} ({pct:.1f}%)"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total", f"R$ {value:,.2f}")
                with col2:
                    st.metric("Transações", len(cat_transactions))
                with col3:
                    st.metric("Média", f"R$ {avg_value:,.2f}")
                
                st.markdown("**Últimas transações:**")
                for t in sorted(cat_transactions, key=lambda x: x.date, reverse=True)[:5]:
                    st.markdown(f"- {t.date.strftime('%d/%m/%Y')}: R$ {float(t.amount):,.2f} - {t.description}")
    else:
        st.info("Nenhuma receita registrada no período selecionado.")
        st.markdown("Registre transações do tipo **Entrada** para ver análises de receitas.")

session.close()
