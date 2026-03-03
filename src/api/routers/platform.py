"""
平台接入API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Dict, Any, Optional
import hashlib
import hmac
import time

from src.platforms import message_adapter
from src.api.main import verify_token

router = APIRouter()


@router.post("/webhook/{platform}")
async def receive_platform_message(
    platform: str,
    request: Request,
    authorization: Optional[str] = Header(None),
    x_signature: Optional[str] = Header(None),
    x_timestamp: Optional[str] = Header(None)
):
    """接收平台消息webhook"""
    try:
        # 获取请求体
        body = await request.body()
        message_data = await request.json()
        
        # 验证签名（根据平台不同）
        if not await verify_platform_signature(platform, request.headers, body, message_data):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # 处理消息
        result = await message_adapter.receive_message(platform, message_data)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "message_id": result.get("message", {}).get("message_id"),
            "platform": platform
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process webhook: {str(e)}")


@router.post("/webhook/{platform}/verify")
async def verify_webhook(
    platform: str,
    request: Request
):
    """验证webhook配置"""
    try:
        # 获取验证参数
        query_params = dict(request.query_params)
        
        # 根据平台验证逻辑
        if platform == "douyin":
            # 抖店验证逻辑
            echostr = query_params.get("echostr")
            if echostr:
                return {"echostr": echostr}
        elif platform == "qianfan":
            # 千帆验证逻辑
            challenge = query_params.get("challenge")
            if challenge:
                return {"challenge": challenge}
        
        return {"status": "verified", "platform": platform}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook verification failed: {str(e)}")


@router.get("/platforms")
async def get_supported_platforms():
    """获取支持的平台列表"""
    platforms = message_adapter.get_supported_platforms()
    return {
        "platforms": platforms,
        "count": len(platforms)
    }


@router.get("/platforms/{platform}/info")
async def get_platform_info(platform: str):
    """获取平台信息"""
    try:
        client = message_adapter.get_platform_client(platform)
        
        # 获取平台基本信息
        if platform == "douyin":
            info = {
                "name": "抖店",
                "description": "抖音电商平台",
                "features": [
                    "消息收发",
                    "用户信息获取",
                    "订单信息查询",
                    "店铺信息管理"
                ],
                "webhook_support": True,
                "api_endpoints": [
                    "/api/v1/webhook/douyin",
                    "/api/v1/platforms/douyin/send"
                ]
            }
        elif platform == "qianfan":
            info = {
                "name": "千帆客服工作台",
                "description": "百度千帆客服工作台",
                "features": [
                    "会话管理",
                    "消息收发",
                    "客服转接",
                    "工作负载统计"
                ],
                "webhook_support": True,
                "api_endpoints": [
                    "/api/v1/webhook/qianfan",
                    "/api/v1/platforms/qianfan/sessions"
                ]
            }
        else:
            raise HTTPException(status_code=404, detail=f"Platform {platform} not found")
        
        return info
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/platforms/{platform}/send")
async def send_platform_message(
    platform: str,
    message_request: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """发送平台消息"""
    try:
        user_id = message_request.get("user_id")
        message = message_request.get("message")
        message_type = message_request.get("message_type", "text")
        
        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")
        
        # 发送消息
        result = await message_adapter.send_message(platform, user_id, message, message_type)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "status": "success",
            "platform": platform,
            "user_id": user_id,
            "message": message,
            "result": result.get("result")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.get("/platforms/{platform}/users/{user_id}")
async def get_platform_user_info(
    platform: str,
    user_id: str,
    token: str = Depends(verify_token)
):
    """获取平台用户信息"""
    try:
        result = await message_adapter.get_platform_user_info(platform, user_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


@router.get("/platforms/{platform}/orders/{order_id}")
async def get_platform_order_info(
    platform: str,
    order_id: str,
    token: str = Depends(verify_token)
):
    """获取平台订单信息"""
    try:
        result = await message_adapter.get_platform_order_info(platform, order_id)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get order info: {str(e)}")


@router.post("/platforms/{platform}/sessions")
async def create_platform_session(
    platform: str,
    session_request: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """创建平台会话"""
    try:
        if platform != "qianfan":
            raise HTTPException(status_code=400, detail=f"Session creation not supported for {platform}")
        
        user_id = session_request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        client = message_adapter.get_platform_client(platform)
        result = await client.create_session(user_id, **session_request)
        
        return {
            "status": "success",
            "platform": platform,
            "user_id": user_id,
            "session": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/platforms/{platform}/sessions/{session_id}")
async def get_platform_session_info(
    platform: str,
    session_id: str,
    token: str = Depends(verify_token)
):
    """获取平台会话信息"""
    try:
        if platform != "qianfan":
            raise HTTPException(status_code=400, detail=f"Session info not supported for {platform}")
        
        client = message_adapter.get_platform_client(platform)
        result = await client.get_session_info(session_id)
        
        return {
            "status": "success",
            "platform": platform,
            "session_id": session_id,
            "session": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}")


@router.post("/platforms/{platform}/sessions/{session_id}/close")
async def close_platform_session(
    platform: str,
    session_id: str,
    close_request: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """关闭平台会话"""
    try:
        if platform != "qianfan":
            raise HTTPException(status_code=400, detail=f"Session close not supported for {platform}")
        
        reason = close_request.get("reason", "")
        
        client = message_adapter.get_platform_client(platform)
        result = await client.close_session(session_id, reason)
        
        return {
            "status": "success",
            "platform": platform,
            "session_id": session_id,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


async def verify_platform_signature(platform: str, headers: Dict[str, str], body: bytes, message_data: Dict[str, Any]) -> bool:
    """验证平台签名"""
    try:
        if platform == "douyin":
            # 抖店签名验证
            signature = headers.get("x-signature")
            timestamp = headers.get("x-timestamp")
            
            if not signature or not timestamp:
                return False
            
            # 检查时间戳是否过期（5分钟）
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                return False
            
            # 重新生成签名进行验证
            client = message_adapter.get_platform_client(platform)
            return client.verify_signature({"signature": signature, "timestamp": timestamp})
            
        elif platform == "qianfan":
            # 千帆签名验证
            authorization = headers.get("authorization")
            if not authorization:
                return False
            
            # 这里实现千帆的签名验证逻辑
            # 简化处理，实际应该验证JWT令牌
            return True
            
        return False
        
    except Exception as e:
        print(f"Signature verification failed for {platform}: {e}")
        return False