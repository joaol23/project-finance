import streamlit as st
from datetime import date
from decimal import Decimal
from database import get_session
from database.models import CreditCard, CreditCardTransaction, Category, CategoryType

st.title("💳 Cartões de Crédito")
st.caption("Gerencie seus cartões e faturas")

session = get_session()

cards = session.query(CreditCard).all()
cc_categories = session.query(Category).filter(Category.category_type == CategoryType.CREDIT_CARD).all()

if "card_saved" not in st.session_state:
    st.session_state.card_saved = False
if "cc_trans_saved" not in st.session_state:
    st.session_state.cc_trans_saved = False
if "cc_trans_updated" not in st.session_state:
    st.session_state.cc_trans_updated = False
if "cc_trans_deleted" not in st.session_state:
    st.session_state.cc_trans_deleted = False

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

if st.session_state.cc_trans_updated:
    st.toast("✅ Transação atualizada!", icon="✅")
    st.session_state.cc_trans_updated = False

if st.session_state.cc_trans_deleted:
    st.toast("🗑️ Transação excluída!", icon="🗑️")
    st.session_state.cc_trans_deleted = False

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
    
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)
    with col_filter1:
        filter_month = st.selectbox("Mês", list(range(1, 13)), 
                                    index=date.today().month - 1,
                                    format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
                                    key="filter_cc_month")
    with col_filter2:
        years = list(range(2020, date.today().year + 2))
        filter_year = st.selectbox("Ano", years, index=years.index(date.today().year), key="filter_cc_year")
    with col_filter3:
        card_filter_options = ["Todos"] + [c.name for c in cards]
        filter_card = st.selectbox("Cartão", card_filter_options, key="filter_cc_card")
    with col_filter4:
        filter_desc = st.text_input("🔍 Filtrar descrição", key="filter_cc_desc", 
                                    placeholder="Ex: UBER, IFOOD...")
    
    filter_no_category = st.checkbox("🏷️ Apenas sem categoria", key="filter_cc_no_cat")
    
    query = session.query(CreditCardTransaction).filter(
        CreditCardTransaction.date >= date(filter_year, filter_month, 1),
        CreditCardTransaction.date < date(filter_year + (1 if filter_month == 12 else 0), 
                                         (filter_month % 12) + 1, 1)
    )
    
    if filter_card != "Todos":
        selected_card = next((c for c in cards if c.name == filter_card), None)
        if selected_card:
            query = query.filter(CreditCardTransaction.credit_card_id == selected_card.id)
    
    if filter_no_category:
        query = query.filter(CreditCardTransaction.category_id == None)
    
    transactions = query.order_by(CreditCardTransaction.date.desc()).all()
    
    if filter_desc:
        filter_lower = filter_desc.lower()
        transactions = [t for t in transactions if filter_lower in t.description.lower()]
    
    total_month = sum(float(t.amount) for t in transactions)
    st.metric("Total do Mês", f"R$ {total_month:,.2f}")
    
    if transactions:
        filter_info = f" que contêm **\"{filter_desc}\"**" if filter_desc else " listadas"
        with st.expander(f"⚡ Alteração em lote ({len(transactions)} transações)"):
            st.info(f"Alterar categoria de todas as {len(transactions)} transações{filter_info}")
            
            col_bulk1, col_bulk2 = st.columns([3, 1])
            with col_bulk1:
                bulk_cat_options = ["Sem categoria"] + [c.name for c in cc_categories]
                bulk_new_cat = st.selectbox("Nova categoria", bulk_cat_options, key="bulk_cc_cat")
            with col_bulk2:
                st.write("")
                st.write("")
                if st.button("✅ Aplicar a todas", key="apply_bulk_cc_cat", use_container_width=True):
                    if bulk_new_cat == "Sem categoria":
                        new_cat_id = None
                    else:
                        selected_cat = next((c for c in cc_categories if c.name == bulk_new_cat), None)
                        new_cat_id = selected_cat.id if selected_cat else None
                    
                    for t in transactions:
                        t.category_id = new_cat_id
                    session.commit()
                    st.toast(f"✅ {len(transactions)} transações atualizadas!", icon="✅")
                    st.rerun()
    
    st.markdown("---")
    
    if transactions:
        pagination_sig = (filter_month, filter_year, filter_card, filter_desc, filter_no_category)
        if st.session_state.get("cc_trans_pagination_sig") != pagination_sig:
            st.session_state.cc_trans_pagination_sig = pagination_sig
            st.session_state.cc_trans_page = 1

        page_size = st.session_state.get("cc_trans_page_size", 20)
        total = len(transactions)
        total_pages = max(1, (total + page_size - 1) // page_size)
        current_page = int(st.session_state.get("cc_trans_page", 1))
        current_page = max(1, min(current_page, total_pages))
        st.session_state.cc_trans_page = current_page

        start_idx = (st.session_state.cc_trans_page - 1) * page_size
        end_idx = min(start_idx + page_size, total)

        page_transactions = transactions[start_idx:end_idx]

        cat_options = ["Sem categoria"] + [c.name for c in cc_categories]
        
        for t in page_transactions:
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
                    key=f"quick_cc_cat_{t.id}", label_visibility="collapsed"
                )
                if (new_cat == "Sem categoria" and t.category_id is not None) or \
                   (new_cat != "Sem categoria" and (t.category is None or t.category.name != new_cat)):
                    if new_cat == "Sem categoria":
                        t.category_id = None
                    else:
                        selected_cat = next((c for c in cc_categories if c.name == new_cat), None)
                        t.category_id = selected_cat.id if selected_cat else None
                    session.commit()
                    st.rerun()
            with col_val:
                st.markdown(f":red[R$ {float(t.amount):,.2f}]")
            with col_edit:
                if st.button("✏️", key=f"edit_btn_cc_{t.id}", help="Editar detalhes"):
                    st.session_state[f"expand_cc_{t.id}"] = not st.session_state.get(f"expand_cc_{t.id}", False)
                    st.rerun()
            
            if st.session_state.get(f"expand_cc_{t.id}", False):
                with st.container():
                    col_edit1, col_edit2 = st.columns(2)
                    with col_edit1:
                        new_date = st.date_input("Data", value=t.date, key=f"edit_cc_date_{t.id}")
                        new_desc = st.text_input("Descrição", value=t.description, key=f"edit_cc_desc_{t.id}")
                        new_amount = st.number_input("Valor", value=float(t.amount), min_value=0.01, 
                                                      step=0.01, key=f"edit_cc_amount_{t.id}")
                    with col_edit2:
                        card_options = [c.name for c in cards]
                        current_card_idx = 0
                        if t.credit_card:
                            try:
                                current_card_idx = card_options.index(t.credit_card.name)
                            except ValueError:
                                pass
                        new_card = st.selectbox("Cartão", card_options, index=current_card_idx,
                                                key=f"edit_cc_card_{t.id}")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Salvar", key=f"save_cc_trans_{t.id}", use_container_width=True):
                            t.date = new_date
                            t.description = new_desc
                            t.amount = Decimal(str(new_amount))
                            
                            selected_card = next((c for c in cards if c.name == new_card), None)
                            if selected_card:
                                t.credit_card_id = selected_card.id
                            
                            session.commit()
                            st.session_state.cc_trans_updated = True
                            st.session_state[f"expand_cc_{t.id}"] = False
                            st.rerun()
                    with col_btn2:
                        if st.button("🗑️ Excluir", key=f"del_cc_trans_{t.id}", use_container_width=True):
                            session.delete(t)
                            session.commit()
                            st.session_state.cc_trans_deleted = True
                            st.rerun()
                    st.markdown("---")
        
        col_pag1, col_pag2, col_pag3 = st.columns([2, 2, 2])
        with col_pag1:
            new_page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="cc_trans_page_input",
            )
            if new_page != current_page:
                st.session_state.cc_trans_page = int(new_page)
                st.rerun()
        with col_pag2:
            new_page_size = st.selectbox(
                "Itens por página",
                [10, 20, 50, 100],
                index=[10, 20, 50, 100].index(page_size) if page_size in [10, 20, 50, 100] else 1,
                key="cc_trans_page_size_select",
            )
            if new_page_size != page_size:
                st.session_state.cc_trans_page_size = new_page_size
                st.session_state.cc_trans_page = 1
                st.rerun()
        with col_pag3:
            st.markdown(f"Mostrando **{start_idx + 1}–{end_idx}** de **{total}**")
    else:
        st.info("Nenhuma transação encontrada")

session.close()
