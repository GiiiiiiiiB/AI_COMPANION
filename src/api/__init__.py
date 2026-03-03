"""
API模块
"""
from .main import app
from .routers import (
    platform_router,
    knowledge_router,
    chat_router,
    user_router,
    analytics_router,
    health_router
)

__all__ = [
    "app",
    "platform_router",
    "knowledge_router",
    "chat_router", 
    "user_router",
    "analytics_router",
    "health_router"
]