import streamlit as st
from decimal import Decimal
from database import get_session
from database.models import Budget, Category, CategoryType

st.title("📋 Orçamentos")
st.caption("Defina limites de gastos por categoria")

session = get_session()

if "budget_saved" not in st.session_state:
    st.session_state.budget_saved = False
if "budget_saved_name" not in st.session_state:
    st.session_state.budget_saved_name = None

if st.session_state.budget_saved:
    if st.session_state.budget_saved_name:
        st.toast(f"✅ Orçamento de {st.session_state.budget_saved_name} salvo!", icon="✅")
    else:
        st.toast("✅ Todos os orçamentos foram salvos!", icon="✅")
    st.session_state.budget_saved = False
    st.session_state.budget_saved_name = None

expense_categories = session.query(Category).filter(Category.category_type == CategoryType.EXPENSE).all()
cc_categories = session.query(Category).filter(Category.category_type == CategoryType.CREDIT_CARD).all()

budgets = {b.category_id: b for b in session.query(Budget).all()}

st.markdown("### Orçamentos de Despesas")
st.markdown("---")

for cat in expense_categories:
    budget = budgets.get(cat.id)
    current_value = float(budget.planned_amount) if budget else 0.0
    
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.markdown(f"<div style='display:flex; align-items:center; height:40px;'>"
                   f"<div style='width:20px; height:20px; background-color:{cat.color or '#9333ea'}; border-radius:3px; margin-right:10px;'></div>"
                   f"<span style='color:#f5f5f5;'>{cat.name}</span></div>", unsafe_allow_html=True)
    with col2:
        new_value = st.number_input(
            "Valor Planejado (R$)",
            min_value=0.0,
            step=50.0,
            format="%.2f",
            value=current_value,
            key=f"budget_{cat.id}",
            label_visibility="collapsed"
        )
    with col3:
        if st.button("💾", key=f"save_budget_{cat.id}"):
            if budget:
                budget.planned_amount = Decimal(str(new_value))
            else:
                new_budget = Budget(
                    category_id=cat.id,
                    planned_amount=Decimal(str(new_value))
                )
                session.add(new_budget)
            session.commit()
            st.session_state.budget_saved = True
            st.session_state.budget_saved_name = cat.name
            st.rerun()

st.markdown("---")
st.markdown("### Orçamentos de Cartão de Crédito")
st.markdown("---")

for cat in cc_categories:
    budget = budgets.get(cat.id)
    current_value = float(budget.planned_amount) if budget else 0.0
    
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        st.markdown(f"<div style='display:flex; align-items:center; height:40px;'>"
                   f"<div style='width:20px; height:20px; background-color:{cat.color or '#a855f7'}; border-radius:3px; margin-right:10px;'></div>"
                   f"<span style='color:#f5f5f5;'>{cat.name}</span></div>", unsafe_allow_html=True)
    with col2:
        new_value = st.number_input(
            "Valor Planejado (R$)",
            min_value=0.0,
            step=50.0,
            format="%.2f",
            value=current_value,
            key=f"budget_cc_{cat.id}",
            label_visibility="collapsed"
        )
    with col3:
        if st.button("💾", key=f"save_budget_cc_{cat.id}"):
            if budget:
                budget.planned_amount = Decimal(str(new_value))
            else:
                new_budget = Budget(
                    category_id=cat.id,
                    planned_amount=Decimal(str(new_value))
                )
                session.add(new_budget)
            session.commit()
            st.session_state.budget_saved = True
            st.session_state.budget_saved_name = cat.name
            st.rerun()

st.markdown("---")
st.markdown("### Salvar Todos os Orçamentos")

if st.button("💾 Salvar Todos", type="primary", use_container_width=True):
    for cat in expense_categories + cc_categories:
        key = f"budget_{cat.id}" if cat.category_type == CategoryType.EXPENSE else f"budget_cc_{cat.id}"
        if key in st.session_state:
            new_value = st.session_state[key]
            budget = budgets.get(cat.id)
            if budget:
                budget.planned_amount = Decimal(str(new_value))
            elif new_value > 0:
                new_budget = Budget(
                    category_id=cat.id,
                    planned_amount=Decimal(str(new_value))
                )
                session.add(new_budget)
    session.commit()
    st.session_state.budget_saved = True
    st.session_state.budget_saved_name = None
    st.rerun()

session.close()
