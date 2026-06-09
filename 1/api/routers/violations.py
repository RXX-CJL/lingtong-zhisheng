from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import base64
import os
from datetime import datetime
import uuid

from database import get_db
from models import ViolationEvidence
from schemas import (
    ViolationEvidenceCreate, ViolationEvidenceResponse, 
    ViolationEvidenceUpdate, BatchViolationCreate, BatchViolationResponse,
    ViolationQuery, ViolationListResponse, ViolationStatistics,
    WeChatViolationSubmit, WeChatViolationListResponse, ApiResponse
)

router = APIRouter(prefix="/api/violations", tags=["违规证据管理"])

# 文件上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_base64_image(base64_data: str, prefix: str = "violation") -> str:
    """保存Base64图片数据"""
    try:
        # 移除数据URL前缀
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        # 解码Base64数据
        image_data = base64.b64decode(base64_data)
        
        # 生成文件名
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # 保存文件
        with open(filepath, "wb") as f:
            f.write(image_data)
        
        return filepath
    except Exception as e:
        print(f"保存图片失败: {e}")
        return None

def save_base64_video(base64_data: str, prefix: str = "violation") -> str:
    """保存Base64视频数据"""
    try:
        # 移除数据URL前缀
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        # 解码Base64数据
        video_data = base64.b64decode(base64_data)
        
        # 生成文件名
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # 保存文件
        with open(filepath, "wb") as f:
            f.write(video_data)
        
        return filepath
    except Exception as e:
        print(f"保存视频失败: {e}")
        return None

@router.post("/submit", response_model=ApiResponse)
async def submit_violation(
    violation: ViolationEvidenceCreate,
    db: Session = Depends(get_db)
):
    """提交单个违规证据"""
    try:
        # 处理图片数据
        image_path = None
        if violation.image_data:
            image_path = save_base64_image(violation.image_data)
        
        # 处理视频数据
        video_path = None
        if violation.video_data:
            video_path = save_base64_video(violation.video_data)
        
        # 创建违规记录
        db_violation = ViolationEvidence(
            violation_type=violation.violation_type,
            track_id=violation.track_id,
            confidence=violation.confidence,
            position=json.dumps(violation.position),
            timestamp=datetime.fromisoformat(violation.timestamp),
            image_path=image_path,
            video_path=video_path,
            additional_info=json.dumps(violation.additional_info) if violation.additional_info else None
        )
        
        db.add(db_violation)
        db.commit()
        db.refresh(db_violation)
        
        return ApiResponse(
            success=True,
            message="违规证据提交成功",
            data={"id": db_violation.id, "image_path": image_path, "video_path": video_path}
        )
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            message=f"提交失败: {str(e)}",
            error_code="SUBMIT_ERROR"
        )

@router.post("/batch", response_model=BatchViolationResponse)
async def batch_submit_violations(
    batch_data: BatchViolationCreate,
    db: Session = Depends(get_db)
):
    """批量提交违规证据"""
    success_count = 0
    failed_count = 0
    results = []
    
    for violation in batch_data.violations:
        try:
            # 处理图片数据
            image_path = None
            if violation.image_data:
                image_path = save_base64_image(violation.image_data)
            
            # 处理视频数据
            video_path = None
            if violation.video_data:
                video_path = save_base64_video(violation.video_data)
            
            # 创建违规记录
            db_violation = ViolationEvidence(
                violation_type=violation.violation_type,
                track_id=violation.track_id,
                confidence=violation.confidence,
                position=json.dumps(violation.position),
                timestamp=datetime.fromisoformat(violation.timestamp),
                image_path=image_path,
                video_path=video_path,
                additional_info=json.dumps(violation.additional_info) if violation.additional_info else None
            )
            
            db.add(db_violation)
            db.commit()
            db.refresh(db_violation)
            
            success_count += 1
            results.append({
                "index": batch_data.violations.index(violation),
                "success": True,
                "id": db_violation.id
            })
        except Exception as e:
            failed_count += 1
            db.rollback()
            results.append({
                "index": batch_data.violations.index(violation),
                "success": False,
                "error": str(e)
            })
    
    return BatchViolationResponse(
        success_count=success_count,
        failed_count=failed_count,
        results=results
    )

@router.get("/list", response_model=ViolationListResponse)
async def get_violation_list(
    violation_type: Optional[str] = None,
    track_id: Optional[int] = None,
    status: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """获取违规证据列表"""
    query = db.query(ViolationEvidence)
    
    # 应用过滤条件
    if violation_type:
        query = query.filter(ViolationEvidence.violation_type == violation_type)
    if track_id:
        query = query.filter(ViolationEvidence.track_id == track_id)
    if status:
        query = query.filter(ViolationEvidence.status == status)
    if start_time:
        query = query.filter(ViolationEvidence.timestamp >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(ViolationEvidence.timestamp <= datetime.fromisoformat(end_time))
    
    # 获取总数
    total = query.count()
    
    # 分页查询
    violations = query.order_by(ViolationEvidence.timestamp.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return ViolationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[ViolationEvidenceResponse.model_validate(v.to_dict()) for v in violations]
    )

@router.get("/{violation_id}", response_model=ViolationEvidenceResponse)
async def get_violation_detail(
    violation_id: int,
    db: Session = Depends(get_db)
):
    """获取违规证据详情"""
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    return ViolationEvidenceResponse.model_validate(violation.to_dict())

@router.put("/{violation_id}", response_model=ApiResponse)
async def update_violation(
    violation_id: int,
    update_data: ViolationEvidenceUpdate,
    db: Session = Depends(get_db)
):
    """更新违规证据"""
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    # 更新字段
    if update_data.status is not None:
        violation.status = update_data.status
    if update_data.cloud_validated is not None:
        violation.cloud_validated = update_data.cloud_validated
    if update_data.cloud_result is not None:
        violation.cloud_result = update_data.cloud_result
    
    violation.updated_at = datetime.utcnow()
    db.commit()
    
    return ApiResponse(
        success=True,
        message="更新成功",
        data={"id": violation.id}
    )

@router.delete("/{violation_id}", response_model=ApiResponse)
async def delete_violation(
    violation_id: int,
    db: Session = Depends(get_db)
):
    """删除违规证据"""
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    # 删除关联的文件
    if violation.image_path and os.path.exists(violation.image_path):
        os.remove(violation.image_path)
    if violation.video_path and os.path.exists(violation.video_path):
        os.remove(violation.video_path)
    
    db.delete(violation)
    db.commit()
    
    return ApiResponse(
        success=True,
        message="删除成功",
        data={"id": violation_id}
    )

@router.get("/statistics/summary", response_model=ViolationStatistics)
async def get_violation_statistics(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取违规统计信息"""
    query = db.query(ViolationEvidence)
    
    if start_time:
        query = query.filter(ViolationEvidence.timestamp >= datetime.fromisoformat(start_time))
    if end_time:
        query = query.filter(ViolationEvidence.timestamp <= datetime.fromisoformat(end_time))
    
    violations = query.all()
    
    # 按类型统计
    by_type = {}
    for v in violations:
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
    
    # 按状态统计
    by_status = {}
    for v in violations:
        by_status[v.status] = by_status.get(v.status, 0) + 1
    
    # 按日期统计
    by_date = {}
    for v in violations:
        date_str = v.timestamp.strftime('%Y-%m-%d')
        by_date[date_str] = by_date.get(date_str, 0) + 1
    
    return ViolationStatistics(
        total_count=len(violations),
        by_type=by_type,
        by_status=by_status,
        by_date=by_date
    )