"""
申诉管理路由模块
提供违规申诉的API
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import json
import os
import uuid
import base64

from database import get_db
from models import SystemConfig, ViolationEvidence

router = APIRouter(prefix="/api/appeals", tags=["申诉管理"])

UPLOAD_DIR = "uploads/appeals"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============== 数据模型 ==============

class AppealCreate(BaseModel):
    """创建申诉请求"""
    violation_id: int = Field(..., description="关联的违规ID")
    reason: str = Field(..., description="申诉理由")
    contact: Optional[str] = Field(None, description="联系方式")
    evidence_urls: Optional[List[str]] = Field([], description="证据图片URL列表")

class AppealUpdate(BaseModel):
    """更新申诉状态"""
    status: Optional[str] = Field(None, description="状态: pending/reviewing/approved/rejected")
    result: Optional[str] = Field(None, description="处理结果")

class ApiResponse(BaseModel):
    """通用响应"""
    success: bool
    message: str
    data: Optional[dict] = None

# ============== 辅助函数 ==============

def _get_appeal_by_violation(db: Session, violation_id: int) -> Optional[dict]:
    """获取违规关联的申诉"""
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == f"appeal:violation:{violation_id}"
    ).first()
    if config and config.config_value:
        return json.loads(config.config_value)
    return None

def _save_appeal(db: Session, violation_id: int, appeal_data: dict):
    """保存申诉到数据库"""
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == f"appeal:violation:{violation_id}"
    ).first()
    if config:
        config.config_value = json.dumps(appeal_data)
        config.updated_at = datetime.utcnow()
    else:
        config = SystemConfig(
            config_key=f"appeal:violation:{violation_id}",
            config_value=json.dumps(appeal_data),
            description=f"申诉记录: {violation_id}"
        )
        db.add(config)
    db.commit()

# ============== API接口 ==============

@router.post("/submit", response_model=ApiResponse)
async def submit_appeal(
    appeal: AppealCreate,
    db: Session = Depends(get_db)
):
    """提交申诉"""
    # 检查违规记录是否存在
    violation = db.query(ViolationEvidence).filter(
        ViolationEvidence.id == appeal.violation_id
    ).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规记录不存在")
    
    # 检查是否已有申诉
    existing = _get_appeal_by_violation(db, appeal.violation_id)
    if existing:
        return ApiResponse(
            success=False,
            message="该违规已有申诉记录",
            data={"appeal_id": appeal.violation_id}
        )
    
    # 创建申诉记录
    now = datetime.utcnow().isoformat()
    appeal_data = {
        "violation_id": appeal.violation_id,
        "reason": appeal.reason,
        "contact": appeal.contact,
        "evidence_urls": appeal.evidence_urls,
        "status": "pending",
        "result": None,
        "created_at": now,
        "processed_at": None,
        "processed_by": None
    }
    
    _save_appeal(db, appeal.violation_id, appeal_data)
    
    # 更新违规状态为申诉中
    violation.status = "appealing"
    violation.updated_at = datetime.utcnow()
    db.commit()
    
    return ApiResponse(
        success=True,
        message="申诉提交成功",
        data={"appeal_id": appeal.violation_id, "status": "pending"}
    )

@router.post("/submit-with-image", response_model=ApiResponse)
async def submit_appeal_with_image(
    violation_id: int = Form(...),
    reason: str = Form(...),
    contact: Optional[str] = Form(None),
    evidence: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """提交申诉（带图片证据）"""
    # 处理图片
    evidence_urls = []
    if evidence:
        try:
            content = await evidence.read()
            filename = f"appeal_{violation_id}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(UPLOAD_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(content)
            evidence_urls.append(f"/uploads/appeals/{filename}")
        except Exception as e:
            pass
    
    # 创建申诉
    appeal = AppealCreate(
        violation_id=violation_id,
        reason=reason,
        contact=contact,
        evidence_urls=evidence_urls
    )
    return await submit_appeal(appeal, db)

@router.get("/list", response_model=ApiResponse)
async def list_appeals(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """获取申诉列表"""
    query = db.query(SystemConfig).filter(
        SystemConfig.config_key.like("appeal:violation:%")
    )
    
    appeals = []
    for config in query.all():
        appeal_data = json.loads(config.config_value)
        if status and appeal_data.get("status") != status:
            continue
        appeals.append(appeal_data)
    
    # 分页
    appeals.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(appeals)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = appeals[start:end]
    
    return ApiResponse(
        success=True,
        message=f"获取到{len(paginated)}条申诉",
        data={
            "appeals": paginated,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    )

@router.get("/{violation_id}", response_model=ApiResponse)
async def get_appeal(
    violation_id: int,
    db: Session = Depends(get_db)
):
    """获取申诉详情"""
    appeal_data = _get_appeal_by_violation(db, violation_id)
    if not appeal_data:
        raise HTTPException(status_code=404, detail="申诉记录不存在")
    
    # 获取违规详情
    violation = db.query(ViolationEvidence).filter(
        ViolationEvidence.id == violation_id
    ).first()
    
    violation_detail = None
    if violation:
        violation_detail = {
            "id": violation.id,
            "violation_type": violation.violation_type,
            "confidence": violation.confidence,
            "timestamp": violation.timestamp.isoformat() if violation.timestamp else None,
            "status": violation.status,
            "image_path": violation.image_path
        }
    
    return ApiResponse(
        success=True,
        message="获取申诉详情成功",
        data={
            "appeal": appeal_data,
            "violation": violation_detail
        }
    )

@router.put("/{violation_id}/process", response_model=ApiResponse)
async def process_appeal(
    violation_id: int,
    update: AppealUpdate,
    db: Session = Depends(get_db)
):
    """处理申诉"""
    appeal_data = _get_appeal_by_violation(db, violation_id)
    if not appeal_data:
        raise HTTPException(status_code=404, detail="申诉记录不存在")
    
    # 更新申诉状态
    if update.status:
        appeal_data["status"] = update.status
    if update.result:
        appeal_data["result"] = update.result
    appeal_data["processed_at"] = datetime.utcnow().isoformat()
    
    _save_appeal(db, violation_id, appeal_data)
    
    # 更新违规状态
    violation = db.query(ViolationEvidence).filter(
        ViolationEvidence.id == violation_id
    ).first()
    if violation:
        if update.status == "approved":
            violation.status = "cancelled"
        elif update.status == "rejected":
            violation.status = "confirmed"
        violation.updated_at = datetime.utcnow()
        db.commit()
    
    return ApiResponse(
        success=True,
        message="申诉处理完成",
        data={"violation_id": violation_id, "status": update.status}
    )

@router.get("/statistics/summary", response_model=ApiResponse)
async def get_appeal_statistics(
    db: Session = Depends(get_db)
):
    """获取申诉统计"""
    query = db.query(SystemConfig).filter(
        SystemConfig.config_key.like("appeal:violation:%")
    )
    
    stats = {"pending": 0, "reviewing": 0, "approved": 0, "rejected": 0}
    for config in query.all():
        appeal_data = json.loads(config.config_value)
        status = appeal_data.get("status", "pending")
        if status in stats:
            stats[status] += 1
    
    return ApiResponse(
        success=True,
        message="获取申诉统计成功",
        data=stats
    )
