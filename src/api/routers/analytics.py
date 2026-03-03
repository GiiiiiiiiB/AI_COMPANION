"""
分析统计API路由
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from src.storage.database import get_db_session
from src.storage.models import ChatSession, Message, User, ConversationAnalytics, SystemMetrics
from src.api.main import verify_token

router = APIRouter()


@router.get("/analytics/dashboard")
async def get_dashboard_stats(
    start_date: str,
    end_date: str,
    token: str = Depends(verify_token)
):
    """获取仪表板统计数据"""
    try:
        # 解析日期
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        async for session in get_db_session():
            # 基础统计
            total_sessions = await session.query(ChatSession).filter(
                ChatSession.created_at >= start_dt,
                ChatSession.created_at <= end_dt
            ).count()
            
            active_sessions = await session.query(ChatSession).filter(
                ChatSession.created_at >= start_dt,
                ChatSession.created_at <= end_dt,
                ChatSession.status == "active"
            ).count()
            
            total_messages = await session.query(Message).filter(
                Message.created_at >= start_dt,
                Message.created_at <= end_dt
            ).count()
            
            escalated_sessions = await session.query(ChatSession).filter(
                ChatSession.created_at >= start_dt,
                ChatSession.created_at <= end_dt,
                ChatSession.escalated == True
            ).count()
            
            # 满意度统计
            satisfaction_stats = await session.query(
                ChatSession.satisfaction_score,
                session.func.count(ChatSession.id)
            ).filter(
                ChatSession.created_at >= start_dt,
                ChatSession.created_at <= end_dt,
                ChatSession.satisfaction_score.isnot(None)
            ).group_by(ChatSession.satisfaction_score).all()
            
            # 平台分布
            platform_stats = await session.query(
                ChatSession.platform,
                session.func.count(ChatSession.id)
            ).filter(
                ChatSession.created_at >= start_dt,
                ChatSession.created_at <= end_dt
            ).group_by(ChatSession.platform).all()
            
            # 意图分布
            intent_stats = await session.query(
                Message.intent,
                session.func.count(Message.id)
            ).filter(
                Message.created_at >= start_dt,
                Message.created_at <= end_dt,
                Message.intent.isnot(None)
            ).group_by(Message.intent).all()
            
            return {
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "overview": {
                    "total_sessions": total_sessions,
                    "active_sessions": active_sessions,
                    "total_messages": total_messages,
                    "escalated_sessions": escalated_sessions,
                    "escalation_rate": escalated_sessions / total_sessions if total_sessions > 0 else 0
                },
                "satisfaction": {
                    "distribution": {str(score): count for score, count in satisfaction_stats},
                    "average": sum(score * count for score, count in satisfaction_stats) / sum(count for _, count in satisfaction_stats) if satisfaction_stats else 0
                },
                "platform_distribution": {platform: count for platform, count in platform_stats},
                "intent_distribution": {intent: count for intent, count in intent_stats}
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(e)}")


@router.get("/analytics/conversations")
async def get_conversation_analytics(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    time_range: str = "7d",
    token: str = Depends(verify_token)
):
    """获取对话分析数据"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        if time_range == "1d":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        async for session in get_db_session():
            query = session.query(ConversationAnalytics).filter(
                ConversationAnalytics.created_at >= start_date,
                ConversationAnalytics.created_at <= end_date
            )
            
            if session_id:
                query = query.filter(ConversationAnalytics.session_id == session_id)
            elif user_id:
                query = query.filter(ConversationAnalytics.user_id == user_id)
            
            analytics = await query.all()
            
            # 聚合统计
            total_conversations = len(analytics)
            
            # 意图分布聚合
            intent_distribution = {}
            emotion_distribution = {}
            response_times = []
            satisfaction_scores = []
            
            for analytic in analytics:
                # 意图分布
                if analytic.intent_distribution:
                    for intent, count in analytic.intent_distribution.items():
                        intent_distribution[intent] = intent_distribution.get(intent, 0) + count
                
                # 情感分布
                if analytic.emotion_distribution:
                    for emotion, count in analytic.emotion_distribution.items():
                        emotion_distribution[emotion] = emotion_distribution.get(emotion, 0) + count
                
                # 响应时间
                if analytic.response_time_stats:
                    response_times.append(analytic.response_time_stats.get("average", 0))
                
                # 满意度
                if analytic.satisfaction_score:
                    satisfaction_scores.append(analytic.satisfaction_score)
            
            return {
                "time_range": time_range,
                "total_conversations": total_conversations,
                "intent_distribution": intent_distribution,
                "emotion_distribution": emotion_distribution,
                "response_time_stats": {
                    "average": sum(response_times) / len(response_times) if response_times else 0,
                    "min": min(response_times) if response_times else 0,
                    "max": max(response_times) if response_times else 0
                },
                "satisfaction_stats": {
                    "average": sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0,
                    "count": len(satisfaction_scores)
                },
                "detailed_analytics": [
                    {
                        "session_id": analytic.session_id,
                        "user_id": analytic.user_id,
                        "platform": analytic.platform,
                        "intent_distribution": analytic.intent_distribution,
                        "emotion_distribution": analytic.emotion_distribution,
                        "response_time_stats": analytic.response_time_stats,
                        "satisfaction_score": analytic.satisfaction_score,
                        "message_count": analytic.message_count,
                        "created_at": analytic.created_at.isoformat()
                    }
                    for analytic in analytics
                ]
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation analytics: {str(e)}")


@router.get("/analytics/users")
async def get_user_analytics(
    time_range: str = "7d",
    group_by: str = "day",
    token: str = Depends(verify_token)
):
    """获取用户分析数据"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        if time_range == "1d":
            start_date = end_date - timedelta(days=1)
        elif time_range == "7d":
            start_date = end_date - timedelta(days=7)
        elif time_range == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=7)
        
        async for session in get_db_session():
            # 用户增长统计
            user_growth = await session.query(
                session.func.date(User.created_at).label('date'),
                session.func.count(User.id).label('count')
            ).filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).group_by(session.func.date(User.created_at)).all()
            
            # 活跃用户统计（基于会话）
            active_users = await session.query(
                session.func.date(ChatSession.created_at).label('date'),
                session.func.count(session.func.distinct(ChatSession.user_id)).label('count')
            ).filter(
                ChatSession.created_at >= start_date,
                ChatSession.created_at <= end_date
            ).group_by(session.func.date(ChatSession.created_at)).all()
            
            # 平台分布
            platform_distribution = await session.query(
                User.platform,
                session.func.count(User.id).label('count')
            ).filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).group_by(User.platform).all()
            
            # 用户行为统计
            total_users = await session.query(User).filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).count()
            
            # 会话统计
            session_stats = await session.query(
                session.func.avg(ChatSession.message_count).label('avg_messages'),
                session.func.avg(ChatSession.satisfaction_score).label('avg_satisfaction')
            ).filter(
                ChatSession.created_at >= start_date,
                ChatSession.created_at <= end_date
            ).first()
            
            return {
                "time_range": time_range,
                "user_growth": [
                    {"date": str(date), "count": count}
                    for date, count in user_growth
                ],
                "active_users": [
                    {"date": str(date), "count": count}
                    for date, count in active_users
                ],
                "platform_distribution": [
                    {"platform": platform, "count": count}
                    for platform, count in platform_distribution
                ],
                "total_users": total_users,
                "average_messages_per_session": float(session_stats.avg_messages) if session_stats.avg_messages else 0,
                "average_satisfaction_score": float(session_stats.avg_satisfaction) if session_stats.avg_satisfaction else 0
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user analytics: {str(e)}")


@router.get("/analytics/system")
async def get_system_metrics(
    metric_name: Optional[str] = None,
    hours: int = 24,
    token: str = Depends(verify_token)
):
    """获取系统指标"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        
        async for session in get_db_session():
            query = session.query(SystemMetrics).filter(
                SystemMetrics.timestamp >= start_date,
                SystemMetrics.timestamp <= end_date
            )
            
            if metric_name:
                query = query.filter(SystemMetrics.metric_name == metric_name)
            
            metrics = await query.order_by(SystemMetrics.timestamp.desc()).all()
            
            # 按指标名称分组
            metrics_by_name = {}
            for metric in metrics:
                if metric.metric_name not in metrics_by_name:
                    metrics_by_name[metric.metric_name] = []
                
                metrics_by_name[metric.metric_name].append({
                    "timestamp": metric.timestamp.isoformat(),
                    "value": metric.metric_value,
                    "tags": metric.tags
                })
            
            return {
                "time_range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "hours": hours
                },
                "metrics": metrics_by_name,
                "total_records": len(metrics)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system metrics: {str(e)}")


@router.get("/analytics/performance")
async def get_performance_metrics(
    time_range: str = "1h",
    token: str = Depends(verify_token)
):
    """获取性能指标"""
    try:
        # 计算时间范围
        end_date = datetime.now()
        if time_range == "1h":
            start_date = end_date - timedelta(hours=1)
        elif time_range == "6h":
            start_date = end_date - timedelta(hours=6)
        elif time_range == "24h":
            start_date = end_date - timedelta(hours=24)
        else:
            start_date = end_date - timedelta(hours=1)
        
        async for session in get_db_session():
            # 响应时间统计
            response_time_stats = await session.query(
                session.func.avg(Message.created_at - ChatSession.created_at).label('avg_response_time'),
                session.func.min(Message.created_at - ChatSession.created_at).label('min_response_time'),
                session.func.max(Message.created_at - ChatSession.created_at).label('max_response_time')
            ).join(ChatSession).filter(
                Message.created_at >= start_date,
                Message.created_at <= end_date,
                Message.direction == "outbound"
            ).first()
            
            # 会话处理时间
            session_duration_stats = await session.query(
                session.func.avg(ChatSession.ended_at - ChatSession.created_at).label('avg_duration'),
                session.func.min(ChatSession.ended_at - ChatSession.created_at).label('min_duration'),
                session.func.max(ChatSession.ended_at - ChatSession.created_at).label('max_duration')
            ).filter(
                ChatSession.created_at >= start_date,
                ChatSession.created_at <= end_date,
                ChatSession.ended_at.isnot(None)
            ).first()
            
            # 错误率统计（基于升级会话）
            total_sessions = await session.query(ChatSession).filter(
                ChatSession.created_at >= start_date,
                ChatSession.created_at <= end_date
            ).count()
            
            escalated_sessions = await session.query(ChatSession).filter(
                ChatSession.created_at >= start_date,
                ChatSession.created_at <= end_date,
                ChatSession.escalated == True
            ).count()
            
            return {
                "time_range": time_range,
                "response_time_stats": {
                    "average": str(response_time_stats.avg_response_time) if response_time_stats.avg_response_time else "0",
                    "min": str(response_time_stats.min_response_time) if response_time_stats.min_response_time else "0",
                    "max": str(response_time_stats.max_response_time) if response_time_stats.max_response_time else "0"
                },
                "session_duration_stats": {
                    "average": str(session_duration_stats.avg_duration) if session_duration_stats.avg_duration else "0",
                    "min": str(session_duration_stats.min_duration) if session_duration_stats.min_duration else "0",
                    "max": str(session_duration_stats.max_duration) if session_duration_stats.max_duration else "0"
                },
                "escalation_rate": escalated_sessions / total_sessions if total_sessions > 0 else 0,
                "total_sessions": total_sessions,
                "escalated_sessions": escalated_sessions
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance metrics: {str(e)}")


@router.get("/analytics/realtime")
async def get_realtime_analytics(
    token: str = Depends(verify_token)
):
    """获取实时分析数据"""
    try:
        # 获取最近5分钟的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(minutes=5)
        
        async for session in get_db_session():
            # 活跃会话数
            active_sessions = await session.query(ChatSession).filter(
                ChatSession.status == "active",
                ChatSession.last_activity >= start_date
            ).count()
            
            # 消息速率（每分钟）
            message_count = await session.query(Message).filter(
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            message_rate = message_count / 5  # 5分钟内的平均每分钟消息数
            
            # 当前在线用户数
            online_users = await session.query(session.func.count(session.func.distinct(ChatSession.user_id))).filter(
                ChatSession.status == "active",
                ChatSession.last_activity >= start_date
            ).scalar()
            
            # 升级会话数
            escalated_sessions = await session.query(ChatSession).filter(
                ChatSession.escalated == True,
                ChatSession.created_at >= start_date
            ).count()
            
            return {
                "timestamp": end_date.isoformat(),
                "active_sessions": active_sessions,
                "message_rate_per_minute": message_rate,
                "online_users": online_users,
                "escalated_sessions": escalated_sessions,
                "system_status": "healthy"  # 可以根据更多指标判断系统状态
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get realtime analytics: {str(e)}")


@router.post("/analytics/export")
async def export_analytics_data(
    export_request: Dict[str, Any],
    token: str = Depends(verify_token)
):
    """导出分析数据"""
    try:
        data_type = export_request.get("type", "conversations")
        format_type = export_request.get("format", "json")
        start_date = export_request.get("start_date")
        end_date = export_request.get("end_date")
        
        if not start_date or not end_date:
            raise HTTPException(status_code=400, detail="start_date and end_date are required")
        
        # 解析日期
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        async for session in get_db_session():
            if data_type == "conversations":
                data = await session.query(ConversationAnalytics).filter(
                    ConversationAnalytics.created_at >= start_dt,
                    ConversationAnalytics.created_at <= end_dt
                ).all()
            elif data_type == "messages":
                data = await session.query(Message).filter(
                    Message.created_at >= start_dt,
                    Message.created_at <= end_dt
                ).all()
            elif data_type == "sessions":
                data = await session.query(ChatSession).filter(
                    ChatSession.created_at >= start_dt,
                    ChatSession.created_at <= end_dt
                ).all()
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported data type: {data_type}")
            
            # 格式化数据
            if format_type == "json":
                formatted_data = [
                    {column.name: getattr(item, column.name) for column in item.__table__.columns}
                    for item in data
                ]
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {format_type}")
            
            return {
                "data_type": data_type,
                "format": format_type,
                "date_range": {
                    "start": start_date,
                    "end": end_date
                },
                "record_count": len(data),
                "data": formatted_data
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export analytics data: {str(e)}")