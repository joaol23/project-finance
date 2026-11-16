"""
test_mobile_views.py — Testes de validação estática para o app mobile (Flet 1.0.0).

Cobre:
  [1] Importações de todos os módulos
  [2] APIs do Flet 1.0.0 (presença/ausência de atributos)
  [3] Criação de Views sem banco de dados real (investments/budgets/setup)
  [4] Estrutura das views (controles, rota, services)
  [5] Configuração de banco via set_database_path
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import traceback
import flet as ft

PASS = []
FAIL = []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  PASS  {name}")
    except Exception as e:
        FAIL.append(name)
        print(f"  FAIL  {name}: {e}")
        traceback.print_exc()


def assert_true(val, msg=""):
    if not val:
        raise AssertionError(msg or "Assertion failed")


# ── Mock Page ─────────────────────────────────────────────────────────────────
class MockPage:
    route = "/"
    window = type("W", (), {"width": 400, "height": 800})()
    overlay = []
    services = []
    views = []

    def update(self): pass
    def navigate(self, r): pass
    def show_dialog(self, d): pass
    def pop_dialog(self): pass


# ── [1] Importações ───────────────────────────────────────────────────────────
print("\n[1] Importações")

check("import mobile.styles",
      lambda: __import__("mobile.styles", fromlist=["COLORS"]))
check("import mobile.state",
      lambda: __import__("mobile.state", fromlist=["app_state"]))
check("import mobile.utils",
      lambda: __import__("mobile.utils", fromlist=["last_business_day"]))
check("import views.setup",
      lambda: __import__("mobile.views.setup", fromlist=["get_setup_view"]))
check("import views.dashboard",
      lambda: __import__("mobile.views.dashboard", fromlist=["get_dashboard_view"]))
check("import views.transactions",
      lambda: __import__("mobile.views.transactions", fromlist=["get_transactions_view"]))
check("import views.investments",
      lambda: __import__("mobile.views.investments", fromlist=["get_investments_view"]))
check("import views.budgets",
      lambda: __import__("mobile.views.budgets", fromlist=["get_budgets_view"]))
check("import database.connection",
      lambda: __import__("database.connection", fromlist=["set_database_path"]))

# ── [2] APIs Flet 1.0.0 ───────────────────────────────────────────────────────
print("\n[2] APIs Flet 1.0.0")

check("ft.FilledButton existe",
      lambda: assert_true(hasattr(ft, "FilledButton"), "ft.FilledButton ausente"))
check("ft.ElevatedButton NÃO existe",
      lambda: assert_true(not hasattr(ft, "ElevatedButton"), "ft.ElevatedButton não deveria existir"))
check("ft.FilePicker existe",
      lambda: assert_true(hasattr(ft, "FilePicker"), "ft.FilePicker ausente"))
check("ft.run existe",
      lambda: assert_true(hasattr(ft, "run"), "ft.run ausente"))
check("Page.navigate existe",
      lambda: assert_true(hasattr(ft.Page, "navigate"), "Page.navigate ausente"))
check("Page.show_dialog existe",
      lambda: assert_true(hasattr(ft.Page, "show_dialog"), "Page.show_dialog ausente"))
check("Page.pop_dialog existe",
      lambda: assert_true(hasattr(ft.Page, "pop_dialog"), "Page.pop_dialog ausente"))
check("Page.go NÃO existe",
      lambda: assert_true(not hasattr(ft.Page, "go"), "Page.go não deveria existir"))
check("Page.overlay existe",
      lambda: assert_true(hasattr(ft.Page, "overlay"), "Page.overlay ausente"))
check("View.services existe (instância)",
      lambda: assert_true(
          hasattr(ft.View(controls=[]), "services"),
          "ft.View instance não tem atributo services"
      ))
check("FilePicker é Service",
      lambda: assert_true(
          issubclass(ft.FilePicker, __import__("flet.controls.services.service", fromlist=["Service"]).Service),
          "FilePicker não herda de Service"
      ))

# ── [3] Criação de Views sem banco ────────────────────────────────────────────
print("\n[3] Criação de Views (sem banco de dados)")

from mobile.views.investments import get_investments_view
from mobile.views.budgets import get_budgets_view
from mobile.views.setup import get_setup_view

mock_page = MockPage()


def check_view(name, view):
    assert isinstance(view, ft.View), f"{name}: não é ft.View"
    assert len(view.controls) > 0, f"{name}: controls vazio"
    print(f"    route={view.route!r}, controls={len(view.controls)}")


check("get_investments_view() sem erro",
      lambda: check_view("investments", get_investments_view(mock_page)))
check("get_budgets_view() sem erro",
      lambda: check_view("budgets", get_budgets_view(mock_page)))
check("get_setup_view() sem erro",
      lambda: check_view("setup", get_setup_view(mock_page, lambda p: None)))

# ── [4] Estrutura das views ───────────────────────────────────────────────────
print("\n[4] Estrutura das views")

setup_view = get_setup_view(mock_page, lambda p: None)

check("setup route == /setup",
      lambda: assert_true(setup_view.route == "/setup", f"route={setup_view.route}"))

check("setup tem FilePicker em services",
      lambda: assert_true(
          any(isinstance(s, ft.FilePicker) for s in setup_view.services),
          "Nenhum FilePicker em setup_view.services"
      ))

check("setup FilePicker tem on_result",
      lambda: assert_true(
          setup_view.services[0].on_result is not None,
          "FilePicker on_result não definido"
      ))

inv_view = get_investments_view(mock_page)
check("investments route == /investments",
      lambda: assert_true(inv_view.route == "/investments", f"route={inv_view.route}"))

budget_view = get_budgets_view(mock_page)
check("budgets route == /budgets",
      lambda: assert_true(budget_view.route == "/budgets", f"route={budget_view.route}"))

# ── [5] set_database_path ─────────────────────────────────────────────────────
print("\n[5] set_database_path (banco padrão do projeto)")

import database.connection as db_conn

def test_set_database_path():
    import tempfile
    # Usa o banco real do projeto para testar
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "financas.db"
    )
    original_path = db_conn.DATABASE_PATH
    try:
        db_conn.set_database_path(db_path)
        assert db_conn.DATABASE_PATH == db_path, "DATABASE_PATH não atualizado"
        assert db_conn.SessionLocal is not None, "SessionLocal não recriado"
        # Testa que a sessão funciona
        session = db_conn.SessionLocal()
        session.close()
    finally:
        # Restaura
        db_conn.set_database_path(original_path)

check("set_database_path funciona corretamente", test_set_database_path)

# ── Resumo ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Resultado: {len(PASS)} PASSOU / {len(FAIL)} FALHOU")
if FAIL:
    print(f"Falhas: {FAIL}")
    sys.exit(1)
else:
    print("Todos os testes passaram!")
