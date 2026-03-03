"""
会话管理器
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.storage.database import get_db_session, get_redis_client
from src.storage.models import ChatSession, Message


class SessionManager:
    """会话管理器"""
    
    def __init__(self, session_ttl: int = 86400):
        self.session_ttl = session_ttl  # 24小时过期
        self.max_sessions_per_user = 10  # 每个用户最大会话数
        self.redis_client = None
    
    async def _get_redis(self):
        """获取Redis客户端"""
        if self.redis_client is None:
            self.redis_client = await get_redis_client()
        return self.redis_client
    
    async def create_session(self, user_id: str, platform: str, **kwargs) -> Dict[str, Any]:
        """创建新会话"""
        session_id = self._generate_session_id()
        
        # 检查用户会话数量限制
        active_sessions = await self.get_user_active_sessions(user_id)
        if len(active_sessions) >= self.max_sessions_per_user:
            # 关闭最老的会话
            oldest_session = min(active_sessions, key=lambda x: x["created_at"])
            await self.close_session(oldest_session["session_id"], "会话数量限制")
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "platform": platform,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "message_count": 0,
            "escalated": False,
            "satisfaction_score": None,
            "metadata": kwargs.get("metadata", {}),
            "source": kwargs.get("source", "unknown"),
            "priority": kwargs.get("priority", "normal"),  # low, normal, high, urgent
            "assigned_agent": kwargs.get("assigned_agent"),
            "tags": kwargs.get("tags", [])
        }
        
        # 保存到数据库（历史记录）
        async for session in get_db_session():
            db_session = ChatSession(
                session_id=session_id,
                user_id=user_id,
                platform=platform,
                status="active",
                satisfaction_score=None,
                escalated=False,
                message_count=0,
                metadata=session_data["metadata"],
                source=session_data["source"],
                priority=session_data["priority"],
                assigned_agent=session_data["assigned_agent"],
                tags=session_data["tags"]
            )
            session.add(db_session)
            await session.commit()
        
        # 保存到Redis（活跃会话）
        redis = await self._get_redis()
        session_key = f"session:active:{session_id}"
        await redis.setex(
            session_key,
            self.session_ttl,
            json.dumps(session_data, ensure_ascii=False)
        )
        
        # 添加到用户会话列表
        user_sessions_key = f"user:sessions:{user_id}"
        await redis.sadd(user_sessions_key, session_id)
        await redis.expire(user_sessions_key, self.session_ttl)
        
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话信息"""
        # 先从Redis获取活跃会话
        redis = await self._get_redis()
        session_key = f"session:active:{session_id}"
        
        try:
            session_data = await redis.get(session_key)
            if session_data:
                return json.loads(session_data)
        except Exception as e:
            print(f"Error getting session from Redis: {e}")
        
        # 如果Redis中没有，从数据库获取
        async for session in get_db_session():
            db_session = await session.query(ChatSession).filter(
                ChatSession.session_id == session_id
            ).first()
            
            if db_session:
                return await self._session_to_dict(db_session)
            
            return None
    
    async def get_active_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的活跃会话"""
        # 获取用户的所有会话
        user_sessions = await self.get_user_active_sessions(user_id)
        
        if not user_sessions:
            return None
        
        # 返回最新的活跃会话
        return max(user_sessions, key=lambda x: x["last_activity"])
    
    async def get_user_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有活跃会话"""
        redis = await self._get_redis()
        user_sessions_key = f"user:sessions:{user_id}"
        
        try:
            session_ids = await redis.smembers(user_sessions_key)
            sessions = []
            
            for session_id in session_ids:
                session_data = await self.get_session(session_id)
                if session_data and session_data.get("status") == "active":
                    sessions.append(session_data)
            
            return sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []
    
    async def update_session_activity(self, session_id: str, message_count: int = 1) -> bool:
        """更新会话活动状态"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["last_activity"] = datetime.now().isoformat()
        session["message_count"] += message_count
        
        # 保存到Redis
        redis = await self._get_redis()
        session_key = f"session:active:{session_id}"
        
        try:
            await redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session, ensure_ascii=False)
            )
            
            # 更新数据库
            async for db_session in get_db_session():
                db_chat_session = await db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if db_chat_session:
                    db_chat_session.last_activity = datetime.fromisoformat(session["last_activity"])
                    db_chat_session.message_count = session["message_count"]
                    await db_session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error updating session activity: {e}")
            return False
    
    async def close_session(self, session_id: str, reason: str = "", satisfaction_score: int = None) -> bool:
        """关闭会话"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["status"] = "closed"
        session["ended_at"] = datetime.now().isoformat()
        session["close_reason"] = reason
        
        if satisfaction_score is not None:
            session["satisfaction_score"] = satisfaction_score
        
        # 从Redis删除活跃会话
        redis = await self._get_redis()
        session_key = f"session:active:{session_id}"
        user_sessions_key = f"user:sessions:{session['user_id']}"
        
        try:
            await redis.delete(session_key)
            await redis.srem(user_sessions_key, session_id)
            
            # 更新数据库
            async for db_session in get_db_session():
                db_chat_session = await db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if db_chat_session:
                    db_chat_session.status = "closed"
                    db_chat_session.ended_at = datetime.now()
                    db_chat_session.satisfaction_score = satisfaction_score
                    await db_session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error closing session: {e}")
            return False
    
    async def escalate_session(self, session_id: str, reason: str = "", agent_id: str = None) -> bool:
        """升级会话到人工客服"""
        session = await self.get_session(session_id)
        if not session:
            return False
        
        session["escalated"] = True
        session["escalation_reason"] = reason
        session["escalated_at"] = datetime.now().isoformat()
        session["assigned_agent"] = agent_id
        session["priority"] = "urgent"
        
        # 保存到Redis
        redis = await self._get_redis()
        session_key = f"session:active:{session_id}"
        
        try:
            await redis.setex(
                session_key,
                self.session_ttl,
                json.dumps(session, ensure_ascii=False)
            )
            
            # 更新数据库
            async for db_session in get_db_session():
                db_chat_session = await db_session.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                
                if db_chat_session:
                    db_chat_session.escalated = True
                    db_chat_session.assigned_agent = agent_id
                    db_chat_session.priority = "urgent"
                    await db_session.commit()
            
            return True
            
        except Exception as e:
            print(f"Error escalating session: {e}")
            return False
    
    async def add_message(self, session_id: str, message_data: Dict[str, Any]) -> bool:
        """添加消息到会话"""
        # 更新会话活动
        await self.update_session_activity(session_id)
        
        # 保存消息到数据库
        async for session in get_db_session():
            message = Message(
                message_id=message_data.get("message_id", str(uuid.uuid4())),
                session_id=session_id,
                user_id=message_data["user_id"],
                platform=message_data["platform"],
                content=message_data["content"],
                message_type=message_data.get("message_type", "text"),
                direction=message_data["direction"],  # inbound or outbound
                intent=message_data.get("intent"),
                emotion=message_data.get("emotion")
            )
            
            session.add(message)
            await session.commit()
        
        return True
    
    async def get_session_messages(self, session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取会话消息"""
        async for session in get_db_session():
            messages = await session.query(Message).filter(
                Message.session_id == session_id
            ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
            
            return [
                {
                    "message_id": msg.message_id,
                    "session_id": msg.session_id,
                    "user_id": msg.user_id,
                    "platform": msg.platform,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "direction": msg.direction,
                    "intent": msg.intent,
                    "emotion": msg.emotion,
                    "created_at": msg.created_at
                }
                for msg in messages
            ]
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计信息"""
        session = await self.get_session(session_id)
        if not session:
            return {}
        
        # 获取消息统计
        async for db_session in get_db_session():
            total_messages = await db_session.query(Message).filter(
                Message.session_id == session_id
            ).count()
            
            user_messages = await db_session.query(Message).filter(
                Message.session_id == session_id,
                Message.direction == "inbound"
            ).count()
            
            bot_messages = await db_session.query(Message).filter(
                Message.session_id == session_id,
                Message.direction == "outbound"
            ).count()
            
            # 获取意图分布
            from sqlalchemy import func
            intent_stats = await db_session.query(
                Message.intent,
                func.count(Message.id)
            ).filter(
                Message.session_id == session_id,
                Message.intent.isnot(None)
            ).group_by(Message.intent).all()
            
            intent_distribution = {intent: count for intent, count in intent_stats}
            
            return {
                "session_id": session_id,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "bot_messages": bot_messages,
                "intent_distribution": intent_distribution,
                "duration": self._calculate_session_duration(session),
                "satisfaction_score": session.get("satisfaction_score"),
                "escalated": session.get("escalated", False),
                "status": session.get("status")
            }
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return f"session_{uuid.uuid4().hex[:16]}"
    
    def _calculate_session_duration(self, session: Dict[str, Any]) -> int:
        """计算会话持续时间（秒）"""
        created_at = session.get("created_at")
        last_activity = session.get("last_activity")
        
        if created_at and last_activity:
            try:
                created_dt = datetime.fromisoformat(created_at)
                activity_dt = datetime.fromisoformat(last_activity)
                duration = int((activity_dt - created_dt).total_seconds())
                return duration
            except:
                pass
        
        return 0
    
    async def _session_to_dict(self, db_session: ChatSession) -> Dict[str, Any]:
        """将数据库会话对象转换为字典"""
        return {
            "session_id": db_session.session_id,
            "user_id": db_session.user_id,
            "platform": db_session.platform,
            "status": db_session.status,
            "created_at": db_session.created_at.isoformat(),
            "ended_at": db_session.ended_at.isoformat() if db_session.ended_at else None,
            "last_activity": db_session.last_activity.isoformat() if db_session.last_activity else None,
            "message_count": db_session.message_count,
            "satisfaction_score": db_session.satisfaction_score,
            "escalated": db_session.escalated,
            "metadata": db_session.metadata,
            "source": db_session.source,
            "priority": db_session.priority,
            "assigned_agent": db_session.assigned_agent,
            "tags": db_session.tags
        }
    
    async def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        redis = await self._get_redis()
        
        try:
            # 获取所有活跃会话
            pattern = "session:active:*"
            keys = await redis.keys(pattern)
            
            cleaned_count = 0
            
            for key in keys:
                try:
                    session_data = await redis.get(key)
                    if session_data:
                        session = json.loads(session_data)
                        
                        # 检查是否过期
                        last_activity = datetime.fromisoformat(session["last_activity"])
                        if datetime.now() - last_activity > timedelta(seconds=self.session_ttl):
                            # 关闭过期会话
                            session_id = session["session_id"]
                            await self.close_session(session_id, "会话过期")
                            cleaned_count += 1
                            
                except Exception as e:
                    print(f"Error processing session key {key}: {e}")
                    continue
            
            return cleaned_count
            
        except Exception as e:
            print(f"Error cleaning up expired sessions: {e}")
            return 0
    
    async def get_active_sessions_count(self) -> int:
        """获取活跃会话数量"""
        redis = await self._get_redis()
        
        try:
            pattern = "session:active:*"
            keys = await redis.keys(pattern)
            return len(keys)
            
        except Exception as e:
            print(f"Error getting active sessions count: {e}")
            return 0