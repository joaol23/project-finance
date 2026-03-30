import streamlit as st
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import CreditCard, CreditCardTransaction, Category, CategoryType

st.title("💳 Cartões de Crédito")

session = get_session()

cards = session.query(CreditCard).all()
cc_categories = session.query(Category).filter(Category.category_type == CategoryType.CREDIT_CARD).all()

if "card_saved" not in st.session_state:
    st.session_state.card_saved = False
if "cc_trans_saved" not in st.session_state:
    st.session_state.cc_trans_saved = False

def clear_card_form():
    keys_to_clear = ["new_card_name"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def clear_cc_trans_form():
    keys_to_clear = ["new_cc_trans_card", "new_cc_trans_date", "new_cc_trans_amount", 
                     "new_cc_trans_desc", "new_cc_trans_cat", "new_cc_trans_parcelas"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

if st.session_state.card_saved:
    st.toast("✅ Cartão salvo com sucesso!", icon="✅")
    st.session_state.card_saved = False

if st.session_state.cc_trans_saved:
    st.toast("✅ Transação salva com sucesso!", icon="✅")
    st.session_state.cc_trans_saved = False

tab_cards, tab_transactions, tab_add_card, tab_add_trans = st.tabs([
    "💳 Meus Cartões", "📋 Transações", "➕ Novo Cartão", "➕ Nova Transação"
])

with tab_add_card:
    st.markdown("### Adicionar Cartão")
    
    card_name = st.text_input("Nome do Cartão", key="new_card_name", value="")
    
    if st.button("💾 Salvar Cartão", type="primary", use_container_width=True, key="btn_save_card"):
        if card_name:
            new_card = CreditCard(name=card_name)
            session.add(new_card)
            session.commit()
            st.session_state.card_saved = True
            clear_card_form()
            st.rerun()
        else:
            st.error("Preencha o nome do cartão")

with tab_add_trans:
    st.markdown("### Adicionar Transação no Cartão")
    
    cards = session.query(CreditCard).all()
    
    if cards:
        card_options = {c.name: c.id for c in cards}
        selected_card = st.selectbox("Cartão", list(card_options.keys()), key="new_cc_trans_card")
        
        col1, col2 = st.columns(2)
        with col1:
            trans_date = st.date_input("Data da Compra", value=date.today(), key="new_cc_trans_date")
        with col2:
            trans_amount = st.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f", key="new_cc_trans_amount", value=0.0)
        
        trans_description = st.text_input("Descrição", key="new_cc_trans_desc", value="")
        
        col3, col4 = st.columns(2)
        with col3:
            if cc_categories:
                cat_options = {c.name: c.id for c in cc_categories}
                selected_cat = st.selectbox("Categoria", list(cat_options.keys()), key="new_cc_trans_cat")
                category_id = cat_options[selected_cat]
            else:
                st.warning("Nenhuma categoria de cartão disponível")
                category_id = None
        with col4:
            total_installments = st.number_input("Parcelas", min_value=1, max_value=48, value=1, key="new_cc_trans_parcelas")
        
        if st.button("💾 Salvar Transação", type="primary", use_container_width=True, key="btn_save_cc_trans"):
            if trans_amount > 0 and trans_description:
                installment_value = Decimal(str(trans_amount)) / total_installments
                for i in range(total_installments):
                    trans_month = trans_date.month + i
                    trans_year = trans_date.year + (trans_month - 1) // 12
                    trans_month = ((trans_month - 1) % 12) + 1
                    
                    new_trans = CreditCardTransaction(
                        date=date(trans_year, trans_month, trans_date.day),
                        amount=installment_value,
                        description=f"{trans_description} ({i+1}/{total_installments})" if total_installments > 1 else trans_description,
                        installment_number=i + 1,
                        total_installments=total_installments,
                        category_id=category_id,
                        credit_card_id=card_options[selected_card]
                    )
                    session.add(new_trans)
                session.commit()
                st.session_state.cc_trans_saved = True
                clear_cc_trans_form()
                st.rerun()
            else:
                st.error("Preencha todos os campos obrigatórios")
    else:
        st.warning("Cadastre um cartão primeiro")

with tab_cards:
    st.markdown("### Meus Cartões")
    
    cards = session.query(CreditCard).all()
    
    if cards:
        for card in cards:
            with st.expander(f"💳 {card.name}"):
                total = sum(float(t.amount) for t in card.transactions)
                st.metric("Total em Aberto", f"R$ {total:,.2f}")
                
                if st.button("🗑️ Excluir Cartão", key=f"del_card_{card.id}"):
                    session.delete(card)
                    session.commit()
                    st.toast("🗑️ Cartão excluído!", icon="🗑️")
                    st.rerun()
    else:
        st.info("Nenhum cartão cadastrado")

with tab_transactions:
    st.markdown("### Transações do Cartão")
    
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_month = st.selectbox("Mês", list(range(1, 13)), 
                                    index=date.today().month - 1,
                                    format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
                                    key="filter_cc_month")
    with col_filter2:
        years = list(range(2020, date.today().year + 2))
        filter_year = st.selectbox("Ano", years, index=years.index(date.today().year), key="filter_cc_year")
    
    transactions = session.query(CreditCardTransaction).filter(
        CreditCardTransaction.date >= date(filter_year, filter_month, 1),
        CreditCardTransaction.date < date(filter_year + (1 if filter_month == 12 else 0), 
                                         (filter_month % 12) + 1, 1)
    ).order_by(CreditCardTransaction.date.desc()).all()
    
    total_month = sum(float(t.amount) for t in transactions)
    st.metric("Total do Mês", f"R$ {total_month:,.2f}")
    
    st.markdown("---")
    
    if transactions:
        for t in transactions:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 1])
                with col1:
                    st.write(t.date.strftime("%d/%m/%Y"))
                with col2:
                    st.write(t.description)
                with col3:
                    cat_name = t.category.name if t.category else "Sem categoria"
                    st.write(cat_name)
                with col4:
                    st.markdown(f":red[R$ {float(t.amount):,.2f}]")
                with col5:
                    if st.button("🗑️", key=f"del_cc_trans_{t.id}"):
                        session.delete(t)
                        session.commit()
                        st.toast("🗑️ Transação excluída!", icon="🗑️")
                        st.rerun()
                st.markdown("---")
    else:
        st.info("Nenhuma transação encontrada")

session.close()
