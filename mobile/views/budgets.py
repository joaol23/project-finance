"""
budgets.py — Tela de Orçamentos completa para o app mobile.

Exibe:
- Lista de categorias de despesa com campo de valor planejado
- Edição inline de cada orçamento com botão de salvar individual
- Seção separada para categorias de cartão de crédito
"""

import flet as ft
from decimal import Decimal
from mobile.styles import COLORS
from database.connection import SessionLocal
from database.models import Budget, Category, CategoryType


def get_budgets_view(page: ft.Page):
    expense_categories = []
    cc_categories = []
    budgets_map = {}

    try:
        session = SessionLocal()
        expense_categories = (
            session.query(Category)
            .filter(Category.category_type == CategoryType.EXPENSE)
            .all()
        )
        cc_categories = (
            session.query(Category)
            .filter(Category.category_type == CategoryType.CREDIT_CARD)
            .all()
        )
        budgets_map = {b.category_id: float(b.planned_amount) for b in session.query(Budget).all()}
        session.close()
    except Exception as ex:
        print(f"[budgets] erro ao carregar: {ex}")

    budget_fields: dict[int, ft.TextField] = {}

    def make_category_row(cat: Category):
        current_val = budgets_map.get(cat.id, 0.0)
        tf = ft.TextField(
            value=f"{current_val:.2f}",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor=COLORS["surface"],
            color=COLORS["text"],
            border_color=COLORS["primary"],
            text_size=14,
            width=130,
            height=42,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
        )
        budget_fields[cat.id] = tf

        dot = ft.Container(
            width=12,
            height=12,
            bgcolor=cat.color or COLORS["primary"],
            border_radius=6,
        )

        def save_one(e, cat_id=cat.id, field=tf):
            try:
                val = Decimal(field.value.replace(",", "."))
                s = SessionLocal()
                existing = s.query(Budget).filter(Budget.category_id == cat_id).first()
                if existing:
                    existing.planned_amount = val
                else:
                    s.add(Budget(category_id=cat_id, planned_amount=val))
                s.commit()
                s.close()
                page.show_dialog(
                    ft.AlertDialog(
                        title=ft.Text("✅ Salvo!", color=COLORS["success"]),
                        content=ft.Text("Orçamento atualizado com sucesso."),
                        actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
                    )
                )
            except Exception as err:
                page.show_dialog(
                    ft.AlertDialog(
                        title=ft.Text("Erro", color=COLORS["danger"]),
                        content=ft.Text(str(err)),
                        actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
                    )
                )

        return ft.Container(
            bgcolor=COLORS["surface"],
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            dot,
                            ft.Text(cat.name, size=14, color=COLORS["text"]),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            tf,
                            ft.IconButton(
                                icon=ft.Icons.SAVE,
                                icon_color=COLORS["primary"],
                                tooltip="Salvar",
                                on_click=save_one,
                            ),
                        ],
                    ),
                ],
            ),
        )

    expense_rows = [make_category_row(c) for c in expense_categories]
    cc_rows = [make_category_row(c) for c in cc_categories]

    def save_all(e):
        try:
            s = SessionLocal()
            for cat_id, tf in budget_fields.items():
                val = Decimal(tf.value.replace(",", "."))
                existing = s.query(Budget).filter(Budget.category_id == cat_id).first()
                if existing:
                    existing.planned_amount = val
                elif val > 0:
                    s.add(Budget(category_id=cat_id, planned_amount=val))
            s.commit()
            s.close()
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("✅ Todos Salvos!", color=COLORS["success"]),
                    content=ft.Text("Todos os orçamentos foram atualizados."),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
                )
            )
        except Exception as err:
            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Erro", color=COLORS["danger"]),
                    content=ft.Text(str(err)),
                    actions=[ft.TextButton("OK", on_click=lambda e: page.pop_dialog())],
                )
            )

    return ft.View(
        controls=[
            ft.Column(
                spacing=12,
                controls=[
                    ft.Text(
                        "Orçamentos",
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["primary"],
                    ),
                    ft.Text(
                        "Defina limites de gastos por categoria",
                        size=13,
                        color=COLORS["text_secondary"],
                    ),
                    ft.Divider(color=COLORS["surface"]),
                    ft.Text(
                        "Despesas",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    *expense_rows,
                    ft.Divider(color=COLORS["surface"]),
                    ft.Text(
                        "Cartão de Crédito",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    *cc_rows,
                    ft.Container(height=10),
                    ft.FilledButton(
                        "💾 Salvar Todos",
                        on_click=save_all,
                        style=ft.ButtonStyle(
                            bgcolor=COLORS["primary"],
                            color=COLORS["text"],
                        ),
                        width=float("inf"),
                    ),
                ],
            )
        ],
        route="/budgets",
        bgcolor=COLORS["background"],
        padding=20,
        scroll=ft.ScrollMode.AUTO,
    )
