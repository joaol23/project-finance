import streamlit as st
import pandas as pd
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import Transaction, TransactionType, Category, CategoryType, Account

st.title("💸 Transações")
st.caption("Gerencie suas entradas e saídas")

session = get_session()

if "trans_saved" not in st.session_state:
    st.session_state.trans_saved = False
if "trans_updated" not in st.session_state:
    st.session_state.trans_updated = False
if "trans_deleted" not in st.session_state:
    st.session_state.trans_deleted = False

if st.session_state.trans_saved:
    st.toast("✅ Transação criada com sucesso!", icon="✅")
    st.session_state.trans_saved = False
if st.session_state.trans_updated:
    st.toast("✅ Transação atualizada!", icon="✅")
    st.session_state.trans_updated = False
if st.session_state.trans_deleted:
    st.toast("🗑️ Transação excluída!", icon="🗑️")
    st.session_state.trans_deleted = False

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
            st.session_state.trans_saved = True
            st.rerun()
        else:
            st.error("Preencha todos os campos obrigatórios")

with tab_list:
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    
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
    with col_filter4:
        filter_desc = st.text_input("🔍 Filtrar descrição", key="filter_trans_desc",
                                    placeholder="Ex: UBER, IFOOD...")
    
    filter_no_category = st.checkbox("🏷️ Apenas sem categoria", key="filter_trans_no_cat")
    
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
    
    if filter_no_category:
        query = query.filter(Transaction.category_id == None)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    
    if filter_desc:
        filter_lower = filter_desc.lower()
        transactions = [t for t in transactions if filter_lower in t.description.lower()]
    
    st.markdown(f"**{len(transactions)} transações encontradas**")
    
    if transactions:
        filter_info = f" que contêm **\"{filter_desc}\"**" if filter_desc else " listadas"
        with st.expander(f"⚡ Alteração em lote ({len(transactions)} transações)"):
            st.info(f"Alterar categoria de todas as {len(transactions)} transações{filter_info}")
            
            all_categories = income_categories + expense_categories
            col_bulk1, col_bulk2 = st.columns([3, 1])
            with col_bulk1:
                bulk_cat_options = ["Sem categoria"] + [c.name for c in all_categories]
                bulk_new_cat = st.selectbox("Nova categoria", bulk_cat_options, key="bulk_trans_cat")
            with col_bulk2:
                st.write("")
                st.write("")
                if st.button("✅ Aplicar a todas", key="apply_bulk_trans_cat", use_container_width=True):
                    if bulk_new_cat == "Sem categoria":
                        new_cat_id = None
                    else:
                        selected_cat = next((c for c in all_categories if c.name == bulk_new_cat), None)
                        new_cat_id = selected_cat.id if selected_cat else None
                    
                    for t in transactions:
                        t.category_id = new_cat_id
                    session.commit()
                    st.toast(f"✅ {len(transactions)} transações atualizadas!", icon="✅")
                    st.rerun()
        pagination_sig = (filter_month, filter_year, filter_type, filter_desc, filter_no_category)
        if st.session_state.get("trans_pagination_sig") != pagination_sig:
            st.session_state.trans_pagination_sig = pagination_sig
            st.session_state.trans_page = 1

        page_size = st.session_state.get("trans_page_size", 20)
        total = len(transactions)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current_page = int(st.session_state.get("trans_page", 1))
        current_page = max(1, min(current_page, total_pages))
        st.session_state.trans_page = current_page

        start_idx = (st.session_state.trans_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)

        page_transactions = transactions[start_idx:end_idx]
        
        all_categories = income_categories + expense_categories
        cat_options = ["Sem categoria"] + [c.name for c in all_categories]

        for t in page_transactions:
            color = "green" if t.transaction_type == TransactionType.INCOME else "red"
            signal = "+" if t.transaction_type == TransactionType.INCOME else "-"
            
            col_date, col_desc, col_cat, col_val, col_edit = st.columns([1.5, 3, 2.5, 1.5, 0.5])
            
            with col_date:
                st.write(t.date.strftime("%d/%m/%Y"))
            with col_desc:
                st.write(t.description[:40] + "..." if len(t.description) > 40 else t.description)
            with col_cat:
                current_cat_idx = 0
                if t.category:
                    try:
                        current_cat_idx = cat_options.index(t.category.name)
                    except ValueError:
                        pass
                new_cat = st.selectbox(
                    "cat", cat_options, index=current_cat_idx,
                    key=f"quick_trans_cat_{t.id}", label_visibility="collapsed"
                )
                if (new_cat == "Sem categoria" and t.category_id is not None) or \
                   (new_cat != "Sem categoria" and (t.category is None or t.category.name != new_cat)):
                    if new_cat == "Sem categoria":
                        t.category_id = None
                    else:
                        selected_cat = next((c for c in all_categories if c.name == new_cat), None)
                        t.category_id = selected_cat.id if selected_cat else None
                    session.commit()
                    st.rerun()
            with col_val:
                st.markdown(f":{color}[{signal} R$ {float(t.amount):,.2f}]")
            with col_edit:
                if st.button("✏️", key=f"edit_btn_trans_{t.id}", help="Editar detalhes"):
                    st.session_state[f"expand_trans_{t.id}"] = not st.session_state.get(f"expand_trans_{t.id}", False)
                    st.rerun()
            
            if st.session_state.get(f"expand_trans_{t.id}", False):
                with st.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_type = st.selectbox(
                            "Tipo", 
                            ["Entrada", "Saída"], 
                            index=0 if t.transaction_type == TransactionType.INCOME else 1,
                            key=f"edit_type_{t.id}"
                        )
                    with col2:
                        edit_date = st.date_input("Data", value=t.date, key=f"edit_date_{t.id}")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        edit_amount = st.number_input(
                            "Valor (R$)", 
                            min_value=0.01, 
                            step=0.01, 
                            format="%.2f", 
                            value=float(t.amount),
                            key=f"edit_amount_{t.id}"
                        )
                    with col4:
                        edit_description = st.text_input("Descrição", value=t.description, key=f"edit_desc_{t.id}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Salvar", type="primary", key=f"save_trans_{t.id}", use_container_width=True):
                            t.date = edit_date
                            t.amount = Decimal(str(edit_amount))
                            t.description = edit_description
                            t.transaction_type = TransactionType.INCOME if edit_type == "Entrada" else TransactionType.EXPENSE
                            session.commit()
                            st.session_state.trans_updated = True
                            st.session_state[f"expand_trans_{t.id}"] = False
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Excluir", key=f"del_trans_{t.id}", use_container_width=True):
                            session.delete(t)
                            session.commit()
                            st.session_state.trans_deleted = True
                            st.rerun()
                    st.markdown("---")
        
        st.markdown("### Navegação")
        col_pag1, col_pag2, col_pag3 = st.columns([2, 2, 2])
        with col_pag1:
            new_page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="trans_page_input",
            )
            if new_page != current_page:
                st.session_state.trans_page = int(new_page)
                st.rerun()
        with col_pag2:
            new_page_size = st.selectbox(
                "Itens por página",
                [10, 20, 50, 100],
                index=[10, 20, 50, 100].index(page_size) if page_size in [10, 20, 50, 100] else 1,
                key="trans_page_size_select",
            )
            if new_page_size != page_size:
                st.session_state.trans_page_size = new_page_size
                st.session_state.trans_page = 1
                st.rerun()
        with col_pag3:
            st.markdown(f"Mostrando **{start_idx + 1}–{end_idx}** de **{total}**")
    else:
        st.info("Nenhuma transação encontrada")

session.close()
