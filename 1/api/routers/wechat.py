from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from database import get_db
from models import ViolationEvidence
from schemas import (
    WeChatViolationSubmit, WeChatViolationListResponse, 
    ViolationEvidenceResponse, ApiResponse
)

router = APIRouter(prefix="/api/wechat", tags=["微信小程序"])

# 模拟的微信用户验证函数（实际项目中需要对接微信API）
def verify_wechat_user(openid: str) -> bool:
    """验证微信用户"""
    # 这里应该调用微信API验证openid
    # 暂时简化处理，假设所有openid都有效
    return bool(openid and len(openid) > 10)

@router.post("/violation/submit", response_model=ApiResponse)
async def wechat_submit_violation(
    violation_data: WeChatViolationSubmit,
    db: Session = Depends(get_db)
):
    """微信小程序提交违规证据"""
    try:
        # 验证微信用户
        if not verify_wechat_user(violation_data.openid):
            return ApiResponse(
                success=False,
                message="微信用户验证失败",
                error_code="WECHAT_AUTH_FAILED"
            )
        
        # 调用通用的违规提交逻辑
        from routers.violations import save_base64_image, save_base64_video
        import json
        import uuid
        
        # 处理图片数据
        image_path = None
        if violation_data.violation_data.image_data:
            image_path = save_base64_image(violation_data.violation_data.image_data, "wechat")
        
        # 处理视频数据
        video_path = None
        if violation_data.violation_data.video_data:
            video_path = save_base64_video(violation_data.violation_data.video_data, "wechat")
        
        # 创建违规记录
        db_violation = ViolationEvidence(
            violation_type=violation_data.violation_data.violation_type,
            track_id=violation_data.violation_data.track_id,
            confidence=violation_data.violation_data.confidence,
            position=json.dumps(violation_data.violation_data.position),
            timestamp=datetime.fromisoformat(violation_data.violation_data.timestamp),
            image_path=image_path,
            video_path=video_path,
            additional_info=json.dumps({
                **violation_data.violation_data.additional_info,
                'wechat_openid': violation_data.openid,
                'device_info': violation_data.device_info
            }) if violation_data.violation_data.additional_info else json.dumps({
                'wechat_openid': violation_data.openid,
                'device_info': violation_data.device_info
            })
        )
        
        db.add(db_violation)
        db.commit()
        db.refresh(db_violation)
        
        return ApiResponse(
            success=True,
            message="微信小程序违规证据提交成功",
            data={
                "id": db_violation.id,
                "image_path": image_path,
                "video_path": video_path,
                "openid": violation_data.openid
            }
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            message=f"提交失败: {str(e)}",
            error_code="WECHAT_SUBMIT_ERROR"
        )

@router.get("/violation/list", response_model=WeChatViolationListResponse)
async def wechat_get_violation_list(
    openid: str,
    violation_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """微信小程序获取违规列表"""
    # 验证微信用户
    if not verify_wechat_user(openid):
        raise HTTPException(status_code=401, detail="微信用户验证失败")
    
    query = db.query(ViolationEvidence)
    
    # 只返回该用户提交的违规记录
    query = query.filter(ViolationEvidence.additional_info.like(f'%"wechat_openid": "{openid}"%'))
    
    # 应用其他过滤条件
    if violation_type:
        query = query.filter(ViolationEvidence.violation_type == violation_type)
    if status:
        query = query.filter(ViolationEvidence.status == status)
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    violations = query.order_by(ViolationEvidence.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    # 判断是否有更多数据
    has_more = (page * page_size) < total
    
    return WeChatViolationListResponse(
        total=total,
        has_more=has_more,
        items=[ViolationEvidenceResponse.model_validate(v.to_dict()) for v in violations]
    )

@router.get("/violation/{violation_id}", response_model=ApiResponse)
async def wechat_get_violation_detail(
    violation_id: int,
    openid: str,
    db: Session = Depends(get_db)
):
    """微信小程序获取违规详情"""
    # 验证微信用户
    if not verify_wechat_user(openid):
        raise HTTPException(status_code=401, detail="微信用户验证失败")
    
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    # 检查是否是该用户的记录
    if not (violation.additional_info and f'"wechat_openid": "{openid}"' in violation.additional_info):
        raise HTTPException(status_code=403, detail="无权访问此记录")
    
    return ApiResponse(
        success=True,
        message="获取成功",
        data=violation.to_dict()
    )

@router.get("/statistics/my", response_model=ApiResponse)
async def wechat_get_my_statistics(
    openid: str,
    db: Session = Depends(get_db)
):
    """微信小程序获取我的统计信息"""
    # 验证微信用户
    if not verify_wechat_user(openid):
        raise HTTPException(status_code=401, detail="微信用户验证失败")
    
    # 查询该用户的所有违规记录
    violations = db.query(ViolationEvidence).filter(
        ViolationEvidence.additional_info.like(f'%"wechat_openid": "{openid}"%')
    ).all()
    
    # 统计信息
    total_count = len(violations)
    by_type = {}
    by_status = {}
    
    for v in violations:
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
        by_status[v.status] = by_status.get(v.status, 0) + 1
    
    return ApiResponse(
        success=True,
        message="获取统计信息成功",
        data={
            "total_count": total_count,
            "by_type": by_type,
            "by_status": by_status
        }
    )