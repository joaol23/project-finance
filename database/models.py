from datetime import date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import String, Integer, Date, Numeric, ForeignKey, Text, Enum as SQLEnum, create_engine, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


class TransactionType(enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"


class CategoryType(enum.Enum):
    EXPENSE = "expense"
    INCOME = "income"
    CREDIT_CARD = "credit_card"


class InvestmentType(enum.Enum):
    STOCK = "stock"
    FII = "fii"
    CRYPTO = "crypto"
    OTHER = "other"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class MonthlyOpeningBalance(Base):
    __tablename__ = "monthly_opening_balances"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..12
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_monthly_opening_balance_year_month"),
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    category_type: Mapped[CategoryType] = mapped_column(SQLEnum(CategoryType))
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    is_investment: Mapped[bool] = mapped_column(default=False)

    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")
    budgets: Mapped[List["Budget"]] = relationship(back_populates="category")
    credit_card_transactions: Mapped[List["CreditCardTransaction"]] = relationship(back_populates="category")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    description: Mapped[str] = mapped_column(String(255))
    transaction_type: Mapped[TransactionType] = mapped_column(SQLEnum(TransactionType))
    
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    
    investment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("investments.id"), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 6), nullable=True)
    price_per_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")
    account: Mapped["Account"] = relationship(back_populates="transactions")
    investment: Mapped[Optional["Investment"]] = relationship(back_populates="transactions")

    __table_args__ = (
        Index('ix_transactions_date', date),
        Index('ix_transactions_category_id', category_id),
        Index('ix_transactions_account_id', account_id),
    )


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    planned_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), unique=True)
    
    category: Mapped["Category"] = relationship(back_populates="budgets")


class CreditCard(Base):
    __tablename__ = "credit_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    
    transactions: Mapped[List["CreditCardTransaction"]] = relationship(back_populates="credit_card", cascade="all, delete-orphan")


class CreditCardTransaction(Base):
    __tablename__ = "credit_card_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    description: Mapped[str] = mapped_column(String(255))
    installment_number: Mapped[int] = mapped_column(Integer, default=1)
    total_installments: Mapped[int] = mapped_column(Integer, default=1)
    
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    credit_card_id: Mapped[int] = mapped_column(ForeignKey("credit_cards.id"))
    
    category: Mapped[Optional["Category"]] = relationship(back_populates="credit_card_transactions")
    credit_card: Mapped["CreditCard"] = relationship(back_populates="transactions")


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    investment_type: Mapped[InvestmentType] = mapped_column(SQLEnum(InvestmentType))
    current_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="investment")

    @property
    def metrics(self) -> dict:
        from services.investment_service import calculate_investment_metrics
        return calculate_investment_metrics(self.transactions)

    @property
    def total_quantity(self) -> Decimal:
        return self.metrics['open_quantity']

    @property
    def total_invested(self) -> Decimal:
        return self.metrics['open_cost']

    @property
    def average_price(self) -> Decimal:
        return self.metrics['average_price']

    @property
    def realized_profit(self) -> Decimal:
        return self.metrics['total_realized_profit']

    @property
    def current_value(self) -> Decimal:
        if self.current_price and self.total_quantity > 0:
            return self.total_quantity * self.current_price
        return Decimal(0)

    @property
    def gain_loss(self) -> Decimal:
        return self.current_value - self.total_invested

    @property
    def gain_loss_percent(self) -> Decimal:
        if self.total_invested > 0:
            return (self.gain_loss / self.total_invested) * 100
        return Decimal(0)

