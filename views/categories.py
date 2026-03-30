import streamlit as st
from database import get_session
from database.models import Category, CategoryType

st.title("📁 Categorias")

session = get_session()

type_labels = {
    CategoryType.INCOME: "Entrada",
    CategoryType.EXPENSE: "Saída",
    CategoryType.CREDIT_CARD: "Cartão de Crédito"
}

if "cat_saved" not in st.session_state:
    st.session_state.cat_saved = False

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
        cat_color = st.color_picker("Cor", value="#3b82f6", key="new_cat_color")
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
    
    st.markdown("### Categorias de Entrada")
    income_cats = [c for c in categories if c.category_type == CategoryType.INCOME]
    for cat in income_cats:
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 4, 2, 1])
            with col1:
                st.markdown(f"<div style='width:30px; height:30px; background-color:{cat.color or '#3b82f6'}; border-radius:5px;'></div>", 
                           unsafe_allow_html=True)
            with col2:
                st.write(cat.name)
            with col3:
                st.write(type_labels[cat.category_type])
            with col4:
                if st.button("🗑️", key=f"del_cat_{cat.id}"):
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
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 4, 2, 1])
            with col1:
                st.markdown(f"<div style='width:30px; height:30px; background-color:{cat.color or '#ef4444'}; border-radius:5px;'></div>", 
                           unsafe_allow_html=True)
            with col2:
                st.write(cat.name)
            with col3:
                st.write(type_labels[cat.category_type])
            with col4:
                if st.button("🗑️", key=f"del_cat_{cat.id}"):
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
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 4, 2, 1])
            with col1:
                st.markdown(f"<div style='width:30px; height:30px; background-color:{cat.color or '#e94560'}; border-radius:5px;'></div>", 
                           unsafe_allow_html=True)
            with col2:
                st.write(cat.name)
            with col3:
                st.write(type_labels[cat.category_type])
            with col4:
                if st.button("🗑️", key=f"del_cat_{cat.id}"):
                    session.delete(cat)
                    session.commit()
                    st.toast("🗑️ Categoria excluída!", icon="🗑️")
                    st.rerun()
    if not cc_cats:
        st.info("Nenhuma categoria de cartão de crédito")
    
    st.markdown("---")
    st.markdown("### Editar Categoria")
    if categories:
        cat_to_edit = st.selectbox(
            "Selecione uma categoria para editar",
            categories,
            format_func=lambda c: f"{c.name} ({type_labels[c.category_type]})",
            key="edit_cat_select"
        )
        
        if cat_to_edit:
            col1, col2 = st.columns(2)
            with col1:
                edit_name = st.text_input("Nome", value=cat_to_edit.name, key="edit_cat_name")
            with col2:
                edit_color = st.color_picker("Cor", value=cat_to_edit.color or "#3b82f6", key="edit_cat_color")
            
            if st.button("💾 Atualizar Categoria", type="primary", key="btn_update_cat"):
                cat_to_edit.name = edit_name
                cat_to_edit.color = edit_color
                session.commit()
                st.toast("✅ Categoria atualizada!", icon="✅")
                st.rerun()

session.close()
