from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import base64
import os
from datetime import datetime
import uuid
import cv2

from database import get_db
from models import ViolationEvidence
from schemas import (
    ViolationEvidenceCreate, ViolationEvidenceResponse, 
    ViolationEvidenceUpdate, BatchViolationCreate, BatchViolationResponse,
    ViolationQuery, ViolationListResponse, ViolationStatistics,
    WeChatViolationSubmit, WeChatViolationListResponse, ApiResponse
)

# 导入图像识别模块
try:
    from image_recognizer import analyze_image
    RECOGNIZER_AVAILABLE = True
    print("✓ 图像识别模块已加载")
except ImportError as e:
    RECOGNIZER_AVAILABLE = False
    print(f"⚠️  图像识别模块未加载: {e}")

router = APIRouter(prefix="/api/violations", tags=["违规证据管理"])

# 文件上传目录
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# M04: 车牌图片目录按日期组织
PLATE_IMAGES_DIR = os.path.join("data", "plate_images")
os.makedirs(PLATE_IMAGES_DIR, exist_ok=True)

def save_base64_image(base64_data: str, prefix: str = "violation") -> str:
    """保存Base64图片数据 —— 返回文件名（不含目录前缀），前端统一拼接 /uploads/"""
    try:
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        image_data = base64.b64decode(base64_data)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        return filename  # 只返回文件名
    except Exception as e:
        print(f"保存图片失败: {e}")
        return None

def save_plate_image(base64_data: str, violation_id: int = None) -> str:
    """
    M04: 保存车牌小图，按日期组织
    路径格式: data/plate_images/{YYYYMMDD}/{violation_id}_{uuid8}.jpg
    返回相对路径（含日期目录）
    """
    try:
        if not base64_data:
            return ''
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        image_data = base64.b64decode(base64_data)
        date_str = datetime.now().strftime('%Y%m%d')
        date_dir = os.path.join(PLATE_IMAGES_DIR, date_str)
        os.makedirs(date_dir, exist_ok=True)
        vid_part = f"{violation_id}_" if violation_id else ""
        filename = f"{vid_part}{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(date_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        # 返回相对路径，前端通过 /api/violations/plate-image?path=... 访问
        return f"{date_str}/{filename}"
    except Exception as e:
        print(f"保存车牌图片失败: {e}")
        return ''

def save_base64_video(base64_data: str, prefix: str = "violation") -> str:
    """保存Base64视频数据 —— 返回文件名（不含目录前缀），前端统一拼接 /uploads/"""
    try:
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        video_data = base64.b64decode(base64_data)
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = os.path.join(UPLOAD_DIR, filename)
        with open(filepath, "wb") as f:
            f.write(video_data)
        return filename
    except Exception as e:
        print(f"保存视频失败: {e}")
        return None

def save_upload_file(filename: str, content: bytes) -> str:
    """保存上传的文件（multipart） —— 返回文件名"""
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filename

