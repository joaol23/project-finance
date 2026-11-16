import flet as ft
from mobile.views.investments import get_investments_view
async def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = '#121212'
    view = get_investments_view(page)
    page.views.append(view)
    page.update()
if __name__ == '__main__':
    ft.run(main)
