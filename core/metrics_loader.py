from sqlalchemy import select, func
import core.di as di
from core.metrics import users_total, cards_total, purchases_total, withdraw_requests_total
from core.database import User, Card, Purchase, WithdrawRequest


async def preload_metrics():
    async with di.db.async_sessionmaker() as session:

        u = await session.scalar(select(func.count()).select_from(User))
        users_total.set(u or 0)

        c = await session.scalar(select(func.count()).select_from(Card))
        cards_total.set(c or 0)

        p = await session.scalar(select(func.count()).select_from(Purchase))
        purchases_total.inc(p or 0)

        w = await session.scalar(select(func.count()).select_from(WithdrawRequest))
        withdraw_requests_total.inc(w or 0)
