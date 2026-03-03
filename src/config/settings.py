"""
系统配置文件
"""
import os
from typing import Optional
from pydantic import BaseSettings, Field


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="password", env="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="ai_companion", env="POSTGRES_DB")
    
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class PlatformSettings(BaseSettings):
    """平台接入配置"""
    # 抖店平台
    douyin_app_key: str = Field(default="", env="DOUYIN_APP_KEY")
    douyin_app_secret: str = Field(default="", env="DOUYIN_APP_SECRET")
    douyin_shop_id: str = Field(default="", env="DOUYIN_SHOP_ID")
    
    # 千帆客服工作台
    qianfan_app_key: str = Field(default="", env="QIANFAN_APP_KEY")
    qianfan_app_secret: str = Field(default="", env="QIANFAN_APP_SECRET")
    
    # Webhook配置
    webhook_secret: str = Field(default="your-webhook-secret", env="WEBHOOK_SECRET")


class AISettings(BaseSettings):
    """AI模型配置"""
    # OpenAI配置
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    
    # 向量模型配置
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    vector_dimension: int = Field(default=384, env="VECTOR_DIMENSION")
    
    # 意图识别模型
    intent_model: str = Field(default="bert-base-chinese", env="INTENT_MODEL")
    
    # 情感分析模型
    emotion_model: str = Field(default="bert-base-chinese", env="EMOTION_MODEL")


class VectorStoreSettings(BaseSettings):
    """向量数据库配置"""
    vector_store_type: str = Field(default="chroma", env="VECTOR_STORE_TYPE")  # chroma, qdrant
    
    # Chroma配置
    chroma_host: str = Field(default="localhost", env="CHROMA_HOST")
    chroma_port: int = Field(default=8000, env="CHROMA_PORT")
    
    # Qdrant配置
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")


class SecuritySettings(BaseSettings):
    """安全配置"""
    secret_key: str = Field(default="your-secret-key-change-this", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # CORS配置
    cors_origins: list = Field(default=["*"], env="CORS_ORIGINS")


class LogSettings(BaseSettings):
    """日志配置"""
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")


class Settings(BaseSettings):
    """主配置类"""
    # 应用配置
    app_name: str = Field(default="AI Companion", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # 子配置
    database: DatabaseSettings = DatabaseSettings()
    platform: PlatformSettings = PlatformSettings()
    ai: AISettings = AISettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    security: SecuritySettings = SecuritySettings()
    log: LogSettings = LogSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()