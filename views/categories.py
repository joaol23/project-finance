import streamlit as st
from sqlalchemy import func
from database import get_session
from database.models import Category, CategoryType, Transaction, CreditCardTransaction

st.title("📁 Categorias")
st.caption("Organize suas transações por categorias")

session = get_session()

type_labels = {
    CategoryType.INCOME: "Entrada",
    CategoryType.EXPENSE: "Saída",
    CategoryType.CREDIT_CARD: "Cartão de Crédito"
}

if "cat_saved" not in st.session_state:
    st.session_state.cat_saved = False
if "cat_updated" not in st.session_state:
    st.session_state.cat_updated = False

if st.session_state.cat_updated:
    st.toast("✅ Categoria atualizada!", icon="✅")
    st.session_state.cat_updated = False

def clear_category_form():
    keys_to_clear = ["new_cat_name", "new_cat_type", "new_cat_color"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

if st.session_state.cat_saved:
    st.toast("✅ Categoria salva com sucesso!", icon="✅")
    st.session_state.cat_saved = False

tab_list, tab_add = st.tabs(["📋 Lista de Categorias", "➕ Nova Categoria"])

with tab_add:
    st.markdown("### Adicionar Categoria")
    
    col1, col2 = st.columns(2)
    with col1:
        cat_name = st.text_input("Nome da Categoria", key="new_cat_name", value="")
    with col2:
        cat_type = st.selectbox("Tipo", ["Entrada", "Saída", "Cartão de Crédito"], key="new_cat_type")
    
    col3, col4 = st.columns(2)
    with col3:
        cat_color = st.color_picker("Cor", value="#9333ea", key="new_cat_color")
    with col4:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        st.markdown(f"<div style='width:100%; height:40px; background-color:{cat_color}; border-radius:5px;'></div>", 
                   unsafe_allow_html=True)
    
    if st.button("💾 Salvar Categoria", type="primary", use_container_width=True):
        if cat_name:
            type_map = {
                "Entrada": CategoryType.INCOME,
                "Saída": CategoryType.EXPENSE,
                "Cartão de Crédito": CategoryType.CREDIT_CARD
            }
            new_category = Category(
                name=cat_name,
                category_type=type_map[cat_type],
                color=cat_color
            )
            session.add(new_category)
            session.commit()
            st.session_state.cat_saved = True
            clear_category_form()
            st.rerun()
        else:
            st.error("Preencha o nome da categoria")

with tab_list:
    categories = session.query(Category).order_by(Category.category_type, Category.name).all()
    
    trans_counts = dict(session.query(
        Transaction.category_id,
        func.count(Transaction.id)
    ).group_by(Transaction.category_id).all())
    
    cc_trans_counts = dict(session.query(
        CreditCardTransaction.category_id,
        func.count(CreditCardTransaction.id)
    ).group_by(CreditCardTransaction.category_id).all())
    
    def get_trans_count(cat):
        if cat.category_type == CategoryType.CREDIT_CARD:
            return cc_trans_counts.get(cat.id, 0)
        return trans_counts.get(cat.id, 0)
    
    unused_cats = [c for c in categories if get_trans_count(c) == 0]
    if unused_cats:
        st.warning(f"⚠️ {len(unused_cats)} categoria(s) sem transações vinculadas")
    
    st.markdown("### Categorias de Entrada")
    income_cats = [c for c in categories if c.category_type == CategoryType.INCOME]
    for cat in income_cats:
        count = get_trans_count(cat)
        count_label = ":orange[0 transações]" if count == 0 else f"{count} transações"
        with st.expander(f"🟢 {cat.name} | {count_label}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("Nome", value=cat.name, key=f"edit_name_{cat.id}")
            with col2:
                edit_color = st.color_picker("Cor", value=cat.color or "#3b82f6", key=f"edit_color_{cat.id}")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar", type="primary", key=f"save_cat_{cat.id}", use_container_width=True):
                    cat.name = edit_name
                    cat.color = edit_color
                    session.commit()
                    st.session_state.cat_updated = True
                    st.rerun()
            with col_btn2:
                if st.button("🗑️ Excluir", key=f"del_cat_{cat.id}", use_container_width=True):
                    session.delete(cat)
                    session.commit()
                    st.toast("🗑️ Categoria excluída!", icon="🗑️")
                    st.rerun()
    if not income_cats:
        st.info("Nenhuma categoria de entrada")
    
    st.markdown("---")
    st.markdown("### Categorias de Saída")
    expense_cats = [c for c in categories if c.category_type == CategoryType.EXPENSE]
    for cat in expense_cats:
        count = get_trans_count(cat)
        count_label = ":orange[0 transações]" if count == 0 else f"{count} transações"
        with st.expander(f"🔴 {cat.name} | {count_label}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("Nome", value=cat.name, key=f"edit_name_{cat.id}")
            with col2:
                edit_color = st.color_picker("Cor", value=cat.color or "#ef4444", key=f"edit_color_{cat.id}")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar", type="primary", key=f"save_cat_{cat.id}", use_container_width=True):
                    cat.name = edit_name
                    cat.color = edit_color
                    session.commit()
                    st.session_state.cat_updated = True
                    st.rerun()
            with col_btn2:
                if st.button("🗑️ Excluir", key=f"del_cat_{cat.id}", use_container_width=True):
                    session.delete(cat)
                    session.commit()
                    st.toast("🗑️ Categoria excluída!", icon="🗑️")
                    st.rerun()
    if not expense_cats:
        st.info("Nenhuma categoria de saída")
    
    st.markdown("---")
    st.markdown("### Categorias de Cartão de Crédito")
    cc_cats = [c for c in categories if c.category_type == CategoryType.CREDIT_CARD]
    for cat in cc_cats:
        count = get_trans_count(cat)
        count_label = ":orange[0 transações]" if count == 0 else f"{count} transações"
        with st.expander(f"💳 {cat.name} | {count_label}"):
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("Nome", value=cat.name, key=f"edit_name_{cat.id}")
            with col2:
                edit_color = st.color_picker("Cor", value=cat.color or "#e94560", key=f"edit_color_{cat.id}")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar", type="primary", key=f"save_cat_{cat.id}", use_container_width=True):
                    cat.name = edit_name
                    cat.color = edit_color
                    session.commit()
                    st.session_state.cat_updated = True
                    st.rerun()
            with col_btn2:
                if st.button("🗑️ Excluir", key=f"del_cat_{cat.id}", use_container_width=True):
                    session.delete(cat)
                    session.commit()
                    st.toast("🗑️ Categoria excluída!", icon="🗑️")
                    st.rerun()
    if not cc_cats:
        st.info("Nenhuma categoria de cartão de crédito")

session.close()
