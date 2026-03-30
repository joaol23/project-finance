import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import Transaction, TransactionType, Category, CategoryType, Account

st.title("💸 Transações")

session = get_session()

account = session.query(Account).first()
if not account:
    account = Account(name="Conta Principal", initial_balance=0)
    session.add(account)
    session.commit()

income_categories = session.query(Category).filter(Category.category_type == CategoryType.INCOME).all()
expense_categories = session.query(Category).filter(Category.category_type == CategoryType.EXPENSE).all()

tab_list, tab_add = st.tabs(["📋 Lista de Transações", "➕ Nova Transação"])

with tab_add:
    st.markdown("### Adicionar Transação")
    
    col1, col2 = st.columns(2)
    with col1:
        trans_type = st.selectbox("Tipo", ["Entrada", "Saída"], key="new_trans_type")
    with col2:
        trans_date = st.date_input("Data", value=date.today(), key="new_trans_date")
    
    if trans_type == "Entrada":
        cat_options = {c.name: c.id for c in income_categories}
    else:
        cat_options = {c.name: c.id for c in expense_categories}
    
    col3, col4 = st.columns(2)
    with col3:
        trans_amount = st.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f", key="new_trans_amount")
    with col4:
        if cat_options:
            selected_cat = st.selectbox("Categoria", list(cat_options.keys()), key="new_trans_cat")
            category_id = cat_options[selected_cat]
        else:
            st.warning("Nenhuma categoria disponível")
            category_id = None
    
    trans_description = st.text_input("Descrição", key="new_trans_desc")
    
    if st.button("💾 Salvar Transação", type="primary", use_container_width=True):
        if trans_amount > 0 and trans_description:
            new_transaction = Transaction(
                date=trans_date,
                amount=Decimal(str(trans_amount)),
                description=trans_description,
                transaction_type=TransactionType.INCOME if trans_type == "Entrada" else TransactionType.EXPENSE,
                category_id=category_id,
                account_id=account.id
            )
            session.add(new_transaction)
            session.commit()
            st.success("✅ Transação salva com sucesso!")
            st.rerun()
        else:
            st.error("Preencha todos os campos obrigatórios")

with tab_list:
    st.markdown("### Filtros")
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        filter_month = st.selectbox("Mês", [None] + list(range(1, 13)), 
                                    format_func=lambda x: "Todos" if x is None else 
                                    ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
                                    key="filter_trans_month")
    with col_filter2:
        years = [None] + list(range(2020, date.today().year + 2))
        filter_year = st.selectbox("Ano", years, 
                                   format_func=lambda x: "Todos" if x is None else str(x),
                                   key="filter_trans_year")
    with col_filter3:
        filter_type = st.selectbox("Tipo", ["Todos", "Entrada", "Saída"], key="filter_trans_type")
    
    query = session.query(Transaction)
    
    if filter_month:
        query = query.filter(
            Transaction.date >= date(filter_year or date.today().year, filter_month, 1),
            Transaction.date < date((filter_year or date.today().year) + (1 if filter_month == 12 else 0), 
                                   (filter_month % 12) + 1, 1)
        )
    elif filter_year:
        query = query.filter(
            Transaction.date >= date(filter_year, 1, 1),
            Transaction.date < date(filter_year + 1, 1, 1)
        )
    
    if filter_type == "Entrada":
        query = query.filter(Transaction.transaction_type == TransactionType.INCOME)
    elif filter_type == "Saída":
        query = query.filter(Transaction.transaction_type == TransactionType.EXPENSE)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    st.markdown(f"**{len(transactions)} transações encontradas**")
    
    if transactions:
        # Pagination (reset page when filters change)
        pagination_sig = (filter_month, filter_year, filter_type)
        if st.session_state.get("trans_pagination_sig") != pagination_sig:
            st.session_state.trans_pagination_sig = pagination_sig
            st.session_state.trans_page = 1

        col_pag1, col_pag2, col_pag3 = st.columns([2, 2, 2])
        with col_pag1:
            page_size = st.selectbox(
                "Itens por página",
                [10, 20, 50, 100],
                index=1,
                key="trans_page_size",
            )
        total = len(transactions)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current_page = int(st.session_state.get("trans_page", 1))
        current_page = max(1, min(current_page, total_pages))
        st.session_state.trans_page = current_page

        with col_pag2:
            current_page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="trans_page_input",
            )
            st.session_state.trans_page = int(current_page)

        start_idx = (st.session_state.trans_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)

        with col_pag3:
            st.markdown(f"Mostrando **{start_idx + 1}–{end_idx}** de **{total}**")

        page_transactions = transactions[start_idx:end_idx]

        for t in page_transactions:
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
                    color = "green" if t.transaction_type == TransactionType.INCOME else "red"
                    signal = "+" if t.transaction_type == TransactionType.INCOME else "-"
                    st.markdown(f":{color}[{signal} R$ {float(t.amount):,.2f}]")
                with col5:
                    if st.button("🗑️", key=f"del_trans_{t.id}"):
                        session.delete(t)
                        session.commit()
                        st.rerun()
                st.markdown("---")
    else:
        st.info("Nenhuma transação encontrada")

    st.markdown("### Editar Transação")
    if transactions:
        trans_to_edit = st.selectbox(
            "Selecione uma transação para editar",
            transactions,
            format_func=lambda t: f"{t.date.strftime('%d/%m/%Y')} - {t.description} - R$ {float(t.amount):,.2f}",
            key="edit_trans_select"
        )
        
        if trans_to_edit:
            col1, col2 = st.columns(2)
            with col1:
                edit_type = st.selectbox(
                    "Tipo", 
                    ["Entrada", "Saída"], 
                    index=0 if trans_to_edit.transaction_type == TransactionType.INCOME else 1,
                    key="edit_trans_type"
                )
            with col2:
                edit_date = st.date_input("Data", value=trans_to_edit.date, key="edit_trans_date")
            
            if edit_type == "Entrada":
                edit_cat_options = {c.name: c.id for c in income_categories}
            else:
                edit_cat_options = {c.name: c.id for c in expense_categories}
            
            col3, col4 = st.columns(2)
            with col3:
                edit_amount = st.number_input(
                    "Valor (R$)", 
                    min_value=0.01, 
                    step=0.01, 
                    format="%.2f", 
                    value=float(trans_to_edit.amount),
                    key="edit_trans_amount"
                )
            with col4:
                if edit_cat_options:
                    current_cat = trans_to_edit.category.name if trans_to_edit.category and trans_to_edit.category.name in edit_cat_options else list(edit_cat_options.keys())[0]
                    edit_cat = st.selectbox("Categoria", list(edit_cat_options.keys()), 
                                           index=list(edit_cat_options.keys()).index(current_cat) if current_cat in edit_cat_options else 0,
                                           key="edit_trans_cat")
                    edit_category_id = edit_cat_options[edit_cat]
                else:
                    edit_category_id = None
            
            edit_description = st.text_input("Descrição", value=trans_to_edit.description, key="edit_trans_desc")
            
            if st.button("💾 Atualizar Transação", type="primary", key="btn_update_trans"):
                trans_to_edit.date = edit_date
                trans_to_edit.amount = Decimal(str(edit_amount))
                trans_to_edit.description = edit_description
                trans_to_edit.transaction_type = TransactionType.INCOME if edit_type == "Entrada" else TransactionType.EXPENSE
                trans_to_edit.category_id = edit_category_id
                session.commit()
                st.success("✅ Transação atualizada!")
                st.rerun()

session.close()
