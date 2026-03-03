"""
意图分类器
"""
import re
from typing import Dict, Any, List, Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch

from src.config.settings import settings


class IntentClassifier:
    """意图分类器"""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.ai.intent_model
        self.model = None
        self.tokenizer = None
        self.intents = {
            "greeting": ["你好", "您好", "hello", "hi", "早上好", "下午好", "晚上好"],
            "product_inquiry": ["产品", "商品", "价格", "库存", "质量", "规格", "型号", "品牌"],
            "order_query": ["订单", "物流", "发货", "快递", "配送", "收货", "退货", "退款"],
            "complaint": ["投诉", "不满", "问题", "错误", "退货", "退款", "差评", "服务差"],
            "praise": ["好评", "满意", "感谢", "棒", "优秀", "不错", "喜欢", "推荐"],
            "price_negotiation": ["便宜", "优惠", "折扣", "促销", "活动", "价格", "多少钱"],
            "shipping_info": ["运费", "包邮", "配送", "快递", "发货时间", "到货时间"],
            "payment": ["支付", "付款", "支付宝", "微信", "银行卡", "分期"],
            "after_sales": ["售后", "保修", "维修", "换货", "补发", "赔偿"],
            "account": ["账户", "登录", "注册", "密码", "个人信息", "积分"]
        }
        self._load_model()
    
    def _load_model(self):
        """加载意图分类模型"""
        try:
            # 尝试加载中文BERT模型
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.classifier = pipeline(
                "text-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                return_all_scores=True
            )
        except Exception as e:
            print(f"Warning: Failed to load intent model {self.model_name}: {e}")
            self.classifier = None
    
    async def classify(self, text: str) -> Dict[str, Any]:
        """意图分类"""
        if not text or not text.strip():
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": [],
                "method": "none"
            }
        
        # 1. 预处理文本
        processed_text = self.preprocess_text(text)
        
        # 2. 模型预测
        model_prediction = None
        if self.classifier:
            try:
                model_prediction = await self._model_predict(processed_text)
            except Exception as e:
                print(f"Model prediction failed: {e}")
        
        # 3. 规则匹配（补充）
        rule_based_intent = self.rule_match(text)
        
        # 4. 结果融合
        final_result = self.fuse_predictions(model_prediction, rule_based_intent)
        
        # 5. 提取实体
        entities = self.extract_entities(text, final_result["intent"])
        
        return {
            "intent": final_result["intent"],
            "confidence": final_result["confidence"],
            "entities": entities,
            "method": final_result["method"]
        }
    
    def preprocess_text(self, text: str) -> str:
        """预处理文本"""
        # 移除多余空白字符
        text = re.sub(r'\s+', ' ', text)
        # 转换为小写
        text = text.lower().strip()
        # 限制长度
        if len(text) > 512:
            text = text[:512]
        return text
    
    async def _model_predict(self, text: str) -> Dict[str, Any]:
        """模型预测"""
        if not self.classifier:
            return None
        
        # 运行模型预测
        predictions = self.classifier(text)[0]
        
        # 找到最高分数的意图
        best_prediction = max(predictions, key=lambda x: x['score'])
        
        return {
            "intent": best_prediction['label'],
            "confidence": float(best_prediction['score']),
            "all_scores": {pred['label']: float(pred['score']) for pred in predictions}
        }
    
    def rule_match(self, text: str) -> Dict[str, Any]:
        """基于规则的意图匹配"""
        text_lower = text.lower()
        intent_scores = {}
        
        for intent, keywords in self.intents.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in text_lower:
                    # 完全匹配得分更高
                    count = text_lower.count(keyword_lower)
                    score += count * 2
                    matched_keywords.append(keyword)
                    
                    # 如果在开头出现，得分更高
                    if text_lower.startswith(keyword_lower):
                        score += 5
            
            if score > 0:
                intent_scores[intent] = {
                    "score": score,
                    "matched_keywords": matched_keywords
                }
        
        if intent_scores:
            best_intent = max(intent_scores.keys(), key=lambda x: intent_scores[x]["score"])
            return {
                "intent": best_intent,
                "confidence": min(0.9, intent_scores[best_intent]["score"] / 10.0),
                "matched_keywords": intent_scores[best_intent]["matched_keywords"]
            }
        
        return {
            "intent": "unknown",
            "confidence": 0.0,
            "matched_keywords": []
        }
    
    def fuse_predictions(self, model_prediction: Dict[str, Any], rule_based: Dict[str, Any]) -> Dict[str, Any]:
        """融合模型预测和规则匹配结果"""
        # 如果模型预测置信度很高，优先使用模型结果
        if model_prediction and model_prediction["confidence"] > 0.8:
            return {
                "intent": model_prediction["intent"],
                "confidence": model_prediction["confidence"],
                "method": "model"
            }
        
        # 如果规则匹配置信度很高，优先使用规则结果
        if rule_based["confidence"] > 0.7:
            return {
                "intent": rule_based["intent"],
                "confidence": rule_based["confidence"],
                "method": "rule"
            }
        
        # 如果两者结果一致，使用任一结果
        if (model_prediction and 
            model_prediction["intent"] == rule_based["intent"] and 
            model_prediction["confidence"] > 0.5):
            return {
                "intent": model_prediction["intent"],
                "confidence": (model_prediction["confidence"] + rule_based["confidence"]) / 2,
                "method": "both"
            }
        
        # 否则使用模型结果（如果可用）
        if model_prediction and model_prediction["confidence"] > 0.3:
            return {
                "intent": model_prediction["intent"],
                "confidence": model_prediction["confidence"] * 0.8,
                "method": "model_fallback"
            }
        
        # 最后使用规则结果
        return {
            "intent": rule_based["intent"],
            "confidence": rule_based["confidence"],
            "method": "rule_fallback"
        }
    
    def extract_entities(self, text: str, intent: str) -> List[Dict[str, Any]]:
        """提取实体"""
        entities = []
        
        # 产品相关实体
        if intent in ["product_inquiry", "price_negotiation"]:
            # 提取产品名称（简单的规则匹配）
            product_patterns = [
                r'(\w+手机)',
                r'(\w+电脑)',
                r'(\w+耳机)',
                r'(\w+衣服)',
                r'(\w+鞋子)'
            ]
            
            for pattern in product_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "entity": "product",
                        "value": match,
                        "start": text.find(match),
                        "end": text.find(match) + len(match)
                    })
            
            # 提取价格信息
            price_patterns = [
                r'(\d+)元',
                r'(\d+)块',
                r'￥(\d+)',
                r'¥(\d+)'
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({
                        "entity": "price",
                        "value": match,
                        "start": text.find(match),
                        "end": text.find(match) + len(match)
                    })
        
        # 订单相关实体
        if intent == "order_query":
            # 提取订单号
            order_patterns = [
                r'订单号[：:]?(\w+)',
                r'订单编号[：:]?(\w+)',
                r'(\d{10,})'  # 10位以上数字可能是订单号
            ]
            
            for pattern in order_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    entities.append({
                        "entity": "order_id",
                        "value": match,
                        "start": text.find(match),
                        "end": text.find(match) + len(match)
                    })
        
        return entities
    
    def add_intent_keywords(self, intent: str, keywords: List[str]):
        """添加意图关键词"""
        if intent not in self.intents:
            self.intents[intent] = []
        
        self.intents[intent].extend(keywords)
        # 去重
        self.intents[intent] = list(set(self.intents[intent]))
    
    def remove_intent(self, intent: str):
        """移除意图"""
        if intent in self.intents:
            del self.intents[intent]
    
    def get_supported_intents(self) -> List[str]:
        """获取支持的意图列表"""
        return list(self.intents.keys())
    
    def get_intent_keywords(self, intent: str) -> List[str]:
        """获取意图关键词"""
        return self.intents.get(intent, [])