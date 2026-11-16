"""
investments.py — Tela de Investimentos completa para o app mobile.

Funcionalidades:
- Resumo do portfólio (Total investido, Valor atual, Ganho/perda, Lucro realizado)
- Abas:
  1. Carteira: posições abertas com Ticker, Tipo, PM, Cotação, Quantidade e Rentabilidade; posições encerradas.
  2. Transações Pendentes: transações de categorias de investimento prontas para vincular a tickers.
  3. Nova Operação: compra ou venda direta de ativo.
- Botão "Atualizar Cotações" via stock_service.
"""

import flet as ft
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import joinedload
from mobile.styles import COLORS
from mobile.state import app_state
from database.connection import SessionLocal
from database.models import (
    Investment, Transaction, TransactionType, Category, CategoryType, Account, InvestmentType
)
from services.stock_service import get_stock_price, extract_ticker_from_description, detect_investment_type

TYPE_LABELS = {
    InvestmentType.STOCK: "Ação",
    InvestmentType.FII: "FII",
    InvestmentType.CRYPTO: "Crypto",
    InvestmentType.OTHER: "Outro",
}


def get_investments_view(page: ft.Page):
    selected_tab_index = 0

    def refresh_screen():
        page.views.clear()
        # Remonta a view
        v = get_investments_view(page)
        v.navigation_bar = page.navigation_bar
        page.views.append(v)
        page.update()

    # 1. Carrega dados do banco com joinedload
    session = SessionLocal()
    try:
        investments = session.query(Investment).options(joinedload(Investment.transactions)).all()

        invest_cat_ids = [
            c.id for c in session.query(Category).filter(Category.is_investment == True).all()
        ]
        pending_transactions = (
            session.query(Transaction)
            .options(joinedload(Transaction.category))
            .filter(
                Transaction.category_id.in_(invest_cat_ids),
                Transaction.investment_id == None,
            )
            .order_by(Transaction.date.desc())
            .all()
        )

        total_invested = Decimal("0")
        total_current = Decimal("0")
        total_gain = Decimal("0")
        total_realized = Decimal("0")

        open_investments_data = []
        closed_investments_data = []

        for inv in investments:
            qty = Decimal(str(inv.total_quantity))
            realized = Decimal(str(inv.realized_profit))
            total_realized += realized

            if qty > 0:
                inv_invested = Decimal(str(inv.total_invested))
                inv_current = Decimal(str(inv.current_value)) if inv.current_value > 0 else inv_invested
                total_invested += inv_invested
                total_current += inv_current

                gain = Decimal(str(inv.gain_loss))
                gain_pct = Decimal(str(inv.gain_loss_percent))

                open_investments_data.append({
                    "id": inv.id,
                    "ticker": inv.ticker,
                    "type": TYPE_LABELS.get(inv.investment_type, "Outro"),
                    "qty": qty,
                    "avg_price": Decimal(str(inv.average_price)),
                    "current_price": Decimal(str(inv.current_price or 0)),
                    "gain": gain,
                    "gain_pct": gain_pct,
                })
            elif len(inv.transactions) > 0:
                closed_investments_data.append({
                    "id": inv.id,
                    "ticker": inv.ticker,
                    "type": TYPE_LABELS.get(inv.investment_type, "Outro"),
                    "realized_profit": realized,
                })

        total_gain = total_current - total_invested

        # Extrai pendências para dicionários enquanto sessão está aberta
        pending_data = []
        for p in pending_transactions:
            pending_data.append({
                "id": p.id,
                "date": p.date,
                "description": p.description,
                "amount": Decimal(str(p.amount)),
                "type": p.transaction_type,
                "category_name": p.category.name if p.category else "Investimento",
            })

        all_tickers = [inv.ticker for inv in investments]
    finally:
        session.close()

    # Cards de Resumo
    gain_pct_overall = float(total_gain / total_invested * 100) if total_invested > 0 else 0.0
    gain_color = COLORS["success"] if total_gain >= 0 else COLORS["danger"]

    def summary_card(title, value, color=None):
        return ft.Container(
            bgcolor=COLORS["surface"],
            border_radius=10,
            padding=10,
            expand=True,
            content=ft.Column(
                spacing=3,
                controls=[
                    ft.Text(title, size=11, color=COLORS["text_secondary"]),
                    ft.Text(
                        value,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=color or COLORS["text"],
                    ),
                ],
            ),
        )

    summary_row = ft.Row(
        spacing=8,
        controls=[
            summary_card("Investido", f"R$ {float(total_invested):,.2f}"),
            summary_card("Atual", f"R$ {float(total_current):,.2f}"),
            summary_card(f"Ganho ({gain_pct_overall:+.1f}%)", f"R$ {float(total_gain):+,.2f}", gain_color),
        ],
    )

    # ── BOTÃO ATUALIZAR COTAÇÕES ────────────────────────────────────────────────
    status_quote_text = ft.Text("", size=12, color=COLORS["text_secondary"])

    def on_refresh_quotes(e):
        status_quote_text.value = "Buscando cotações no Yahoo/B3..."
        status_quote_text.color = COLORS["primary_light"]
        page.update()

        s = SessionLocal()
        try:
            inv_list = s.query(Investment).all()
            updated = 0
            for inv in inv_list:
                price = get_stock_price(inv.ticker)
                if price and price > 0:
                    inv.current_price = Decimal(str(price))
                    updated += 1
            s.commit()
            status_quote_text.value = f"✓ {updated} cotações atualizadas!"
            status_quote_text.color = COLORS["success"]
            page.update()
            refresh_screen()
        except Exception as ex:
            status_quote_text.value = f"Erro ao atualizar: {ex}"
            status_quote_text.color = COLORS["danger"]
            page.update()
        finally:
            s.close()

    refresh_quotes_btn = ft.OutlinedButton(
        "Atualizar Cotações",
        icon=ft.Icons.REFRESH,
        on_click=on_refresh_quotes,
        style=ft.ButtonStyle(color=COLORS["primary_light"]),
    )

    # ── ABA 1: CARTEIRA ──────────────────────────────────────────────────────────
    portfolio_column = ft.Column(spacing=10)

    if open_investments_data:
        for item in open_investments_data:
            g_col = COLORS["success"] if item["gain"] >= 0 else COLORS["danger"]
            portfolio_column.controls.append(
                ft.Container(
                    bgcolor=COLORS["surface"],
                    border_radius=10,
                    padding=14,
                    content=ft.Column(
                        spacing=8,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Row([
                                        ft.Text(item["ticker"], size=17, weight=ft.FontWeight.BOLD, color=COLORS["primary_light"]),
                                        ft.Container(
                                            bgcolor="#2d2d2d",
                                            border_radius=6,
                                            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                            content=ft.Text(item["type"], size=11, color=COLORS["text_secondary"]),
                                        ),
                                    ], spacing=6),
                                    ft.Text(
                                        f"R$ {float(item['gain']):+,.2f} ({float(item['gain_pct']):+.1f}%)",
                                        size=13,
                                        weight=ft.FontWeight.BOLD,
                                        color=g_col,
                                    ),
                                ],
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(f"Qtd: {float(item['qty']):,.2f}", size=12, color=COLORS["text_secondary"]),
                                    ft.Text(f"PM: R$ {float(item['avg_price']):,.2f}", size=12, color=COLORS["text_secondary"]),
                                    ft.Text(f"Cotação: R$ {float(item['current_price']):,.2f}", size=12, color=COLORS["text"]),
                                ],
                            ),
                        ],
                    ),
                )
            )
    else:
        portfolio_column.controls.append(
            ft.Container(
                padding=20,
                content=ft.Text("Nenhum ativo com saldo em carteira.", color=COLORS["text_secondary"]),
            )
        )

    if closed_investments_data:
        portfolio_column.controls.append(ft.Container(height=10))
        portfolio_column.controls.append(ft.Text("Posições Encerradas", size=15, weight=ft.FontWeight.BOLD, color=COLORS["text_secondary"]))
        for c_item in closed_investments_data:
            c_profit = float(c_item["realized_profit"])
            c_color = COLORS["success"] if c_profit >= 0 else COLORS["danger"]
            portfolio_column.controls.append(
                ft.Container(
                    bgcolor=COLORS["surface"],
                    border_radius=8,
                    padding=12,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(c_item["ticker"], size=14, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Lucro Realizado: R$ {c_profit:+,.2f}", size=13, weight=ft.FontWeight.BOLD, color=c_color),
                        ],
                    ),
                )
            )

    # ── ABA 2: TRANSAÇÕES PENDENTES DE VINCULAÇÃO ─────────────────────────────────
    pending_column = ft.Column(spacing=10)

    def open_link_dialog(tx_item):
        sug_ticker = extract_ticker_from_description(tx_item["description"]) or ""
        ticker_input = ft.TextField(
            label="Ticker (ex: PETR4, MXRF11, BTC)",
            value=sug_ticker.upper(),
            bgcolor=COLORS["surface"],
            color=COLORS["text"],
            border_color=COLORS["primary"],
        )
        qty_input = ft.TextField(
            label="Quantidade comprada/vendida",
            value="1",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=COLORS["surface"],
            color=COLORS["text"],
            border_color=COLORS["primary"],
        )
        price_input = ft.TextField(
            label="Preço por unidade (R$)",
            value=f"{float(tx_item['amount']):.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=COLORS["surface"],
            color=COLORS["text"],
            border_color=COLORS["primary"],
        )

        def on_qty_change(e):
            try:
                q = Decimal(qty_input.value.replace(",", "."))
                if q > 0:
                    unit_p = tx_item["amount"] / q
                    price_input.value = f"{float(unit_p):.2f}"
                    page.update()
            except:
                pass

        qty_input.on_change = on_qty_change

        def save_link(ev):
            t_val = ticker_input.value.strip().upper()
            if not t_val:
                return
            try:
                q_val = Decimal(qty_input.value.replace(",", "."))
                p_val = Decimal(price_input.value.replace(",", "."))

                s = SessionLocal()
                tx = s.query(Transaction).filter(Transaction.id == tx_item["id"]).first()
                if not tx:
                    s.close()
                    return

                inv = s.query(Investment).filter(Investment.ticker == t_val).first()
                if not inv:
                    inv_type_code = detect_investment_type(t_val)
                    type_map = {
                        "stock": InvestmentType.STOCK,
                        "fii": InvestmentType.FII,
                        "crypto": InvestmentType.CRYPTO,
                        "other": InvestmentType.OTHER,
                    }
                    inv = Investment(
                        ticker=t_val,
                        investment_type=type_map.get(inv_type_code, InvestmentType.STOCK),
                        current_price=p_val,
                    )
                    s.add(inv)
                    s.flush()

                tx.investment_id = inv.id
                tx.quantity = q_val
                tx.price_per_unit = p_val
                s.commit()
                s.close()

                page.pop_dialog()
                refresh_screen()
            except Exception as ex:
                print(f"Erro ao vincular ativo: {ex}")

        dialog = ft.AlertDialog(
            title=ft.Text("Vincular Ativo"),
            content=ft.Column(
                tight=True,
                spacing=10,
                controls=[
                    ft.Text(f"{tx_item['date'].strftime('%d/%m/%Y')} • {tx_item['description']}", size=12, color=COLORS["text_secondary"]),
                    ft.Text(f"Valor Total: R$ {float(tx_item['amount']):,.2f}", size=14, weight=ft.FontWeight.BOLD),
                    ticker_input,
                    qty_input,
                    price_input,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton("Vincular Ativo", icon=ft.Icons.LINK, on_click=save_link, style=ft.ButtonStyle(bgcolor=COLORS["primary"])),
            ],
        )
        page.show_dialog(dialog)

    if pending_data:
        pending_column.controls.append(
            ft.Text(f"{len(pending_data)} transação(ões) aguardando vínculo:", size=13, color=COLORS["text_secondary"])
        )
        for item in pending_data:
            pending_column.controls.append(
                ft.Container(
                    bgcolor=COLORS["surface"],
                    border_radius=10,
                    padding=12,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=3,
                                controls=[
                                    ft.Text(item["description"], size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{item['date'].strftime('%d/%m/%Y')} • R$ {float(item['amount']):,.2f}", size=12, color=COLORS["text_secondary"]),
                                ],
                            ),
                            ft.FilledButton(
                                "Vincular",
                                icon=ft.Icons.LINK,
                                on_click=lambda e, it=item: open_link_dialog(it),
                                style=ft.ButtonStyle(bgcolor=COLORS["primary"]),
                            ),
                        ],
                    ),
                )
            )
    else:
        pending_column.controls.append(
            ft.Container(
                padding=20,
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=22),
                    ft.Text("Nenhuma transação pendente de vinculação!", color=COLORS["success"], size=14),
                ], spacing=10),
            )
        )

    # ── ABA 3: NOVA OPERAÇÃO MANUAL ───────────────────────────────────────────────
    ticker_new_input = ft.TextField(label="Ticker (ex: VALE3, MXRF11)", bgcolor=COLORS["surface"])
    type_new_dropdown = ft.Dropdown(
        label="Tipo de Ativo",
        value="Ações",
        options=[ft.dropdown.Option("Ações"), ft.dropdown.Option("FIIs"), ft.dropdown.Option("Criptomoedas"), ft.dropdown.Option("Outro")],
        bgcolor=COLORS["surface"],
    )
    operation_type = ft.Dropdown(
        label="Operação",
        value="Compra",
        options=[ft.dropdown.Option("Compra"), ft.dropdown.Option("Venda")],
        bgcolor=COLORS["surface"],
    )
    qty_new_input = ft.TextField(label="Quantidade", value="1", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=COLORS["surface"])
    price_new_input = ft.TextField(label="Preço Unitário (R$)", keyboard_type=ft.KeyboardType.NUMBER, bgcolor=COLORS["surface"])
    feedback_text = ft.Text("", size=13)

    def on_save_manual_op(e):
        t_code = ticker_new_input.value.strip().upper()
        if not t_code or not qty_new_input.value or not price_new_input.value:
            feedback_text.value = "Preencha todos os campos obrigatórios."
            feedback_text.color = COLORS["danger"]
            page.update()
            return
        try:
            q_num = Decimal(qty_new_input.value.replace(",", "."))
            p_num = Decimal(price_new_input.value.replace(",", "."))
            total_op = q_num * p_num

            s = SessionLocal()
            acc = s.query(Account).first()
            if not acc:
                acc = Account(name="Conta Principal", initial_balance=Decimal("0"))
                s.add(acc)
                s.flush()

            cat = s.query(Category).filter(Category.is_investment == True).first()

            inv = s.query(Investment).filter(Investment.ticker == t_code).first()
            if not inv:
                inv_type_map = {
                    "Ações": InvestmentType.STOCK,
                    "FIIs": InvestmentType.FII,
                    "Criptomoedas": InvestmentType.CRYPTO,
                    "Outro": InvestmentType.OTHER,
                }
                inv = Investment(
                    ticker=t_code,
                    investment_type=inv_type_map.get(type_new_dropdown.value, InvestmentType.STOCK),
                    current_price=p_num,
                )
                s.add(inv)
                s.flush()

            tx = Transaction(
                date=datetime.now().date(),
                amount=total_op,
                description=f"{operation_type.value} de {q_num} {t_code}",
                transaction_type=TransactionType.EXPENSE if operation_type.value == "Compra" else TransactionType.INCOME,
                account_id=acc.id,
                investment_id=inv.id,
                quantity=q_num,
                price_per_unit=p_num,
                category_id=cat.id if cat else None,
            )
            s.add(tx)
            s.commit()
            s.close()

            feedback_text.value = "✓ Transação de investimento registrada com sucesso!"
            feedback_text.color = COLORS["success"]
            ticker_new_input.value = ""
            qty_new_input.value = "1"
            price_new_input.value = ""
            page.update()
            refresh_screen()
        except Exception as ex:
            feedback_text.value = f"Erro: {ex}"
            feedback_text.color = COLORS["danger"]
            page.update()

    new_op_column = ft.Column(
        spacing=12,
        controls=[
            ft.Text("Cadastrar Compra ou Venda Direta", size=15, weight=ft.FontWeight.BOLD),
            operation_type,
            ticker_new_input,
            type_new_dropdown,
            qty_new_input,
            price_new_input,
            feedback_text,
            ft.FilledButton(
                "Salvar Operação",
                icon=ft.Icons.CHECK,
                on_click=on_save_manual_op,
                style=ft.ButtonStyle(bgcolor=COLORS["primary"]),
            ),
        ],
    )

    # Conteúdo alternável com botões de aba estilizados
    content_area = ft.Container(content=portfolio_column)

    active_style = ft.ButtonStyle(
        bgcolor=COLORS["primary"],
        color=COLORS["text"],
    )
    inactive_style = ft.ButtonStyle(
        bgcolor=COLORS["surface"],
        color=COLORS["text_secondary"],
    )

    btn_carteira = ft.FilledButton("Minha Carteira", icon=ft.Icons.PIE_CHART, style=active_style)
    pend_label = f"Pendentes ({len(pending_data)})" if pending_data else "Pendentes"
    btn_pendentes = ft.FilledButton(pend_label, icon=ft.Icons.PENDING_ACTIONS, style=inactive_style)
    btn_nova = ft.FilledButton("Nova Operação", icon=ft.Icons.ADD_CIRCLE_OUTLINE, style=inactive_style)

    def set_tab(idx):
        btn_carteira.style = active_style if idx == 0 else inactive_style
        btn_pendentes.style = active_style if idx == 1 else inactive_style
        btn_nova.style = active_style if idx == 2 else inactive_style
        if idx == 0:
            content_area.content = portfolio_column
        elif idx == 1:
            content_area.content = pending_column
        else:
            content_area.content = new_op_column
        page.update()

    btn_carteira.on_click = lambda _: set_tab(0)
    btn_pendentes.on_click = lambda _: set_tab(1)
    btn_nova.on_click = lambda _: set_tab(2)

    tabs_row = ft.Row(
        scroll=ft.ScrollMode.AUTO,
        spacing=8,
        controls=[btn_carteira, btn_pendentes, btn_nova],
    )

    return ft.View(
        controls=[
            ft.Column(
                spacing=14,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Investimentos", size=24, weight=ft.FontWeight.BOLD, color=COLORS["primary"]),
                            refresh_quotes_btn,
                        ],
                    ),
                    status_quote_text,
                    summary_row,
                    tabs_row,
                    content_area,
                ],
            )
        ],
        route="/investments",
        bgcolor=COLORS["background"],
        padding=16,
        scroll=ft.ScrollMode.AUTO,
    )
