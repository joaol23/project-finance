"""
dashboard.py — Tela principal com saldo e resumo do mês.

Flet 1.0.0:
- page.navigate(route) nativo
- ft.View com scroll=ft.ScrollMode.AUTO para layout responsivo
"""

import flet as ft
from decimal import Decimal
from mobile.styles import COLORS
from mobile.state import app_state, MONTH_NAMES
from database.connection import SessionLocal
from database.models import Transaction, TransactionType, MonthlyOpeningBalance, Account


def get_dashboard_view(page: ft.Page):
    start_bound, end_bound = app_state.get_period_bounds()

    total_income = Decimal("0")
    total_expense = Decimal("0")
    opening_balance = Decimal("0")
    expenses_by_cat: dict[str, Decimal] = {}

    try:
        session = SessionLocal()

        transactions = (
            session.query(Transaction)
            .filter(
                Transaction.date > start_bound,
                Transaction.date <= end_bound,
            )
            .all()
        )

        for t in transactions:
            if t.transaction_type == TransactionType.INCOME:
                total_income += Decimal(str(t.amount))
            elif t.transaction_type == TransactionType.EXPENSE:
                val = Decimal(str(t.amount))
                total_expense += val
                cat_name = t.category.name if t.category else "Outros"
                expenses_by_cat[cat_name] = expenses_by_cat.get(cat_name, Decimal("0")) + val

        account = session.query(Account).first()
        acc_initial = Decimal(str(account.initial_balance)) if account else Decimal("0")

        monthly_record = (
            session.query(MonthlyOpeningBalance)
            .filter_by(year=app_state.selected_year, month=app_state.selected_month)
            .first()
        )

        if monthly_record:
            opening_balance = Decimal(str(monthly_record.initial_balance))
        else:
            prev_txs = (
                session.query(Transaction)
                .filter(Transaction.date <= start_bound)
                .all()
            )
            opening_balance = acc_initial
            for t in prev_txs:
                if t.transaction_type == TransactionType.INCOME:
                    opening_balance += Decimal(str(t.amount))
                else:
                    opening_balance -= Decimal(str(t.amount))

        session.close()
    except Exception as e:
        print(f"Erro no banco: {e}")

    closing_balance = opening_balance + total_income - total_expense
    period_result = total_income - total_expense

    def on_month_change(e):
        app_state.selected_month = int(e.control.value)
        page.navigate("/dashboard")

    month_dropdown = ft.Dropdown(
        value=str(app_state.selected_month),
        options=[ft.dropdown.Option(str(i + 1), MONTH_NAMES[i]) for i in range(12)],
        width=150,
        bgcolor=COLORS["surface"],
        color=COLORS["text"],
        on_select=on_month_change,
        border_color=COLORS["primary"],
    )

    card_width = (page.window.width / 2.3) if page.window and page.window.width else 165

    def open_edit_initial_balance(e):
        tf = ft.TextField(
            label="Saldo Inicial (R$)",
            value=f"{opening_balance:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            color=COLORS["text"],
            border_color=COLORS["primary"],
        )

        def save_balance(ev):
            try:
                val = Decimal(tf.value.replace(",", "."))
                s = SessionLocal()
                rec = s.query(MonthlyOpeningBalance).filter_by(
                    year=app_state.selected_year, month=app_state.selected_month
                ).first()
                if rec:
                    rec.initial_balance = val
                else:
                    rec = MonthlyOpeningBalance(
                        year=app_state.selected_year,
                        month=app_state.selected_month,
                        initial_balance=val,
                    )
                    s.add(rec)
                s.commit()
                s.close()
                page.pop_dialog()
                page.navigate("/dashboard")
            except Exception as ex:
                print("Erro ao salvar saldo inicial:", ex)

        dialog = ft.AlertDialog(
            title=ft.Text("Configurar Saldo Inicial"),
            content=ft.Column(
                [
                    ft.Text(
                        f"Defina o saldo para {MONTH_NAMES[app_state.selected_month - 1]}/{app_state.selected_year}:",
                        size=13,
                        color=COLORS["text_secondary"],
                    ),
                    tf,
                ],
                tight=True,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda _: page.pop_dialog()),
                ft.FilledButton(
                    "Salvar",
                    on_click=save_balance,
                    style=ft.ButtonStyle(bgcolor=COLORS["primary"]),
                ),
            ],
        )
        page.show_dialog(dialog)

    def create_card(title, value, color, on_edit=None):
        header_controls = [ft.Text(title, size=13, color=COLORS["text_secondary"])]
        if on_edit:
            header_controls.append(
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_size=15,
                    icon_color=COLORS["primary_light"],
                    tooltip="Editar saldo inicial",
                    on_click=on_edit,
                )
            )

        return ft.Container(
            bgcolor=COLORS["surface"],
            border_radius=10,
            padding=12,
            width=card_width,
            content=ft.Column(
                [
                    ft.Row(
                        header_controls,
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Text(
                        f"R$ {value:,.2f}",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                        color=color,
                    ),
                ],
                spacing=4,
            ),
        )

    # Lista de despesas por categoria
    category_cards = []
    if expenses_by_cat and total_expense > 0:
        sorted_cats = sorted(expenses_by_cat.items(), key=lambda x: x[1], reverse=True)
        for cat_name, amt in sorted_cats[:6]:
            pct = float(amt / total_expense)
            category_cards.append(
                ft.Container(
                    bgcolor=COLORS["surface"],
                    border_radius=8,
                    padding=10,
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        cat_name,
                                        size=14,
                                        weight=ft.FontWeight.W_500,
                                        color=COLORS["text"],
                                    ),
                                    ft.Text(
                                        f"R$ {amt:,.2f} ({pct*100:.1f}%)",
                                        size=13,
                                        color=COLORS["text_secondary"],
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.ProgressBar(
                                value=pct,
                                color=COLORS["primary_light"],
                                bgcolor="#2d2d2d",
                                height=6,
                            ),
                        ],
                        spacing=6,
                    ),
                )
            )

    return ft.View(
        controls=[
            ft.Column(
                spacing=16,
                controls=[
                    ft.Row(
                        [
                            ft.Text(
                                "Dashboard",
                                size=26,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["primary"],
                            ),
                            month_dropdown,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        bgcolor=COLORS["surface"],
                        border_radius=12,
                        padding=18,
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Saldo Final Estimado",
                                    size=14,
                                    color=COLORS["text_secondary"],
                                ),
                                ft.Text(
                                    f"R$ {closing_balance:,.2f}",
                                    size=30,
                                    weight=ft.FontWeight.BOLD,
                                    color=(
                                        COLORS["success"]
                                        if closing_balance >= 0
                                        else COLORS["danger"]
                                    ),
                                ),
                            ]
                        ),
                    ),
                    ft.Row(
                        [
                            create_card("Saldo Inicial", opening_balance, COLORS["text"], on_edit=open_edit_initial_balance),
                            create_card("Resultado Mês", period_result, COLORS["success"] if period_result >= 0 else COLORS["danger"]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [
                            create_card("Entradas", total_income, COLORS["success"]),
                            create_card("Saídas", total_expense, COLORS["danger"]),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    *(
                        [
                            ft.Container(height=6),
                            ft.Text(
                                "Maiores Gastos do Mês",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=COLORS["text"],
                            ),
                            *category_cards,
                        ]
                        if category_cards
                        else []
                    ),
                    ft.Container(
                        margin=ft.Margin.only(top=10, bottom=20),
                        content=ft.Text(
                            f"Período contábil: {start_bound.strftime('%d/%m/%Y')} a {end_bound.strftime('%d/%m/%Y')}",
                            size=12,
                            color=COLORS["text_secondary"],
                        ),
                    ),
                ],
            )
        ],
        route="/dashboard",
        bgcolor=COLORS["background"],
        padding=16,
        scroll=ft.ScrollMode.AUTO,
    )
