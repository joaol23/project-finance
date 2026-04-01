import streamlit as st
import pandas as pd
import os
import re
import calendar
from datetime import datetime, date
from decimal import Decimal
import io
try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
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

st.title("📥 Importar / 📤 Exportar Dados")
st.caption("Importe extratos ou exporte seus dados")

session = get_session()

main_tab_import, main_tab_export = st.tabs(["📥 Importar", "📤 Exportar"])

def _parse_ptbr_money(value) -> Decimal | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except Exception:
        return None

PAYMENT_PATTERNS = [
    r"pagamento\s+recebido",
    r"pagamento\s+de\s+fatura",
    r"pagamento\s+efetuado",
    r"saldo\s+anterior",
    r"pagto\s+antecipado",
    r"^pagamento$",
]

def _is_payment_entry(desc: str) -> bool:
    """Verifica se é um pagamento de fatura (deve ser ignorado). Estornos NÃO são ignorados."""
    desc_lower = desc.lower().strip()
    for pattern in PAYMENT_PATTERNS:
        if re.search(pattern, desc_lower):
            return True
    return False

def _adjust_date_to_ref_month(original_date, ref_month: int, ref_year: int):
    """
    Ajusta datas que estão fora do mês de referência para o mês correto da fatura.
    Se a transação está em uma fatura de março/2026, mas a data original é fevereiro ou outubro,
    a data deve ser ajustada para março/2026 (mantendo o dia se possível).
    """
    if original_date is None:
        return date(ref_year, ref_month, 1)
    
    if original_date.month == ref_month and original_date.year == ref_year:
        return original_date
    
    try:
        last_day = calendar.monthrange(ref_year, ref_month)[1]
        day = min(original_date.day, last_day)
        return date(ref_year, ref_month, day)
    except Exception:
        return date(ref_year, ref_month, 1)

def _parse_nubank_csv(file_bytes: bytes, ref_month: int | None = None, ref_year: int | None = None, adjust_dates: bool = True) -> pd.DataFrame:
    """
    Lê o CSV do extrato Nubank (cartão de crédito) e devolve um DataFrame
    normalizado com colunas: Data, Descricao, Valor.
    - Filtra apenas pagamentos de fatura
    - Mantém estornos (valores negativos são convertidos para positivos com prefixo)
    - Ajusta datas de parcelas para o mês de referência da fatura
    """
    text = file_bytes.decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(text))
    
    df.columns = [c.strip().lower() for c in df.columns]
    
    df.rename(columns={
        "date": "Data",
        "title": "Descricao", 
        "amount": "Valor"
    }, inplace=True)
    
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
    
    df = df[~df["Descricao"].apply(_is_payment_entry)].copy()
    df = df[df["Data"].notna()].copy()
    df = df[df["Valor"].notna()].copy()
    
    def process_row(row):
        valor = row["Valor"]
        desc = row["Descricao"]
        if valor < 0:
            desc = f"ESTORNO: {desc}"
            valor = abs(valor)
        return pd.Series({"Descricao": desc, "Valor": valor})
    
    processed = df.apply(process_row, axis=1)
    df["Descricao"] = processed["Descricao"]
    df["Valor"] = processed["Valor"]
    
    if adjust_dates and ref_month and ref_year:
        df["Data"] = df["Data"].apply(lambda d: _adjust_date_to_ref_month(d, ref_month, ref_year))
    
    return df[["Data", "Descricao", "Valor"]]

