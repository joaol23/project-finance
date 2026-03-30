import streamlit as st
import pandas as pd
import os
from datetime import datetime
from decimal import Decimal
from database import get_session
from database.models import (
    Transaction, TransactionType, Category, CategoryType, Account,
    CreditCard, CreditCardTransaction, Investment, InvestmentType
)
try:
    from services.stock_service import detect_investment_type, extract_ticker_from_description
except ImportError:
    def detect_investment_type(ticker):
        ticker_upper = ticker.upper()
        if ticker_upper.endswith('11') and len(ticker_upper) >= 5:
            return "fii"
        if ticker_upper in ['BTC', 'ETH', 'SOL', 'ADA', 'DOT', 'AVAX', 'MATIC']:
            return "crypto"
        return "stock"
    
    def extract_ticker_from_description(description):
        import re
        patterns = [r'\b([A-Z]{4}[0-9]{1,2})\b', r'\b([A-Z]{3}[0-9]{1,2})\b']
        for pattern in patterns:
            match = re.search(pattern, description.upper())
            if match:
                return match.group(1)
        return None

st.title("📥 Importar Dados")

session = get_session()

try:
    _root = PROJECT_ROOT
except NameError:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_PATH = os.path.join(_root, "exemplos", "planilha_exemplo.xlsx")

