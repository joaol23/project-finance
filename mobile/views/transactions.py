"""
transactions.py — Tela de listagem e criação de transações.

Flet 1.0.0:
- ft.FilledButton (ElevatedButton não existe)
- page.show_dialog() / page.pop_dialog()
- ft.View com scroll=ft.ScrollMode.AUTO
"""

import flet as ft
from datetime import datetime
from decimal import Decimal
from mobile.styles import COLORS
from mobile.state import app_state
from database.connection import SessionLocal
from database.models import Transaction, TransactionType, Category, Account
from services.transaction_service import create_transaction


def get_transactions_view(page: ft.Page):
    start_bound, end_bound = app_state.get_period_bounds()
    transactions_column = ft.Column(spacing=10)

    def carregar_transacoes():
        transactions_column.controls.clear()
        try:
            session = SessionLocal()
            txs = (
                session.query(Transaction)
                .filter(
                    Transaction.date > start_bound,
                    Transaction.date <= end_bound,
                )
                .order_by(Transaction.date.desc())
                .all()
            )

            for tx in txs:
                icon_color = (
                    COLORS["success"]
                    if tx.transaction_type == TransactionType.INCOME
                    else COLORS["danger"]
                )
                icon_data = (
                    ft.Icons.ARROW_UPWARD
                    if tx.transaction_type == TransactionType.INCOME
                    else ft.Icons.ARROW_DOWNWARD
                )
                cat_name = tx.category.name if tx.category else "Sem Categoria"

                transactions_column.controls.append(
                    ft.Container(
                        bgcolor=COLORS["surface"],
                        border_radius=10,
                        padding=15,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    [
                                        ft.Icon(icon_data, color=icon_color, size=24),
                                        ft.Column(
                                            [
                                                ft.Text(
                                                    tx.description,
                                                    size=16,
                                                    weight=ft.FontWeight.BOLD,
                                                ),
                                                ft.Text(
                                                    f"{tx.date.strftime('%d/%m')} • {cat_name}",
                                                    size=12,
                                                    color=COLORS["text_secondary"],
                                                ),
                                            ],
                                            spacing=2,
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    f"R$ {tx.amount:,.2f}",
                                    size=16,
                                    color=icon_color,
                                    weight=ft.FontWeight.BOLD,
                                ),
                            ],
                        ),
                    )
                )

            if not txs:
                transactions_column.controls.append(
                    ft.Text(
                        "Nenhuma transação no período.",
                        color=COLORS["text_secondary"],
                    )
                )
            session.close()
        except Exception as e:
            transactions_column.controls.append(
                ft.Text(f"Erro ao carregar: {e}", color=COLORS["danger"])
            )
        page.update()

    carregar_transacoes()

    def show_add_modal(e):
        session = SessionLocal()
        try:
            categories = session.query(Category).all()
            cat_options = [ft.dropdown.Option(c.name) for c in categories]
            account = session.query(Account).first()
        finally:
            session.close()

        desc_input = ft.TextField(label="Descrição", bgcolor=COLORS["surface"])
        amount_input = ft.TextField(
            label="Valor (R$)",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=COLORS["surface"],
        )
        type_dropdown = ft.Dropdown(
            label="Tipo",
            options=[
                ft.dropdown.Option("Entrada"),
                ft.dropdown.Option("Saída"),
            ],
            value="Saída",
            bgcolor=COLORS["surface"],
        )
        cat_dropdown = ft.Dropdown(
            label="Categoria", options=cat_options, bgcolor=COLORS["surface"]
        )

        def fechar_dialog(e=None):
            page.pop_dialog()

        def save_new_transaction(e):
            if not desc_input.value or not amount_input.value:
                return
            try:
                val = Decimal(amount_input.value.replace(",", "."))
                create_transaction(
                    trans_date=datetime.now().date(),
                    amount=val,
                    description=desc_input.value,
                    trans_type=type_dropdown.value,
                    category_name=cat_dropdown.value,
                    account=account,
                )
                fechar_dialog()
                carregar_transacoes()
            except Exception as err:
                print(f"Erro ao salvar: {err}")

        dialog = ft.AlertDialog(
            title=ft.Text("Nova Transação"),
            content=ft.Column(
                [
                    type_dropdown,
                    desc_input,
                    amount_input,
                    cat_dropdown,
                ],
                height=280,
                spacing=10,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=fechar_dialog),
                ft.FilledButton(
                    "Salvar",
                    on_click=save_new_transaction,
                    style=ft.ButtonStyle(bgcolor=COLORS["primary"]),
                ),
            ],
        )
        page.show_dialog(dialog)

    return ft.View(
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        padding=ft.Padding.only(bottom=10),
                        content=ft.Text(
                            "Transações",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=COLORS["primary"],
                        ),
                    ),
                    transactions_column,
                ],
            )
        ],
        floating_action_button=ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            bgcolor=COLORS["primary"],
            on_click=show_add_modal,
        ),
        route="/transactions",
        bgcolor=COLORS["background"],
        padding=20,
        scroll=ft.ScrollMode.AUTO,
    )
