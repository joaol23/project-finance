"""
main.py — Ponto de entrada do aplicativo mobile.

Flet 1.0.0:
- main() é async (necessário para await pick_files e outras coroutines)
- ft.run(main) inicia o app
- FilePicker é registrado como service da View (não de page), via ft.View(..., services=[picker])
- page.navigate(route) nativo
- page.window.width / page.window.height
"""

import flet as ft
import sys
import os
import types

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mobile.styles import COLORS
from mobile.views.setup import get_setup_view
from mobile.views.dashboard import get_dashboard_view
from mobile.views.transactions import get_transactions_view
from mobile.views.investments import get_investments_view
from mobile.views.budgets import get_budgets_view


async def main(page: ft.Page):
    page.title = "Organizador Financeiro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = COLORS["background"]
    page.window.width = 400
    page.window.height = 800

    db_configured = False

    nav_bar = ft.NavigationBar(
        bgcolor=COLORS["surface"],
        selected_index=0,
        visible=False,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.HOME, selected_icon=ft.Icons.HOME, label="Dashboard"),
            ft.NavigationBarDestination(icon=ft.Icons.LIST, selected_icon=ft.Icons.LIST, label="Transações"),
            ft.NavigationBarDestination(icon=ft.Icons.PIE_CHART, selected_icon=ft.Icons.PIE_CHART, label="Invest."),
            ft.NavigationBarDestination(icon=ft.Icons.ACCOUNT_BALANCE_WALLET, selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET, label="Orçamentos"),
        ]
    )
    page.navigation_bar = nav_bar

    ROUTE_ORDER = ["/dashboard", "/transactions", "/investments", "/budgets"]

    def on_nav_change(e):
        if not db_configured:
            return
        idx = e.control.selected_index
        if 0 <= idx < len(ROUTE_ORDER):
            page.navigate(ROUTE_ORDER[idx])

    nav_bar.on_change = on_nav_change

    def on_db_selected(path):
        nonlocal db_configured
        db_configured = True
        nav_bar.visible = True
        page.update()
        page.navigate("/dashboard")

    def on_route_change(e):
        route = e.route if hasattr(e, "route") else str(e)
        page.views.clear()

        # Sync nav bar selected index
        if route in ROUTE_ORDER:
            nav_bar.selected_index = ROUTE_ORDER.index(route)

        if route in ("/", "/setup", ""):
            nav_bar.visible = False
            page.views.append(get_setup_view(page, on_db_selected))
        elif route == "/dashboard" and db_configured:
            nav_bar.visible = True
            view = get_dashboard_view(page)
            view.navigation_bar = nav_bar
            page.views.append(view)
        elif route == "/transactions" and db_configured:
            nav_bar.visible = True
            view = get_transactions_view(page)
            view.navigation_bar = nav_bar
            page.views.append(view)
        elif route == "/investments" and db_configured:
            nav_bar.visible = True
            view = get_investments_view(page)
            view.navigation_bar = nav_bar
            page.views.append(view)
        elif route == "/budgets" and db_configured:
            nav_bar.visible = True
            view = get_budgets_view(page)
            view.navigation_bar = nav_bar
            page.views.append(view)
        else:
            # Banco ainda não configurado ou rota desconhecida → volta p/ setup
            nav_bar.visible = False
            page.views.append(get_setup_view(page, on_db_selected))

        page.update()

    page.on_route_change = on_route_change
    # Garante renderização síncrona da view inicial sem instanciar RouteChangeEvent incompatível
    on_route_change(types.SimpleNamespace(route=page.route or "/setup"))


if __name__ == "__main__":
    ft.run(main)
