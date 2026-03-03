"""
数据库模型定义
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, Boolean, DateTime, JSON, ARRAY, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    nickname = Column(String(128))
    avatar = Column(Text)
    gender = Column(String(8))
    location = Column(String(128))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    sessions = relationship("ChatSession", back_populates="user")
    messages = relationship("Message", back_populates="user")
    profile = relationship("UserProfile", back_populates="user", uselist=False)


class ChatSession(Base):
    """会话表"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    platform = Column(String(32), nullable=False)
    status = Column(String(32), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime)
    satisfaction_score = Column(Integer)
    escalated = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)
    
    # 关联
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    """消息表"""
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(64), unique=True, nullable=False, index=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.session_id"), nullable=False)
    user_id = Column(String(64), ForeignKey("users.user_id"), nullable=False)
    platform = Column(String(32), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(32), default="text")
    direction = Column(String(16), nullable=False)  # 'inbound' or 'outbound'
    intent = Column(String(64))
    emotion = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User", back_populates="messages")


class KnowledgeDocument(Base):
    """知识库文档表"""
    __tablename__ = "knowledge_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)
    filename = Column(String(256), nullable=False)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer)
    file_hash = Column(String(64))
    category = Column(String(128))
    tags = Column(ARRAY(String))
    content = Column(Text)
    status = Column(String(32), default="processing")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    vectors = relationship("KnowledgeVector", back_populates="document")


class KnowledgeVector(Base):
    """知识向量表"""
    __tablename__ = "knowledge_vectors"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    vector = Column(JSON)  # 存储向量数据
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    document = relationship("KnowledgeDocument", back_populates="vectors")


class UserProfile(Base):
    """用户画像表"""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), ForeignKey("users.user_id"), unique=True, nullable=False)
    platform = Column(String(32), nullable=False)
    basic_info = Column(JSON)
    behavior_profile = Column(JSON)
    preference_profile = Column(JSON)
    purchase_profile = Column(JSON)
    psychographic_profile = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    user = relationship("User", back_populates="profile")


class ConversationAnalytics(Base):
    """对话分析表"""
    __tablename__ = "conversation_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), nullable=False)
    platform = Column(String(32), nullable=False)
    intent_distribution = Column(JSON)
    emotion_distribution = Column(JSON)
    response_time_stats = Column(JSON)
    satisfaction_score = Column(Integer)
    message_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemMetrics(Base):
    """系统指标表"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(64), nullable=False)
    metric_value = Column(JSON)
    tags = Column(ARRAY(String))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)