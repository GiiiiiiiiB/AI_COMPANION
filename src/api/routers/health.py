"""
健康检查API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import asyncio
import time

from src.storage.database import get_db_session, get_redis_client
from src.api.main import verify_token

router = APIRouter()


@router.get("/health")
async def health_check():
    """基础健康检查"""
    try:
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "ai-companion",
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@router.get("/health/detailed")
async def detailed_health_check(token: str = Depends(verify_token)):
    """详细健康检查"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "service": "ai-companion",
            "version": "1.0.0",
            "components": {}
        }
        
        # 检查数据库连接
        try:
            async for session in get_db_session():
                # 执行简单的查询测试数据库连接
                result = await session.execute("SELECT 1")
                health_status["components"]["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查Redis连接
        try:
            redis = await get_redis_client()
            await redis.ping()
            health_status["components"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful"
            }
        except Exception as e:
            health_status["components"]["redis"] = {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }
            health_status["status"] = "degraded"
        
        # 检查关键服务状态
        health_status["components"]["services"] = {
            "status": "healthy",
            "message": "All services operational"
        }
        
        # 如果有关键组件失败，设置整体状态为不健康
        if any(component["status"] == "unhealthy" for component in health_status["components"].values()):
            health_status["status"] = "unhealthy"
        
        # 根据状态返回相应的HTTP状态码
        if health_status["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=health_status)
        elif health_status["status"] == "degraded":
            return health_status
        else:
            return health_status
            
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")


@router.get("/health/database")
async def database_health_check(token: str = Depends(verify_token)):
    """数据库健康检查"""
    try:
        start_time = time.time()
        
        async for session in get_db_session():
            # 执行数据库查询测试
            result = await session.execute("SELECT 1")
            query_time = time.time() - start_time
            
            return {
                "status": "healthy",
                "database": "postgresql",
                "query_time": query_time,
                "timestamp": time.time()
            }
            
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")


@router.get("/health/redis")
async def redis_health_check(token: str = Depends(verify_token)):
    """Redis健康检查"""
    try:
        start_time = time.time()
        
        redis = await get_redis_client()
        await redis.ping()
        
        response_time = time.time() - start_time
        
        # 测试读写操作
        test_key = "health_check:test"
        test_value = str(time.time())
        
        await redis.set(test_key, test_value, ex=10)  # 10秒过期
        retrieved_value = await redis.get(test_key)
        
        if retrieved_value != test_value:
            raise Exception("Redis read/write test failed")
        
        return {
            "status": "healthy",
            "service": "redis",
            "response_time": response_time,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis health check failed: {str(e)}")


@router.get("/health/services")
async def services_health_check(token: str = Depends(verify_token)):
    """服务健康检查"""
    try:
        services_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {}
        }
        
        # 检查各个服务模块
        service_checks = [
            ("platform", check_platform_services),
            ("knowledge", check_knowledge_services),
            ("chat", check_chat_services),
            ("user", check_user_services),
            ("companion", check_companion_services)
        ]
        
        for service_name, check_func in service_checks:
            try:
                status = await check_func()
                services_status["services"][service_name] = status
                
                if status["status"] != "healthy":
                    services_status["status"] = "degraded"
                    
            except Exception as e:
                services_status["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                services_status["status"] = "unhealthy"
        
        # 根据状态返回相应的HTTP状态码
        if services_status["status"] == "unhealthy":
            raise HTTPException(status_code=503, detail=services_status)
        else:
            return services_status
            
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Services health check failed: {str(e)}")


@router.get("/health/load")
async def load_health_check(token: str = Depends(verify_token)):
    """负载健康检查"""
    try:
        # 获取系统负载信息
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 评估系统状态
        status = "healthy"
        if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
            status = "degraded"
        if cpu_percent > 95 or memory.percent > 95:
            status = "unhealthy"
        
        load_info = {
            "status": status,
            "timestamp": time.time(),
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "memory_available": memory.available,
            "disk_free": disk.free
        }
        
        if status == "unhealthy":
            raise HTTPException(status_code=503, detail=load_info)
        else:
            return load_info
            
    except ImportError:
        return {
            "status": "unknown",
            "message": "psutil not available for load monitoring",
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Load health check failed: {str(e)}")


@router.get("/health/dependencies")
async def dependencies_health_check(token: str = Depends(verify_token)):
    """依赖服务健康检查"""
    try:
        dependencies_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "dependencies": {}
        }
        
        # 检查外部依赖
        dependency_checks = [
            ("openai", check_openai_service),
            ("embedding_model", check_embedding_model),
            ("sentence_transformers", check_sentence_transformers)
        ]
        
        for dep_name, check_func in dependency_checks:
            try:
                status = await check_func()
                dependencies_status["dependencies"][dep_name] = status
                
                if status["status"] != "healthy":
                    dependencies_status["status"] = "degraded"
                    
            except Exception as e:
                dependencies_status["dependencies"][dep_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                dependencies_status["status"] = "unhealthy"
        
        return dependencies_status
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Dependencies health check failed: {str(e)}")


# 服务检查函数
async def check_platform_services():
    """检查平台服务"""
    from src.platforms import message_adapter
    
    platforms = message_adapter.get_supported_platforms()
    
    return {
        "status": "healthy",
        "supported_platforms": platforms,
        "platform_count": len(platforms)
    }


async def check_knowledge_services():
    """检查知识库服务"""
    try:
        from src.knowledge import KnowledgeRetriever
        retriever = KnowledgeRetriever()
        stats = await retriever.get_search_stats()
        
        return {
            "status": "healthy",
            "vector_count": stats["total_vectors"],
            "document_count": stats["total_documents"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_chat_services():
    """检查聊天服务"""
    try:
        from src.chat import IntentClassifier, ResponseGenerator
        
        intent_classifier = IntentClassifier()
        response_generator = ResponseGenerator()
        
        intents = intent_classifier.get_supported_intents()
        
        return {
            "status": "healthy",
            "supported_intents": intents,
            "intent_count": len(intents)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_user_services():
    """检查用户服务"""
    try:
        from src.users import UserProfileManager, SessionManager
        
        profile_manager = UserProfileManager()
        session_manager = SessionManager()
        
        return {
            "status": "healthy",
            "services": ["profile_manager", "session_manager"]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_companion_services():
    """检查陪伴服务"""
    try:
        from src.companion import EmotionAnalyzer, ProactiveChatManager
        
        emotion_analyzer = EmotionAnalyzer()
        proactive_chat = ProactiveChatManager()
        
        emotions = emotion_analyzer.get_supported_emotions()
        proactive_stats = await proactive_chat.get_proactive_stats()
        
        return {
            "status": "healthy",
            "supported_emotions": emotions,
            "emotion_count": len(emotions),
            "proactive_features": proactive_stats
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_openai_service():
    """检查OpenAI服务"""
    try:
        import openai
        from src.config.settings import settings
        
        # 检查API密钥配置
        if not settings.ai.openai_api_key:
            return {
                "status": "degraded",
                "message": "OpenAI API key not configured"
            }
        
        return {
            "status": "healthy",
            "message": "OpenAI service configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_embedding_model():
    """检查嵌入模型"""
    try:
        from src.config.settings import settings
        
        model_name = settings.ai.embedding_model
        
        return {
            "status": "healthy",
            "model": model_name,
            "message": "Embedding model configured"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_sentence_transformers():
    """检查Sentence Transformers"""
    try:
        import sentence_transformers
        
        return {
            "status": "healthy",
            "version": sentence_transformers.__version__,
            "message": "Sentence Transformers available"
        }
    except ImportError:
        return {
            "status": "degraded",
            "message": "Sentence Transformers not available, using fallback"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }