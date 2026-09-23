# -*- coding: utf-8 -*-
"""
端云协作 API 路由模块

提供本地AI主动咨询云端AI的接口，包含：
1. POST /api/cloud/consult            - 本地AI主动咨询云端（核心接口）
2. GET  /api/cloud/collab-list         - 获取协作记录列表（支持分页）
3. GET  /api/cloud/collab-detail/{id}  - 获取单次协作详情
4. GET  /api/cloud/statistics          - 获取协作统计数据
5. GET  /api/cloud/disagreements       - 获取分歧案例列表（待人工复核）
6. POST /api/cloud/resolve-disagreement - 人工裁决分歧案例

响应统一包含 ai_trace v3 嵌套结构（yolo / doubao / deepseek / final）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import ViolationEvidence, CollaborationSession
from cloud_collaborator import CloudCollaborator
import uuid
import json
import os
import base64
import logging
from datetime import datetime

logger = logging.getLogger("zhitong_api")

router = APIRouter(prefix="/api/cloud", tags=["端云协作管理"])

# 文件上传目录（与 violations.py 保持一致）
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ============================================================
# Pydantic 请求模型
# ============================================================

class LocalJudgment(BaseModel):
    """本地AI判断结果"""
    violation_type: str  # 违规类型（英文，如 no_helmet）
    violation_cn: Optional[str] = None  # 违规类型中文（如 未戴头盔）
    confidence: float  # 本地置信度 (0-1)
    detections: Optional[List[dict]] = None  # 检测对象列表


class ConsultRequest(BaseModel):
    """咨询云端请求模型"""
    session_id: str  # 会话ID（UUID）
    image_base64: str  # 图像Base64数据（可带 data:image/jpeg;base64, 前缀）
    local_judgment: LocalJudgment  # 本地判断结果
    consult_reason: str = "low_confidence"  # 咨询原因
    urgency: str = "normal"  # 紧急程度 normal / urgent


class ResolveDisagreementRequest(BaseModel):
    """人工裁决分歧请求模型"""
    session_id: str  # 协作会话ID
    resolution: str  # 裁决结果：confirmed / rejected
    resolver_id: int  # 裁决人用户ID


# ============================================================
# 工具函数
# ============================================================

def save_base64_image(base64_data: str, prefix: str = "cloud") -> Optional[str]:
    """保存 Base64 图片数据，返回文件名；失败时返回 None"""
    try:
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        image_bytes = base64.b64decode(base64_data)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return filename
    except Exception as e:
        logger.warning(f"[cloud_collab] 保存图片失败: {e}")
        return None


# ============================================================
# 1. POST /api/cloud/consult - 本地AI主动咨询云端（核心接口）
# ============================================================

@router.post("/consult")
async def consult_cloud(req: ConsultRequest, db: Session = Depends(get_db)):
    """
    本地AI主动咨询云端（核心接口）

    流程：
        1. 接收本地判断结果 + 图像
        2. 实例化 CloudCollaborator
        3. 调用 consult_cloud → process_cloud_response → build_ai_trace
        4. 保存到 CollaborationSession 表
        5. 返回完整响应（含 ai_trace v3）
    """
    try:
        # 1. 保存图片（用于云端视觉分析及后续取证）
        image_filename = save_base64_image(req.image_base64, prefix="cloud")
        image_path_for_cloud = os.path.join(UPLOAD_DIR, image_filename) if image_filename else None

        # 2. 实例化协作管理器
        collaborator = CloudCollaborator()

        # 3. 构造本地判断字典（透传 yolo_result 给 DeepSeek 审核）
        detections = req.local_judgment.detections or []
        local_judgment_dict = {
            'violation_type': req.local_judgment.violation_type,
            'confidence': req.local_judgment.confidence,
            'detections': detections,
            'yolo_result': {
                'violation_type': req.local_judgment.violation_type,
                'confidence': req.local_judgment.confidence,
                'detections': detections,
            },
            'is_violation': bool(req.local_judgment.violation_type),
        }

        # 触发原因映射：urgency=urgent → urgent；其他 → consult
        reason = "urgent" if req.urgency == "urgent" else "consult"

        # 4. 调用云端咨询（豆包视觉 + DeepSeek 二次审核）
        cloud_result = collaborator.consult_cloud(
            image_data=image_path_for_cloud or req.image_base64,
            local_judgment=local_judgment_dict,
            reason=reason,
        )

        # 5. 处理云端响应，生成最终裁决
        final_result = collaborator.process_cloud_response(
            local_result=local_judgment_dict,
            cloud_result=cloud_result,
        )

        # 6. 构建 ai_trace v3 嵌套结构
        ai_trace = collaborator.build_ai_trace(
            yolo_result=local_judgment_dict.get('yolo_result', {}),
            doubao_result=cloud_result.get('doubao_result', {}),
            deepseek_result=cloud_result.get('deepseek_result', {}),
            final_result=final_result,
        )

        # 7. 保存到数据库 CollaborationSession 表
        session_record = CollaborationSession(
            session_id=req.session_id,
            violation_type=req.local_judgment.violation_type,
            local_confidence=req.local_judgment.confidence,
            final_confidence=final_result.get('confidence', 0.0),
            judgment_result=final_result.get('judgment', 'pending_review'),
            disagreement=bool(final_result.get('disagreement_flag', False)),
            resolved=False,
            resolver_id=None,
            ai_trace_json=json.dumps({
                'ai_trace': ai_trace,
                'cloud_result': cloud_result,
                'final_result': final_result,
            }, ensure_ascii=False),
            image_path=image_filename,
            created_at=datetime.utcnow(),
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

        # 8. 保存协作日志到 JSON 文件（不阻塞主流程）
        try:
            collaborator.save_collaboration_log(req.session_id, {
                'session_id': req.session_id,
                'local_judgment': local_judgment_dict,
                'cloud_result': cloud_result,
                'final_result': final_result,
                'ai_trace': ai_trace,
                'reason': reason,
            })
        except Exception as log_err:
            logger.warning(f"[cloud/consult] 保存协作日志失败: {log_err}")

        # 9. 组装响应（含 ai_trace v3 + 证据列表）
        evidence = []
        doubao_res = cloud_result.get('doubao_result', {}) or {}
        deepseek_res = cloud_result.get('deepseek_result', {}) or {}
        if doubao_res.get('success'):
            evidence.append({
                'source': 'doubao',
                'judgment': 'confirmed' if doubao_res.get('is_violation_confirmed') else 'rejected',
                'confidence': float(doubao_res.get('confidence_adjusted', 0.0)),
                'reasoning': doubao_res.get('result_text', ''),
            })
        if deepseek_res.get('success'):
            evidence.append({
                'source': 'deepseek',
                'judgment': 'confirmed' if deepseek_res.get('is_violation_confirmed') else 'rejected',
                'confidence': float(deepseek_res.get('confidence_adjusted', 0.0)),
                'reasoning': deepseek_res.get('result_text', ''),
            })

        return {
            'success': True,
            'session_id': req.session_id,
            'final_judgment': final_result.get('judgment', 'pending_review'),
            'final_confidence': float(final_result.get('confidence', 0.0)),
            'ai_trace': ai_trace,
            'evidence': evidence,
            'disagreement': bool(final_result.get('disagreement_flag', False)),
            'learning_hint': None,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[cloud/consult] 咨询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"咨询失败: {str(e)}")


# ============================================================
# 2. GET /api/cloud/collab-list - 获取协作记录列表（分页）
# ============================================================

@router.get("/collab-list")
async def get_collab_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    violation_type: Optional[str] = Query(None, description="违规类型过滤"),
    judgment: Optional[str] = Query(None, description="裁决结果过滤"),
    db: Session = Depends(get_db),
):
    """获取协作记录列表（支持分页），按 created_at 倒序"""
    query = db.query(CollaborationSession)
    if violation_type:
        query = query.filter(CollaborationSession.violation_type == violation_type)
    if judgment:
        query = query.filter(CollaborationSession.judgment_result == judgment)

    total = query.count()
    items = (
        query.order_by(CollaborationSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': [item.to_dict() for item in items],
    }


# ============================================================
# 3. GET /api/cloud/collab-detail/{id} - 获取单次协作详情
# ============================================================

@router.get("/collab-detail/{record_id}")
async def get_collab_detail(record_id: int, db: Session = Depends(get_db)):
    """获取单次协作详情，返回完整 ai_trace_json 解析后的数据"""
    record = db.query(CollaborationSession).filter(
        CollaborationSession.id == record_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="协作记录不存在")

    result = record.to_dict()
    # 将 ai_trace_json 字段重命名为 ai_trace 以提升前端可读性
    result['ai_trace'] = result.pop('ai_trace_json', None)
    return result


# ============================================================
# 4. GET /api/cloud/statistics - 获取协作统计数据
# ============================================================

@router.get("/statistics")
async def get_statistics(db: Session = Depends(get_db)):
    """
    获取协作统计数据：
    - log_statistics: 来自 CloudCollaborator.get_statistics() 的日志文件聚合
    - db_statistics : 来自数据库 CollaborationSession 表的聚合
    """
    collaborator = CloudCollaborator()
    log_stats = collaborator.get_statistics()

    # 数据库聚合统计
    total_sessions = db.query(CollaborationSession).count()
    confirmed = db.query(CollaborationSession).filter(
        CollaborationSession.judgment_result == 'confirmed'
    ).count()
    rejected = db.query(CollaborationSession).filter(
        CollaborationSession.judgment_result == 'rejected'
    ).count()
    pending = db.query(CollaborationSession).filter(
        CollaborationSession.judgment_result == 'pending_review'
    ).count()
    disagreements = db.query(CollaborationSession).filter(
        CollaborationSession.disagreement == True  # noqa: E712
    ).count()
    unresolved = db.query(CollaborationSession).filter(
        CollaborationSession.disagreement == True,  # noqa: E712
        CollaborationSession.resolved == False,  # noqa: E712
    ).count()

    return {
        'log_statistics': log_stats,
        'db_statistics': {
            'total_sessions': total_sessions,
            'confirmed_count': confirmed,
            'rejected_count': rejected,
            'pending_review_count': pending,
            'disagreement_count': disagreements,
            'unresolved_disagreement_count': unresolved,
        },
    }


# ============================================================
# 5. GET /api/cloud/disagreements - 获取分歧案例列表（待人工复核）
# ============================================================

@router.get("/disagreements")
async def get_disagreements(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取分歧案例列表（disagreement=True 且 resolved=False），按 created_at 倒序"""
    query = db.query(CollaborationSession).filter(
        CollaborationSession.disagreement == True,  # noqa: E712
        CollaborationSession.resolved == False,  # noqa: E712
    )
    total = query.count()
    items = (
        query.order_by(CollaborationSession.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'items': [item.to_dict() for item in items],
    }


# ============================================================
# 6. POST /api/cloud/resolve-disagreement - 人工裁决分歧案例
# ============================================================

@router.post("/resolve-disagreement")
async def resolve_disagreement(req: ResolveDisagreementRequest, db: Session = Depends(get_db)):
    """
    人工裁决分歧案例

    接收 {session_id, resolution, resolver_id}，更新：
    - resolved       = True
    - resolver_id    = req.resolver_id
    - resolved_at    = now
    - judgment_result = req.resolution（覆盖原裁决结果）
    """
    record = db.query(CollaborationSession).filter(
        CollaborationSession.session_id == req.session_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="协作会话不存在")

    if req.resolution not in ('confirmed', 'rejected'):
        raise HTTPException(
            status_code=400,
            detail="resolution 必须为 confirmed 或 rejected"
        )

    record.resolved = True
    record.resolver_id = req.resolver_id
    record.resolved_at = datetime.utcnow()
    record.judgment_result = req.resolution

    db.commit()
    db.refresh(record)

    return {
        'success': True,
        'session_id': req.session_id,
        'resolution': req.resolution,
        'resolver_id': req.resolver_id,
        'resolved_at': record.resolved_at.isoformat() if record.resolved_at else None,
    }