@router.post("/submit", response_model=ApiResponse)
async def submit_violation(
    violation: ViolationEvidenceCreate,
    db: Session = Depends(get_db)
):
    """提交单个违规证据（带图像识别）"""
    try:
        # 处理图片数据
        image_path = None
        if violation.image_data:
            image_path = save_base64_image(violation.image_data)
        
        # 处理视频数据
        video_path = None
        if violation.video_data:
            video_path = save_base64_video(violation.video_data)
        
        # 图像识别分析（v3·三阶段：YOLO + 豆包 + DeepSeek 审核）
        cloud_validated = False
        cloud_result = None
        yolo_detection_result = None
        deepseek_result_text = None  # 新增：保存 DeepSeek 审核报告
        final_confidence = violation.confidence
        needs_human_review = False   # 新增：标记是否需要人工审核
        additional_info = violation.additional_info if violation.additional_info else {}

        if image_path and RECOGNIZER_AVAILABLE:
            full_image_path = os.path.join(UPLOAD_DIR, image_path)
            print(f"🔍 开始图像识别分析: {full_image_path}")
            try:
                result = analyze_image(full_image_path, violation.violation_type)
                print(f"📊 识别结果: {result}")

                # 保存 YOLO 检测结果
                if result.get('yolo_result'):
                    yolo_detection_result = json.dumps(result['yolo_result'])

                # 保存豆包分析结果（作为辅助信息）
                if result.get('doubao_result') and result['doubao_result'].get('success'):
                    cloud_result = result['doubao_result']['result_text']

                # 保存 DeepSeek 审核报告（新增）
                if result.get('deepseek_result') and result['deepseek_result'].get('success'):
                    deepseek_result_text = result['deepseek_result']['result_text']

                # 使用系统的最终决策作为 cloud_validated
                cloud_validated = result.get('final_decision', False)

                # 使用系统的最终置信度
                if result.get('final_confidence') is not None:
                    final_confidence = result['final_confidence']

                # 保存 DeepSeek 标记的"需人工审核"状态
                needs_human_review = result.get('needs_human_review', False)

                # 保存完整 AI 推理链（便于前端展示）
                if result.get('ai_trace'):
                    additional_info['ai_trace'] = result['ai_trace']

                # 记录分析状态
                if result.get('fallback', False):
                    additional_info['analysis_note'] = "模型未运行，使用兜底结果"
                elif result.get('success', False):
                    note = "已完成 YOLO + 豆包 + DeepSeek 三阶段审核（v3）"
                    if needs_human_review:
                        note += "（标记为待人工审核）"
                    additional_info['analysis_note'] = note
                else:
                    additional_info['analysis_note'] = result.get('message', '分析失败')

            except Exception as e:
                print(f"⚠️  图像识别异常: {e}")
                additional_info['analysis_note'] = f"分析异常: {str(e)}"
        else:
            additional_info['analysis_note'] = "未进行图像识别（无图片或识别模块未加载）"

        # 保存 DeepSeek 审核结果到 additional_info
        if deepseek_result_text:
            additional_info['deepseek_audit'] = deepseek_result_text
        additional_info['needs_human_review'] = needs_human_review

        # M04: 处理车牌相关字段
        plate_image_path = ''
        if violation.plate_image_data:
            plate_image_path = save_plate_image(violation.plate_image_data, violation_id=None)

        # 创建违规记录（最终决策来自系统引擎，而非仅豆包）
        db_violation = ViolationEvidence(
            violation_type=violation.violation_type,
            track_id=violation.track_id,
            confidence=final_confidence,
            position=json.dumps(violation.position),
            timestamp=datetime.fromisoformat(violation.timestamp),
            image_path=image_path,
            video_path=video_path,
            additional_info=json.dumps(additional_info),
            cloud_validated=cloud_validated,
            cloud_result=cloud_result,
            yolo_detection_result=yolo_detection_result,
            # M04: 车牌绑定字段
            plate_number=violation.plate_number or '',
            plate_confidence=violation.plate_confidence if violation.plate_confidence is not None else 0.0,
            plate_image_path=plate_image_path,
            plate_color=violation.plate_color or 'unknown',
            confirmed_frames=violation.confirmed_frames or 0,
            # v3：需要人工审核时，即使系统标为违规，也强制置为 pending_review
            status="pending_review" if needs_human_review else ("confirmed" if cloud_validated else "pending")
        )

        db.add(db_violation)
        db.commit()
        db.refresh(db_violation)

        # M04: 如果车牌图片未带 violation_id，则用 commit 后的 id 重命名（保持路径一致即可，不强制重命名）
        # 这里只更新 plate_image_path 中含 violation_id 的信息记录到 additional_info
        if plate_image_path and db_violation.id:
            try:
                ai = json.loads(db_violation.additional_info) if db_violation.additional_info else {}
                ai['plate_image_path'] = plate_image_path
                db_violation.additional_info = json.dumps(ai)
                db.commit()
            except Exception:
                pass
        
        return ApiResponse(
            success=True,
            message="违规证据提交成功",
            data={
                "id": db_violation.id, 
                "image_path": image_path, 
                "video_path": video_path,
                "cloud_validated": cloud_validated,
                "confidence": final_confidence
            }
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
    plate_number: Optional[str] = None,
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
    # M04: 车牌号模糊查询
    if plate_number:
        query = query.filter(ViolationEvidence.plate_number.like(f"%{plate_number}%"))

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

@router.get("/plate/{plate_number}")
async def get_violations_by_plate(
    plate_number: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """
    M04: 按车牌号查询历史违规记录
    支持精确匹配和模糊匹配（车牌号部分字符）
    """
    try:
        # 先尝试精确匹配
        query = db.query(ViolationEvidence).filter(
            ViolationEvidence.plate_number == plate_number
        )
        exact_count = query.count()

        # 如果精确匹配无结果，尝试模糊匹配
        if exact_count == 0:
            query = db.query(ViolationEvidence).filter(
                ViolationEvidence.plate_number.like(f"%{plate_number}%")
            )

        total = query.count()
        violations = query.order_by(ViolationEvidence.timestamp.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()

        return {
            "success": True,
            "plate_number": plate_number,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [v.to_dict() for v in violations]
        }
    except Exception as e:
        return {"success": False, "message": f"查询失败: {str(e)}", "items": [], "total": 0}

@router.get("/plate-image/file")
async def get_plate_image(path: str):
    """
    M04: 获取车牌小图文件
    通过 ?path=YYYYMMDD/filename.jpg 访问 data/plate_images/YYYYMMDD/filename.jpg
    """
    from fastapi.responses import FileResponse
    if not path:
        raise HTTPException(status_code=400, detail="path 参数必填")
    # 安全检查：防止路径遍历
    if ".." in path or path.startswith("/") or "\\" in path:
        raise HTTPException(status_code=400, detail="非法路径")
    full_path = os.path.join(PLATE_IMAGES_DIR, path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="车牌图片不存在")
    return FileResponse(full_path, media_type="image/jpeg")

@router.get("/{violation_id}", response_model=ViolationEvidenceResponse)
async def get_violation_detail(
    violation_id: int,
    db: Session = Depends(get_db)
):
    """获取违规证据详情"""
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    result = violation.to_dict()
    
    # 将 ai_trace 提升到顶层
    if result.get('additional_info') and isinstance(result['additional_info'], dict):
        if 'ai_trace' in result['additional_info']:
            result['ai_trace'] = result['additional_info']['ai_trace']
    
    return ViolationEvidenceResponse.model_validate(result)

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

@router.put("/{violation_id}/reanalyze", response_model=ApiResponse)
async def reanalyze_violation(
    violation_id: int,
    db: Session = Depends(get_db)
):
    """重新分析违规证据（调用YOLOv8 + 豆包大模型）"""
    violation = db.query(ViolationEvidence).filter(ViolationEvidence.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="违规证据不存在")
    
    if not violation.image_path:
        return ApiResponse(
            success=False,
            message="该记录没有关联的图片",
            error_code="NO_IMAGE"
        )
    
    # 数据库存的是纯文件名，这里补全为完整路径
    image_file_full = os.path.join(UPLOAD_DIR, violation.image_path) if violation.image_path else None
    
    if not image_file_full or not os.path.exists(image_file_full):
        return ApiResponse(
            success=False,
            message="图片文件不存在",
            error_code="FILE_NOT_FOUND"
        )
    
    if not RECOGNIZER_AVAILABLE:
        return ApiResponse(
            success=False,
            message="图像识别模块未加载",
            error_code="RECOGNIZER_NOT_AVAILABLE"
        )
    
    try:
        print(f"🔄 重新分析违规记录 #{violation_id}")
        
        # 调用图像识别（v3·三阶段流程）
        result = analyze_image(image_file_full, violation.violation_type)
        
        # 获取最终决策（v3 流程已由引擎综合判定）
        final_decision = result.get('final_decision', False)
        final_conf = result.get('final_confidence', violation.confidence)
        needs_human = result.get('needs_human_review', False)
        
        # 更新数据库字段
        if result.get('yolo_result'):
            violation.yolo_detection_result = json.dumps(result['yolo_result'])
        
        # 豆包：只保留原文本作为辅助信息，不再直接用它判断状态
        if result.get('doubao_result') and result['doubao_result'].get('success'):
            violation.cloud_result = result['doubao_result']['result_text']
        
        # DeepSeek 审核报告（保存进 additional_info）
        deepseek_text = None
        if result.get('deepseek_result') and result['deepseek_result'].get('success'):
            deepseek_text = result['deepseek_result']['result_text']
        
        # 核心状态字段：使用系统的最终决策
        violation.cloud_validated = final_decision
        if final_conf is not None:
            violation.confidence = final_conf
        
        # v3 状态：需人工审核时，强制标记为 pending_review
        if needs_human:
            violation.status = "pending_review"
        else:
            violation.status = "confirmed" if final_decision else "pending"
        
        # 更新附加信息
        additional_info = json.loads(violation.additional_info) if violation.additional_info else {}
        if result.get('fallback', False):
            additional_info['reanalysis_note'] = "重新分析：模型未运行，使用兜底结果"
        elif result.get('success', False):
            note = f"重新分析完成（v3·三阶段审核）：{result.get('message', '')}"
            if needs_human:
                note += "（已标记待人工审核）"
            additional_info['reanalysis_note'] = note
        else:
            additional_info['reanalysis_note'] = f"重新分析失败: {result.get('message', '未知错误')}"
        
        # 保存 DeepSeek 审核结果
        if deepseek_text:
            additional_info['deepseek_audit'] = deepseek_text
        additional_info['needs_human_review'] = needs_human
        
        # 保存 AI 推理链
        if result.get('ai_trace'):
            additional_info['ai_trace'] = result['ai_trace']
        
        violation.additional_info = json.dumps(additional_info)
        
        violation.updated_at = datetime.utcnow()
        db.commit()
        
        return ApiResponse(
            success=True,
            message="重新分析完成",
            data={
                "id": violation.id,
                "cloud_validated": violation.cloud_validated,
                "confidence": violation.confidence,
                "status": violation.status,
                "yolo_detection_result": json.loads(violation.yolo_detection_result) if violation.yolo_detection_result else None,
                "cloud_result": violation.cloud_result,
                "ai_trace": result.get('ai_trace')
            }
        )
        
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            message=f"重新分析失败: {str(e)}",
            error_code="REANALYZE_ERROR"
        )

@router.post("/upload-multipart", response_model=ApiResponse)
async def upload_violation_multipart(
    file: UploadFile = File(...),
    violation_type: str = Form("lane_departure"),
    user_note: str = Form(""),
    run_ai: bool = Form(True),
    db: Session = Depends(get_db)
):
    """
    上传文件进行智能识别（支持图片和视频）
    
    参数:
        file: 上传的文件（jpg/png/jpeg/mp4/avi）
        violation_type: 违规类型（默认 lane_departure）
        user_note: 用户备注
        run_ai: 是否立即运行 AI 分析（默认 True）
    
    返回:
        ApiResponse with analysis results
    """
    try:
        # 验证文件类型
        allowed_image_exts = ['.jpg', '.jpeg', '.png']
        allowed_video_exts = ['.mp4', '.avi']
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_image_exts + allowed_video_exts:
            return ApiResponse(
                success=False,
                message=f"不支持的文件类型: {file_ext}",
                error_code="INVALID_FILE_TYPE"
            )
        
        # 生成文件名
        file_uuid = uuid.uuid4().hex[:8]
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"upload_{file_uuid}_{timestamp_str}{file_ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # 保存文件
        # ★★2026-10-06 由 DSH 重写（真 bug）：
        #   原实现是 `content = await file.read()` **整个读进内存**，**然后**才判大小，
        #   而且此刻文件已 open 在磁盘上 -> 超大文件会：
        #     ① 先吃掉与文件等大的内存（1 GB 视频 = 1 GB RAM）；
        #     ② 被拒绝时已在 uploads/ 留下半个垃圾文件，永不清理。
        #   现改为**流式分块**：边读边写边累计，超限立刻中止并删掉半成品。
        #   上限同时从 50MB 提到 500MB（用户要传 120MB 的真实路口视频）。
        #   注：要测"整段长视频/数 GB"仍推荐走「实时监测」页的路径接入
        #       （后端直接读原文件，不复制、无上限）。
        MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
        _CHUNK = 1024 * 1024               # 1MB/块
        try:
            written = 0
            too_large = False
            with open(filepath, "wb") as f:
                while True:
                    chunk = await file.read(_CHUNK)
                    if not chunk:
                        break
                    written += len(chunk)
                    if written > MAX_FILE_SIZE:
                        too_large = True
                        break
                    f.write(chunk)
            if too_large:
                # 关键：把已写入的半成品删掉，不留垃圾
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                return ApiResponse(
                    success=False,
                    message=(f"文件超过 {MAX_FILE_SIZE // (1024 * 1024)}MB 上限。"
                             f"要传更大的视频请到「实时监测」页按路径接入（不复制文件、无上限）"),
                    error_code="FILE_TOO_LARGE"
                )
        except PermissionError as pe:
            # 权限问题
            print(f"❌ 文件写入权限不足: {filepath}")
            print(f"   错误详情: {str(pe)}")
            return ApiResponse(
                success=False,
                message="服务器上传目录权限不足，请联系管理员检查 uploads 目录权限配置",
                error_code="PERMISSION_DENIED"
            )
        except OSError as oe:
            # 其他系统错误（文件锁定等）
            print(f"❌ 文件写入失败: {filepath}")
            print(f"   错误详情: {str(oe)}")
            return ApiResponse(
                success=False,
                message=f"文件写入失败，可能是文件被其他程序占用: {str(oe)}",
                error_code="FILE_WRITE_ERROR"
            )
        
        # 初始化结果变量
        image_path = None
        video_path = None
        yolo_detection_result = None
        cloud_validated = False
        cloud_result = None
        final_confidence = 0.5
        ai_trace = None
        ai_error = None
        # ★2026-10-06 由 DSH 修复（真 bug）：`result` 原来**只**在"图片 + run_ai"
        #   分支里被赋值，而下面 L801 无条件读 `result.get(...)` -> 视频上传或
        #   run_ai=false 时抛 UnboundLocalError("cannot access local variable
        #   'result'")，被外层 except 兜成 UPLOAD_ERROR。
        #   **实测后果：视频上传 100% 失败**（与 50MB/500MB 上限无关）。
        #   这里补上初始化，并把下面那两行改成有值才读。
        result = None
        
        is_image = file_ext in allowed_image_exts
        is_video = file_ext in allowed_video_exts
        
        # 数据库存纯文件名，分析时用完整路径
        if is_image:
            image_path = filename
            full_image_path = filepath
        else:
            video_path = filename
            full_image_path = None
        
        # AI 分析
        if run_ai and RECOGNIZER_AVAILABLE:
            if is_image:
                # 图片分析
                try:
                    print(f"🔍 开始图像识别分析: {full_image_path}")
                    result = analyze_image(full_image_path, violation_type)
                    print(f"📊 识别结果: {result}")
                    
                    # 保存 YOLO 检测结果
                    if result.get('yolo_result'):
                        yolo_detection_result = json.dumps(result['yolo_result'])
                    
                    # 保存豆包分析结果
                    if result.get('doubao_result') and result['doubao_result'].get('success'):
                        cloud_validated = result['doubao_result']['is_violation_confirmed']
                        cloud_result = result['doubao_result']['result_text']
                    
                    # 更新置信度
                    if result.get('final_confidence'):
                        final_confidence = result['final_confidence']
                    
                    # 保存 AI 推理链
                    if result.get('ai_trace'):
                        ai_trace = result['ai_trace']
                        
                except Exception as e:
                    ai_error = f"AI分析异常: {str(e)}"
                    print(f"⚠️  {ai_error}")
                    
            elif is_video:
                # 视频分析（降级处理）
                ai_error = None
                try:
                    # 提取首帧
                    cap = cv2.VideoCapture(filepath)
                    ret, frame = cap.read()
                    cap.release()
                    
                    if not ret:
                        ai_error = "无法读取视频首帧"
                    else:
                        # 保存首帧为缩略图
                        thumbnail_filename = f"upload_{file_uuid}_{timestamp_str}_frame.jpg"
                        thumbnail_path = os.path.join(UPLOAD_DIR, thumbnail_filename)
                        cv2.imwrite(thumbnail_path, frame)
                        image_path = thumbnail_filename  # 数据库存纯文件名
                        
                        # 安全地调用 YOLO 检测（先检查是否可用）
                        try:
                            from image_recognizer import detect_with_yolo
                            yolo_result = detect_with_yolo(thumbnail_path)
                            if yolo_result and yolo_result.get('success'):
                                yolo_detection_result = json.dumps(yolo_result)
                                ai_trace = {
                                    'yolo_raw': yolo_result,
                                    'doubao_prompt': '',
                                    'doubao_raw_text': '',
                                    'final_decision': '视频分析待接入（仅本地检测）',
                                    'yolo_duration_ms': 0,
                                    'doubao_duration_ms': 0,
                                    'total_duration_ms': 0,
                                    'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'finished_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                }
                        except Exception as yolo_e:
                            print(f"⚠️  视频 YOLO 检测失败: {yolo_e}")
                            # YOLO 失败不影响主流程，继续
                        
                        cloud_result = "视频分析功能待接入（当前仅支持图片云端AI识别），已对首帧完成本地对象检测作为参考"
                        cloud_validated = False
                        
                except Exception as video_e:
                    ai_error = f"视频处理异常: {str(video_e)}"
                    print(f"⚠️  {ai_error}")
        else:
            ai_error = "未进行AI分析（run_ai=False 或识别模块未加载）"
        
        # 创建违规记录
        additional_info = {
            'source': 'web-admin_upload',
            'user_note': user_note,
            'original_filename': file.filename
        }
        
        if ai_error:
            additional_info['ai_error'] = ai_error
        
        if ai_trace:
            additional_info['ai_trace'] = ai_trace
        
        # 保存 DeepSeek 审核结果和人工审核标记
        # ★2026-10-06 由 DSH 加 `result` 判空：视频分支 / run_ai=false 时 result 为 None
        if isinstance(result, dict) and result.get('deepseek_result') \
                and result['deepseek_result'].get('success'):
            additional_info['deepseek_audit'] = result['deepseek_result']['result_text']
        additional_info['needs_human_review'] = bool(
            result.get('needs_human_review', False)) if isinstance(result, dict) else False
        
        db_violation = ViolationEvidence(
            violation_type=violation_type,
            track_id=int(file_uuid, 16) % 10000,  # 使用 UUID 生成 track_id
            confidence=final_confidence,
            position=json.dumps({'x': 0, 'y': 0, 'width': 0, 'height': 0}),
            timestamp=datetime.now(),
            image_path=image_path,
            video_path=video_path,
            additional_info=json.dumps(additional_info),
            cloud_validated=cloud_validated,
            cloud_result=cloud_result,
            yolo_detection_result=yolo_detection_result,
            status="confirmed" if cloud_validated else "pending"
        )
        
        db.add(db_violation)
        db.commit()
        db.refresh(db_violation)
        
        return ApiResponse(
            success=True,
            message="上传成功" + ("，AI分析完成" if run_ai and not ai_error else ""),
            data={
                "id": db_violation.id,
                "image_path": image_path,
                "video_path": video_path,
                "yolo_detection_result": json.loads(yolo_detection_result) if yolo_detection_result else None,
                "cloud_result": cloud_result,
                "cloud_validated": cloud_validated,
                "confidence": final_confidence,
                "ai_trace": ai_trace
            }
        )
        
    except Exception as e:
        db.rollback()
        return ApiResponse(
            success=False,
            message=f"上传失败: {str(e)}",
            error_code="UPLOAD_ERROR"
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