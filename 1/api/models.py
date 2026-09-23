from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json

Base = declarative_base()

class ViolationEvidence(Base):
    """违规证据表"""
    __tablename__ = "violation_evidences"

    id = Column(Integer, primary_key=True, index=True)
    violation_type = Column(String(50), index=True)  # 违规类型
    track_id = Column(Integer, index=True)  # 跟踪ID
    confidence = Column(Float)  # 置信度
    position = Column(Text)  # 位置信息 (JSON格式)
    timestamp = Column(DateTime, index=True)  # 时间戳
    image_path = Column(String(255))  # 图片路径
    video_path = Column(String(255))  # 视频路径
    additional_info = Column(Text)  # 附加信息 (JSON格式)
    cloud_validated = Column(Boolean, default=False)  # 是否云端验证
    cloud_result = Column(Text)  # 云端验证结果
    yolo_detection_result = Column(Text)  # YOLO检测结果 (JSON格式)
    status = Column(String(20), default="pending")  # 状态: pending, confirmed, rejected
    # M04: 车牌与违规记录绑定字段
    plate_number = Column(String(20), index=True)  # 车牌号
    plate_confidence = Column(Float)  # 车牌识别置信度
    plate_image_path = Column(String(255))  # 车牌小图路径
    plate_color = Column(String(20))  # 车牌颜色: blue/green/yellow/unknown
    confirmed_frames = Column(Integer, default=0)  # 多帧确认命中数
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        result = {
            'id': self.id,
            'violation_type': self.violation_type,
            'track_id': self.track_id,
            'confidence': self.confidence,
            'position': json.loads(self.position) if self.position else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'image_path': self.image_path,
            'video_path': self.video_path,
            'cloud_validated': self.cloud_validated,
            'cloud_result': self.cloud_result,
            'status': self.status,
            # M04: 车牌绑定字段
            'plate_number': self.plate_number or '',
            'plate_confidence': self.plate_confidence if self.plate_confidence is not None else 0.0,
            'plate_image_path': self.plate_image_path or '',
            'plate_color': self.plate_color or 'unknown',
            'confirmed_frames': self.confirmed_frames or 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        # 安全处理 additional_info
        raw_additional = self.additional_info
        if raw_additional and raw_additional.strip():
            try:
                result['additional_info'] = json.loads(raw_additional)
            except:
                result['additional_info'] = None
        else:
            result['additional_info'] = None
        
        # 安全处理 yolo_detection_result
        raw_yolo = self.yolo_detection_result
        if raw_yolo and raw_yolo.strip():
            try:
                result['yolo_detection_result'] = json.loads(raw_yolo)
            except:
                result['yolo_detection_result'] = None
        else:
            result['yolo_detection_result'] = None
        
        return result

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True, index=True)
    config_value = Column(Text)
    description = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APILog(Base):
    """API调用日志表"""
    __tablename__ = "api_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    client_type = Column(String(20), index=True)  # 客户端类型: wechat, web
    endpoint = Column(String(100))  # API端点
    method = Column(String(10))  # HTTP方法
    request_data = Column(Text)  # 请求数据
    response_data = Column(Text)  # 响应数据
    status_code = Column(Integer)  # HTTP状态码
    execution_time = Column(Float)  # 执行时间(秒)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user")  # 角色: admin, user
    email = Column(String(100))
    name = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CollaborationSession(Base):
    """端云协作会话表"""
    __tablename__ = "collaboration_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, index=True)  # UUID
    violation_type = Column(String(50), index=True)
    local_confidence = Column(Float)
    final_confidence = Column(Float)
    judgment_result = Column(String(20))  # confirmed/rejected/uncertain
    disagreement = Column(Boolean, default=False)
    resolved = Column(Boolean, default=False)
    resolver_id = Column(Integer, nullable=True)
    ai_trace_json = Column(Text)  # 完整ai_trace v3 JSON
    image_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        """转换为字典格式，包含ai_trace_json的JSON解析"""
        result = {
            'id': self.id,
            'session_id': self.session_id,
            'violation_type': self.violation_type,
            'local_confidence': self.local_confidence,
            'final_confidence': self.final_confidence,
            'judgment_result': self.judgment_result,
            'disagreement': self.disagreement,
            'resolved': self.resolved,
            'resolver_id': self.resolver_id,
            'image_path': self.image_path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }

        # 安全处理 ai_trace_json
        raw_ai_trace = self.ai_trace_json
        if raw_ai_trace and raw_ai_trace.strip():
            try:
                result['ai_trace_json'] = json.loads(raw_ai_trace)
            except Exception:
                result['ai_trace_json'] = None
        else:
            result['ai_trace_json'] = None

        return result

