"""
diagnose_filepicker.py - Testa onde o FilePicker pode ser registrado no Flet 1.0.0
"""
import flet as ft

results = {}

def main(page: ft.Page):
    picker = ft.FilePicker(on_result=lambda e: None)

    # Teste 1: View.services
    try:
        view = ft.View(
            controls=[ft.Text("test")],
            route="/test",
            services=[picker]
        )
        page.views.append(view)
        page.update()
        results["View.services"] = "OK"
    except Exception as e:
        results["View.services"] = f"ERRO: {e}"

    print(f"View.services: {results.get('View.services')}")
    page.window.destroy()

ft.run(main)
