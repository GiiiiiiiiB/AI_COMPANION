"""
主API应用
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

from src.config.settings import settings
from src.storage.database import init_database, close_database
from src.platforms import message_adapter
from src.knowledge import DocumentManager, KnowledgeRetriever
from src.chat import IntentClassifier, ContextManager, ResponseGenerator
from src.users import UserProfileManager, SessionManager
from src.companion import EmotionAnalyzer, ProactiveChatManager
from src.api.routers import (
    platform_router, knowledge_router, chat_router, 
    user_router, analytics_router, health_router
)

# 全局服务实例
services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    await startup()
    yield
    # 关闭时清理
    await shutdown()


async def startup():
    """启动初始化"""
    print("Starting AI Companion API...")
    
    # 初始化数据库
    await init_database()
    
    # 初始化服务
    services["document_manager"] = DocumentManager()
    services["knowledge_retriever"] = KnowledgeRetriever()
    services["intent_classifier"] = IntentClassifier()
    services["context_manager"] = ContextManager()
    services["response_generator"] = ResponseGenerator(
        knowledge_retriever=services["knowledge_retriever"]
    )
    services["user_profile_manager"] = UserProfileManager()
    services["session_manager"] = SessionManager()
    services["emotion_analyzer"] = EmotionAnalyzer()
    services["proactive_chat_manager"] = ProactiveChatManager(
        user_profile_manager=services["user_profile_manager"],
        emotion_analyzer=services["emotion_analyzer"]
    )
    
    print("AI Companion API started successfully!")


async def shutdown():
    """关闭清理"""
    print("Shutting down AI Companion API...")
    await close_database()
    print("AI Companion API shutdown complete!")


# 创建FastAPI应用
app = FastAPI(
    title="AI Companion API",
    description="智能陪伴机器人客服系统API",
    version=settings.app_version,
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全配置
security = HTTPBearer()


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证访问令牌"""
    # 这里可以实现JWT验证逻辑
    # 目前简化处理，只检查是否提供了令牌
    if not credentials.credentials:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return credentials.credentials


# 注册路由
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(platform_router, prefix="/api/v1", tags=["platform"])
app.include_router(knowledge_router, prefix="/api/v1", tags=["knowledge"])
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(user_router, prefix="/api/v1", tags=["user"])
app.include_router(analytics_router, prefix="/api/v1", tags=["analytics"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "AI Companion API",
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/api/v1/info")
async def get_api_info():
    """获取API信息"""
    return {
        "name": "AI Companion API",
        "version": settings.app_version,
        "description": "智能陪伴机器人客服系统",
        "features": [
            "多平台接入支持",
            "智能知识库管理",
            "自然语言对话",
            "用户画像分析",
            "情感分析",
            "主动对话"
        ],
        "supported_platforms": message_adapter.get_supported_platforms()
    }


# 获取服务实例的依赖函数
def get_document_manager():
    return services["document_manager"]


def get_knowledge_retriever():
    return services["knowledge_retriever"]


def get_intent_classifier():
    return services["intent_classifier"]


def get_context_manager():
    return services["context_manager"]


def get_response_generator():
    return services["response_generator"]


def get_user_profile_manager():
    return services["user_profile_manager"]


def get_session_manager():
    return services["session_manager"]


def get_emotion_analyzer():
    return services["emotion_analyzer"]


def get_proactive_chat_manager():
    return services["proactive_chat_manager"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )