"""
统计分析路由模块
提供违规数据的统计分析API
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from database import get_db
from models import ViolationEvidence

router = APIRouter(prefix="/api/statistics", tags=["统计分析"])

class StatisticsResponse(BaseModel):
    """统计响应模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class DailyStats(BaseModel):
    """每日统计"""
    date: str
    count: int

class TypeStats(BaseModel):
    """类型统计"""
    violation_type: str
    count: int
    percentage: float

class StatusStats(BaseModel):
    """状态统计"""
    status: str
    count: int
    percentage: float

@router.get("/overview", response_model=StatisticsResponse)
async def get_statistics_overview(
    db: Session = Depends(get_db)
):
    """获取统计概览（今日/本周/本月/总数）"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # 统计查询
    total_count = db.query(ViolationEvidence).count()
    today_count = db.query(ViolationEvidence).filter(
        ViolationEvidence.timestamp >= today_start
    ).count()
    week_count = db.query(ViolationEvidence).filter(
        ViolationEvidence.timestamp >= week_start
    ).count()
    month_count = db.query(ViolationEvidence).filter(
        ViolationEvidence.timestamp >= month_start
    ).count()
    
    # 按类型统计
    type_results = db.query(
        ViolationEvidence.violation_type,
        func.count(ViolationEvidence.id).label('count')
    ).group_by(ViolationEvidence.violation_type).all()
    
    type_stats = []
    for r in type_results:
        type_stats.append({
            "violation_type": r.violation_type,
            "count": r.count,
            "percentage": round(r.count / total_count * 100, 2) if total_count > 0 else 0
        })
    
    # 按状态统计
    status_results = db.query(
        ViolationEvidence.status,
        func.count(ViolationEvidence.id).label('count')
    ).group_by(ViolationEvidence.status).all()
    
    status_stats = []
    for r in status_results:
        status_stats.append({
            "status": r.status,
            "count": r.count,
            "percentage": round(r.count / total_count * 100, 2) if total_count > 0 else 0
        })
    
    return StatisticsResponse(
        success=True,
        message="获取统计成功",
        data={
            "total": total_count,
            "today": today_count,
            "week": week_count,
            "month": month_count,
            "by_type": type_stats,
            "by_status": status_stats
        }
    )

@router.get("/daily", response_model=StatisticsResponse)
async def get_daily_statistics(
    days: int = Query(7, ge=1, le=90, description="查询天数"),
    db: Session = Depends(get_db)
):
    """获取每日违规统计"""
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    results = db.query(
        func.date(ViolationEvidence.timestamp).label('date'),
        func.count(ViolationEvidence.id).label('count')
    ).filter(
        ViolationEvidence.timestamp >= start_date
    ).group_by(
        func.date(ViolationEvidence.timestamp)
    ).order_by(
        func.date(ViolationEvidence.timestamp)
    ).all()
    
    daily_stats = []
    for r in results:
        daily_stats.append({
            "date": str(r.date),
            "count": r.count
        })
    
    return StatisticsResponse(
        success=True,
        message="获取每日统计成功",
        data={"daily": daily_stats}
    )

@router.get("/type-distribution", response_model=StatisticsResponse)
async def get_type_distribution(
    period: str = Query("all", description="统计周期: today/week/month/all"),
    db: Session = Depends(get_db)
):
    """获取违规类型分布"""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    
    # 根据周期设置过滤条件
    if period == "today":
        filter_cond = ViolationEvidence.timestamp >= today_start
    elif period == "week":
        filter_cond = ViolationEvidence.timestamp >= week_start
    elif period == "month":
        filter_cond = ViolationEvidence.timestamp >= month_start
    else:
        filter_cond = True
    
    total_count = db.query(ViolationEvidence).filter(filter_cond).count()
    
    type_results = db.query(
        ViolationEvidence.violation_type,
        func.count(ViolationEvidence.id).label('count')
    ).filter(filter_cond).group_by(
        ViolationEvidence.violation_type
    ).all()
    
    distribution = []
    for r in type_results:
        distribution.append({
            "type": r.violation_type,
            "count": r.count,
            "percentage": round(r.count / total_count * 100, 2) if total_count > 0 else 0
        })
    
    return StatisticsResponse(
        success=True,
        message="获取类型分布成功",
        data={
            "total": total_count,
            "period": period,
            "distribution": distribution
        }
    )

@router.get("/hourly", response_model=StatisticsResponse)
async def get_hourly_distribution(
    db: Session = Depends(get_db)
):
    """获取24小时分布统计"""
    # 使用SQLite的strftime提取小时
    from sqlalchemy import text
    
    results = db.query(
        text("CAST(strftime('%H', timestamp) AS INTEGER)").label('hour'),
        func.count(ViolationEvidence.id).label('count')
    ).group_by(
        text("strftime('%H', timestamp)")
    ).order_by(
        text("strftime('%H', timestamp)")
    ).all()
    
    # 填充缺失的小时
    hourly_data = {i: 0 for i in range(24)}
    for r in results:
        hourly_data[r.hour] = r.count
    
    hourly_stats = [{"hour": h, "count": c} for h, c in hourly_data.items()]
    
    return StatisticsResponse(
        success=True,
        message="获取小时分布成功",
        data={"hourly": hourly_stats}
    )
