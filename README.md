# AI Companion - 智能陪伴机器人客服系统

一个基于大语言模型的智能陪伴机器人客服系统，支持多平台接入、智能知识库管理、情感分析和主动对话功能。

## 🌟 功能特性

### 🤖 多平台接入
- **抖店平台**: 支持抖音电商平台的客服接入
- **千帆客服工作台**: 支持百度千帆客服工作台接入
- **统一消息适配**: 标准化不同平台的消息格式
- **Webhook支持**: 实时接收平台消息推送

### 📚 智能知识库
- **文档管理**: 支持PDF、Word、Markdown等多种格式文档上传
- **智能向量化**: 自动文档解析和向量化处理
- **混合搜索**: 结合向量搜索和关键词搜索
- **知识检索**: 智能匹配用户问题与知识库内容

### 💬 对话引擎
- **意图识别**: 基于BERT模型的智能意图分类
- **上下文管理**: 维护对话历史和用户状态
- **回复生成**: 基于知识库和LLM的智能回复生成
- **多轮对话**: 支持复杂的对话流程管理

### 👤 用户管理
- **用户画像**: 多维度用户画像构建
- **行为分析**: 用户行为数据收集和分析
- **会话管理**: 会话生命周期管理
- **个性化服务**: 基于用户偏好的个性化回复

### 😊 智能陪伴
- **情感分析**: 实时分析用户情感状态
- **主动对话**: 基于用户行为的主动关怀
- **情绪安抚**: 针对负面情绪的智能安抚
- **特殊时机**: 节假日、生日等特殊时机主动问候

### 📊 数据分析
- **实时监控**: 系统性能和业务指标实时监控
- **对话分析**: 对话质量、意图分布、情感趋势分析
- **用户分析**: 用户行为、满意度、留存率分析
- **性能分析**: 响应时间、错误率、系统负载分析

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        API Gateway                          │
├─────────────────────────────────────────────────────────────┤
│  Platform  │  Knowledge  │    Chat     │    User    │Companion│
│   Module   │   Module    │   Module    │   Module   │ Module  │
├─────────────────────────────────────────────────────────────┤
│                    Service Layer                           │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL │    Redis    │   Chroma    │   OpenAI   │  Models │
│  (Database) │   (Cache)   │(Vector DB)  │   (LLM)    │  (ML)   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- ChromaDB

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-repo/ai-companion.git
cd ai-companion
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库、API密钥等信息
```

5. **初始化数据库**
```bash
# 创建数据库
createdb ai_companion

# 运行数据库迁移
alembic upgrade head
```

6. **启动服务**
```bash
python main.py
```

### Docker部署

1. **使用Docker Compose启动**
```bash
docker-compose up -d
```

2. **查看服务状态**
```bash
docker-compose ps
```

3. **查看日志**
```bash
docker-compose logs -f app
```

## 📖 API文档

启动服务后，访问 `http://localhost:8000/docs` 查看完整的API文档。

### 主要API端点

#### 平台接入
- `POST /api/v1/webhook/{platform}` - 接收平台消息
- `POST /api/v1/platforms/{platform}/send` - 发送平台消息
- `GET /api/v1/platforms` - 获取支持的平台列表

#### 知识库管理
- `POST /api/v1/knowledge/documents` - 上传文档
- `GET /api/v1/knowledge/search` - 搜索知识库
- `POST /api/v1/knowledge/documents/{id}/vectorize` - 文档向量化

#### 聊天对话
- `POST /api/v1/chat/message` - 处理聊天消息
- `POST /api/v1/chat/session` - 创建聊天会话
- `GET /api/v1/chat/session/{id}` - 获取会话信息

#### 用户管理
- `GET /api/v1/users/{user_id}` - 获取用户画像
- `PUT /api/v1/users/{user_id}/behavior` - 更新用户行为
- `GET /api/v1/users/{user_id}/analytics` - 获取用户分析

#### 数据分析
- `GET /api/v1/analytics/dashboard` - 仪表板统计
- `GET /api/v1/analytics/conversations` - 对话分析
- `GET /api/v1/analytics/realtime` - 实时监控

#### 健康检查
- `GET /api/v1/health` - 基础健康检查
- `GET /api/v1/health/detailed` - 详细健康检查
- `GET /api/v1/health/services` - 服务健康检查

## 🔧 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `POSTGRES_HOST` | PostgreSQL主机 | localhost |
| `POSTGRES_PORT` | PostgreSQL端口 | 5432 |
| `REDIS_HOST` | Redis主机 | localhost |
| `REDIS_PORT` | Redis端口 | 6379 |
| `OPENAI_API_KEY` | OpenAI API密钥 | - |
| `DOUYIN_APP_KEY` | 抖店应用密钥 | - |
| `QIANFAN_APP_KEY` | 千帆应用密钥 | - |

### 核心配置

所有配置都在 `src/config/settings.py` 中定义，可以通过环境变量覆盖。

## 🧪 开发指南

### 项目结构

```
ai_companion/
├── src/                    # 源代码
│   ├── api/               # API接口层
│   ├── chat/              # 对话引擎
│   ├── companion/         # 智能陪伴
│   ├── config/            # 配置管理
│   ├── knowledge/         # 知识库管理
│   ├── platforms/         # 平台接入
│   ├── storage/           # 数据存储
│   └── users/             # 用户管理
├── scripts/               # 脚本文件
├── tests/                 # 测试文件
├── requirements.txt       # Python依赖
├── docker-compose.yml     # Docker配置
└── main.py               # 主入口
```

### 开发模式

1. **启动开发服务器**
```bash
python main.py --reload --log-level debug
```

2. **运行测试**
```bash
pytest tests/
```

3. **代码格式化**
```bash
black src/
```

4. **类型检查**
```bash
mypy src/
```

### 添加新平台

1. 在 `src/platforms/` 目录下创建新的平台模块
2. 实现平台接入类，继承基础接口
3. 在统一消息适配器中注册新平台
4. 添加相应的API路由

### 扩展知识库

1. 支持新的文档格式：修改 `DocumentManager` 类
2. 优化搜索算法：调整 `KnowledgeRetriever` 参数
3. 添加新的向量化模型：更新 `KnowledgeVectorizer`

## 📊 性能优化

### 数据库优化
- 使用连接池管理数据库连接
- 为常用查询字段添加索引
- 定期分析和优化查询性能

### 缓存策略
- Redis缓存用户会话和上下文
- 向量搜索结果缓存
- API响应缓存

### 异步处理
- 使用async/await处理IO密集型操作
- 消息队列处理耗时任务
- 并发处理多个用户请求

## 🔒 安全考虑

### 认证授权
- API访问令牌验证
- 平台Webhook签名验证
- 用户数据访问控制

### 数据保护
- 敏感数据加密存储
- 用户隐私信息脱敏
- 数据传输加密

### 安全监控
- 异常访问检测
- 恶意请求过滤
- 安全日志记录

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如遇到问题，请：

1. 查看文档和FAQ
2. 在GitHub Issues中搜索类似问题
3. 创建新的Issue描述问题

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代、快速的Web框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL工具包和ORM
- [Redis](https://redis.io/) - 内存数据结构存储
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [OpenAI](https://openai.com/) - 大语言模型API
- [Hugging Face](https://huggingface.co/) - 机器学习模型库

---

**Made with ❤️ by AI Companion Team**