def _parse_bradesco_cc_pdf(file_bytes: bytes, ref_month: int, ref_year: int, adjust_dates: bool = True) -> pd.DataFrame:
    """
    Lê o PDF do extrato Bradesco Cartão e devolve um DataFrame
    normalizado com colunas: Data, Descricao, Valor.
    - Filtra apenas pagamentos de fatura (SALDO ANTERIOR, PAGTO ANTECIPADO)
    - Mantém estornos (valores negativos são convertidos com prefixo)
    - Ajusta datas de parcelas para o mês de referência da fatura
    """
    if PDF_SUPPORT:
        try:
            pdf_reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        except Exception:
            text = file_bytes.decode("utf-8", errors="replace")
    else:
        text = file_bytes.decode("utf-8", errors="replace")
    
    pattern_date_start = r"^(\d{2}/\d{2})\s+(.+)"
    pattern_value_end = r"(-?[\d.]+,\d{2})$"
    
    skip_patterns = [
        r"^XXXX\.",
        r"^-- \d+ of \d+ --$",
        r"^Data Histórico",
        r"^origem US\$",
        r"^Aplicativo Bradesco",
        r"^Data:",
        r"^Situação",
        r"Extrato em Aberto",
        r"^\. Total",
        r"^US\$ R\$$",
        r"^Moeda de$",
        r"^R\$$",
        r"VISA SIGNATURE$",
        r"VISA GOLD$",
        r"MASTERCARD$",
    ]
    
    rows = []
    lines = text.splitlines()
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        
        if not line:
            continue
        
        should_skip = False
        for pattern in skip_patterns:
            if re.search(pattern, line):
                should_skip = True
                break
        if should_skip:
            continue
        
        match_date = re.match(pattern_date_start, line)
        if not match_date:
            continue
        
        date_str = match_date.group(1)
        rest = match_date.group(2).strip()
        
        match_value = re.search(pattern_value_end, rest)
        
        if not match_value:
            if i < len(lines):
                next_line = lines[i].strip()
                if not re.match(r"^\d{2}/\d{2}", next_line) and not any(re.search(p, next_line) for p in skip_patterns):
                    rest = rest + " " + next_line
                    i += 1
                    match_value = re.search(pattern_value_end, rest)
        
        if not match_value:
            continue
        
        valor_str = match_value.group(1)
        desc = rest[:match_value.start()].strip()
        
        if not desc:
            continue
        
        if _is_payment_entry(desc):
            continue
        
        valor_str = valor_str.replace(".", "").replace(",", ".")
        try:
            valor = float(valor_str)
        except Exception:
            continue
        
        if valor < 0:
            desc = f"ESTORNO: {desc}"
            valor = abs(valor)
        
        try:
            day, month = map(int, date_str.split("/"))
        except Exception:
            continue
        
        if month > ref_month + 1:
            year = ref_year - 1
        elif month < ref_month - 1 and month <= 2:
            year = ref_year + 1
        else:
            year = ref_year
        
        try:
            original_date = date(year, month, day)
        except Exception:
            continue
        
        if adjust_dates:
            final_date = _adjust_date_to_ref_month(original_date, ref_month, ref_year)
        else:
            final_date = original_date
        
        rows.append({
            "Data": final_date,
            "Descricao": desc,
            "Valor": valor
        })
    
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["Data", "Descricao", "Valor"])
    
    return df

def _read_bradesco_csv(file_bytes: bytes) -> pd.DataFrame:
    """
    Lê o CSV do extrato Bradesco (separador ;, vírgula decimal) e devolve um DataFrame
    normalizado com colunas: Data, Descricao, Credito, Debito.
    """
    text = file_bytes.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Data;Histórico;Docto.;Crédito"):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Não encontrei o cabeçalho do Bradesco no CSV.")

    # Coleta linhas até a próxima seção/rodapé
    data_lines: list[str] = []
    for j in range(header_idx, len(lines)):
        l = lines[j].strip()
        if j > header_idx and (l.startswith("Últimos Lancamentos") or l.startswith("Filtro de resultados")):
            break
        if l == "" or set(l) == {";"}:
            continue
        data_lines.append(lines[j])

    buf = io.StringIO("\n".join(data_lines))
    df = pd.read_csv(buf, sep=";", dtype=str)

    # Remove linhas de total/ruído
    if "Data" in df.columns:
        df = df[df["Data"].notna() & (df["Data"].str.strip() != "")].copy()

    df.rename(
        columns={
            "Histórico": "Descricao",
            "Crédito (R$)": "Credito",
            "Débito (R$)": "Debito",
        },
        inplace=True,
    )

    # Normaliza campos
    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce").dt.date
    df["Descricao"] = df["Descricao"].astype(str).str.strip()
    df["Credito"] = df.get("Credito", "").astype(str).str.strip()
    df["Debito"] = df.get("Debito", "").astype(str).str.strip()

    # Filtra datas inválidas e "COD. LANC. 0" (linha de saldo)
    df = df[df["Data"].notna()].copy()
    df = df[~df["Descricao"].str.upper().str.startswith("COD. LANC.")].copy()
    df = df[~df["Descricao"].str.upper().str.contains("TOTAL", na=False)].copy()

    return df[["Data", "Descricao", "Credito", "Debito"]]

