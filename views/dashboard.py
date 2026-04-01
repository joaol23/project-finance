import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
from decimal import Decimal
from database import get_session
from database.models import Transaction, TransactionType, Category, CategoryType, Account, CreditCardTransaction, Budget, MonthlyOpeningBalance

st.title("📊 Painel")
st.caption("Visão geral das suas finanças")

session = get_session()

today = date.today()

col_filter1, col_filter2 = st.columns(2)

def last_business_day(year: int, month: int) -> date:
    """
    Retorna o último dia útil do mês.

    Nota: aqui consideramos como "dia útil" apenas de segunda a sexta, com uma exceção
    prática comum em fechamentos bancários: 31/12 é tratado como não útil.
    """
    # Último dia do mês (dia anterior ao primeiro dia do mês seguinte)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    d = last_day
    while True:
        # weekday(): Monday=0 ... Sunday=6
        if d.weekday() < 5:
            # Ajuste para o exemplo informado: 31/12 costuma ser considerado "fora do útil"
            if not (d.month == 12 and d.day == 31):
                return d
        d -= timedelta(days=1)

def month_period_bounds(year: int, month: int) -> tuple[date, date]:
    """
    Para o mês selecionado, define:
      início (marco) = último dia útil do mês anterior
      fim            = último dia útil do mês selecionado

    Regra de contagem (sem sobreposição):
      período do mês = (início, fim]  -> exclusivo no início, inclusivo no fim
    """
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    start_boundary = last_business_day(prev_year, prev_month)
    end_boundary = last_business_day(year, month)
    return start_boundary, end_boundary