class SystemStatistics(Base):
    """系统统计表"""
    __tablename__ = "system_statistics"

    id = Column(Integer, primary_key=True, index=True)
    stat_date = Column(String(10), index=True)  # YYYY-MM-DD
    total_detections = Column(Integer, default=0)
    consultations = Column(Integer, default=0)
    confirmations = Column(Integer, default=0)
    disagreements = Column(Integer, default=0)
    accuracy_before = Column(Float, default=0.0)
    accuracy_after = Column(Float, default=0.0)
    saved_cost = Column(Float, default=0.0)  # 估算节省的云端调用费用
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'stat_date': self.stat_date,
            'total_detections': self.total_detections,
            'consultations': self.consultations,
            'confirmations': self.confirmations,
            'disagreements': self.disagreements,
            'accuracy_before': self.accuracy_before,
            'accuracy_after': self.accuracy_after,
            'saved_cost': self.saved_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TrafficEventRecord(Base):
    """交通事件记录表（GPT §10 证据链持久化）

    对应 TrafficEvent + EvidenceChain 的全部字段，用于事件全生命周期落库。
    """
    __tablename__ = "traffic_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    event_type = Column(String(50), index=True)
    track_id = Column(Integer, index=True)
    state = Column(String(20), nullable=False, default="detecting", index=True)
    trigger_time = Column(DateTime, index=True)

    # 上下文（JSON 字符串）
    vehicle_info = Column(Text)        # JSON
    scene_context = Column(Text)       # JSON
    trajectory = Column(Text)          # JSON
    key_frames = Column(Text)          # JSON (路径列表)

    # 视觉证据
    event_video_path = Column(String(255))

    # 判断结果（JSON 字符串）
    rule_judgment = Column(Text)       # JSON
    ai_judgment = Column(Text)         # JSON (ai_trace v3)
    ai_confidence = Column(Float, default=0.0)
    ai_explanation = Column(Text)

    # 完整证据链（JSON 字符串）
    evidence_chain = Column(Text)       # JSON
    state_history = Column(Text)       # JSON

    # 摄像头 ID
    camera_id = Column(String(50), default="default", index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """转换为字典（JSON 字段自动解析）"""
        def _safe_json(raw):
            if not raw or not (isinstance(raw, str) and raw.strip()):
                return None
            try:
                return json.loads(raw)
            except Exception:
                return None

        return {
            'id': self.id,
            'event_id': self.event_id,
            'event_type': self.event_type,
            'track_id': self.track_id,
            'state': self.state,
            'trigger_time': self.trigger_time.isoformat() if self.trigger_time else None,
            'vehicle_info': _safe_json(self.vehicle_info),
            'scene_context': _safe_json(self.scene_context),
            'trajectory': _safe_json(self.trajectory),
            'key_frames': _safe_json(self.key_frames),
            'event_video_path': self.event_video_path or '',
            'rule_judgment': _safe_json(self.rule_judgment),
            'ai_judgment': _safe_json(self.ai_judgment),
            'ai_confidence': self.ai_confidence if self.ai_confidence is not None else 0.0,
            'ai_explanation': self.ai_explanation or '',
            'evidence_chain': _safe_json(self.evidence_chain),
            'state_history': _safe_json(self.state_history),
            'camera_id': self.camera_id or 'default',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }