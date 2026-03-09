from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .config import settings
from sqlalchemy.orm import DeclarativeBase



database_url = settings.database_url()
engine = create_async_engine(database_url, echo=True)
async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    __abstract__ = True