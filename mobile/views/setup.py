"""
setup.py — Tela inicial de seleção do banco de dados.

Flet 1.0.0:
- ft.FilledButton (ElevatedButton não existe)
- FilePicker é Service → registrado em ft.View(..., services=[picker])
- ft.View: vertical_alignment e horizontal_alignment para centralizar layout
  sem usar expand=True em sub-containers (evita erros de layout no Flutter engine)
"""

import flet as ft
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from mobile.styles import COLORS
import database.connection as db_conn


def get_setup_view(page: ft.Page, on_db_selected):
    status_text = ft.Text(
        "Nenhum banco de dados selecionado.",
        color=COLORS["text_secondary"],
        text_align=ft.TextAlign.CENTER,
    )

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            selected_path = e.files[0].path
            if selected_path:
                try:
                    db_conn.set_database_path(selected_path)
                    status_text.value = f"✓ {os.path.basename(selected_path)}"
                    status_text.color = COLORS["success"]
                    page.update()
                    on_db_selected(selected_path)
                except Exception as ex:
                    status_text.value = f"Erro ao abrir banco: {ex}"
                    status_text.color = COLORS["danger"]
                    page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)

    async def open_picker(e):
        await file_picker.pick_files(
            dialog_title="Selecione o financas.db",
            allowed_extensions=["db", "sqlite"],
        )

    action_controls = []
    if os.path.exists(db_conn.DATABASE_PATH):
        db_name = os.path.basename(db_conn.DATABASE_PATH)
        action_controls.extend([
            ft.FilledButton(
                f"Usar banco detectado ({db_name})",
                icon=ft.Icons.CHECK_CIRCLE,
                on_click=lambda _: on_db_selected(db_conn.DATABASE_PATH),
                style=ft.ButtonStyle(
                    bgcolor=COLORS["primary"],
                    color=COLORS["text"],
                ),
            ),
            ft.Container(height=10),
            ft.OutlinedButton(
                "Escolher outro arquivo .db",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=open_picker,
                style=ft.ButtonStyle(
                    color=COLORS["text"],
                ),
            ),
        ])
    else:
        action_controls.append(
            ft.FilledButton(
                "Selecionar Banco de Dados",
                icon=ft.Icons.FOLDER_OPEN,
                on_click=open_picker,
                style=ft.ButtonStyle(
                    bgcolor=COLORS["primary"],
                    color=COLORS["text"],
                ),
            )
        )

    return ft.View(
        controls=[
            ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.CLOUD_SYNC, size=80, color=COLORS["primary"]),
                    ft.Text(
                        "Organizador Financeiro",
                        size=26,
                        weight=ft.FontWeight.BOLD,
                        color=COLORS["text"],
                    ),
                    ft.Text(
                        "Selecione o arquivo financas.db do seu\nGoogle Drive para começar.",
                        text_align=ft.TextAlign.CENTER,
                        color=COLORS["text_secondary"],
                        size=15,
                    ),
                    ft.Container(height=30),
                    status_text,
                    ft.Container(height=10),
                    *action_controls,
                ],
            )
        ],
        route="/setup",
        bgcolor=COLORS["background"],
        padding=30,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        services=[file_picker],
    )
