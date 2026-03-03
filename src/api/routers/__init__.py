"""
API路由模块
"""
from .platform import router as platform_router
from .knowledge import router as knowledge_router
from .chat import router as chat_router
from .user import router as user_router
from .analytics import router as analytics_router
from .health import router as health_router

__all__ = [
    "platform_router",
    "knowledge_router", 
    "chat_router",
    "user_router",
    "analytics_router",
    "health_router"
]