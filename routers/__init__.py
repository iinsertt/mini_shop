from aiogram import Router

from .start_router import start_router
from .user_router import user_router
from .admin_router import admin_router

router_head = Router(name=__name__)

router_head.include_routers(
    start_router,
    user_router,
    admin_router,
)
