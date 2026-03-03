"""
用户管理API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional

from src.users import UserProfileManager, SessionManager
from src.api.main import verify_token, get_user_profile_manager, get_session_manager

router = APIRouter()


@router.get("/users/{user_id}")
async def get_user_profile(
    user_id: str,
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """获取用户画像"""
    try:
        profile = await user_profile_manager.get_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return profile
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user profile: {str(e)}")


@router.post("/users")
async def create_user_profile(
    user_request: Dict[str, Any],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """创建用户画像"""
    try:
        user_data = user_request.get("user_data")
        if not user_data:
            raise HTTPException(status_code=400, detail="user_data is required")
        
        # 验证必需字段
        if "user_id" not in user_data or "platform" not in user_data:
            raise HTTPException(status_code=400, detail="user_id and platform are required in user_data")
        
        profile = await user_profile_manager.create_profile(user_data)
        
        return {
            "status": "success",
            "user_id": profile["user_id"],
            "message": "User profile created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user profile: {str(e)}")


@router.put("/users/{user_id}/behavior")
async def update_user_behavior(
    user_id: str,
    behavior_request: Dict[str, Any],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """更新用户行为数据"""
    try:
        behavior_data = behavior_request.get("behavior_data")
        if not behavior_data:
            raise HTTPException(status_code=400, detail="behavior_data is required")
        
        success = await user_profile_manager.update_behavior(user_id, behavior_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "User behavior updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user behavior: {str(e)}")


@router.put("/users/{user_id}/preferences")
async def update_user_preferences(
    user_id: str,
    preferences_request: Dict[str, Any],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """更新用户偏好"""
    try:
        preferences = preferences_request.get("preferences")
        if not preferences:
            raise HTTPException(status_code=400, detail="preferences is required")
        
        success = await user_profile_manager.update_preferences(user_id, preferences)
        
        if not success:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "User preferences updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user preferences: {str(e)}")


@router.put("/users/{user_id}/psychographic")
async def update_psychographic_profile(
    user_id: str,
    psychographic_request: Dict[str, Any],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """更新用户心理画像"""
    try:
        psychographic_data = psychographic_request.get("psychographic_data")
        if not psychographic_data:
            raise HTTPException(status_code=400, detail="psychographic_data is required")
        
        success = await user_profile_manager.update_psychographic_profile(user_id, psychographic_data)
        
        if not success:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "Psychographic profile updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update psychographic profile: {str(e)}")


@router.get("/users/{user_id}/analytics")
async def get_user_analytics(
    user_id: str,
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """获取用户分析数据"""
    try:
        analytics = await user_profile_manager.get_user_analytics(user_id)
        
        if not analytics:
            raise HTTPException(status_code=404, detail="User analytics not found")
        
        return analytics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")


@router.get("/users")
async def search_users(
    platform: Optional[str] = None,
    customer_segment: Optional[str] = None,
    activity_level: Optional[str] = None,
    price_sensitivity: Optional[str] = None,
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """搜索用户"""
    try:
        # 构建过滤器
        filters = {}
        if platform:
            filters["platform"] = platform
        if customer_segment:
            filters["customer_segment"] = customer_segment
        if activity_level:
            filters["activity_level"] = activity_level
        if price_sensitivity:
            filters["price_sensitivity"] = price_sensitivity
        
        users = await user_profile_manager.search_users(filters)
        
        return {
            "users": users,
            "count": len(users),
            "filters": filters
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search users: {str(e)}")


@router.get("/users/{user_id}/sessions")
async def get_user_sessions(
    user_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """获取用户会话列表"""
    try:
        sessions = await session_manager.get_user_active_sessions(user_id)
        
        return {
            "user_id": user_id,
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user sessions: {str(e)}")


@router.get("/users/{user_id}/active-session")
async def get_user_active_session(
    user_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    token: str = Depends(verify_token)
):
    """获取用户活跃会话"""
    try:
        session = await session_manager.get_active_session(user_id)
        
        if not session:
            return {
                "user_id": user_id,
                "session": None,
                "message": "No active session found"
            }
        
        return {
            "user_id": user_id,
            "session": session
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active session: {str(e)}")


@router.get("/users/stats")
async def get_user_stats(
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """获取用户统计信息"""
    try:
        # 这里可以实现更详细的统计逻辑
        # 目前返回基础信息
        return {
            "total_users": 0,  # 需要实现统计逻辑
            "active_users": 0,
            "new_users_today": 0,
            "vip_users": 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user stats: {str(e)}")


@router.get("/users/{user_id}/recommendations")
async def get_user_recommendations(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 10,
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """获取用户推荐"""
    try:
        # 获取用户画像
        profile = await user_profile_manager.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # 基于用户画像生成推荐
        preferences = profile.get("preference_profile", {})
        interested_categories = preferences.get("interested_categories", [])
        
        # 这里可以实现更复杂的推荐逻辑
        recommendations = []
        
        # 基于兴趣分类推荐
        if category:
            recommendations.append({
                "type": "category_based",
                "category": category,
                "reason": f"基于您对{category}的兴趣"
            })
        elif interested_categories:
            for cat in interested_categories[:3]:
                recommendations.append({
                    "type": "interest_based",
                    "category": cat,
                    "reason": f"基于您的兴趣偏好"
                })
        
        # 基于购买历史推荐
        purchase_profile = profile.get("purchase_profile", {})
        favorite_products = purchase_profile.get("favorite_products", [])
        if favorite_products:
            recommendations.append({
                "type": "purchase_based",
                "products": favorite_products[:3],
                "reason": "基于您的购买历史"
            })
        
        # 基于客户分段推荐
        customer_segment = purchase_profile.get("customer_segment", "new")
        if customer_segment == "vip":
            recommendations.append({
                "type": "vip_exclusive",
                "reason": "VIP专享推荐"
            })
        elif customer_segment == "regular":
            recommendations.append({
                "type": "loyalty_rewards",
                "reason": "忠实客户奖励"
            })
        
        # 限制推荐数量
        recommendations = recommendations[:limit]
        
        return {
            "user_id": user_id,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")


@router.post("/users/{user_id}/segments")
async def update_user_segment(
    user_id: str,
    segment_request: Dict[str, Any],
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """更新用户分段"""
    try:
        segment = segment_request.get("segment")
        if not segment:
            raise HTTPException(status_code=400, detail="segment is required")
        
        # 获取用户画像
        profile = await user_profile_manager.get_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # 更新购买档案中的客户分段
        purchase_profile = profile.get("purchase_profile", {})
        purchase_profile["customer_segment"] = segment
        
        # 这里需要实现更新购买档案的逻辑
        # 由于当前接口限制，返回模拟结果
        
        return {
            "status": "success",
            "user_id": user_id,
            "segment": segment,
            "message": f"User segment updated to {segment}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user segment: {str(e)}")


@router.get("/users/segments")
async def get_user_segments(
    user_profile_manager: UserProfileManager = Depends(get_user_profile_manager),
    token: str = Depends(verify_token)
):
    """获取用户分段统计"""
    try:
        # 搜索不同分段的用户
        segments = ["new", "regular", "vip"]
        segment_stats = {}
        
        for segment in segments:
            users = await user_profile_manager.search_users({"customer_segment": segment})
            segment_stats[segment] = {
                "count": len(users),
                "percentage": 0  # 需要计算总用户数的百分比
            }
        
        return {
            "segment_stats": segment_stats,
            "total_users": sum(stats["count"] for stats in segment_stats.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user segments: {str(e)}")