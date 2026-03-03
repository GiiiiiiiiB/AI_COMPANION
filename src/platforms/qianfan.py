"""
千帆客服工作台平台接入模块
"""
import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Dict, Optional, Any
import httpx
from src.config.settings import settings


class QianfanPlatform:
    """千帆客服工作台平台接入类"""
    
    def __init__(self, app_key: str = None, app_secret: str = None):
        self.app_key = app_key or settings.platform.qianfan_app_key
        self.app_secret = app_secret or settings.platform.qianfan_app_secret
        self.base_url = "https://qianfan-workbench.example.com"  # 实际URL需要替换
        self.access_token = None
        self.token_expires_at = 0
    
    async def get_access_token(self) -> str:
        """获取访问令牌"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
            
        url = f"{self.base_url}/auth/token"
        
        # 生成签名
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        sign_str = f"app_key={self.app_key}&timestamp={timestamp}&nonce={nonce}&app_secret={self.app_secret}"
        signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        data = {
            "app_key": self.app_key,
            "timestamp": timestamp,
            "nonce": nonce,
            "signature": signature,
            "grant_type": "client_credentials"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data)
            result = response.json()
            
        if result.get("code") == 0:
            self.access_token = result["data"]["access_token"]
            expires_in = result["data"].get("expires_in", 7200)
            self.token_expires_at = time.time() + expires_in - 300  # 提前5分钟过期
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {result.get('message')}")
    
    async def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送API请求"""
        access_token = await self.get_access_token()
        
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            else:
                response = await client.post(url, headers=headers, json=data)
            
            result = response.json()
            
        if result.get("code") == 0:
            return result["data"]
        else:
            raise Exception(f"API request failed: {result.get('message')}")
    
    async def create_session(self, user_id: str, **kwargs) -> Dict[str, Any]:
        """创建客服会话"""
        endpoint = "/session/create"
        data = {
            "user_id": user_id,
            "session_type": kwargs.get("session_type", "text"),
            "priority": kwargs.get("priority", "normal"),
            "subject": kwargs.get("subject", "用户咨询"),
            "description": kwargs.get("description", ""),
            "metadata": kwargs.get("metadata", {})
        }
        
        return await self._make_request("POST", endpoint, data=data)
    
    async def send_message(self, session_id: str, message: str, message_type: str = "text", **kwargs) -> Dict[str, Any]:
        """发送消息"""
        endpoint = "/message/send"
        data = {
            "session_id": session_id,
            "content": message,
            "message_type": message_type,
            "sender_type": "agent",  # agent: 客服, user: 用户
            "metadata": kwargs.get("metadata", {})
        }
        
        return await self._make_request("POST", endpoint, data=data)
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        endpoint = f"/session/{session_id}"
        
        return await self._make_request("GET", endpoint)
    
    async def get_session_messages(self, session_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """获取会话消息"""
        endpoint = f"/session/{session_id}/messages"
        params = {
            "limit": limit,
            "offset": offset
        }
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def close_session(self, session_id: str, reason: str = "") -> Dict[str, Any]:
        """关闭会话"""
        endpoint = f"/session/{session_id}/close"
        data = {
            "reason": reason
        }
        
        return await self._make_request("POST", endpoint, data=data)
    
    async def transfer_session(self, session_id: str, agent_id: str, reason: str = "") -> Dict[str, Any]:
        """转接会话"""
        endpoint = f"/session/{session_id}/transfer"
        data = {
            "agent_id": agent_id,
            "reason": reason
        }
        
        return await self._make_request("POST", endpoint, data=data)
    
    async def get_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """获取客服信息"""
        endpoint = f"/agent/{agent_id}"
        
        return await self._make_request("GET", endpoint)
    
    async def get_workload_stats(self, date: str = None) -> Dict[str, Any]:
        """获取工作负载统计"""
        endpoint = "/stats/workload"
        params = {}
        if date:
            params["date"] = date
        
        return await self._make_request("GET", endpoint, params=params)


class QianfanMessageHandler:
    """千帆消息处理器"""
    
    def __init__(self, platform: QianfanPlatform):
        self.platform = platform
        self.active_sessions = {}  # 存储活跃会话
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理webhook回调"""
        try:
            event_type = webhook_data.get("event_type")
            
            if event_type == "message_received":
                return await self.handle_incoming_message(webhook_data)
            elif event_type == "session_created":
                return await self.handle_session_created(webhook_data)
            elif event_type == "session_closed":
                return await self.handle_session_closed(webhook_data)
            else:
                return {"status": "ignored", "reason": f"Unknown event type: {event_type}"}
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def handle_incoming_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的消息"""
        message_data = webhook_data.get("data", {})
        
        # 标准化消息格式
        standardized_message = {
            "platform": "qianfan",
            "message_id": message_data.get("message_id"),
            "session_id": message_data.get("session_id"),
            "user_id": message_data.get("user_id"),
            "content": message_data.get("content"),
            "message_type": message_data.get("message_type", "text"),
            "timestamp": message_data.get("timestamp"),
            "metadata": {
                "sender_type": message_data.get("sender_type"),
                "session_type": message_data.get("session_type"),
                "priority": message_data.get("priority")
            }
        }
        
        # 更新活跃会话
        session_id = standardized_message["session_id"]
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = {
                "user_id": standardized_message["user_id"],
                "created_at": time.time()
            }
        
        return {
            "status": "success",
            "message": standardized_message
        }
    
    async def handle_session_created(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理会话创建"""
        session_data = webhook_data.get("data", {})
        session_id = session_data.get("session_id")
        user_id = session_data.get("user_id")
        
        self.active_sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time()
        }
        
        return {
            "status": "success",
            "session_id": session_id,
            "user_id": user_id
        }
    
    async def handle_session_closed(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理会话关闭"""
        session_data = webhook_data.get("data", {})
        session_id = session_data.get("session_id")
        
        # 从活跃会话中移除
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return {
            "status": "success",
            "session_id": session_id
        }
    
    async def send_response(self, session_id: str, response: str, message_type: str = "text") -> Dict[str, Any]:
        """发送回复消息"""
        try:
            result = await self.platform.send_message(session_id, response, message_type)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_active_sessions(self) -> Dict[str, Any]:
        """获取活跃会话列表"""
        return self.active_sessions.copy()
    
    def cleanup_expired_sessions(self, max_age: int = 3600):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session_info in self.active_sessions.items():
            if current_time - session_info["created_at"] > max_age:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        return expired_sessions