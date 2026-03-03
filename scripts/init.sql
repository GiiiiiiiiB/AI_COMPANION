-- AI Companion 数据库初始化脚本
-- 创建数据库和基本表结构

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    platform VARCHAR(32) NOT NULL,
    nickname VARCHAR(128),
    avatar TEXT,
    gender VARCHAR(8),
    location VARCHAR(128),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    status VARCHAR(32) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity TIMESTAMP,
    satisfaction_score INTEGER,
    escalated BOOLEAN DEFAULT FALSE,
    message_count INTEGER DEFAULT 0,
    metadata JSONB,
    source VARCHAR(64),
    priority VARCHAR(32) DEFAULT 'normal',
    assigned_agent VARCHAR(128),
    tags TEXT[],
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    message_id VARCHAR(64) UNIQUE NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(32) DEFAULT 'text',
    direction VARCHAR(16) NOT NULL, -- 'inbound' or 'outbound'
    intent VARCHAR(64),
    emotion VARCHAR(32),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 知识库文档表
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(64) UNIQUE NOT NULL,
    filename VARCHAR(256) NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    file_hash VARCHAR(64),
    category VARCHAR(128),
    tags TEXT[],
    content TEXT,
    status VARCHAR(32) DEFAULT 'processing',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识向量表
CREATE TABLE IF NOT EXISTS knowledge_vectors (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    vector vector(768), -- 向量维度根据模型调整
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES knowledge_documents(id)
);

-- 用户画像表
CREATE TABLE IF NOT EXISTS user_profiles (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(64) UNIQUE NOT NULL,
    platform VARCHAR(32) NOT NULL,
    basic_info JSONB,
    behavior_profile JSONB,
    preference_profile JSONB,
    purchase_profile JSONB,
    psychographic_profile JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- 对话分析表
CREATE TABLE IF NOT EXISTS conversation_analytics (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    intent_distribution JSONB,
    emotion_distribution JSONB,
    response_time_stats JSONB,
    satisfaction_score INTEGER,
    message_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id)
);

-- 系统指标表
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(64) NOT NULL,
    metric_value JSONB,
    tags TEXT[],
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_users_platform ON users(platform);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_platform ON chat_sessions(platform);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_status ON chat_sessions(status);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_created_at ON chat_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_messages_intent ON messages(intent);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_document_id ON knowledge_documents(document_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_category ON knowledge_documents(category);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_status ON knowledge_documents(status);
CREATE INDEX IF NOT EXISTS idx_knowledge_vectors_document_id ON knowledge_vectors(document_id);
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_session_id ON conversation_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_analytics_created_at ON conversation_analytics(created_at);
CREATE INDEX IF NOT EXISTS idx_system_metrics_metric_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_timestamp ON system_metrics(timestamp);

-- 创建触发器函数来更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_documents_updated_at BEFORE UPDATE ON knowledge_documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据（可选）
-- 用户数据
INSERT INTO users (user_id, platform, nickname, gender, location) VALUES
('user_001', 'douyin', '张三', 'male', '北京'),
('user_002', 'qianfan', '李四', 'female', '上海'),
('user_003', 'douyin', '王五', 'male', '广州')
ON CONFLICT (user_id) DO NOTHING;

-- 用户画像数据
INSERT INTO user_profiles (user_id, platform, basic_info, behavior_profile, preference_profile, purchase_profile, psychographic_profile) VALUES
('user_001', 'douyin', 
 '{"nickname": "张三", "gender": "male", "location": "北京", "age_group": "25-35"}',
 '{"total_interactions": 10, "activity_level": "medium", "engagement_score": 75.0}',
 '{"communication_style": "friendly", "price_sensitivity": "medium", "interested_categories": ["电子产品", "服装"]}',
 '{"total_orders": 5, "total_spent": 2500.0, "customer_segment": "regular"}',
 '{"personality_traits": ["友好", "理性"], "risk_tolerance": "medium"}'
),
('user_002', 'qianfan',
 '{"nickname": "李四", "gender": "female", "location": "上海", "age_group": "25-35"}',
 '{"total_interactions": 20, "activity_level": "high", "engagement_score": 85.0}',
 '{"communication_style": "formal", "price_sensitivity": "low", "interested_categories": ["化妆品", "服装"]}',
 '{"total_orders": 15, "total_spent": 8000.0, "customer_segment": "vip"}',
 '{"personality_traits": ["优雅", "品质导向"], "risk_tolerance": "high"}'
)
ON CONFLICT (user_id) DO NOTHING;

-- 知识库文档数据
INSERT INTO knowledge_documents (document_id, filename, file_path, category, content, status) VALUES
('doc_001', '产品手册.pdf', '/uploads/doc_001.pdf', '产品说明', '这是产品手册的内容...', 'vectorized'),
('doc_002', '常见问题.md', '/uploads/doc_002.md', 'FAQ', '常见问题和解答...', 'vectorized'),
('doc_003', '退货政策.txt', '/uploads/doc_003.txt', '售后政策', '退货和退款政策说明...', 'vectorized')
ON CONFLICT (document_id) DO NOTHING;

-- 系统指标数据（示例）
INSERT INTO system_metrics (metric_name, metric_value, tags) VALUES
('api_requests_total', '{"count": 1000, "status": "success"}', '{"endpoint": "/api/v1/chat", "method": "POST"}'),
('response_time_avg', '{"value": 0.5, "unit": "seconds"}', '{"service": "chat", "percentile": "p50"}'),
('error_rate', '{"value": 0.01, "unit": "percentage"}', '{"service": "api", "time_window": "1h"}')
ON CONFLICT DO NOTHING;

-- 创建视图以方便查询
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT 
    u.user_id,
    u.platform,
    u.nickname,
    COUNT(DISTINCT cs.session_id) as total_sessions,
    COUNT(m.id) as total_messages,
    AVG(cs.satisfaction_score) as avg_satisfaction,
    MAX(cs.created_at) as last_session_date
FROM users u
LEFT JOIN chat_sessions cs ON u.user_id = cs.user_id
LEFT JOIN messages m ON cs.session_id = m.session_id
GROUP BY u.user_id, u.platform, u.nickname;

CREATE OR REPLACE VIEW daily_conversation_stats AS
SELECT 
    DATE(cs.created_at) as date,
    COUNT(DISTINCT cs.session_id) as total_sessions,
    COUNT(m.id) as total_messages,
    AVG(cs.satisfaction_score) as avg_satisfaction,
    COUNT(CASE WHEN cs.escalated = true THEN 1 END) as escalated_sessions
FROM chat_sessions cs
LEFT JOIN messages m ON cs.session_id = m.session_id
GROUP BY DATE(cs.created_at)
ORDER BY date DESC;