try:
    _root = PROJECT_ROOT
except NameError:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_PATH = os.path.join(_root, "exemplos", "planilha_exemplo.xlsx")

with main_tab_import:
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
    st.markdown("### Importar")
    tab_excel, tab_bradesco, tab_nubank_cc, tab_bradesco_cc = st.tabs([
        "📘 Excel (modelo)", 
        "🏦 Bradesco Conta (CSV)",
        "💜 Nubank Cartão (CSV)",
        "🔴 Bradesco Cartão (PDF)"
    ])

with tab_excel:
    uploaded_excel = st.file_uploader("Escolha um arquivo Excel", type=['xlsx', 'xls'], key="uploader_excel")

    if uploaded_excel:
        st.markdown("---")
        st.markdown("### Pré-visualização")
        try:
            excel_file = pd.ExcelFile(uploaded_excel)
            sheets = excel_file.sheet_names
            st.write(f"**Abas encontradas:** {', '.join(sheets)}")

            import_trans = 'Transacoes' in sheets
            import_cc = 'Cartao' in sheets
            df_trans = None
            df_cc = None

            if import_trans:
                df_trans = pd.read_excel(uploaded_excel, sheet_name='Transacoes')
                st.markdown("#### Transações")
                st.dataframe(df_trans.head(10))

                if 'Quantidade' in df_trans.columns:
                    inv_rows = df_trans[(df_trans['Quantidade'].notna()) & (df_trans['Quantidade'] != '') & (df_trans['Quantidade'] != 0)]
                    if len(inv_rows) > 0:
                        st.info(f"📈 {len(inv_rows)} transações de investimento detectadas (com Quantidade). O ticker será extraído da descrição.")

            selected_import_card = None
            if import_cc:
                df_cc = pd.read_excel(uploaded_excel, sheet_name='Cartao')
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

            if st.button("📥 Importar Excel", type="primary", use_container_width=True, key="btn_import_excel"):
                account = session.query(Account).first()
                if not account:
                    account = Account(name="Conta Principal", initial_balance=0)
                    session.add(account)
                    session.commit()
                
                categories = {c.name.lower(): c for c in session.query(Category).all()}
                
                imported_count = {'transactions': 0, 'cc': 0, 'investments': 0}
                
                if import_trans:
                    if df_trans is not None:
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
                                date_val = pd.to_datetime(row["Data"], dayfirst=True).date()
                                amount = Decimal(str(row["Valor"]))
                                description = str(row["Descricao"])
                                cat_name = str(row.get("Categoria", "")).lower()
                                trans_type = str(row.get("Tipo", "saida")).lower()

                                ticker = ""
                                quantity = None
                                preco_unidade = None

                                if has_ticker_col:
                                    ticker_val = row.get("Ticker")
                                    if pd.notna(ticker_val) and str(ticker_val).strip():
                                        ticker = str(ticker_val).upper().strip()

                                if has_qty_col:
                                    qty_val = row.get("Quantidade")
                                    if pd.notna(qty_val):
                                        try:
                                            qty_float = float(qty_val)
                                            if qty_float > 0:
                                                quantity = Decimal(str(qty_float))
                                        except (ValueError, TypeError):
                                            quantity = None

                                if has_price_col:
                                    pu_val = row.get("PrecoUnidade")
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

                                is_investment_trans = ticker != "" and quantity is not None and quantity > 0

                                category = categories.get(cat_name)
                                if not category and cat_name:
                                    cat_type = CategoryType.INCOME if trans_type == "entrada" else CategoryType.EXPENSE
                                    category = Category(
                                        name=row["Categoria"],
                                        category_type=cat_type,
                                        color="#7c3aed" if is_investment_trans else "#3b82f6",
                                        is_investment=is_investment_trans,
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
                                            investment_type=inv_type_map.get(inv_type_str, InvestmentType.STOCK),
                                        )
                                        session.add(investment)
                                        session.flush()
                                        investments_cache[ticker] = investment
                                    else:
                                        investment = investments_cache[ticker]

                                    investment_id = investment.id
                                    price_per_unit = preco_unidade if preco_unidade else (amount / quantity)
                                    imported_count["investments"] += 1

                                transaction = Transaction(
                                    date=date_val,
                                    amount=amount,
                                    description=description,
                                    transaction_type=TransactionType.INCOME if trans_type == "entrada" else TransactionType.EXPENSE,
                                    category_id=category.id if category else None,
                                    account_id=account.id,
                                    investment_id=investment_id,
                                    quantity=quantity,
                                    price_per_unit=price_per_unit,
                                )
                                session.add(transaction)
                                imported_count["transactions"] += 1
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
            st.error(f"Erro ao ler arquivo Excel: {e}")

