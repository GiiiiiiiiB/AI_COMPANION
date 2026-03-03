"""
主动对话管理器
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.users.profile_manager import UserProfileManager
from src.companion.emotion_analyzer import EmotionAnalyzer
from src.chat.context_manager import ContextManager
from src.users.session_manager import SessionManager


class ProactiveChatManager:
    """主动对话管理器"""
    
    def __init__(self, user_profile_manager=None, emotion_analyzer=None, context_manager=None):
        self.user_profiles = user_profile_manager or UserProfileManager()
        self.emotion_analyzer = emotion_analyzer or EmotionAnalyzer()
        self.context_manager = context_manager or ContextManager()
        self.session_manager = SessionManager()
        
        # 主动对话触发条件
        self.proactive_triggers = {
            "long_time_no_response": {
                "threshold": 300,  # 5分钟无回复
                "priority": "medium",
                "description": "用户长时间未回复"
            },
            "negative_emotion": {
                "threshold": 0.7,  # 负面情绪阈值
                "priority": "urgent",
                "description": "用户情绪负面"
            },
            "browsing_specific_product": {
                "threshold": 1,  # 浏览特定产品次数
                "priority": "high",
                "description": "用户浏览特定产品"
            },
            "repeated_question": {
                "threshold": 3,  # 重复询问同一问题次数
                "priority": "high",
                "description": "用户重复询问同一问题"
            },
            "special_occasion": {
                "threshold": 1,  # 特殊场合
                "priority": "low",
                "description": "节假日或生日"
            },
            "cart_abandonment": {
                "threshold": 1800,  # 购物车放弃30分钟
                "priority": "medium",
                "description": "用户购物车放弃"
            },
            "new_user_welcome": {
                "threshold": 1,  # 新用户
                "priority": "low",
                "description": "新用户欢迎"
            },
            "vip_check_in": {
                "threshold": 1,  # VIP用户关怀
                "priority": "low",
                "description": "VIP用户关怀"
            }
        }
        
        # 主动对话消息模板
        self.proactive_message_templates = {
            "long_time_no_response": [
                "您好！刚才的咨询还有什么不清楚的地方吗？我随时为您解答~",
                "亲，还在吗？有什么其他问题需要我帮忙的吗？",
                "感谢您的耐心等待，有任何问题都可以随时问我哦！",
                "您好！我注意到您可能还在考虑，有什么需要我详细说明的吗？"
            ],
            "negative_emotion": [
                "非常抱歉让您有不愉快的体验，我会尽全力帮您解决问题！",
                "我理解您的感受，让我们一起找到最好的解决方案吧！",
                "您的满意是我们最大的追求，请告诉我如何能帮助到您？",
                "很抱歉给您带来了困扰，我会立即为您处理这个问题。"
            ],
            "browsing_specific_product": [
                "我看到您对{product}很感兴趣，这款产品现在有特别优惠哦！",
                "亲，您浏览的{product}是我们的人气产品，很多客户都给予了好评~",
                "关于{product}有任何疑问都可以问我，我为您详细介绍！",
                "{product}现在有现货，需要我为您预留吗？"
            ],
            "repeated_question": [
                "我注意到您对{topic}很关心，让我为您详细解释一下...",
                "关于{topic}，我理解您的疑虑，让我提供更详细的信息...",
                "您对{topic}的关心我理解，让我为您整理一份完整的说明...",
                "我看到您多次询问{topic}，这确实很重要，让我重点说明..."
            ],
            "special_occasion": [
                "今天是您的生日，祝您生日快乐！我们为您准备了特别优惠哦~",
                "节日快乐！在这个特别的日子里，我们为您准备了专属礼物！",
                "祝您节日快乐！我们推出了节日特惠活动，不要错过哦！",
                "在这个特殊的日子里，祝您一切顺利！有特别的优惠等着您~"
            ],
            "cart_abandonment": [
                "亲，我看到您购物车里的商品还没结算，是有什么顾虑吗？",
                "您购物车里的商品库存有限哦，需要我为您保留吗？",
                "关于购物车里的商品有任何疑问都可以问我，我为您解答！",
                "现在结算可以享受额外优惠，需要我为您申请吗？"
            ],
            "new_user_welcome": [
                "欢迎新用户！首次购买有专属优惠哦~",
                "感谢您选择我们！新用户专享福利等您来领取！",
                "欢迎加入我们的大家庭！有任何问题都可以随时咨询我。",
                "作为新用户，您享有特别的优惠和服务，让我为您介绍~"
            ],
            "vip_check_in": [
                "尊敬的VIP用户，我们为您准备了专属服务~",
                "VIP专享：我们为您提供了特别的优惠和优先服务！",
                "感谢您一直以来的支持，VIP专属福利等您来体验！",
                "作为我们的VIP客户，您享有最高级别的服务体验！"
            ]
        }
    
    async def check_proactive_opportunity(self, session_id: str, user_id: str) -> List[Dict[str, Any]]:
        """检查主动对话机会"""
        opportunities = []
        
        # 1. 获取用户信息和上下文
        user_profile = await self.user_profiles.get_profile(user_id)
        context = await self.context_manager.get_context(session_id)
        
        if not user_profile or not context:
            return opportunities
        
        # 2. 检查最后互动时间
        last_activity = datetime.fromisoformat(context.get("last_activity", datetime.now().isoformat()))
        time_since_last_activity = (datetime.now() - last_activity).total_seconds()
        
        if time_since_last_activity > self.proactive_triggers["long_time_no_response"]["threshold"]:
            opportunities.append({
                "type": "long_time_no_response",
                "priority": self.proactive_triggers["long_time_no_response"]["priority"],
                "suggestion": "主动问候用户，询问是否需要帮助",
                "trigger_data": {
                    "time_since_last_activity": time_since_last_activity
                }
            })
        
        # 3. 检查用户情绪
        recent_messages = await self._get_recent_messages(session_id, limit=5)
        if recent_messages:
            # 分析最近消息的情感
            emotion_analysis = await self.emotion_analyzer.analyze_conversation_emotions(recent_messages)
            
            if emotion_analysis["overall_emotion"] == "negative" and emotion_analysis["confidence"] > 0.7:
                opportunities.append({
                    "type": "negative_emotion",
                    "priority": self.proactive_triggers["negative_emotion"]["priority"],
                    "suggestion": "立即安抚用户情绪，提供解决方案",
                    "trigger_data": {
                        "emotion": emotion_analysis["overall_emotion"],
                        "confidence": emotion_analysis["confidence"],
                        "trend": emotion_analysis["emotion_trend"]
                    }
                })
        
        # 4. 检查重复问题
        conversation_history = context.get("conversation_history", [])
        repeated_topics = self._detect_repeated_topics(conversation_history)
        
        for topic, count in repeated_topics.items():
            if count >= self.proactive_triggers["repeated_question"]["threshold"]:
                opportunities.append({
                    "type": "repeated_question",
                    "priority": self.proactive_triggers["repeated_question"]["priority"],
                    "suggestion": f"用户多次询问{topic}，需要详细解释",
                    "trigger_data": {
                        "topic": topic,
                        "repeat_count": count
                    }
                })
        
        # 5. 检查特殊时机
        if self._is_special_occasion(user_profile):
            opportunities.append({
                "type": "special_occasion",
                "priority": self.proactive_triggers["special_occasion"]["priority"],
                "suggestion": "发送节日祝福或生日祝福",
                "trigger_data": {
                    "occasion": self._get_special_occasion_type(user_profile)
                }
            })
        
        # 6. 检查新用户
        if self._is_new_user(user_profile):
            opportunities.append({
                "type": "new_user_welcome",
                "priority": self.proactive_triggers["new_user_welcome"]["priority"],
                "suggestion": "欢迎新用户，介绍服务",
                "trigger_data": {
                    "user_type": "new"
                }
            })
        
        # 7. 检查VIP用户
        if self._is_vip_user(user_profile):
            opportunities.append({
                "type": "vip_check_in",
                "priority": self.proactive_triggers["vip_check_in"]["priority"],
                "suggestion": "VIP用户关怀，提供专属服务",
                "trigger_data": {
                    "user_type": "vip"
                }
            })
        
        # 按优先级排序
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        opportunities.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        return opportunities
    
    async def generate_proactive_message(self, opportunity: Dict[str, Any], user_profile: Dict[str, Any]) -> str:
        """生成主动对话消息"""
        opportunity_type = opportunity["type"]
        templates = self.proactive_message_templates.get(opportunity_type, [])
        
        if not templates:
            return "您好，有什么可以帮助您的吗？"
        
        # 选择模板
        template = random.choice(templates)
        
        # 个性化处理
        personalized_message = self._personalize_proactive_message(template, user_profile, opportunity)
        
        return personalized_message
    
    def _personalize_proactive_message(self, template: str, user_profile: Dict[str, Any], opportunity: Dict[str, Any]) -> str:
        """个性化主动对话消息"""
        # 获取用户昵称
        nickname = user_profile.get("basic_info", {}).get("nickname", "亲")
        
        # 根据沟通风格调整
        communication_style = user_profile.get("preference_profile", {}).get("communication_style", "friendly")
        
        # 替换占位符
        message = template
        
        # 替换用户名称
        if "{nickname}" in message:
            message = message.replace("{nickname}", nickname)
        
        # 替换产品名称（如果有）
        if "{product}" in message and "trigger_data" in opportunity:
            product = opportunity["trigger_data"].get("product", "这款产品")
            message = message.replace("{product}", product)
        
        # 替换主题（如果有）
        if "{topic}" in message and "trigger_data" in opportunity:
            topic = opportunity["trigger_data"].get("topic", "这个问题")
            message = message.replace("{topic}", topic)
        
        # 根据沟通风格调整
        if communication_style == "formal":
            # 正式风格：移除表情符号和口语化表达
            message = message.replace("~", "。")
            message = message.replace("亲", "您好")
            message = message.replace("哦", "")
            message = message.replace("哈", "")
        elif communication_style == "casual":
            # 随意风格：可以添加更多口语化表达
            if not any(emoji in message for emoji in ["~", "😊", "👍"]):
                message += "~"
        
        return message
    
    async def _get_recent_messages(self, session_id: str, limit: int = 5) -> List[str]:
        """获取最近的消息内容"""
        messages = await self.session_manager.get_session_messages(session_id, limit=limit)
        return [msg["content"] for msg in messages if msg["direction"] == "inbound"]
    
    def _detect_repeated_topics(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, int]:
        """检测重复话题"""
        if not conversation_history:
            return {}
        
        # 简单的关键词提取
        keywords = ["价格", "质量", "发货", "退货", "优惠", "折扣", "库存", "尺寸", "颜色", "保修"]
        topic_counts = {}
        
        for message in conversation_history:
            if message.get("direction") == "inbound":
                content = message.get("content", "")
                for keyword in keywords:
                    if keyword in content:
                        topic_counts[keyword] = topic_counts.get(keyword, 0) + 1
        
        # 只返回重复次数超过阈值的
        repeated_topics = {topic: count for topic, count in topic_counts.items() if count >= 2}
        
        return repeated_topics
    
    def _is_special_occasion(self, user_profile: Dict[str, Any]) -> bool:
        """检查是否是特殊场合"""
        # 检查生日
        basic_info = user_profile.get("basic_info", {})
        if "birthday" in basic_info:
            birthday = basic_info["birthday"]
            today = datetime.now()
            # 简化检查，假设birthday是月日格式
            if birthday and today.strftime("%m-%d") in birthday:
                return True
        
        # 检查节假日（简化版）
        today = datetime.now()
        holidays = [
            "01-01",  # 元旦
            "02-14",  # 情人节
            "03-08",  # 妇女节
            "05-01",  # 劳动节
            "06-01",  # 儿童节
            "10-01",  # 国庆节
            "12-25"   # 圣诞节
        ]
        
        return today.strftime("%m-%d") in holidays
    
    def _get_special_occasion_type(self, user_profile: Dict[str, Any]) -> str:
        """获取特殊场合类型"""
        # 检查生日
        basic_info = user_profile.get("basic_info", {})
        if "birthday" in basic_info:
            birthday = basic_info["birthday"]
            today = datetime.now()
            if birthday and today.strftime("%m-%d") in birthday:
                return "birthday"
        
        # 检查节假日
        today = datetime.now()
        holidays = {
            "01-01": "new_year",
            "02-14": "valentine",
            "03-08": "womens_day",
            "05-01": "labor_day",
            "06-01": "childrens_day",
            "10-01": "national_day",
            "12-25": "christmas"
        }
        
        today_str = today.strftime("%m-%d")
        return holidays.get(today_str, "holiday")
    
    def _is_new_user(self, user_profile: Dict[str, Any]) -> bool:
        """检查是否为新用户"""
        behavior_profile = user_profile.get("behavior_profile", {})
        total_interactions = behavior_profile.get("total_interactions", 0)
        return total_interactions <= 3
    
    def _is_vip_user(self, user_profile: Dict[str, Any]) -> bool:
        """检查是否为VIP用户"""
        purchase_profile = user_profile.get("purchase_profile", {})
        customer_segment = purchase_profile.get("customer_segment", "new")
        return customer_segment == "vip"
    
    async def execute_proactive_chat(self, session_id: str, user_id: str, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """执行主动对话"""
        try:
            # 获取用户画像
            user_profile = await self.user_profiles.get_profile(user_id)
            if not user_profile:
                return {
                    "status": "error",
                    "error": "User profile not found"
                }
            
            # 生成主动对话消息
            message = await self.generate_proactive_message(opportunity, user_profile)
            
            # 记录主动对话行为
            await self._record_proactive_action(session_id, user_id, opportunity, message)
            
            return {
                "status": "success",
                "message": message,
                "opportunity_type": opportunity["type"],
                "priority": opportunity["priority"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _record_proactive_action(self, session_id: str, user_id: str, opportunity: Dict[str, Any], message: str):
        """记录主动对话行为"""
        # 这里可以记录到数据库或分析系统
        print(f"Proactive chat executed: session={session_id}, user={user_id}, type={opportunity['type']}, message={message[:50]}...")
    
    async def get_proactive_stats(self) -> Dict[str, Any]:
        """获取主动对话统计"""
        return {
            "triggers": list(self.proactive_triggers.keys()),
            "template_count": sum(len(templates) for templates in self.proactive_message_templates.values()),
            "supported_opportunities": len(self.proactive_triggers)
        }