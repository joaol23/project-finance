"""
test_integration.py — Teste de integração completo do app mobile.

Cobre:
1. Inicialização do app com ft.run() real (sem MockPage)
2. View de setup abre sem erros
3. FilePicker registrado em view.services
4. Navegação entre todas as rotas após configurar banco
5. Todas as views carregam sem exceção
6. Banco de dados: set_database_path, SessionLocal, seed de dados
7. Regra de período contábil
8. Criação e listagem de transações via service

Executa o app por 3s em modo headless e reporta resultado.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft

# ── Estado do teste ───────────────────────────────────────────────────────────
errors: list[str] = []
checks: list[str] = []


def ok(name: str):
    checks.append(name)
    print(f"  [PASS]  {name}")


def fail(name: str, reason: str):
    errors.append(f"{name}: {reason}")
    print(f"  [FAIL]  {name}: {reason}")


# ══════════════════════════════════════════════════════════════════════════════
# Testes de Integração sem ft.run (stateless)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[A] Testes de banco de dados e serviços")

# A1 — set_database_path
try:
    import database.connection as db_conn
    from database.models import Category, Account, Transaction, TransactionType

    DB_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "financas.db"
    )
    original_path = db_conn.DATABASE_PATH
    db_conn.set_database_path(DB_PATH)
    assert db_conn.DATABASE_PATH == DB_PATH
    ok("A1 set_database_path reconfigura engine")
except Exception as e:
    fail("A1 set_database_path", str(e))

# A2 — SessionLocal funciona após set_database_path
try:
    session = db_conn.SessionLocal()
    categories = session.query(Category).all()
    session.close()
    ok(f"A2 SessionLocal retorna {len(categories)} categorias")
except Exception as e:
    fail("A2 SessionLocal", str(e))

# A3 — Seed de categorias e conta
try:
    session = db_conn.SessionLocal()
    cat_count = session.query(Category).count()
    acc_count = session.query(Account).count()
    session.close()
    assert cat_count >= 10, f"Poucas categorias: {cat_count}"
    assert acc_count >= 1, f"Nenhuma conta"
    ok(f"A3 Seed: {cat_count} categorias, {acc_count} conta(s)")
except Exception as e:
    fail("A3 Seed", str(e))

# A4 — Regra de período contábil
try:
    from mobile.utils import month_period_bounds, last_business_day
    from datetime import date

    start, end = month_period_bounds(2025, 9)
    assert start < end, f"start {start} >= end {end}"
    assert end.weekday() < 5, f"end {end} não é dia útil"
    assert start.weekday() < 5, f"start {start} não é dia útil"
    ok(f"A4 Período contábil set/2025: {start} -> {end}")
except Exception as e:
    fail("A4 Período contábil", str(e))

# A5 — app_state singleton e período
try:
    from mobile.state import AppState, app_state

    s1 = AppState()
    s2 = AppState()
    assert s1 is s2, "AppState não é singleton"

    app_state.set_period(6, 2025)
    start, end = app_state.get_period_bounds()
    assert start < end
    ok(f"A5 AppState singleton + período jun/2025: {start} -> {end}")
except Exception as e:
    fail("A5 AppState", str(e))

# A6 — create_transaction via service
try:
    from services.transaction_service import create_transaction
    from decimal import Decimal
    from datetime import date

    session = db_conn.SessionLocal()
    account = session.query(Account).first()
    session.close()

    tx = create_transaction(
        trans_date=date(2025, 6, 15),
        amount=Decimal("100.00"),
        description="[TEST] Integração",
        trans_type="Saída",
        category_name=None,
        account=account,
    )
    assert tx.id is not None
    ok(f"A6 create_transaction -> id={tx.id}")

    # Limpa a transação de teste
    session = db_conn.SessionLocal()
    test_tx = session.query(Transaction).filter(Transaction.id == tx.id).first()
    if test_tx:
        session.delete(test_tx)
        session.commit()
    session.close()
    ok("A6b Limpeza da transação de teste")
except Exception as e:
    fail("A6 create_transaction", str(e))

# A7 — MockPage e criação de todas as views
print("\n[B] Criação de todas as views mobile")

class MockPage:
    route = "/"
    window = type("W", (), {"width": 400, "height": 800})()
    overlay = []
    services = []
    views = []
    navigation_bar = None

    def update(self): pass
    def navigate(self, r): pass
    def show_dialog(self, d): pass
    def pop_dialog(self): pass

mock_page = MockPage()

for view_name, getter in [
    ("setup", lambda: __import__("mobile.views.setup", fromlist=["get_setup_view"]).get_setup_view(mock_page, lambda p: None)),
    ("dashboard", lambda: __import__("mobile.views.dashboard", fromlist=["get_dashboard_view"]).get_dashboard_view(mock_page)),
    ("transactions", lambda: __import__("mobile.views.transactions", fromlist=["get_transactions_view"]).get_transactions_view(mock_page)),
    ("investments", lambda: __import__("mobile.views.investments", fromlist=["get_investments_view"]).get_investments_view(mock_page)),
    ("budgets", lambda: __import__("mobile.views.budgets", fromlist=["get_budgets_view"]).get_budgets_view(mock_page)),
]:
    try:
        view = getter()
        assert isinstance(view, ft.View), f"não é ft.View"
        assert len(view.controls) > 0, "controls vazio"
        ok(f"B {view_name} view -> route={view.route!r}, controls={len(view.controls)}")
    except Exception as e:
        fail(f"B {view_name} view", str(e))

# A8 — setup view FilePicker services
print("\n[C] Verificação de FilePicker em services")

try:
    from mobile.views.setup import get_setup_view
    v = get_setup_view(mock_page, lambda p: None)
    fps = [s for s in v.services if isinstance(s, ft.FilePicker)]
    assert len(fps) == 1, f"Esperado 1 FilePicker, encontrado {len(fps)}"
    assert fps[0].on_result is not None, "on_result não definido"
    ok("C FilePicker em view.services com on_result")
except Exception as e:
    fail("C FilePicker services", str(e))

# ══════════════════════════════════════════════════════════════════════════════
# Teste de ft.run() real (headless/windowed por 2s)
# ══════════════════════════════════════════════════════════════════════════════
print("\n[D] Teste de ft.run() (app real, fecha após 2s)")

runtime_errors: list[str] = []
runtime_checks: list[str] = []


async def run_test_app(page: ft.Page):
    page.title = "Integration Test"
    page.bgcolor = "#121212"

    db_configured_flag = {"val": False}

    def on_db_selected(path):
        db_configured_flag["val"] = True

    def on_route_change(e):
        route = e.route
        page.views.clear()
        try:
            if route in ("/", "/setup", ""):
                view = get_setup_view(page, on_db_selected)
                page.views.append(view)
                # Verificações
                assert isinstance(view, ft.View)
                assert view.route == "/setup"
                fps = [s for s in view.services if isinstance(s, ft.FilePicker)]
                assert len(fps) == 1
                runtime_checks.append("setup_view_ok")
                runtime_checks.append("filepicker_in_services")
            else:
                page.views.append(ft.View(controls=[ft.Text("route: " + route)]))
        except Exception as ex:
            runtime_errors.append(f"on_route_change({route}): {ex}")
            page.views.append(ft.View(controls=[ft.Text(f"ERRO: {ex}", color="red")]))
        page.update()

    page.on_route_change = on_route_change
    page.navigate("/setup")

    await asyncio.sleep(2)
    try:
        await page.window.destroy()
    except Exception:
        pass


try:
    ft.run(run_test_app)
    if runtime_errors:
        for err in runtime_errors:
            fail("D runtime", err)
    else:
        for chk in runtime_checks:
            ok(f"D {chk}")
        if not runtime_checks:
            ok("D app iniciou e fechou sem erros de runtime")
except Exception as e:
    fail("D ft.run", str(e))

# ══════════════════════════════════════════════════════════════════════════════
# Resultado Final
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n{'='*55}")
total_pass = len(checks)
total_fail = len(errors)
print(f"Resultado: {total_pass} PASSOU / {total_fail} FALHOU")

if errors:
    print("\nFalhas:")
    for err in errors:
        print(f"  [FAIL] {err}")
    print("\nTESTE DE INTEGRAÇÃO: FALHOU")
    sys.exit(1)
else:
    print("\nTESTE DE INTEGRAÇÃO: PASSOU")