with tab_bradesco:
    uploaded_bradesco = st.file_uploader("Escolha o CSV do Bradesco", type=['csv'], key="uploader_bradesco")

    if uploaded_bradesco:
        st.markdown("---")
        st.markdown("### Pré-visualização")
        try:
            df_bradesco = _read_bradesco_csv(uploaded_bradesco.getvalue())
            st.markdown("#### Transações (Bradesco)")
            st.dataframe(df_bradesco.head(30))

            st.markdown("---")
            if st.button("🏦 Importar CSV Bradesco", type="primary", use_container_width=True, key="btn_import_bradesco"):
                account = session.query(Account).first()
                if not account:
                    account = Account(name="Conta Principal", initial_balance=0)
                    session.add(account)
                    session.commit()

                imported = 0
                for _, row in df_bradesco.iterrows():
                    try:
                        date_val = row["Data"]
                        description = str(row["Descricao"])

                        credit = _parse_ptbr_money(row.get("Credito"))
                        debit = _parse_ptbr_money(row.get("Debito"))

                        if credit and credit > 0:
                            amount = credit
                            ttype = TransactionType.INCOME
                        elif debit and debit > 0:
                            amount = debit
                            ttype = TransactionType.EXPENSE
                        else:
                            continue

                        transaction = Transaction(
                            date=date_val,
                            amount=amount,
                            description=description,
                            transaction_type=ttype,
                            category_id=None,
                            account_id=account.id,
                        )
                        session.add(transaction)
                        imported += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar linha do Bradesco: {e}")

                session.commit()
                st.toast("✅ Importação Bradesco concluída!", icon="✅")
                st.success(f"Importadas **{imported}** transações do Bradesco.")

        except Exception as e:
            st.error(f"Erro ao ler CSV do Bradesco: {e}")

