import enum
from datetime import datetime, timezone
from typing import Type, TypeVar, Optional, Any, Dict
from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    select,
    func
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, relationship

from .inmemory import AsyncRedisCache

T = TypeVar("T")
Base = declarative_base()


class CardStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    sold = "sold"


class WithdrawStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    balance = Column(Float, default=0.0, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    cards = relationship("Card", back_populates="owner", cascade="all, delete-orphan")
    purchases = relationship("Purchase", back_populates="buyer")
    withdraw_requests = relationship("WithdrawRequest", back_populates="user")

    @staticmethod
    def count_query():
        return select(func.count(User.id))


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    photo_file_id = Column(String, nullable=True)
    status = Column(SAEnum(CardStatus), default=CardStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="cards")
    purchases = relationship("Purchase", back_populates="card")


class Purchase(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    card_id = Column(Integer, ForeignKey("cards.id", ondelete="SET NULL"))
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    buyer = relationship("User", back_populates="purchases")
    card = relationship("Card", back_populates="purchases")


class WithdrawRequest(Base):
    __tablename__ = "withdraw_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    requisites = Column(String, nullable=False)
    status = Column(SAEnum(WithdrawStatus), default=WithdrawStatus.pending, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="withdraw_requests")


class Database:
    _instance: Optional["Database"] = None

    engine: AsyncEngine
    async_sessionmaker: async_sessionmaker[AsyncSession]

    def __new__(cls, db_url: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.engine = create_async_engine(
                db_url,
                echo=False,
                pool_size=10,
                max_overflow=20,
            )
            cls._instance.async_sessionmaker = async_sessionmaker(
                cls._instance.engine,
                expire_on_commit=False,
            )
        return cls._instance

    async def init_db(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


class SqlEndpointRepository:

    def __init__(self, async_sessionmaker: async_sessionmaker[AsyncSession], cache: AsyncRedisCache):
        self._async_sessionmaker = async_sessionmaker
        self._cache = cache

    async def get_by_id(self, entity_class: Type[T], entity_id: int) -> Optional[T]:
        key = f"{entity_class.__tablename__}:{entity_id}"
        cached = await self._cache.get(key)
        if cached:
            return self._deserialize(entity_class, cached)

        async with self._async_sessionmaker() as session:
            obj = await session.get(entity_class, entity_id)
            if obj:
                await self._cache.set(key, self._serialize(obj))
            return obj

    async def upsert(self, entity: Any) -> Any:
        async with self._async_sessionmaker() as session:
            async with session.begin():
                session.add(entity)
                await session.flush()
                key = f"{entity.__tablename__}:{entity.id}"
                await self._cache.set(key, self._serialize(entity))
        return entity

    async def delete(self, entity: Any) -> None:
        key = f"{entity.__tablename__}:{entity.id}"
        await self._cache.delete(key)

        async with self._async_sessionmaker() as session:
            async with session.begin():
                await session.delete(entity)

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self._async_sessionmaker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalars().first()
            if user:
                key = f"{User.__tablename__}:{user.id}"
                await self._cache.set(key, self._serialize(user))
            return user

    @staticmethod
    def _serialize(obj) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)

            if isinstance(value, enum.Enum):
                value = value.value

            from datetime import datetime
            if isinstance(value, datetime):
                value = value.isoformat()

            data[column.name] = value
        return data


    @staticmethod
    def _deserialize(entity_class: Type[T], data: Dict[str, Any]) -> T:
        from sqlalchemy import Enum as SAEnum_local

        kwargs: Dict[str, Any] = {}
        for column in entity_class.__table__.columns:
            value = data.get(column.name)
            col_type = column.type
            if isinstance(col_type, SAEnum_local) and value is not None:
                enum_cls = col_type.enum_class
                if enum_cls is not None:
                    value = enum_cls(value)
            kwargs[column.name] = value
        return entity_class(**kwargs)
