import os
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    monthly_budget = Column(Float, nullable=True)  # NULL = not set

    def __repr__(self):
        return f"<UserSettings user_id={self.user_id} budget={self.monthly_budget}>"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, nullable=True)  # NULL = system default, set = user custom
    expenses = relationship("Expense", back_populates="category", lazy="selectin")

    def __repr__(self):
        return f"<Category {self.name}>"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="RUB")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    description = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    category = relationship("Category", back_populates="expenses", lazy="selectin")

    def __repr__(self):
        return f"<Expense {self.amount} {self.currency} - {self.description}>"