with tab_nubank_cc:
    st.markdown("""
    **Formato esperado:** CSV exportado do app Nubank com colunas `date`, `title`, `amount`.
    
    **Registros ignorados automaticamente:**
    - Pagamentos de fatura ("Pagamento recebido", "Pagamento efetuado")
    
    **Tratamento especial:**
    - Estornos (valores negativos) são mantidos com prefixo "ESTORNO:"
    - Datas de parcelas são ajustadas para o mês de referência da fatura
    """)
    
    uploaded_nubank = st.file_uploader("Escolha o CSV do Nubank", type=['csv'], key="uploader_nubank_cc")
    
    col_ref1, col_ref2, col_ref3 = st.columns(3)
    with col_ref1:
        nubank_ref_month = st.selectbox(
            "Mês de Referência",
            range(1, 13),
            index=date.today().month - 1,
            format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
            key="nubank_ref_month"
        )
    with col_ref2:
        nubank_ref_year = st.selectbox(
            "Ano de Referência",
            range(2020, date.today().year + 2),
            index=date.today().year - 2020,
            key="nubank_ref_year"
        )
    with col_ref3:
        nubank_adjust_dates = st.checkbox("Ajustar datas para o mês", value=True, key="nubank_adjust_dates",
                                         help="Transações de outros meses (parcelas) terão a data ajustada para o mês de referência da fatura")
    
    if uploaded_nubank:
        st.markdown("---")
        st.markdown("### Pré-visualização")
        try:
            df_nubank = _parse_nubank_csv(
                uploaded_nubank.getvalue(),
                nubank_ref_month,
                nubank_ref_year,
                nubank_adjust_dates
            )
            st.markdown(f"**{len(df_nubank)} transações encontradas**")
            st.dataframe(df_nubank.head(30))
            
            cards = session.query(CreditCard).all()
            if cards:
                card_options = {c.name: c.id for c in cards}
                selected_nubank_card = st.selectbox(
                    "Selecione o cartão para importar",
                    list(card_options.keys()),
                    key="nubank_card_select"
                )
            else:
                st.warning("⚠️ Nenhum cartão cadastrado. Será criado um cartão 'Nubank'.")
                selected_nubank_card = None
            
            st.markdown("---")
            if st.button("💜 Importar Nubank", type="primary", use_container_width=True, key="btn_import_nubank"):
                if selected_nubank_card:
                    target_card = session.query(CreditCard).filter(CreditCard.name == selected_nubank_card).first()
                else:
                    target_card = session.query(CreditCard).filter(CreditCard.name == "Nubank").first()
                    if not target_card:
                        target_card = CreditCard(name="Nubank")
                        session.add(target_card)
                        session.flush()
                
                imported = 0
                for _, row in df_nubank.iterrows():
                    try:
                        cc_trans = CreditCardTransaction(
                            date=row["Data"],
                            amount=Decimal(str(row["Valor"])),
                            description=str(row["Descricao"]),
                            installment_number=1,
                            total_installments=1,
                            category_id=None,
                            credit_card_id=target_card.id
                        )
                        session.add(cc_trans)
                        imported += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar: {e}")
                
                session.commit()
                st.toast("✅ Importação Nubank concluída!", icon="✅")
                st.success(f"Importadas **{imported}** transações do Nubank.")
        
        except Exception as e:
            st.error(f"Erro ao ler CSV do Nubank: {e}")

