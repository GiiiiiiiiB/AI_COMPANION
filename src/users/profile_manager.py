"""
用户画像管理器
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.storage.database import get_db_session
from src.storage.models import User, UserProfile


class UserProfileManager:
    """用户画像管理器"""
    
    def __init__(self):
        self.default_profiles = {
            "communication_style": "friendly",  # friendly, formal, casual
            "price_sensitivity": "medium",      # high, medium, low
            "language_preference": "zh-CN",
            "preferred_contact_time": None
        }
    
    async def create_profile(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建用户画像"""
        user_id = user_data["user_id"]
        platform = user_data["platform"]
        
        # 检查用户是否已存在
        existing_user = await self.get_user_by_id(user_id, platform)
        if existing_user:
            return existing_user
        
        async for session in get_db_session():
            # 创建用户基础信息
            user = User(
                user_id=user_id,
                platform=platform,
                nickname=user_data.get("nickname"),
                avatar=user_data.get("avatar"),
                gender=user_data.get("gender"),
                location=user_data.get("location")
            )
            session.add(user)
            await session.flush()
            
            # 创建用户画像
            profile = UserProfile(
                user_id=user_id,
                platform=platform,
                basic_info={
                    "nickname": user_data.get("nickname"),
                    "avatar": user_data.get("avatar"),
                    "gender": user_data.get("gender"),
                    "location": user_data.get("location"),
                    "age_group": user_data.get("age_group"),
                    "occupation": user_data.get("occupation")
                },
                behavior_profile={
                    "first_contact": datetime.now(),
                    "last_contact": datetime.now(),
                    "total_interactions": 0,
                    "average_response_time": 0,
                    "preferred_contact_time": None,
                    "activity_level": "low",  # low, medium, high
                    "engagement_score": 0.0
                },
                preference_profile={
                    "interested_categories": [],
                    "price_sensitivity": self.default_profiles["price_sensitivity"],
                    "communication_style": self.default_profiles["communication_style"],
                    "language_preference": self.default_profiles["language_preference"],
                    "preferred_contact_time": self.default_profiles["preferred_contact_time"],
                    "product_preferences": [],
                    "brand_preferences": []
                },
                purchase_profile={
                    "total_orders": 0,
                    "total_spent": 0.0,
                    "average_order_value": 0.0,
                    "last_purchase": None,
                    "favorite_products": [],
                    "purchase_frequency": "rare",  # rare, occasional, frequent
                    "customer_segment": "new"  # new, regular, vip
                },
                psychographic_profile={
                    "personality_traits": [],
                    "values": [],
                    "lifestyle": [],
                    "pain_points": [],
                    "motivations": [],
                    "risk_tolerance": "medium"  # low, medium, high
                }
            )
            
            session.add(profile)
            await session.commit()
            
            return await self._profile_to_dict(profile)
    
    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像"""
        async for session in get_db_session():
            profile = await session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if profile:
                return await self._profile_to_dict(profile)
            return None
    
    async def get_user_by_id(self, user_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """根据用户ID和平台获取用户信息"""
        async for session in get_db_session():
            user = await session.query(User).filter(
                User.user_id == user_id,
                User.platform == platform
            ).first()
            
            if user:
                return await self._user_to_dict(user)
            return None
    
    async def update_behavior(self, user_id: str, behavior_data: Dict[str, Any]) -> bool:
        """更新用户行为数据"""
        async for session in get_db_session():
            profile = await session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                return False
            
            behavior = profile.behavior_profile
            
            # 更新基本行为统计
            behavior["total_interactions"] += 1
            behavior["last_contact"] = datetime.now()
            
            # 更新响应时间统计
            if "response_time" in behavior_data:
                old_avg = behavior.get("average_response_time", 0)
                total_interactions = behavior["total_interactions"]
                new_avg = (old_avg * (total_interactions - 1) + behavior_data["response_time"]) / total_interactions
                behavior["average_response_time"] = round(new_avg, 2)
            
            # 更新活动级别
            if behavior["total_interactions"] > 50:
                behavior["activity_level"] = "high"
            elif behavior["total_interactions"] > 10:
                behavior["activity_level"] = "medium"
            else:
                behavior["activity_level"] = "low"
            
            # 更新参与分数
            engagement_score = self._calculate_engagement_score(behavior)
            behavior["engagement_score"] = engagement_score
            
            # 更新偏好分析
            if "interested_category" in behavior_data:
                categories = profile.preference_profile["interested_categories"]
                category = behavior_data["interested_category"]
                if category not in categories:
                    categories.append(category)
            
            if "preferred_contact_time" in behavior_data:
                behavior["preferred_contact_time"] = behavior_data["preferred_contact_time"]
            
            # 更新购买行为
            if "purchase_data" in behavior_data:
                await self._update_purchase_behavior(profile, behavior_data["purchase_data"])
            
            profile.behavior_profile = behavior
            await session.commit()
            return True
    
    async def update_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """更新用户偏好"""
        async for session in get_db_session():
            profile = await session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                return False
            
            preference_profile = profile.preference_profile
            
            # 更新价格敏感度
            if "price_sensitivity" in preferences:
                preference_profile["price_sensitivity"] = preferences["price_sensitivity"]
            
            # 更新沟通风格
            if "communication_style" in preferences:
                preference_profile["communication_style"] = preferences["communication_style"]
            
            # 更新语言偏好
            if "language_preference" in preferences:
                preference_profile["language_preference"] = preferences["language_preference"]
            
            # 更新产品偏好
            if "product_preferences" in preferences:
                preference_profile["product_preferences"] = preferences["product_preferences"]
            
            # 更新品牌偏好
            if "brand_preferences" in preferences:
                preference_profile["brand_preferences"] = preferences["brand_preferences"]
            
            profile.preference_profile = preference_profile
            await session.commit()
            return True
    
    async def update_psychographic_profile(self, user_id: str, psychographic_data: Dict[str, Any]) -> bool:
        """更新心理画像"""
        async for session in get_db_session():
            profile = await session.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).first()
            
            if not profile:
                return False
            
            psychographic = profile.psychographic_profile
            
            # 更新人格特质
            if "personality_traits" in psychographic_data:
                psychographic["personality_traits"] = psychographic_data["personality_traits"]
            
            # 更新价值观
            if "values" in psychographic_data:
                psychographic["values"] = psychographic_data["values"]
            
            # 更新生活方式
            if "lifestyle" in psychographic_data:
                psychographic["lifestyle"] = psychographic_data["lifestyle"]
            
            # 更新痛点
            if "pain_points" in psychographic_data:
                psychographic["pain_points"] = psychographic_data["pain_points"]
            
            # 更新动机
            if "motivations" in psychographic_data:
                psychographic["motivations"] = psychographic_data["motivations"]
            
            # 更新风险承受能力
            if "risk_tolerance" in psychographic_data:
                psychographic["risk_tolerance"] = psychographic_data["risk_tolerance"]
            
            profile.psychographic_profile = psychographic
            await session.commit()
            return True
    
    async def _update_purchase_behavior(self, profile: UserProfile, purchase_data: Dict[str, Any]):
        """更新购买行为"""
        purchase_profile = profile.purchase_profile
        
        # 更新订单统计
        if "order_amount" in purchase_data:
            purchase_profile["total_orders"] += 1
            purchase_profile["total_spent"] += purchase_data["order_amount"]
            purchase_profile["average_order_value"] = purchase_profile["total_spent"] / purchase_profile["total_orders"]
            purchase_profile["last_purchase"] = datetime.now()
        
        # 更新购买频率
        total_orders = purchase_profile["total_orders"]
        if total_orders > 20:
            purchase_profile["purchase_frequency"] = "frequent"
        elif total_orders > 5:
            purchase_profile["purchase_frequency"] = "occasional"
        else:
            purchase_profile["purchase_frequency"] = "rare"
        
        # 更新客户分段
        total_spent = purchase_profile["total_spent"]
        if total_spent > 10000:
            purchase_profile["customer_segment"] = "vip"
        elif total_spent > 1000:
            purchase_profile["customer_segment"] = "regular"
        else:
            purchase_profile["customer_segment"] = "new"
        
        # 更新喜欢的产品
        if "product_name" in purchase_data:
            favorite_products = purchase_profile["favorite_products"]
            product_name = purchase_data["product_name"]
            if product_name not in favorite_products:
                favorite_products.append(product_name)
                # 限制数量
                if len(favorite_products) > 10:
                    favorite_products.pop(0)
        
        profile.purchase_profile = purchase_profile
    
    def _calculate_engagement_score(self, behavior: Dict[str, Any]) -> float:
        """计算参与分数"""
        total_interactions = behavior.get("total_interactions", 0)
        average_response_time = behavior.get("average_response_time", 0)
        activity_level = behavior.get("activity_level", "low")
        
        # 基础分数
        score = min(100, total_interactions * 2)
        
        # 响应时间奖励（响应时间越短分数越高）
        if average_response_time > 0:
            response_score = max(0, 100 - average_response_time / 10)
            score += response_score * 0.3
        
        # 活动级别奖励
        level_multipliers = {"low": 1.0, "medium": 1.2, "high": 1.5}
        score *= level_multipliers.get(activity_level, 1.0)
        
        return min(100.0, score)
    
    async def get_user_analytics(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户分析数据"""
        profile = await self.get_profile(user_id)
        if not profile:
            return None
        
        behavior = profile["behavior_profile"]
        purchase = profile["purchase_profile"]
        preference = profile["preference_profile"]
        
        return {
            "user_id": user_id,
            "engagement_level": self._get_engagement_level(behavior.get("engagement_score", 0)),
            "customer_value": self._get_customer_value(purchase.get("total_spent", 0)),
            "risk_level": self._get_risk_level(profile.get("psychographic_profile", {}).get("risk_tolerance", "medium")),
            "preferred_categories": preference.get("interested_categories", []),
            "communication_style": preference.get("communication_style"),
            "price_sensitivity": preference.get("price_sensitivity"),
            "purchase_frequency": purchase.get("purchase_frequency"),
            "customer_segment": purchase.get("customer_segment"),
            "last_activity": behavior.get("last_contact"),
            "total_interactions": behavior.get("total_interactions", 0)
        }
    
    def _get_engagement_level(self, score: float) -> str:
        """获取参与级别"""
        if score >= 80:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"
    
    def _get_customer_value(self, total_spent: float) -> str:
        """获取客户价值级别"""
        if total_spent >= 10000:
            return "high"
        elif total_spent >= 1000:
            return "medium"
        else:
            return "low"
    
    def _get_risk_level(self, risk_tolerance: str) -> str:
        """获取风险级别"""
        risk_mapping = {
            "high": "low",  # 高风险承受能力 = 低风险级别
            "medium": "medium",
            "low": "high"
        }
        return risk_mapping.get(risk_tolerance, "medium")
    
    async def _profile_to_dict(self, profile: UserProfile) -> Dict[str, Any]:
        """将用户画像转换为字典"""
        return {
            "user_id": profile.user_id,
            "platform": profile.platform,
            "basic_info": profile.basic_info,
            "behavior_profile": profile.behavior_profile,
            "preference_profile": profile.preference_profile,
            "purchase_profile": profile.purchase_profile,
            "psychographic_profile": profile.psychographic_profile,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at
        }
    
    async def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """将用户转换为字典"""
        return {
            "id": user.id,
            "user_id": user.user_id,
            "platform": user.platform,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "gender": user.gender,
            "location": user.location,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }
    
    async def search_users(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """搜索用户"""
        async for session in get_db_session():
            query = session.query(UserProfile)
            
            # 平台过滤
            if "platform" in filters:
                query = query.filter(UserProfile.platform == filters["platform"])
            
            # 客户分段过滤
            if "customer_segment" in filters:
                query = query.filter(
                    UserProfile.purchase_profile["customer_segment"].astext == filters["customer_segment"]
                )
            
            # 活动级别过滤
            if "activity_level" in filters:
                query = query.filter(
                    UserProfile.behavior_profile["activity_level"].astext == filters["activity_level"]
                )
            
            # 价格敏感度过滤
            if "price_sensitivity" in filters:
                query = query.filter(
                    UserProfile.preference_profile["price_sensitivity"].astext == filters["price_sensitivity"]
                )
            
            profiles = await query.all()
            
            return [await self._profile_to_dict(profile) for profile in profiles]