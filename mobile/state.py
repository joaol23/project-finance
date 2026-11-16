# mobile/state.py
# Estado global compartilhado entre as telas do app mobile.

from datetime import date
from mobile.utils import month_period_bounds

class AppState:
    """Estado global do app mobile: mês/ano selecionado e caminho do banco."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            today = date.today()
            cls._instance.selected_month = today.month
            cls._instance.selected_year = today.year
            cls._instance.db_path = None
        return cls._instance

    def set_period(self, month: int, year: int):
        self.selected_month = month
        self.selected_year = year

    def set_db_path(self, path: str):
        self.db_path = path
        
    def get_period_bounds(self):
        return month_period_bounds(self.selected_year, self.selected_month)


# Instância singleton
app_state = AppState()

MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]
