# services/transaction_service.py
"""Transaction service layer.
Provides CRUD operations with proper session handling, validation, and logging.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from database import get_session
from database.models import (
    Transaction,
    TransactionType,
    Category,
    Account,
)

logger = logging.getLogger(__name__)


def _apply_filters(query, filters: Dict[str, Any]):
    """Apply filters to a SQLAlchemy query based on the same logic used in the view.
    Supported keys: month, year, type, category, no_category, description.
    """
    month = filters.get("month")
    year = filters.get("year")
    if month:
        start = date(year or date.today().year, month, 1)
        end = date((year or date.today().year) + (1 if month == 12 else 0), (month % 12) + 1, 1)
        query = query.filter(Transaction.date >= start, Transaction.date < end)
    elif year:
        query = query.filter(
            Transaction.date >= date(year, 1, 1),
            Transaction.date < date(year + 1, 1, 1),
        )
    ttype = filters.get("type")
    if ttype == "Entrada":
        query = query.filter(Transaction.transaction_type == TransactionType.INCOME)
    elif ttype == "Saída":
        query = query.filter(Transaction.transaction_type == TransactionType.EXPENSE)
    if filters.get("no_category"):
        query = query.filter(Transaction.category_id.is_(None))
    elif filters.get("category") and filters["category"] != "Todas":
        cat_name = filters["category"]
        cat = get_session().query(Category).filter(Category.name == cat_name).first()
        if cat:
            query = query.filter(Transaction.category_id == cat.id)
    desc = filters.get("description")
    if desc:
        query = query.filter(Transaction.description.ilike(f"%{desc}%"))
    return query


def list_transactions(filters: Dict[str, Any]) -> List[Transaction]:
    """Return transactions respecting the provided filters."""
    session = get_session()
    try:
        query = session.query(Transaction)
        query = _apply_filters(query, filters)
        return query.order_by(Transaction.date.desc()).all()
    finally:
        session.close()


def create_transaction(
    *,
    trans_date: date,
    amount: Decimal,
    description: str,
    trans_type: str,
    category_name: Optional[str],
    account: Account,
) -> Transaction:
    """Create a new transaction with validation and proper rollback.
    Raises ValueError for invalid input.
    """
    if amount <= 0:
        raise ValueError("O valor da transação deve ser maior que zero.")
    if not description:
        raise ValueError("A descrição da transação é obrigatória.")
    session = get_session()
    try:
        category_id = None
        if category_name:
            cat = session.query(Category).filter(Category.name == category_name).first()
            if not cat:
                raise ValueError(f"Categoria '{category_name}' não encontrada.")
            category_id = cat.id
        transaction = Transaction(
            date=trans_date,
            amount=Decimal(str(amount)),
            description=description,
            transaction_type=TransactionType.INCOME if trans_type == "Entrada" else TransactionType.EXPENSE,
            category_id=category_id,
            account_id=account.id,
        )
        session.add(transaction)
        session.commit()
        logger.info("Transação criada: %s", transaction.id)
        return transaction
    except Exception as exc:
        session.rollback()
        logger.exception("Erro ao criar transação")
        raise exc
    finally:
        session.close()


def update_transaction(
    *,
    trans_id: int,
    trans_date: date,
    amount: Decimal,
    description: str,
    trans_type: str,
    category_name: Optional[str],
) -> Transaction:
    """Update an existing transaction, handling rollback on error."""
    if amount <= 0:
        raise ValueError("O valor da transação deve ser maior que zero.")
    session = get_session()
    try:
        tx = session.query(Transaction).filter(Transaction.id == trans_id).first()
        if not tx:
            raise ValueError(f"Transação id={trans_id} não encontrada.")
        tx.date = trans_date
        tx.amount = Decimal(str(amount))
        tx.description = description
        tx.transaction_type = TransactionType.INCOME if trans_type == "Entrada" else TransactionType.EXPENSE
        if category_name:
            cat = session.query(Category).filter(Category.name == category_name).first()
            tx.category_id = cat.id if cat else None
        else:
            tx.category_id = None
        session.commit()
        logger.info("Transação atualizada: %s", trans_id)
        return tx
    except Exception as exc:
        session.rollback()
        logger.exception("Erro ao atualizar transação %s", trans_id)
        raise exc
    finally:
        session.close()


def bulk_update_category(tx_ids: List[int], new_category_name: Optional[str]) -> int:
    """Bulk update the category of multiple transactions.
    Returns the number of rows affected.
    """
    session = get_session()
    try:
        new_category_id = None
        if new_category_name:
            cat = session.query(Category).filter(Category.name == new_category_name).first()
            new_category_id = cat.id if cat else None
        updated = (
            session.query(Transaction)
            .filter(Transaction.id.in_(tx_ids))
            .update({Transaction.category_id: new_category_id}, synchronize_session=False)
        )
        session.commit()
        logger.info("Bulk category update: %d rows", updated)
        return updated
    except Exception as exc:
        session.rollback()
        logger.exception("Erro no bulk update de categoria")
        raise exc
    finally:
        session.close()
