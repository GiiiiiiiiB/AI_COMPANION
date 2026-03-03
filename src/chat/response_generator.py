"""
回复生成器
"""
import asyncio
import random
from typing import Dict, Any, List, Optional
import openai
from datetime import datetime

from src.config.settings import settings
from src.knowledge.retriever import KnowledgeRetriever


class ResponseGenerator:
    """回复生成器"""
    
    def __init__(self, llm_client=None, knowledge_retriever=None):
        self.llm = llm_client or openai.AsyncOpenAI(api_key=settings.ai.openai_api_key)
        self.knowledge = knowledge_retriever or KnowledgeRetriever()
        
        # 回复模板
        self.response_templates = {
            "greeting": [
                "您好！我是您的专属客服助手，有什么可以帮助您的吗？",
                "你好！欢迎咨询，我很乐意为您解答问题~",
                "您好！感谢您联系客服，请问有什么可以帮您的吗？",
                "哈喽！我是智能客服助手，有什么需要我帮忙的吗？"
            ],
            "goodbye": [
                "感谢您的咨询，祝您生活愉快，再见！",
                "很高兴能为您服务，如有其他问题随时联系，再见！",
                "感谢您的耐心，祝您购物愉快，再见！",
                "祝您一切顺利，期待再次为您服务，再见！"
            ],
            "thanks": [
                "不客气，这是我们应该做的！",
                "很高兴能帮助到您！",
                "不用谢，为您服务是我的荣幸~",
                "感谢您的认可，我们会继续努力提供更好的服务！"
            ],
            "apology": [
                "非常抱歉给您带来了不便，我们会立即处理这个问题。",
                "对不起，这是我们的疏忽，我们会尽快为您解决。",
                "很抱歉让您有这样的体验，我们会认真对待并改进。",
                "请接受我们的歉意，我们会尽全力弥补给您带来的困扰。"
            ],
            "waiting": [
                "请稍等，我为您查询一下相关信息。",
                "好的，让我为您查看一下具体情况。",
                "请稍候，我正在处理您的请求。",
                "马上为您查询，请稍等片刻~"
            ]
        }
        
        # 意图特定的提示模板
        self.intent_prompts = {
            "product_inquiry": """
            用户询问产品相关信息，请基于以下知识库内容提供专业回复：
            
            知识库信息：
            {knowledge}
            
            用户问题：{question}
            
            请提供准确、详细的产品信息回复，语气要友好专业。
            """,
            
            "order_query": """
            用户询问订单相关问题，请基于订单状态提供准确信息：
            
            用户问题：{question}
            当前上下文：{context}
            
            请提供订单查询、物流信息或相关帮助，语气要耐心细致。
            """,
            
            "complaint": """
            用户有投诉或不满情绪，需要特别关注和安抚：
            
            用户反馈：{question}
            情感分析：用户情绪较为{emotion}
            
            回复要点：
            1. 首先表达歉意和理解
            2. 承诺会认真处理
            3. 提供具体的解决方案或下一步行动
            4. 保持同理心和专业态度
            """,
            
            "praise": """
            用户表达满意或赞扬，需要恰当回应：
            
            用户反馈：{question}
            
            回复要点：
            1. 表达感谢
            2. 表示会继续努力
            3. 可以询问是否还有其他需要帮助的地方
            """
        }
    
    async def generate_response(self, message: str, context: Dict[str, Any]) -> str:
        """生成回复"""
        intent = context.get("current_intent", "unknown")
        confidence = context.get("intent_confidence", 0.0)
        
        # 1. 基于意图选择回复策略
        if intent in ["greeting", "goodbye", "thanks", "apology", "waiting"]:
            response = self.get_template_response(intent)
        
        # 2. 产品相关问题，检索知识库
        elif intent == "product_inquiry":
            response = await self.generate_knowledge_based_response(message, context)
        
        # 3. 订单相关问题
        elif intent == "order_query":
            response = await self.generate_order_response(message, context)
        
        # 4. 投诉处理
        elif intent == "complaint":
            response = await self.generate_complaint_response(message, context)
        
        # 5. 赞扬回应
        elif intent == "praise":
            response = await self.generate_praise_response(message, context)
        
        # 6. 其他情况使用LLM生成
        else:
            response = await self.generate_llm_response(message, context)
        
        # 7. 个性化处理
        response = await self.personalize_response(response, context)
        
        return response
    
    def get_template_response(self, intent: str) -> str:
        """获取模板回复"""
        templates = self.response_templates.get(intent, [])
        if templates:
            return random.choice(templates)
        return "您好，有什么可以帮助您的吗？"
    
    async def generate_knowledge_based_response(self, message: str, context: Dict[str, Any]) -> str:
        """基于知识库生成回复"""
        try:
            # 1. 检索相关知识
            knowledge_results = await self.knowledge.search(message, top_k=3)
            
            if not knowledge_results:
                return "很抱歉，我暂时没有找到相关产品信息，让我为您查询一下..."
            
            # 2. 构建知识库内容
            knowledge_text = self._format_knowledge_results(knowledge_results)
            
            # 3. 构建提示词
            prompt = self.intent_prompts["product_inquiry"].format(
                knowledge=knowledge_text,
                question=message
            )
            
            # 4. 调用LLM生成回复
            response = await self._call_llm(prompt)
            
            return response or "很抱歉，我暂时无法回答这个问题，建议您联系人工客服。"
            
        except Exception as e:
            print(f"Error generating knowledge-based response: {e}")
            return "很抱歉，我在查询产品信息时遇到了问题，请稍后再试。"
    
    async def generate_order_response(self, message: str, context: Dict[str, Any]) -> str:
        """生成订单相关回复"""
        try:
            # 获取上下文中的订单信息
            entities = context.get("entities", {})
            order_ids = entities.get("order_id", [])
            
            # 构建提示词
            context_summary = await self._get_context_summary(context)
            
            prompt = self.intent_prompts["order_query"].format(
                question=message,
                context=context_summary
            )
            
            # 调用LLM生成回复
            response = await self._call_llm(prompt)
            
            return response or "我理解您想了解订单信息，请提供订单号，我来为您查询。"
            
        except Exception as e:
            print(f"Error generating order response: {e}")
            return "很抱歉，我在处理订单查询时遇到了问题，请稍后再试。"
    
    async def generate_complaint_response(self, message: str, context: Dict[str, Any]) -> str:
        """生成投诉处理回复"""
        try:
            # 情感分析（简化版）
            emotion = "负面"  # 可以根据实际情感分析结果调整
            
            # 构建提示词
            prompt = self.intent_prompts["complaint"].format(
                question=message,
                emotion=emotion
            )
            
            # 调用LLM生成回复
            response = await self._call_llm(prompt)
            
            return response or "非常抱歉给您带来了不愉快的体验，我们会认真对待您的反馈并尽快处理。"
            
        except Exception as e:
            print(f"Error generating complaint response: {e}")
            return "非常抱歉让您有这样的体验，我们会立即处理您的问题。"
    
    async def generate_praise_response(self, message: str, context: Dict[str, Any]) -> str:
        """生成赞扬回应"""
        try:
            # 构建提示词
            prompt = self.intent_prompts["praise"].format(question=message)
            
            # 调用LLM生成回复
            response = await self._call_llm(prompt)
            
            return response or "非常感谢您的认可！我们会继续努力为您提供更好的服务。"
            
        except Exception as e:
            print(f"Error generating praise response: {e}")
            return "感谢您的支持和鼓励，这是对我们最大的认可！"
    
    async def generate_llm_response(self, message: str, context: Dict[str, Any]) -> str:
        """使用LLM生成通用回复"""
        try:
            # 构建通用提示词
            context_summary = await self._get_context_summary(context)
            
            prompt = f"""
            你是一个专业的客服助手，请基于以下上下文信息回复用户：
            
            用户消息：{message}
            对话上下文：{context_summary}
            
            回复要求：
            1. 语气要友好、专业、有耐心
            2. 回复要简洁明了，避免冗长
            3. 如果无法回答，要诚实说明并建议联系人工客服
            4. 使用中文回复
            
            请提供合适的回复：
            """
            
            response = await self._call_llm(prompt)
            return response or "您好，我是智能客服助手，有什么可以帮助您的吗？"
            
        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return "您好，我是智能客服助手，有什么可以帮助您的吗？"
    
    async def personalize_response(self, response: str, context: Dict[str, Any]) -> str:
        """个性化回复"""
        # 获取用户画像信息（如果有）
        user_profile = context.get("user_profile", {})
        
        # 根据用户偏好调整回复
        if user_profile.get("communication_style") == "formal":
            # 正式风格
            response = response.replace("~", "。")
            response = response.replace("哈", "")
            response = response.replace("哦", "")
        elif user_profile.get("communication_style") == "friendly":
            # 友好风格，可以添加表情符号
            if not any(emoji in response for emoji in ["~", "😊", "👍"]):
                response += "~"
        
        # 根据时间添加问候
        current_hour = datetime.now().hour
        if current_hour < 12:
            greeting = "早上好"
        elif current_hour < 18:
            greeting = "下午好"
        else:
            greeting = "晚上好"
        
        # 如果回复以问候开头，替换为时间相关的问候
        if response.startswith(("您好", "你好", "哈喽")):
            response = greeting + response[2:]
        
        return response
    
    def _format_knowledge_results(self, knowledge_results: List[Dict[str, Any]]) -> str:
        """格式化知识库搜索结果"""
        if not knowledge_results:
            return "暂无相关信息"
        
        formatted_parts = []
        for i, result in enumerate(knowledge_results, 1):
            content = result.get("content", "")
            metadata = result.get("metadata", {})
            score = result.get("score", 0)
            
            part = f"信息{i}（相关度：{score:.2f}）:\n{content[:200]}..."
            if metadata.get("category"):
                part += f"\n分类：{metadata['category']}"
            if metadata.get("tags"):
                part += f"\n标签：{', '.join(metadata['tags'])}"
            
            formatted_parts.append(part)
        
        return "\n\n".join(formatted_parts)
    
    async def _get_context_summary(self, context: Dict[str, Any]) -> str:
        """获取上下文摘要"""
        parts = []
        
        # 当前意图
        current_intent = context.get("current_intent")
        if current_intent:
            parts.append(f"当前意图：{current_intent}")
        
        # 关键实体
        entities = context.get("entities", {})
        if entities:
            entity_info = []
            for entity_type, entity_list in entities.items():
                if entity_list:
                    latest = entity_list[-1]
                    entity_info.append(f"{entity_type}：{latest['value']}")
            if entity_info:
                parts.append("关键信息：" + "，".join(entity_info))
        
        # 对话状态
        state = context.get("state")
        if state:
            parts.append(f"对话状态：{state}")
        
        return "；".join(parts) if parts else "无相关上下文信息"
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM生成回复"""
        try:
            response = await self.llm.chat.completions.create(
                model=settings.ai.openai_model,
                messages=[
                    {"role": "system", "content": "你是一个专业的客服助手，请提供准确、友好、有帮助的回复。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return None
    
    def add_response_template(self, intent: str, templates: List[str]):
        """添加回复模板"""
        if intent not in self.response_templates:
            self.response_templates[intent] = []
        
        self.response_templates[intent].extend(templates)
        # 去重
        self.response_templates[intent] = list(set(self.response_templates[intent]))
    
    def get_response_templates(self, intent: str) -> List[str]:
        """获取回复模板"""
        return self.response_templates.get(intent, [])