with tab_bradesco_cc:
    if not PDF_SUPPORT:
        st.error("⚠️ Biblioteca PyPDF2 não instalada. Execute: `pip install PyPDF2`")
    
    st.markdown("""
    **Formato esperado:** PDF do extrato do cartão Bradesco.
    
    **Registros ignorados automaticamente:**
    - Pagamentos de fatura ("SALDO ANTERIOR", "PAGTO ANTECIPADO")
    
    **Tratamento especial:**
    - Estornos (valores negativos) são mantidos com prefixo "ESTORNO:"
    - Datas de parcelas são ajustadas para o mês de referência da fatura
    """)
    
    uploaded_bradesco_cc = st.file_uploader("Escolha o PDF do Bradesco Cartão", type=['pdf'], key="uploader_bradesco_cc")
    
    col_bcc1, col_bcc2, col_bcc3 = st.columns(3)
    with col_bcc1:
        bradesco_cc_ref_month = st.selectbox(
            "Mês de Referência",
            range(1, 13),
            index=date.today().month - 1,
            format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                   "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
            key="bradesco_cc_ref_month"
        )
    with col_bcc2:
        bradesco_cc_ref_year = st.selectbox(
            "Ano de Referência",
            range(2020, date.today().year + 2),
            index=date.today().year - 2020,
            key="bradesco_cc_ref_year"
        )
    with col_bcc3:
        bradesco_cc_adjust_dates = st.checkbox("Ajustar datas para o mês", value=True, key="bradesco_cc_adjust_dates",
                                              help="Transações de outros meses (parcelas) terão a data ajustada para o mês de referência da fatura")
    
    if uploaded_bradesco_cc:
        st.markdown("---")
        st.markdown("### Pré-visualização")
        try:
            df_bradesco_cc = _parse_bradesco_cc_pdf(
                uploaded_bradesco_cc.getvalue(),
                bradesco_cc_ref_month,
                bradesco_cc_ref_year,
                bradesco_cc_adjust_dates
            )
            st.markdown(f"**{len(df_bradesco_cc)} transações encontradas**")
            st.dataframe(df_bradesco_cc.head(30))
            
            cards = session.query(CreditCard).all()
            if cards:
                card_options = {c.name: c.id for c in cards}
                selected_bradesco_card = st.selectbox(
                    "Selecione o cartão para importar",
                    list(card_options.keys()),
                    key="bradesco_cc_card_select"
                )
            else:
                st.warning("⚠️ Nenhum cartão cadastrado. Será criado um cartão 'Bradesco'.")
                selected_bradesco_card = None
            
            st.markdown("---")
            if st.button("🔴 Importar Bradesco Cartão", type="primary", use_container_width=True, key="btn_import_bradesco_cc"):
                if selected_bradesco_card:
                    target_card = session.query(CreditCard).filter(CreditCard.name == selected_bradesco_card).first()
                else:
                    target_card = session.query(CreditCard).filter(CreditCard.name == "Bradesco").first()
                    if not target_card:
                        target_card = CreditCard(name="Bradesco")
                        session.add(target_card)
                        session.flush()
                
                imported = 0
                for _, row in df_bradesco_cc.iterrows():
                    try:
                        cc_trans = CreditCardTransaction(
                            date=row["Data"],
                            amount=Decimal(str(row["Valor"])),
                            description=str(row["Descricao"]),
                            installment_number=1,
                            total_installments=1,
                            category_id=None,
                            credit_card_id=target_card.id
                        )
                        session.add(cc_trans)
                        imported += 1
                    except Exception as e:
                        st.warning(f"Erro ao importar: {e}")
                
                session.commit()
                st.toast("✅ Importação Bradesco Cartão concluída!", icon="✅")
                st.success(f"Importadas **{imported}** transações do Bradesco Cartão.")
        
        except Exception as e:
            st.error(f"Erro ao ler PDF do Bradesco: {e}")

