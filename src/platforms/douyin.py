"""
抖店平台接入模块
"""
import asyncio
import hashlib
import hmac
import json
import time
from typing import Dict, Optional, Any
from urllib.parse import urlencode
import httpx
from src.config.settings import settings


class DouyinPlatform:
    """抖店平台接入类"""
    
    def __init__(self, app_key: str = None, app_secret: str = None, shop_id: str = None):
        self.app_key = app_key or settings.platform.douyin_app_key
        self.app_secret = app_secret or settings.platform.douyin_app_secret
        self.shop_id = shop_id or settings.platform.douyin_shop_id
        self.base_url = "https://openapi-fxg.jinritemai.com"
        self.access_token = None
        self.token_expires_at = 0
        
    async def get_access_token(self) -> str:
        """获取访问令牌"""
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
            
        url = f"{self.base_url}/oauth2/access_token"
        params = {
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "grant_type": "authorization_self"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            result = response.json()
            
        if result.get("code") == 0:
            self.access_token = result["data"]["access_token"]
            expires_in = result["data"].get("expires_in", 7200)
            self.token_expires_at = time.time() + expires_in - 300  # 提前5分钟过期
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {result.get('message')}")
    
    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 按key排序
        sorted_params = sorted(params.items())
        # 拼接字符串
        sign_str = self.app_secret
        for key, value in sorted_params:
            sign_str += f"{key}{value}"
        sign_str += self.app_secret
        # MD5加密
        return hashlib.md5(sign_str.encode()).hexdigest().upper()
    
    async def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送API请求"""
        access_token = await self.get_access_token()
        
        url = f"{self.base_url}{endpoint}"
        
        # 添加公共参数
        if params is None:
            params = {}
        
        params.update({
            "app_key": self.app_key,
            "access_token": access_token,
            "timestamp": str(int(time.time())),
            "v": "2"
        })
        
        # 生成签名
        sign = self._generate_sign(params)
        params["sign"] = sign
        
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            else:
                response = await client.post(url, params=params, json=data)
            
            result = response.json()
            
        if result.get("code") == 0:
            return result["data"]
        else:
            raise Exception(f"API request failed: {result.get('message')}")
    
    async def send_message(self, user_id: str, message: str, message_type: str = "text") -> Dict[str, Any]:
        """发送消息给用户"""
        endpoint = "/message/send"
        data = {
            "buyer_nick": user_id,
            "content": message,
            "message_type": message_type
        }
        
        return await self._make_request("POST", endpoint, data=data)
    
    async def receive_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """接收用户消息"""
        # 验证签名
        if not self.verify_signature(webhook_data):
            raise ValueError("Invalid signature")
        
        # 解析消息内容
        message_data = webhook_data.get("data", {})
        
        return {
            "message_id": message_data.get("msg_id"),
            "user_id": message_data.get("buyer_nick"),
            "content": message_data.get("content"),
            "message_type": message_data.get("msg_type", "text"),
            "timestamp": message_data.get("create_time"),
            "metadata": {
                "shop_id": message_data.get("shop_id"),
                "order_id": message_data.get("order_id")
            }
        }
    
    def verify_signature(self, webhook_data: Dict[str, Any]) -> bool:
        """验证webhook签名"""
        signature = webhook_data.get("signature")
        timestamp = webhook_data.get("timestamp")
        
        if not signature or not timestamp:
            return False
        
        # 检查时间戳是否过期（5分钟）
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 300:
            return False
        
        # 重新生成签名进行验证
        sign_str = f"{timestamp}{self.app_secret}"
        expected_signature = hashlib.md5(sign_str.encode()).hexdigest().upper()
        
        return signature == expected_signature
    
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """获取用户信息"""
        endpoint = "/user/get"
        params = {
            "buyer_nick": user_id
        }
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def get_order_info(self, order_id: str) -> Dict[str, Any]:
        """获取订单信息"""
        endpoint = "/order/detail"
        params = {
            "order_id": order_id
        }
        
        return await self._make_request("GET", endpoint, params=params)
    
    async def get_shop_info(self) -> Dict[str, Any]:
        """获取店铺信息"""
        endpoint = "/shop/getShopInfo"
        
        return await self._make_request("GET", endpoint)


class DouyinMessageHandler:
    """抖店消息处理器"""
    
    def __init__(self, platform: DouyinPlatform):
        self.platform = platform
    
    async def handle_message(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理接收到的消息"""
        try:
            # 1. 验证消息签名
            if not self.platform.verify_signature(message_data):
                return {"error": "Invalid signature"}
            
            # 2. 解析消息内容
            message = await self.platform.receive_message(message_data)
            
            # 3. 保存消息到数据库（由上层调用者处理）
            # await self.save_message(message)
            
            # 4. 转发到对话引擎（由上层调用者处理）
            # response = await self.forward_to_chat_engine(message)
            
            # 5. 发送回复（由上层调用者处理）
            # await self.send_response(message.user_id, response)
            
            return {
                "status": "success",
                "message": message,
                "message_id": message["message_id"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def send_response(self, user_id: str, response: str) -> Dict[str, Any]:
        """发送回复消息"""
        try:
            result = await self.platform.send_message(user_id, response)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }