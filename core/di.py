from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import settings
from .database import Database, SqlEndpointRepository
from .inmemory import AsyncRedisCache

db: Database | None = None
redis_cache: AsyncRedisCache | None = None
repo: SqlEndpointRepository | None = None
bot: Bot | None = None


async def init() -> None:
    global db, redis_cache, repo, bot

    db = Database(settings.database_url)
    await db.init_db()

    redis_cache = AsyncRedisCache(settings.redis_url)
    await redis_cache.init()

    repo = SqlEndpointRepository(db.async_sessionmaker, redis_cache)

    bot = Bot(
        token=settings.tg_api_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
