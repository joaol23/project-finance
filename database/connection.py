import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .models import Base, Category, CategoryType, Account

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "financas.db")

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(engine)
    _seed_initial_data()


def get_session() -> Session:
    return SessionLocal()


def _seed_initial_data():
    session = SessionLocal()
    try:
        if session.query(Category).count() == 0:
            categories = [
                Category(name="Salário", category_type=CategoryType.INCOME, color="#22c55e"),
                Category(name="Freelance", category_type=CategoryType.INCOME, color="#10b981"),
                Category(name="Dividendos", category_type=CategoryType.INCOME, color="#06b6d4", is_investment=True),
                Category(name="Ações vendidas", category_type=CategoryType.INCOME, color="#7c3aed", is_investment=True),
                Category(name="Outros (Entrada)", category_type=CategoryType.INCOME, color="#14b8a6"),
                Category(name="Alimentação", category_type=CategoryType.EXPENSE, color="#ef4444"),
                Category(name="Transporte", category_type=CategoryType.EXPENSE, color="#f97316"),
                Category(name="Moradia", category_type=CategoryType.EXPENSE, color="#eab308"),
                Category(name="Saúde", category_type=CategoryType.EXPENSE, color="#84cc16"),
                Category(name="Educação", category_type=CategoryType.EXPENSE, color="#06b6d4"),
                Category(name="Lazer", category_type=CategoryType.EXPENSE, color="#8b5cf6"),
                Category(name="Ações", category_type=CategoryType.EXPENSE, color="#7c3aed", is_investment=True),
                Category(name="FIIs", category_type=CategoryType.EXPENSE, color="#6366f1", is_investment=True),
                Category(name="Criptomoedas", category_type=CategoryType.EXPENSE, color="#f59e0b", is_investment=True),
                Category(name="Outros (Saída)", category_type=CategoryType.EXPENSE, color="#ec4899"),
                Category(name="Alimentação (CC)", category_type=CategoryType.CREDIT_CARD, color="#f87171"),
                Category(name="Compras (CC)", category_type=CategoryType.CREDIT_CARD, color="#fb923c"),
                Category(name="Assinaturas (CC)", category_type=CategoryType.CREDIT_CARD, color="#a78bfa"),
                Category(name="Outros (CC)", category_type=CategoryType.CREDIT_CARD, color="#f472b6"),
            ]
            session.add_all(categories)
            session.commit()

        if session.query(Account).count() == 0:
            account = Account(name="Conta Principal", initial_balance=0)
            session.add(account)
            session.commit()
    finally:
        session.close()
