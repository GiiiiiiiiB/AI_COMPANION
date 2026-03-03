"""
聊天API路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, Optional
import uuid

from src.chat import IntentClassifier, ContextManager, ResponseGenerator
from src.users import SessionManager, UserProfileManager
from src.companion import EmotionAnalyzer, ProactiveChatManager
from src.api.main import (
    verify_token, get_intent_classifier, get_context_manager, 
    get_response_generator, get_session_manager, get_user_profile_manager,
    get_emotion_analyzer, get_proactive_chat_manager
)

router = APIRouter()


@router.post("/chat/message")
async def process_chat_message(
    message_request: Dict[str, Any],
    intent_classifier: IntentClassifier = Depends(get_intent_classifier),
    context_manager: ContextManager = Depends(get_context_manager),
    response_generator: ResponseGenerator = Depends(get_response_generator),
    session_manager: SessionManager = Depends(get_session_manager),
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    emotion_analyzer: EmotionAnalyzer = Depends(get_emotion_analyzer),
    token: str = Depends(verify_token)
):
    """处理聊天消息"""
    try:
        # 获取请求参数
        user_id = message_request.get("user_id")
        platform = message_request.get("platform")
        message = message_request.get("message")
        session_id = message_request.get("session_id")
        
        if not user_id or not platform or not message:
            raise HTTPException(status_code=400, detail="user_id, platform, and message are required")
        
        # 获取或创建会话
        if not session_id:
            session = await session_manager.get_active_session(user_id)
            if not session:
                session = await session_manager.create_session(user_id, platform)
            session_id = session["session_id"]
        
        # 获取用户画像
        user_profile = await user_profile_manager.get_profile(user_id)
        if not user_profile:
            # 创建新用户画像
            user_profile = await user_profile_manager.create_profile({
                "user_id": user_id,
                "platform": platform
            })
        
        # 意图识别
        intent_result = await intent_classifier.classify(message)
        
        # 情感分析
        emotion_result = await emotion_analyzer.analyze(message)
        
        # 更新上下文
        context = await context_manager.get_context(session_id)
        context = await context_manager.update_intent(
            session_id, 
            intent_result["intent"], 
            intent_result["confidence"]
        )
        context = await context_manager.update_entities(
            session_id, 
            intent_result.get("entities", [])
        )
        
        # 添加用户消息到上下文
        await context_manager.add_message(
            session_id, 
            message, 
            "inbound",
            {
                "intent": intent_result["intent"],
                "emotion": emotion_result["emotion"],
                "confidence": intent_result["confidence"]
            }
        )
        
        # 生成回复
        response = await response_generator.generate_response(message, context)
        
        # 添加回复到上下文
        await context_manager.add_message(
            session_id, 
            response, 
            "outbound"
        )
        
        # 保存消息到会话
        message_id = str(uuid.uuid4())
        await session_manager.add_message(session_id, {
            "message_id": message_id,
            "user_id": user_id,
            "platform": platform,
            "content": message,
            "message_type": "text",
            "direction": "inbound",
            "intent": intent_result["intent"],
            "emotion": emotion_result["emotion"]
        })
        
        await session_manager.add_message(session_id, {
            "message_id": f"{message_id}_response",
            "user_id": "bot",
            "platform": platform,
            "content": response,
            "message_type": "text",
            "direction": "outbound"
        })
        
        # 更新用户行为数据
        await user_profile_manager.update_behavior(user_id, {
            "response_time": 0  # 可以计算实际响应时间
        })
        
        return {
            "message_id": message_id,
            "session_id": session_id,
            "response": response,
            "intent": intent_result["intent"],
            "intent_confidence": intent_result["confidence"],
            "emotion": emotion_result["emotion"],
            "emotion_confidence": emotion_result["confidence"],
            "entities": intent_result.get("entities", [])
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.post("/chat/session")
async def create_chat_session(
    session_request: Dict[str, Any],
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """创建聊天会话"""
    try:
        user_id = session_request.get("user_id")
        platform = session_request.get("platform")
        metadata = session_request.get("metadata", {})
        
        if not user_id or not platform:
            raise HTTPException(status_code=400, detail="user_id and platform are required")
        
        # 创建会话
        session = await session_manager.create_session(user_id, platform, **metadata)
        
        return {
            "session_id": session["session_id"],
            "user_id": user_id,
            "platform": platform,
            "status": session["status"],
            "created_at": session["created_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/chat/session/{session_id}")
async def get_chat_session(
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    context_manager: ContextManager = Depends(get_context_manager),
    token: str = Depends(verify_token)
):
    """获取聊天会话信息"""
    try:
        # 获取会话信息
        session = await session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # 获取上下文信息
        context = await context_manager.get_context(session_id)
        
        # 获取会话统计
        stats = await session_manager.get_session_stats(session_id)
        
        return {
            "session": session,
            "context": {
                "current_intent": context.get("current_intent"),
                "state": context.get("state"),
                "message_count": context.get("message_count"),
                "entities": context.get("entities", {})
            },
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.get("/chat/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """获取会话消息"""
    try:
        messages = await session_manager.get_session_messages(session_id, limit, offset)
        
        return {
            "session_id": session_id,
            "messages": messages,
            "count": len(messages),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")


@router.post("/chat/session/{session_id}/close")
async def close_chat_session(
    session_id: str,
    close_request: Dict[str, Any],
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """关闭聊天会话"""
    try:
        reason = close_request.get("reason", "")
        satisfaction_score = close_request.get("satisfaction_score")
        
        success = await session_manager.close_session(session_id, reason, satisfaction_score)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or already closed")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session closed successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


@router.post("/chat/session/{session_id}/escalate")
async def escalate_chat_session(
    session_id: str,
    escalate_request: Dict[str, Any],
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """升级会话到人工客服"""
    try:
        reason = escalate_request.get("reason", "")
        agent_id = escalate_request.get("agent_id")
        
        success = await session_manager.escalate_session(session_id, reason, agent_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Session escalated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to escalate session: {str(e)}")


@router.get("/chat/intents")
async def get_supported_intents(
    intent_classifier: IntentClassifier = Depends(get_intent_classifier),
    token: str = Depends(verify_token)
):
    """获取支持的意图列表"""
    try:
        intents = intent_classifier.get_supported_intents()
        
        return {
            "intents": intents,
            "count": len(intents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get intents: {str(e)}")


@router.post("/chat/analyze-intent")
async def analyze_intent(
    analyze_request: Dict[str, Any],
    intent_classifier: IntentClassifier = Depends(get_intent_classifier),
    token: str = Depends(verify_token)
):
    """分析文本意图"""
    try:
        text = analyze_request.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        
        result = await intent_classifier.classify(text)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze intent: {str(e)}")


@router.post("/chat/analyze-emotion")
async def analyze_emotion(
    analyze_request: Dict[str, Any],
    emotion_analyzer: EmotionAnalyzer = Depends(get_emotion_analyzer),
    token: str = Depends(verify_token)
):
    """分析文本情感"""
    try:
        text = analyze_request.get("text")
        if not text:
            raise HTTPException(status_code=400, detail="text is required")
        
        result = await emotion_analyzer.analyze(text)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze emotion: {str(e)}")


@router.get("/chat/context/{session_id}")
async def get_chat_context(
    session_id: str,
    context_manager: ContextManager = Depends(get_context_manager),
    token: str = Depends(verify_token)
):
    """获取聊天上下文"""
    try:
        context = await context_manager.get_context(session_id)
        
        return {
            "session_id": session_id,
            "context": context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@router.delete("/chat/context/{session_id}")
async def clear_chat_context(
    session_id: str,
    context_manager: ContextManager = Depends(get_context_manager),
    token: str = Depends(verify_token)
):
    """清除聊天上下文"""
    try:
        success = await context_manager.clear_context(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Context not found")
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Context cleared successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear context: {str(e)}")


@router.get("/chat/context/{session_id}/summary")
async def get_context_summary(
    session_id: str,
    max_messages: int = 10,
    context_manager: ContextManager = Depends(get_context_manager),
    token: str = Depends(verify_token)
):
    """获取上下文摘要"""
    try:
        summary = await context_manager.get_conversation_summary(session_id, max_messages)
        
        return {
            "session_id": session_id,
            "summary": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get context summary: {str(e)}")


@router.post("/chat/proactive-check")
async def check_proactive_opportunities(
    check_request: Dict[str, Any],
    proactive_chat_manager: ProactiveChatManager = Depends(get_proactive_chat_manager),
    token: str = Depends(verify_token)
):
    """检查主动对话机会"""
    try:
        session_id = check_request.get("session_id")
        user_id = check_request.get("user_id")
        
        if not session_id or not user_id:
            raise HTTPException(status_code=400, detail="session_id and user_id are required")
        
        opportunities = await proactive_chat_manager.check_proactive_opportunity(session_id, user_id)
        
        return {
            "session_id": session_id,
            "user_id": user_id,
            "opportunities": opportunities,
            "count": len(opportunities)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check proactive opportunities: {str(e)}")


@router.post("/chat/execute-proactive")
async def execute_proactive_chat(
    execute_request: Dict[str, Any],
    proactive_chat_manager: ProactiveChatManager = Depends(get_proactive_chat_manager),
    token: str = Depends(verify_token)
):
    """执行主动对话"""
    try:
        session_id = execute_request.get("session_id")
        user_id = execute_request.get("user_id")
        opportunity = execute_request.get("opportunity")
        
        if not session_id or not user_id or not opportunity:
            raise HTTPException(status_code=400, detail="session_id, user_id, and opportunity are required")
        
        result = await proactive_chat_manager.execute_proactive_chat(session_id, user_id, opportunity)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute proactive chat: {str(e)}")