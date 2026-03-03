"""
情感分析器
"""
import asyncio
import re
from typing import Dict, Any, List, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

from src.config.settings import settings


class EmotionAnalyzer:
    """情感分析器"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.ai.emotion_model
        self.model = None
        self.tokenizer = None
        
        # 情感标签定义
        self.emotion_labels = {
            "positive": ["高兴", "满意", "开心", "愉快", "兴奋", "惊喜", "喜欢", "爱"],
            "negative": ["生气", "失望", "沮丧", "焦虑", "愤怒", "悲伤", "恐惧", "厌恶"],
            "neutral": ["平静", "正常", "一般", "中性", "客观"]
        }
        
        # 情感强度映射
        self.intensity_mapping = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.3
        }
        
        self._load_model()
    
    def _load_model(self):
        """加载情感分析模型"""
        try:
            # 尝试加载中文情感分析模型
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.classifier = pipeline(
                "text-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                return_all_scores=True
            )
        except Exception as e:
            print(f"Warning: Failed to load emotion model {self.model_name}: {e}")
            # 使用简化的规则-based方法
            self.classifier = None
    
    async def analyze(self, text: str) -> Dict[str, Any]:
        """分析文本情感"""
        if not text or not text.strip():
            return {
                "emotion": "neutral",
                "intensity": "low",
                "confidence": 0.0,
                "suggestions": "保持正常交流",
                "method": "none"
            }
        
        # 1. 模型预测
        model_prediction = None
        if self.classifier:
            try:
                model_prediction = await self._model_predict(text)
            except Exception as e:
                print(f"Model emotion prediction failed: {e}")
        
        # 2. 规则匹配
        rule_based_emotion = self.rule_match(text)
        
        # 3. 结果融合
        final_emotion = self.fuse_predictions(model_prediction, rule_based_emotion)
        
        # 4. 计算情感强度
        intensity = self.calculate_intensity(final_emotion)
        
        # 5. 生成应对建议
        suggestions = self.get_emotion_suggestions(final_emotion["emotion"], intensity)
        
        return {
            "emotion": final_emotion["emotion"],
            "intensity": intensity,
            "confidence": final_emotion["confidence"],
            "suggestions": suggestions,
            "method": final_emotion["method"],
            "details": final_emotion.get("details", {})
        }
    
    async def _model_predict(self, text: str) -> Dict[str, Any]:
        """模型情感预测"""
        if not self.classifier:
            return None
        
        # 预处理文本
        processed_text = self.preprocess_text(text)
        
        # 运行模型预测
        predictions = self.classifier(processed_text)[0]
        
        # 映射到我们的情感类别
        emotion_scores = {
            "positive": 0.0,
            "negative": 0.0,
            "neutral": 0.0
        }
        
        for pred in predictions:
            label = pred['label'].lower()
            score = float(pred['score'])
            
            # 映射模型标签到我们的类别
            if any(pos_word in label for pos_word in ['positive', 'happy', 'joy', 'love', 'satisfaction']):
                emotion_scores["positive"] += score
            elif any(neg_word in label for neg_word in ['negative', 'angry', 'sad', 'fear', 'disgust']):
                emotion_scores["negative"] += score
            else:
                emotion_scores["neutral"] += score
        
        # 找到最高分数的情感
        best_emotion = max(emotion_scores.keys(), key=lambda x: emotion_scores[x])
        
        return {
            "emotion": best_emotion,
            "confidence": emotion_scores[best_emotion],
            "all_scores": emotion_scores
        }
    
    def rule_match(self, text: str) -> Dict[str, Any]:
        """基于规则的情感匹配"""
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_labels.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower:
                    # 计算匹配次数
                    count = text_lower.count(keyword_lower)
                    score += count * 2
                    matched_keywords.append(keyword)
                    
                    # 加强词检查
                    intensifiers = ["很", "非常", "特别", "极其", "超级"]
                    for intensifier in intensifiers:
                        if intensifier + keyword_lower in text_lower:
                            score += 3
                    
                    # 否定词检查
                    negations = ["不", "没", "无"]
                    for negation in negations:
                        if negation + keyword_lower in text_lower:
                            score -= 2
            
            if score > 0:
                emotion_scores[emotion] = {
                    "score": score,
                    "matched_keywords": matched_keywords
                }
        
        # 检查情感强化词
        emotion_intensifiers = {
            "positive": ["喜欢", "爱", "棒", "好", "满意", "开心", "高兴"],
            "negative": ["讨厌", "恨", "差", "坏", "失望", "生气", "愤怒"]
        }
        
        for emotion, intensifiers in emotion_intensifiers.items():
            for intensifier in intensifiers:
                if intensifier in text_lower:
                    if emotion in emotion_scores:
                        emotion_scores[emotion]["score"] += 5
                    else:
                        emotion_scores[emotion] = {
                            "score": 5,
                            "matched_keywords": [intensifier]
                        }
        
        if emotion_scores:
            best_emotion = max(emotion_scores.keys(), key=lambda x: emotion_scores[x]["score"])
            return {
                "emotion": best_emotion,
                "confidence": min(0.9, emotion_scores[best_emotion]["score"] / 20.0),
                "matched_keywords": emotion_scores[best_emotion]["matched_keywords"]
            }
        
        return {
            "emotion": "neutral",
            "confidence": 0.5,
            "matched_keywords": []
        }
    
    def fuse_predictions(self, model_prediction: Dict[str, Any], rule_based: Dict[str, Any]) -> Dict[str, Any]:
        """融合模型预测和规则匹配结果"""
        # 如果模型预测置信度很高，优先使用模型结果
        if model_prediction and model_prediction["confidence"] > 0.7:
            return {
                "emotion": model_prediction["emotion"],
                "confidence": model_prediction["confidence"],
                "method": "model",
                "details": model_prediction
            }
        
        # 如果规则匹配置信度很高，优先使用规则结果
        if rule_based["confidence"] > 0.6:
            return {
                "emotion": rule_based["emotion"],
                "confidence": rule_based["confidence"],
                "method": "rule",
                "details": rule_based
            }
        
        # 如果两者结果一致，使用任一结果
        if (model_prediction and 
            model_prediction["emotion"] == rule_based["emotion"] and 
            model_prediction["confidence"] > 0.4):
            return {
                "emotion": model_prediction["emotion"],
                "confidence": (model_prediction["confidence"] + rule_based["confidence"]) / 2,
                "method": "both",
                "details": {"model": model_prediction, "rule": rule_based}
            }
        
        # 否则使用模型结果（如果可用）
        if model_prediction and model_prediction["confidence"] > 0.3:
            return {
                "emotion": model_prediction["emotion"],
                "confidence": model_prediction["confidence"] * 0.8,
                "method": "model_fallback",
                "details": model_prediction
            }
        
        # 最后使用规则结果
        return {
            "emotion": rule_based["emotion"],
            "confidence": rule_based["confidence"],
            "method": "rule_fallback",
            "details": rule_based
        }
    
    def calculate_intensity(self, emotion_result: Dict[str, Any]) -> str:
        """计算情感强度"""
        confidence = emotion_result["confidence"]
        
        if confidence >= 0.8:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"
    
    def get_emotion_suggestions(self, emotion: str, intensity: str) -> str:
        """根据情感提供应对建议"""
        suggestions = {
            "positive": {
                "high": "用户情绪很好，可以保持友好互动，适当推荐产品或服务",
                "medium": "用户情绪不错，可以适当推荐产品，保持积极互动",
                "low": "用户情绪一般积极，需要更多关怀和关注"
            },
            "negative": {
                "high": "用户情绪很差，需要立即安抚和人工介入，优先处理投诉",
                "medium": "用户有不满，需要耐心解释和补偿，提供解决方案",
                "low": "用户略有不满，需要关注和改善，主动询问需求"
            },
            "neutral": {
                "high": "用户情绪稳定，可以正常交流，保持专业态度",
                "medium": "用户情绪平淡，需要激发兴趣，提供更多帮助信息",
                "low": "用户情绪低落，需要更多关注和主动服务"
            }
        }
        
        return suggestions.get(emotion, {}).get(intensity, "保持正常交流")
    
    def preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        # 限制长度
        if len(text) > 512:
            text = text[:512]
        return text.strip()
    
    async def analyze_conversation_emotions(self, messages: List[str]) -> Dict[str, Any]:
        """分析对话情感趋势"""
        if not messages:
            return {
                "overall_emotion": "neutral",
                "emotion_trend": "stable",
                "emotion_distribution": {},
                "confidence": 0.0
            }
        
        emotions = []
        confidences = []
        
        for message in messages:
            result = await self.analyze(message)
            emotions.append(result["emotion"])
            confidences.append(result["confidence"])
        
        # 计算情感分布
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # 计算总体情感
        overall_emotion = max(emotion_counts.keys(), key=lambda x: emotion_counts[x])
        
        # 计算情感趋势
        if len(emotions) >= 2:
            first_half = emotions[:len(emotions)//2]
            second_half = emotions[len(emotions)//2:]
            
            first_emotion = max(set(first_half), key=first_half.count)
            second_emotion = max(set(second_half), key=second_half.count)
            
            if first_emotion != second_emotion:
                emotion_trend = f"从{first_emotion}转向{second_emotion}"
            else:
                emotion_trend = "稳定"
        else:
            emotion_trend = "稳定"
        
        # 计算平均置信度
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "overall_emotion": overall_emotion,
            "emotion_trend": emotion_trend,
            "emotion_distribution": emotion_counts,
            "confidence": avg_confidence,
            "recent_emotions": emotions[-5:]  # 最近5条消息的情感
        }
    
    def add_emotion_keywords(self, emotion: str, keywords: List[str]):
        """添加情感关键词"""
        if emotion not in self.emotion_labels:
            self.emotion_labels[emotion] = []
        
        self.emotion_labels[emotion].extend(keywords)
        # 去重
        self.emotion_labels[emotion] = list(set(self.emotion_labels[emotion]))
    
    def get_supported_emotions(self) -> List[str]:
        """获取支持的情感列表"""
        return list(self.emotion_labels.keys())
    
    def get_emotion_keywords(self, emotion: str) -> List[str]:
        """获取情感关键词"""
        return self.emotion_labels.get(emotion, [])