with main_tab_export:
    st.markdown("### Exportar Dados")
    st.markdown("""
    Exporte seus dados em formato CSV compatível com a importação.
    Os arquivos exportados podem ser reimportados posteriormente.
    """)
    
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        export_month = st.selectbox(
            "Mês",
            [None] + list(range(1, 13)),
            format_func=lambda x: "Todos" if x is None else ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                                              "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][x-1],
            key="export_month"
        )
    with col_exp2:
        export_year = st.selectbox(
            "Ano",
            [None] + list(range(2020, date.today().year + 2)),
            format_func=lambda x: "Todos" if x is None else str(x),
            key="export_year"
        )
    
    export_type = st.multiselect(
        "O que exportar",
        ["Transações", "Cartão de Crédito"],
        default=["Transações", "Cartão de Crédito"],
        key="export_type"
    )
    
    if st.button("📤 Gerar Exportação", type="primary", use_container_width=True, key="btn_export"):
        from zipfile import ZipFile
        import tempfile
        
        trans_query = session.query(Transaction)
        cc_query = session.query(CreditCardTransaction)
        
        if export_month:
            year = export_year or date.today().year
            start_date = date(year, export_month, 1)
            if export_month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, export_month + 1, 1)
            trans_query = trans_query.filter(Transaction.date >= start_date, Transaction.date < end_date)
            cc_query = cc_query.filter(CreditCardTransaction.date >= start_date, CreditCardTransaction.date < end_date)
        elif export_year:
            trans_query = trans_query.filter(Transaction.date >= date(export_year, 1, 1), 
                                             Transaction.date < date(export_year + 1, 1, 1))
            cc_query = cc_query.filter(CreditCardTransaction.date >= date(export_year, 1, 1),
                                       CreditCardTransaction.date < date(export_year + 1, 1, 1))
        
        files_to_zip = []
        
        if "Transações" in export_type:
            transactions = trans_query.order_by(Transaction.date.desc()).all()
            
            trans_data = []
            for t in transactions:
                trans_data.append({
                    "Data": t.date.strftime("%d/%m/%Y"),
                    "Valor": float(t.amount),
                    "Descricao": t.description,
                    "Categoria": t.category.name if t.category else "",
                    "Tipo": "entrada" if t.transaction_type == TransactionType.INCOME else "saida",
                    "Quantidade": float(t.quantity) if t.quantity else "",
                    "PrecoUnidade": float(t.price_per_unit) if t.price_per_unit else ""
                })
            
            if trans_data:
                df_trans_export = pd.DataFrame(trans_data)
                trans_csv = df_trans_export.to_csv(index=False)
                files_to_zip.append(("transacoes.csv", trans_csv))
                st.success(f"✅ {len(trans_data)} transações prontas para exportação")
            else:
                st.info("Nenhuma transação encontrada no período")
        
        if "Cartão de Crédito" in export_type:
            cc_transactions = cc_query.order_by(CreditCardTransaction.date.desc()).all()
            
            cc_data = []
            for t in cc_transactions:
                cc_data.append({
                    "Data": t.date.strftime("%d/%m/%Y"),
                    "Valor": float(t.amount),
                    "Descricao": t.description,
                    "Categoria": t.category.name if t.category else "",
                    "Parcela": f"{t.installment_number}/{t.total_installments}",
                    "Cartao": t.credit_card.name if t.credit_card else ""
                })
            
            if cc_data:
                df_cc_export = pd.DataFrame(cc_data)
                cc_csv = df_cc_export.to_csv(index=False)
                files_to_zip.append(("cartao_credito.csv", cc_csv))
                st.success(f"✅ {len(cc_data)} transações de cartão prontas para exportação")
            else:
                st.info("Nenhuma transação de cartão encontrada no período")
        
        if files_to_zip:
            if len(files_to_zip) == 1:
                filename, content = files_to_zip[0]
                st.download_button(
                    label=f"📥 Baixar {filename}",
                    data=content,
                    file_name=filename,
                    mime="text/csv",
                    use_container_width=True,
                    key="download_single"
                )
            else:
                zip_buffer = io.BytesIO()
                with ZipFile(zip_buffer, "w") as zf:
                    for filename, content in files_to_zip:
                        zf.writestr(filename, content)
                zip_buffer.seek(0)
                
                period_str = ""
                if export_month and export_year:
                    period_str = f"_{export_year}_{export_month:02d}"
                elif export_year:
                    period_str = f"_{export_year}"
                
                st.download_button(
                    label="📥 Baixar ZIP com todos os arquivos",
                    data=zip_buffer,
                    file_name=f"exportacao_financeira{period_str}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="download_zip"
                )

session.close()
