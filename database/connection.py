import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from models.expense import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/expenses.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _seed_default_categories()


async def _seed_default_categories():
    """Insert default categories if they don't exist."""
    from models.expense import Category

    defaults = [
        "Food", "Transport", "Entertainment", "Shopping",
        "Utilities", "Health", "Education", "Other"
    ]
    async with async_session() as session:
        for name in defaults:
            from sqlalchemy import select
            result = await session.execute(
                select(Category).where(Category.name == name, Category.user_id.is_(None))
            )
            if not result.scalar_one_or_none():
                session.add(Category(name=name, user_id=None))
        await session.commit()


async def get_session() -> AsyncSession:
    """Yield a database session."""
    async with async_session() as session:
        yield session
