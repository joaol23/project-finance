"""
Script de diagnóstico para a versão instalada do Flet.
Verifica quais controles, métodos e APIs estão disponíveis.
"""
import flet as ft
import inspect
import sys

print(f"Python: {sys.version}")
print(f"Flet version: {ft.__version__}")
print()

# Botões disponíveis
button_types = [k for k in dir(ft) if 'Button' in k and not k.startswith('_')]
print(f"Botões disponíveis: {button_types}")
print()

# Métodos de Page relacionados a navegação
page_nav = [k for k in dir(ft.Page) if 'route' in k.lower() or 'nav' in k.lower() or 'go' in k.lower()]
print(f"Métodos de navegação em Page: {page_nav}")
print()

# Verificar assinatura de FilledButton
if hasattr(ft, 'FilledButton'):
    sig = inspect.signature(ft.FilledButton.__init__)
    params = list(sig.parameters.keys())
    print(f"FilledButton params: {params[:15]}")
    print()

# Verificar assinatura de ElevatedButton
if hasattr(ft, 'ElevatedButton'):
    sig = inspect.signature(ft.ElevatedButton.__init__)
    params = list(sig.parameters.keys())
    print(f"ElevatedButton params: {params[:15]}")
else:
    print("ElevatedButton: NÃO EXISTE nesta versão")
print()

# Verificar assinatura de View.__init__
sig = inspect.signature(ft.View.__init__)
params = list(sig.parameters.keys())
print(f"View.__init__ params (primeiros 5): {params[:5]}")
print()

# Verificar se page.navigate existe
print(f"Page.navigate existe: {hasattr(ft.Page, 'navigate')}")
print(f"Page.push_route existe: {hasattr(ft.Page, 'push_route')}")
print(f"Page.go existe: {hasattr(ft.Page, 'go')}")
print()

# Verificar page.dialog
print(f"Page.dialog existe: {hasattr(ft.Page, 'dialog')}")
print(f"Page.overlay existe: {hasattr(ft.Page, 'overlay')}")
print()

# Verificar FilePicker
if hasattr(ft, 'FilePicker'):
    sig = inspect.signature(ft.FilePicker.__init__)
    print(f"FilePicker.__init__ params: {list(sig.parameters.keys())[:10]}")
    # Verificar método pick_files
    if hasattr(ft.FilePicker, 'pick_files'):
        sig2 = inspect.signature(ft.FilePicker.pick_files)
        print(f"FilePicker.pick_files params: {list(sig2.parameters.keys())}")
        print(f"FilePicker.pick_files is coroutine: {inspect.iscoroutinefunction(ft.FilePicker.pick_files)}")
print()

# Verificar AlertDialog
if hasattr(ft, 'AlertDialog'):
    sig = inspect.signature(ft.AlertDialog.__init__)
    params = list(sig.parameters.keys())
    print(f"AlertDialog params: {params[:15]}")
print()

# Verificar show_dialog
print(f"Page.show_dialog existe: {hasattr(ft.Page, 'show_dialog')}")
if hasattr(ft.Page, 'show_dialog'):
    print(f"show_dialog is coroutine: {inspect.iscoroutinefunction(ft.Page.show_dialog)}")
print()

# Verificar pop_dialog
print(f"Page.pop_dialog existe: {hasattr(ft.Page, 'pop_dialog')}")
print()

print("Diagnóstico concluído.")
