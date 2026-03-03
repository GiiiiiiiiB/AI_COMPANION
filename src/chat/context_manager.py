"""
对话上下文管理器
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio

from src.storage.database import get_redis_client


class ContextManager:
    """对话上下文管理器"""
    
    def __init__(self, redis_client=None, context_ttl: int = 3600):
        self.redis = redis_client
        self.context_ttl = context_ttl  # 1小时过期
        self.max_history_length = 20  # 最大历史记录长度
        self.max_context_size = 4096  # 最大上下文大小（字符）
    
    async def _get_redis(self):
        """获取Redis客户端"""
        if self.redis is None:
            self.redis = await get_redis_client()
        return self.redis
    
    async def get_context(self, session_id: str) -> Dict[str, Any]:
        """获取会话上下文"""
        redis = await self._get_redis()
        context_key = f"context:{session_id}"
        
        try:
            context_data = await redis.get(context_key)
            
            if not context_data:
                return self.create_default_context(session_id)
            
            context = json.loads(context_data)
            
            # 检查是否需要清理历史记录
            context = self._cleanup_history(context)
            
            return context
            
        except Exception as e:
            print(f"Error getting context for {session_id}: {e}")
            return self.create_default_context(session_id)
    
    async def update_context(self, session_id: str, context_update: Dict[str, Any]) -> Dict[str, Any]:
        """更新会话上下文"""
        context = await self.get_context(session_id)
        
        # 更新上下文信息
        context.update(context_update)
        
        # 添加时间戳
        context["last_updated"] = datetime.now().isoformat()
        
        # 清理历史记录
        context = self._cleanup_history(context)
        
        # 保存到Redis
        await self._save_context(session_id, context)
        
        return context
    
    async def add_message(self, session_id: str, message: str, direction: str = "inbound", metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """添加消息到上下文"""
        context = await self.get_context(session_id)
        
        message_data = {
            "content": message,
            "direction": direction,  # inbound: 用户消息, outbound: 机器人回复
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # 添加到历史记录
        context["conversation_history"].append(message_data)
        
        # 更新消息计数
        context["message_count"] = len(context["conversation_history"])
        
        # 保存更新后的上下文
        await self._save_context(session_id, context)
        
        return context
    
    async def update_intent(self, session_id: str, intent: str, confidence: float = None) -> Dict[str, Any]:
        """更新当前意图"""
        context = await self.get_context(session_id)
        
        context["current_intent"] = intent
        if confidence is not None:
            context["intent_confidence"] = confidence
        
        # 添加到意图历史
        if "intent_history" not in context:
            context["intent_history"] = []
        
        context["intent_history"].append({
            "intent": intent,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        })
        
        # 限制历史长度
        if len(context["intent_history"]) > 10:
            context["intent_history"] = context["intent_history"][-10:]
        
        await self._save_context(session_id, context)
        return context
    
    async def update_entities(self, session_id: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """更新实体信息"""
        context = await self.get_context(session_id)
        
        if "entities" not in context:
            context["entities"] = {}
        
        for entity in entities:
            entity_type = entity.get("entity")
            entity_value = entity.get("value")
            
            if entity_type and entity_value:
                if entity_type not in context["entities"]:
                    context["entities"][entity_type] = []
                
                # 避免重复
                existing_values = {e["value"] for e in context["entities"][entity_type]}
                if entity_value not in existing_values:
                    context["entities"][entity_type].append({
                        "value": entity_value,
                        "timestamp": datetime.now().isoformat(),
                        "confidence": entity.get("confidence", 1.0)
                    })
        
        await self._save_context(session_id, context)
        return context
    
    async def update_state(self, session_id: str, state: str) -> Dict[str, Any]:
        """更新对话状态"""
        context = await self.get_context(session_id)
        
        # 状态转换验证
        valid_transitions = {
            "greeting": ["inquiry", "waiting", "ended"],
            "inquiry": ["processing", "waiting", "escalated", "ended"],
            "processing": ["waiting", "resolved", "escalated", "ended"],
            "waiting": ["processing", "resolved", "escalated", "ended"],
            "resolved": ["ended"],
            "escalated": ["ended"],
            "ended": []
        }
        
        current_state = context.get("state", "greeting")
        if state in valid_transitions.get(current_state, []):
            context["state"] = state
            context["state_history"] = context.get("state_history", [])
            context["state_history"].append({
                "from": current_state,
                "to": state,
                "timestamp": datetime.now().isoformat()
            })
        else:
            print(f"Invalid state transition: {current_state} -> {state}")
        
        await self._save_context(session_id, context)
        return context
    
    async def get_conversation_summary(self, session_id: str, max_messages: int = 10) -> str:
        """获取对话摘要"""
        context = await self.get_context(session_id)
        history = context.get("conversation_history", [])
        
        if not history:
            return ""
        
        # 获取最近的消息
        recent_messages = history[-max_messages:]
        
        summary_parts = []
        
        # 添加用户意图
        current_intent = context.get("current_intent")
        if current_intent:
            summary_parts.append(f"用户意图: {current_intent}")
        
        # 添加关键实体
        entities = context.get("entities", {})
        if entities:
            entity_summary = []
            for entity_type, entity_list in entities.items():
                if entity_list:
                    latest_entity = entity_list[-1]
                    entity_summary.append(f"{entity_type}: {latest_entity['value']}")
            if entity_summary:
                summary_parts.append("关键信息: " + ", ".join(entity_summary))
        
        # 添加最近对话
        if recent_messages:
            message_summary = []
            for msg in recent_messages[-3:]:  # 最近3条消息
                direction = "用户" if msg["direction"] == "inbound" else "客服"
                content = msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                message_summary.append(f"{direction}: {content}")
            
            summary_parts.append("最近对话:\n" + "\n".join(message_summary))
        
        return "\n".join(summary_parts)
    
    def create_default_context(self, session_id: str) -> Dict[str, Any]:
        """创建默认上下文"""
        return {
            "session_id": session_id,
            "user_id": None,
            "current_intent": None,
            "intent_confidence": 0.0,
            "conversation_history": [],
            "entities": {},
            "state": "greeting",
            "message_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "intent_history": [],
            "state_history": []
        }
    
    async def _save_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """保存上下文到Redis"""
        redis = await self._get_redis()
        context_key = f"context:{session_id}"
        
        try:
            await redis.setex(
                context_key,
                self.context_ttl,
                json.dumps(context, ensure_ascii=False)
            )
        except Exception as e:
            print(f"Error saving context for {session_id}: {e}")
    
    def _cleanup_history(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """清理历史记录"""
        # 清理对话历史
        history = context.get("conversation_history", [])
        if len(history) > self.max_history_length:
            context["conversation_history"] = history[-self.max_history_length:]
        
        # 检查上下文大小
        context_size = len(json.dumps(context, ensure_ascii=False))
        if context_size > self.max_context_size:
            # 如果太大，清理一些历史记录
            history = context["conversation_history"]
            if len(history) > 5:
                context["conversation_history"] = history[-5:]
        
        return context
    
    async def clear_context(self, session_id: str) -> bool:
        """清除上下文"""
        redis = await self._get_redis()
        context_key = f"context:{session_id}"
        
        try:
            await redis.delete(context_key)
            return True
        except Exception as e:
            print(f"Error clearing context for {session_id}: {e}")
            return False
    
    async def get_context_stats(self, session_id: str) -> Dict[str, Any]:
        """获取上下文统计信息"""
        context = await self.get_context(session_id)
        
        return {
            "session_id": session_id,
            "message_count": context.get("message_count", 0),
            "current_intent": context.get("current_intent"),
            "current_state": context.get("state"),
            "entity_count": sum(len(values) for values in context.get("entities", {}).values()),
            "conversation_duration": self._calculate_duration(context),
            "created_at": context.get("created_at"),
            "last_updated": context.get("last_updated")
        }
    
    def _calculate_duration(self, context: Dict[str, Any]) -> int:
        """计算对话持续时间（秒）"""
        created_at = context.get("created_at")
        last_updated = context.get("last_updated")
        
        if created_at and last_updated:
            try:
                created_dt = datetime.fromisoformat(created_at)
                updated_dt = datetime.fromisoformat(last_updated)
                duration = int((updated_dt - created_dt).total_seconds())
                return duration
            except:
                pass
        
        return 0
    
    async def get_all_active_sessions(self) -> List[str]:
        """获取所有活跃会话ID"""
        redis = await self._get_redis()
        
        try:
            pattern = "context:*"
            keys = await redis.keys(pattern)
            session_ids = [key.replace("context:", "") for key in keys]
            return session_ids
        except Exception as e:
            print(f"Error getting active sessions: {e}")
            return []