st.markdown("""
### Formato da Planilha

A planilha Excel deve conter as seguintes abas:

**Aba "Transacoes":**
| Coluna | Descrição |
|--------|-----------|
| Data | Data da transação (DD/MM/AAAA) |
| Valor | Valor total da transação |
| Descricao | Descrição da transação (ex: "Compra PETR4") |
| Categoria | Nome da categoria |
| Tipo | "entrada" ou "saida" |
| Quantidade | (Opcional) Quantidade de cotas/ações |
| PrecoUnidade | (Opcional) Preço pago por unidade |

*O ticker é extraído automaticamente da descrição (ex: "Compra PETR4" → PETR4). Quando a Quantidade é preenchida, a transação é vinculada ao investimento. Se PrecoUnidade não for informado, é calculado como Valor ÷ Quantidade.*

**Aba "Cartao":**
| Coluna | Descrição |
|--------|-----------|
| Data | Data da compra (DD/MM/AAAA) |
| Valor | Valor da compra |
| Descricao | Descrição da compra |
| Categoria | Nome da categoria |
| Parcela | Número da parcela (ex: "1/3") |
""")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Baixar Planilha de Exemplo")
    if os.path.exists(EXAMPLE_PATH):
        with open(EXAMPLE_PATH, "rb") as f:
            st.download_button(
                label="📥 Baixar Exemplo",
                data=f,
                file_name="planilha_exemplo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        if st.button("🔧 Criar Planilha de Exemplo", use_container_width=True):
            os.makedirs(os.path.dirname(EXAMPLE_PATH), exist_ok=True)
            
            df_trans = pd.DataFrame({
                'Data': ['01/03/2026', '05/03/2026', '10/03/2026', '15/03/2026', '20/03/2026', '22/03/2026'],
                'Valor': [5000.00, 150.00, 800.00, 200.00, 3550.00, 8000.00],
                'Descricao': ['Salário', 'Supermercado', 'Aluguel', 'Restaurante', 'Compra PETR4', 'Compra MXRF11'],
                'Categoria': ['Salário', 'Alimentação', 'Moradia', 'Alimentação', 'Ações', 'FIIs'],
                'Tipo': ['entrada', 'saida', 'saida', 'saida', 'saida', 'saida'],
                'Quantidade': ['', '', '', '', 100, 800],
                'PrecoUnidade': ['', '', '', '', 35.50, 10.00]
            })
            
            df_cartao = pd.DataFrame({
                'Data': ['02/03/2026', '08/03/2026', '12/03/2026'],
                'Valor': [299.90, 89.90, 150.00],
                'Descricao': ['Tênis Nike', 'Netflix + Spotify', 'Jantar'],
                'Categoria': ['Compras (CC)', 'Assinaturas (CC)', 'Alimentação (CC)'],
                'Parcela': ['1/3', '1/1', '1/1']
            })
            
            with pd.ExcelWriter(EXAMPLE_PATH, engine='openpyxl') as writer:
                df_trans.to_excel(writer, sheet_name='Transacoes', index=False)
                df_cartao.to_excel(writer, sheet_name='Cartao', index=False)
            
            st.toast("✅ Planilha de exemplo criada!", icon="✅")
            st.rerun()

with col2:
    st.markdown("### Importar Planilha")
    uploaded_file = st.file_uploader("Escolha um arquivo Excel", type=['xlsx', 'xls'])

if uploaded_file:
    st.markdown("---")
    st.markdown("### Pré-visualização")
    
    try:
        excel_file = pd.ExcelFile(uploaded_file)
        sheets = excel_file.sheet_names
        
        st.write(f"**Abas encontradas:** {', '.join(sheets)}")
        
        import_trans = 'Transacoes' in sheets
        import_cc = 'Cartao' in sheets
        
        if import_trans:
            df_trans = pd.read_excel(uploaded_file, sheet_name='Transacoes')
            st.markdown("#### Transações")
            st.dataframe(df_trans.head(10))
            
            if 'Quantidade' in df_trans.columns:
                inv_rows = df_trans[(df_trans['Quantidade'].notna()) & (df_trans['Quantidade'] != '') & (df_trans['Quantidade'] != 0)]
                if len(inv_rows) > 0:
                    st.info(f"📈 {len(inv_rows)} transações de investimento detectadas (com Quantidade). O ticker será extraído da descrição.")
        
        if import_cc:
            df_cc = pd.read_excel(uploaded_file, sheet_name='Cartao')
            st.markdown("#### Cartão de Crédito")
            st.dataframe(df_cc.head(10))
            
            cards = session.query(CreditCard).all()
            if cards:
                card_options = {c.name: c.id for c in cards}
                selected_import_card = st.selectbox(
                    "Selecione o cartão para importar os dados",
                    list(card_options.keys()),
                    key="import_card_select"
                )
            else:
                st.warning("⚠️ Nenhum cartão cadastrado. Será criado um cartão 'Cartão Importado'.")
                selected_import_card = None
        
        st.markdown("---")
        
        if st.button("📥 Importar Dados", type="primary", use_container_width=True):
            account = session.query(Account).first()
            if not account:
                account = Account(name="Conta Principal", initial_balance=0)
                session.add(account)
                session.commit()
            
            categories = {c.name.lower(): c for c in session.query(Category).all()}
            
            imported_count = {'transactions': 0, 'cc': 0, 'investments': 0}
            
            if import_trans:
                investments_cache = {i.ticker: i for i in session.query(Investment).all()}
                inv_type_map = {
                    "stock": InvestmentType.STOCK,
                    "fii": InvestmentType.FII,
                    "crypto": InvestmentType.CRYPTO,
                    "other": InvestmentType.OTHER
                }
                
                has_ticker_col = 'Ticker' in df_trans.columns
                has_qty_col = 'Quantidade' in df_trans.columns
                has_price_col = 'PrecoUnidade' in df_trans.columns
                
                for _, row in df_trans.iterrows():
                    try:
                        date_val = pd.to_datetime(row['Data'], dayfirst=True).date()
                        amount = Decimal(str(row['Valor']))
                        description = str(row['Descricao'])
                        cat_name = str(row.get('Categoria', '')).lower()
                        trans_type = str(row.get('Tipo', 'saida')).lower()
                        
                        ticker = ''
                        quantity = None
                        preco_unidade = None
                        
                        if has_ticker_col:
                            ticker_val = row.get('Ticker')
                            if pd.notna(ticker_val) and str(ticker_val).strip():
                                ticker = str(ticker_val).upper().strip()
                        
                        if has_qty_col:
                            qty_val = row.get('Quantidade')
                            if pd.notna(qty_val):
                                try:
                                    qty_float = float(qty_val)
                                    if qty_float > 0:
                                        quantity = Decimal(str(qty_float))
                                except (ValueError, TypeError):
                                    quantity = None
                        
                        if has_price_col:
                            pu_val = row.get('PrecoUnidade')
                            if pd.notna(pu_val):
                                try:
                                    pu_float = float(pu_val)
                                    if pu_float > 0:
                                        preco_unidade = Decimal(str(pu_float))
                                except (ValueError, TypeError):
                                    preco_unidade = None
                        
                        if not ticker and quantity is not None and quantity > 0:
                            extracted = extract_ticker_from_description(description)
                            if extracted:
                                ticker = extracted
                        
                        is_investment_trans = ticker != '' and quantity is not None and quantity > 0
                        
                        category = categories.get(cat_name)
                        if not category and cat_name:
                            cat_type = CategoryType.INCOME if trans_type == 'entrada' else CategoryType.EXPENSE
                            category = Category(
                                name=row['Categoria'], 
                                category_type=cat_type, 
                                color="#7c3aed" if is_investment_trans else "#3b82f6", 
                                is_investment=is_investment_trans
                            )
                            session.add(category)
                            session.flush()
                            categories[cat_name] = category
                        elif category and is_investment_trans and not category.is_investment:
                            category.is_investment = True
                            session.flush()
                        
                        investment_id = None
                        price_per_unit = None
                        
                        if is_investment_trans:
                            if ticker not in investments_cache:
                                inv_type_str = detect_investment_type(ticker)
                                investment = Investment(
                                    ticker=ticker,
                                    investment_type=inv_type_map.get(inv_type_str, InvestmentType.STOCK)
                                )
                                session.add(investment)
                                session.flush()
                                investments_cache[ticker] = investment
                            else:
                                investment = investments_cache[ticker]
                            
                            investment_id = investment.id
                            if preco_unidade:
                                price_per_unit = preco_unidade
                            else:
                                price_per_unit = amount / quantity
                            imported_count['investments'] += 1
                        
                        transaction = Transaction(
                            date=date_val,
                            amount=amount,
                            description=description,
                            transaction_type=TransactionType.INCOME if trans_type == 'entrada' else TransactionType.EXPENSE,
                            category_id=category.id if category else None,
                            account_id=account.id,
                            investment_id=investment_id,
                            quantity=quantity,
                            price_per_unit=price_per_unit
                        )
                        session.add(transaction)
                        imported_count['transactions'] += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar transação: {e}")
            
            if import_cc:
                if selected_import_card:
                    target_card = session.query(CreditCard).filter(CreditCard.name == selected_import_card).first()
                else:
                    target_card = CreditCard(name="Cartão Importado")
                    session.add(target_card)
                    session.flush()
                
                for _, row in df_cc.iterrows():
                    try:
                        date_val = pd.to_datetime(row['Data'], dayfirst=True).date()
                        amount = Decimal(str(row['Valor']))
                        description = str(row['Descricao'])
                        cat_name = str(row.get('Categoria', '')).lower()
                        parcela = str(row.get('Parcela', '1/1'))
                        
                        parts = parcela.split('/')
                        installment_number = int(parts[0]) if len(parts) >= 1 else 1
                        total_installments = int(parts[1]) if len(parts) >= 2 else 1
                        
                        category = categories.get(cat_name)
                        if not category and cat_name:
                            category = Category(name=row['Categoria'], category_type=CategoryType.CREDIT_CARD, color="#e94560")
                            session.add(category)
                            session.flush()
                            categories[cat_name] = category
                        
                        cc_trans = CreditCardTransaction(
                            date=date_val,
                            amount=amount,
                            description=description,
                            installment_number=installment_number,
                            total_installments=total_installments,
                            category_id=category.id if category else None,
                            credit_card_id=target_card.id
                        )
                        session.add(cc_trans)
                        imported_count['cc'] += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar transação de cartão: {e}")
            
            session.commit()
            
            st.toast("✅ Importação concluída!", icon="✅")
            inv_msg = f" (sendo {imported_count['investments']} de investimentos)" if imported_count['investments'] > 0 else ""
            st.success(f"""
            Importação concluída!
            - Transações: {imported_count['transactions']}{inv_msg}
            - Cartão de Crédito: {imported_count['cc']}
            """)
    
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")

session.close()
