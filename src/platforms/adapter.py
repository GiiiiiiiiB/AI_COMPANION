"""
统一消息适配器
"""
import asyncio
import time
from typing import Dict, Any, Optional, List
from src.platforms.douyin import DouyinPlatform, DouyinMessageHandler
from src.platforms.qianfan import QianfanPlatform, QianfanMessageHandler
from src.config.settings import settings


class UnifiedMessageAdapter:
    """统一消息适配器"""
    
    def __init__(self):
        self.platforms = {
            'douyin': {
                'client': DouyinPlatform(),
                'handler': None  # 延迟初始化
            },
            'qianfan': {
                'client': QianfanPlatform(),
                'handler': None  # 延迟初始化
            }
        }
        
        # 初始化处理器
        self.platforms['douyin']['handler'] = DouyinMessageHandler(self.platforms['douyin']['client'])
        self.platforms['qianfan']['handler'] = QianfanMessageHandler(self.platforms['qianfan']['client'])
    
    async def send_message(self, platform: str, user_id: str, message: str, message_type: str = "text", **kwargs) -> Dict[str, Any]:
        """统一发送消息接口"""
        platform_config = self.platforms.get(platform)
        if not platform_config:
            raise ValueError(f"Unsupported platform: {platform}")
        
        try:
            client = platform_config['client']
            
            if platform == 'douyin':
                result = await client.send_message(user_id, message, message_type)
            elif platform == 'qianfan':
                session_id = kwargs.get('session_id')
                if not session_id:
                    # 创建新会话
                    session_result = await client.create_session(user_id)
                    session_id = session_result.get('session_id')
                
                result = await client.send_message(session_id, message, message_type)
            else:
                raise ValueError(f"Platform {platform} not implemented")
            
            return {
                "status": "success",
                "platform": platform,
                "user_id": user_id,
                "message": message,
                "result": result
            }
            
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "user_id": user_id,
                "message": message,
                "error": str(e)
            }
    
    async def receive_message(self, platform: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """统一接收消息接口"""
        platform_config = self.platforms.get(platform)
        if not platform_config:
            raise ValueError(f"Unsupported platform: {platform}")
        
        try:
            handler = platform_config['handler']
            
            if platform == 'douyin':
                result = await handler.handle_message(message_data)
            elif platform == 'qianfan':
                result = await handler.handle_webhook(message_data)
            else:
                raise ValueError(f"Platform {platform} not implemented")
            
            if result.get("status") == "success" and "message" in result:
                # 标准化消息格式
                standardized_message = self.standardize_message(platform, result["message"])
                result["standardized_message"] = standardized_message
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "error": str(e)
            }
    
    def standardize_message(self, platform: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化不同平台的消息格式"""
        # 基础字段
        standardized = {
            "platform": platform,
            "message_id": message_data.get("message_id"),
            "user_id": message_data.get("user_id"),
            "content": message_data.get("content"),
            "message_type": message_data.get("message_type", "text"),
            "timestamp": message_data.get("timestamp", int(time.time())),
            "metadata": message_data.get("metadata", {})
        }
        
        # 平台特定字段处理
        if platform == "douyin":
            standardized.update({
                "session_id": f"douyin_{message_data.get('user_id')}_{int(time.time())}",
                "direction": "inbound"
            })
        elif platform == "qianfan":
            standardized.update({
                "session_id": message_data.get("session_id"),
                "direction": "inbound"
            })
        
        return standardized
    
    async def process_message(self, standardized_message: Dict[str, Any]) -> Dict[str, Any]:
        """处理标准化消息"""
        # 这里可以添加消息预处理逻辑
        # 如：敏感词过滤、消息分类、优先级判断等
        
        return {
            "status": "success",
            "message": standardized_message,
            "processed_at": int(time.time())
        }
    
    def get_platform_client(self, platform: str):
        """获取平台客户端"""
        platform_config = self.platforms.get(platform)
        if not platform_config:
            raise ValueError(f"Unsupported platform: {platform}")
        return platform_config['client']
    
    def get_platform_handler(self, platform: str):
        """获取平台处理器"""
        platform_config = self.platforms.get(platform)
        if not platform_config:
            raise ValueError(f"Unsupported platform: {platform}")
        return platform_config['handler']
    
    def get_supported_platforms(self) -> List[str]:
        """获取支持的平台列表"""
        return list(self.platforms.keys())
    
    async def get_platform_user_info(self, platform: str, user_id: str) -> Dict[str, Any]:
        """获取平台用户信息"""
        client = self.get_platform_client(platform)
        
        try:
            if platform == "douyin":
                user_info = await client.get_user_info(user_id)
            elif platform == "qianfan":
                # 千帆平台可能需要不同的方式获取用户信息
                user_info = {"user_id": user_id, "platform": "qianfan"}
            else:
                raise ValueError(f"Platform {platform} not implemented")
            
            return {
                "status": "success",
                "platform": platform,
                "user_id": user_id,
                "user_info": user_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "user_id": user_id,
                "error": str(e)
            }
    
    async def get_platform_order_info(self, platform: str, order_id: str) -> Dict[str, Any]:
        """获取平台订单信息"""
        client = self.get_platform_client(platform)
        
        try:
            if platform == "douyin":
                order_info = await client.get_order_info(order_id)
            elif platform == "qianfan":
                # 千帆平台可能需要不同的方式获取订单信息
                order_info = {"order_id": order_id, "platform": "qianfan"}
            else:
                raise ValueError(f"Platform {platform} not implemented")
            
            return {
                "status": "success",
                "platform": platform,
                "order_id": order_id,
                "order_info": order_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "platform": platform,
                "order_id": order_id,
                "error": str(e)
            }


# 全局适配器实例
message_adapter = UnifiedMessageAdapter()