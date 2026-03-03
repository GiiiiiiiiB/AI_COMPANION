"""
平台接入模块
"""
from .adapter import UnifiedMessageAdapter, message_adapter
from .douyin import DouyinPlatform, DouyinMessageHandler
from .qianfan import QianfanPlatform, QianfanMessageHandler

__all__ = [
    "UnifiedMessageAdapter",
    "message_adapter",
    "DouyinPlatform", 
    "DouyinMessageHandler",
    "QianfanPlatform",
    "QianfanMessageHandler"
]