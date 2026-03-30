import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime
from decimal import Decimal
from database import get_session
from database.models import Transaction, TransactionType, Category, CategoryType, Account, CreditCardTransaction, Budget

st.title("📊 Painel")

session = get_session()

today = date.today()
col_filter1, col_filter2 = st.columns(2)
with col_filter1:
    selected_month = st.selectbox("Mês", range(1, 13), index=today.month - 1, 
                                   format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                          "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1])
with col_filter2:
    years = list(range(2020, today.year + 2))
    selected_year = st.selectbox("Ano", years, index=years.index(today.year))

account = session.query(Account).first()
initial_balance = float(account.initial_balance) if account else 0

transactions = session.query(Transaction).filter(
    Transaction.date >= date(selected_year, selected_month, 1),
    Transaction.date < date(selected_year + (1 if selected_month == 12 else 0), 
                           (selected_month % 12) + 1, 1)
).all()

total_income = sum(float(t.amount) for t in transactions if t.transaction_type == TransactionType.INCOME)
total_expense = sum(float(t.amount) for t in transactions if t.transaction_type == TransactionType.EXPENSE)

prev_transactions = session.query(Transaction).filter(
    Transaction.date < date(selected_year, selected_month, 1)
).all()
prev_balance = initial_balance
for t in prev_transactions:
    if t.transaction_type == TransactionType.INCOME:
        prev_balance += float(t.amount)
    else:
        prev_balance -= float(t.amount)

opening_balance = prev_balance
closing_balance = opening_balance + total_income - total_expense

st.markdown("### Resumo do Mês")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Saldo Inicial", f"R$ {opening_balance:,.2f}")

with col2:
    st.metric("Entradas", f"R$ {total_income:,.2f}", 
              delta=f"R$ {total_income:,.2f}" if total_income > 0 else None,
              delta_color="off")

with col3:
    st.metric("Saídas", f"R$ {total_expense:,.2f}", 
              delta=f"R$ {total_expense:,.2f}" if total_expense > 0 else None,
              delta_color="off")

with col4:
    delta = closing_balance - opening_balance
    st.metric("Saldo Final", f"R$ {closing_balance:,.2f}", 
              delta=f"R$ {delta:+,.2f}" if delta != 0 else None,
              delta_color="normal")

with col5:
    if opening_balance != 0:
        pct_change = ((closing_balance - opening_balance) / abs(opening_balance)) * 100
    else:
        pct_change = 100 if closing_balance > 0 else (-100 if closing_balance < 0 else 0)
    
    st.metric("Variação", f"{pct_change:+.1f}%", 
              delta=f"{pct_change:+.1f}%" if pct_change != 0 else None,
              delta_color="normal")

st.markdown("---")

col_charts1, col_charts2 = st.columns(2)

with col_charts1:
    st.markdown("### Despesas por Categoria")
    expense_by_cat = {}
    for t in transactions:
        if t.transaction_type == TransactionType.EXPENSE and t.category:
            cat_name = t.category.name
            expense_by_cat[cat_name] = expense_by_cat.get(cat_name, 0) + float(t.amount)
    
    if expense_by_cat:
        fig = px.pie(
            values=list(expense_by_cat.values()),
            names=list(expense_by_cat.keys()),
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma despesa registrada neste mês")

with col_charts2:
    st.markdown("### Entradas por Categoria")
    income_by_cat = {}
    for t in transactions:
        if t.transaction_type == TransactionType.INCOME and t.category:
            cat_name = t.category.name
            income_by_cat[cat_name] = income_by_cat.get(cat_name, 0) + float(t.amount)
    
    if income_by_cat:
        fig = px.pie(
            values=list(income_by_cat.values()),
            names=list(income_by_cat.keys()),
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='white',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma entrada registrada neste mês")

st.markdown("---")
st.markdown("### Orçamento vs Realizado (Despesas)")

budgets = session.query(Budget).all()
expense_categories = session.query(Category).filter(Category.category_type == CategoryType.EXPENSE).all()

budget_data = []
for cat in expense_categories:
    budget = next((b for b in budgets if b.category_id == cat.id), None)
    planned = float(budget.planned_amount) if budget else 0
    actual = expense_by_cat.get(cat.name, 0)
    if planned > 0 or actual > 0:
        budget_data.append({
            "Categoria": cat.name,
            "Planejado": planned,
            "Realizado": actual,
            "Diferença": planned - actual
        })

if budget_data:
    df_budget = pd.DataFrame(budget_data)
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Planejado', x=df_budget['Categoria'], y=df_budget['Planejado'], marker_color='#3b82f6'))
    fig.add_trace(go.Bar(name='Realizado', x=df_budget['Categoria'], y=df_budget['Realizado'], marker_color='#ef4444'))
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum orçamento de despesas definido")

st.markdown("---")
st.markdown("### Gastos no Cartão de Crédito")

cc_transactions = session.query(CreditCardTransaction).filter(
    CreditCardTransaction.date >= date(selected_year, selected_month, 1),
    CreditCardTransaction.date < date(selected_year + (1 if selected_month == 12 else 0), 
                                      (selected_month % 12) + 1, 1)
).all()

total_cc = sum(float(t.amount) for t in cc_transactions)

cc_by_cat = {}
for t in cc_transactions:
    if t.category:
        cat_name = t.category.name
        cc_by_cat[cat_name] = cc_by_cat.get(cat_name, 0) + float(t.amount)

st.metric("Total Cartão de Crédito", f"R$ {total_cc:,.2f}")

st.markdown("---")
st.markdown("### Orçamento vs Realizado (Cartão de Crédito)")

cc_categories = session.query(Category).filter(Category.category_type == CategoryType.CREDIT_CARD).all()

cc_budget_data = []
for cat in cc_categories:
    budget = next((b for b in budgets if b.category_id == cat.id), None)
    planned = float(budget.planned_amount) if budget else 0
    actual = cc_by_cat.get(cat.name, 0)
    if planned > 0 or actual > 0:
        cc_budget_data.append({
            "Categoria": cat.name,
            "Planejado": planned,
            "Realizado": actual,
            "Diferença": planned - actual
        })

if cc_budget_data:
    df_cc_budget = pd.DataFrame(cc_budget_data)
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Planejado', x=df_cc_budget['Categoria'], y=df_cc_budget['Planejado'], marker_color='#8b5cf6'))
    fig.add_trace(go.Bar(name='Realizado', x=df_cc_budget['Categoria'], y=df_cc_budget['Realizado'], marker_color='#e94560'))
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
elif cc_by_cat:
    fig = px.bar(
        x=list(cc_by_cat.keys()),
        y=list(cc_by_cat.values()),
        color_discrete_sequence=['#e94560']
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='white',
        xaxis_title="",
        yaxis_title="Valor (R$)",
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Defina orçamentos para categorias de cartão na página de Orçamentos")
else:
    st.info("Nenhum gasto no cartão neste mês")

session.close()