with col_filter1:
    selected_month = st.selectbox("📅 Mês", range(1, 13), index=today.month - 1, 
                                   format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                          "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1])
with col_filter2:
    years = list(range(2020, today.year + 2))
    selected_year = st.selectbox("📆 Ano", years, index=years.index(today.year))

period_start_boundary, period_end = month_period_bounds(selected_year, selected_month)
period_start = period_start_boundary

account = session.query(Account).first()
account_initial_balance = Decimal(str(account.initial_balance)) if account else Decimal("0")

transactions = session.query(Transaction).filter(
    Transaction.date > period_start_boundary,
    Transaction.date <= period_end
).all()

total_income = sum(Decimal(str(t.amount)) for t in transactions if t.transaction_type == TransactionType.INCOME)
total_expense = sum(Decimal(str(t.amount)) for t in transactions if t.transaction_type == TransactionType.EXPENSE)

prev_transactions = session.query(Transaction).filter(
    Transaction.date < period_start_boundary
).all()
prev_balance = account_initial_balance
for t in prev_transactions:
    if t.transaction_type == TransactionType.INCOME:
        prev_balance += Decimal(str(t.amount))
    else:
        prev_balance -= Decimal(str(t.amount))

#
# Sugestão do saldo inicial:
# - Se existir "saldo inicial manual" salvo para o mês anterior, a sugestão do mês atual
#   será o "saldo final" do mês anterior calculado com o saldo inicial manual.
# - Caso contrário, usamos a sugestão automática (acumulado até o marco contábil).
#
prev_year = selected_year - 1 if selected_month == 1 else selected_year
prev_month = 12 if selected_month == 1 else (selected_month - 1)

prev_month_record = session.query(MonthlyOpeningBalance).filter_by(
    year=prev_year,
    month=prev_month,
).first()

if prev_month_record:
    suggestion_source = f"saldo manual salvo em {prev_month:02d}/{prev_year}"
    prev_start_boundary, prev_end_boundary = month_period_bounds(prev_year, prev_month)

    prev_month_transactions = session.query(Transaction).filter(
        Transaction.date >= prev_start_boundary,
        # Importante: evitamos duplicidade do "dia de virada" (fim do mês anterior),
        # já que ele é o início do mês atual.
        Transaction.date < prev_end_boundary,
    ).all()

    prev_month_income = sum(
        Decimal(str(t.amount)) for t in prev_month_transactions
        if t.transaction_type == TransactionType.INCOME
    )
    prev_month_expense = sum(
        Decimal(str(t.amount)) for t in prev_month_transactions
        if t.transaction_type == TransactionType.EXPENSE
    )

    prev_month_closing = Decimal(str(prev_month_record.initial_balance)) + prev_month_income - prev_month_expense
    suggested_opening_balance = prev_month_closing
else:
    suggestion_source = "acumulado automático até o marco"
    suggested_opening_balance = prev_balance

monthly_record = session.query(MonthlyOpeningBalance).filter_by(
    year=selected_year,
    month=selected_month,
).first()

default_opening = float(monthly_record.initial_balance) if monthly_record else float(suggested_opening_balance)

with st.expander("⚙️ Configurar Saldo Inicial", expanded=False):
    st.caption(f"Período contábil: {period_start:%d/%m/%Y} até {period_end:%d/%m/%Y}")
    st.caption(f"💡 Sugestão: R$ {suggested_opening_balance:,.2f} — {suggestion_source}")
    
    col_balance1, col_balance2 = st.columns([3, 1])
    with col_balance1:
        manual_opening_balance = st.number_input(
            "Saldo Inicial",
            value=default_opening,
            step=0.01,
            format="%.2f",
            key=f"manual_opening_{selected_year}_{selected_month}",
            label_visibility="collapsed"
        )
    with col_balance2:
        if st.button("💾 Salvar", key=f"save_manual_opening_{selected_year}_{selected_month}", type="primary", use_container_width=True):
            new_value = Decimal(str(manual_opening_balance))
            if monthly_record:
                monthly_record.initial_balance = new_value
            else:
                monthly_record = MonthlyOpeningBalance(
                    year=selected_year,
                    month=selected_month,
                    initial_balance=new_value,
                )
                session.add(monthly_record)
            session.commit()
            st.toast("✅ Saldo inicial salvo", icon="✅")

opening_balance = Decimal(str(manual_opening_balance))
closing_balance = opening_balance + total_income - total_expense

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
    if closing_balance < 0:
        delta_color = "inverse" if delta > 0 else "normal"
    else:
        delta_color = "normal"
    st.metric("Saldo Final", f"R$ {closing_balance:,.2f}", 
              delta=f"R$ {delta:+,.2f}" if delta != 0 else None,
              delta_color=delta_color)

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
        purple_palette = ['#9333ea', '#a855f7', '#7c3aed', '#8b5cf6', '#6366f1', '#818cf8', '#c084fc', '#a78bfa']
        fig = px.pie(
            values=list(expense_by_cat.values()),
            names=list(expense_by_cat.keys()),
            hole=0.4,
            color_discrete_sequence=purple_palette
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f5f5f5',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(color='#9ca3af'))
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
        gray_green_palette = ['#22c55e', '#4ade80', '#86efac', '#6b7280', '#9ca3af', '#d1d5db', '#e5e7eb', '#f3f4f6']
        fig = px.pie(
            values=list(income_by_cat.values()),
            names=list(income_by_cat.keys()),
            hole=0.4,
            color_discrete_sequence=gray_green_palette
        )
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color='#f5f5f5',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, font=dict(color='#9ca3af'))
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
    fig.add_trace(go.Bar(name='Planejado', x=df_budget['Categoria'], y=df_budget['Planejado'], marker_color='#9333ea'))
    fig.add_trace(go.Bar(name='Realizado', x=df_budget['Categoria'], y=df_budget['Realizado'], marker_color='#6b7280'))
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#f5f5f5',
        xaxis=dict(showgrid=False, color='#9ca3af'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum orçamento de despesas definido")

st.markdown("---")
st.markdown("### Gastos no Cartão de Crédito")

cc_transactions = session.query(CreditCardTransaction).filter(
    CreditCardTransaction.date > period_start_boundary,
    CreditCardTransaction.date <= period_end
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
    fig.add_trace(go.Bar(name='Planejado', x=df_cc_budget['Categoria'], y=df_cc_budget['Planejado'], marker_color='#a855f7'))
    fig.add_trace(go.Bar(name='Realizado', x=df_cc_budget['Categoria'], y=df_cc_budget['Realizado'], marker_color='#6b7280'))
    fig.update_layout(
        barmode='group',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#f5f5f5',
        xaxis=dict(showgrid=False, color='#9ca3af'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', color='#9ca3af'),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)
elif cc_by_cat:
    fig = px.bar(
        x=list(cc_by_cat.keys()),
        y=list(cc_by_cat.values()),
        color_discrete_sequence=['#9333ea']
    )
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color='#f5f5f5',
        xaxis_title="",
        yaxis_title="Valor (R$)",
        xaxis=dict(color='#9ca3af'),
        yaxis=dict(color='#9ca3af'),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    st.info("💡 Defina orçamentos para categorias de cartão na página de Orçamentos")
else:
    st.info("Nenhum gasto no cartão neste mês")

session.close()
