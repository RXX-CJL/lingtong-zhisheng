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
    status = Column(String(20), default="pending")  # 状态: pending, confirmed, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """转换为字典格式"""
        return {
            'id': self.id,
            'violation_type': self.violation_type,
            'track_id': self.track_id,
            'confidence': self.confidence,
            'position': json.loads(self.position) if self.position else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'image_path': self.image_path,
            'video_path': self.video_path,
            'additional_info': json.loads(self.additional_info) if self.additional_info else None,
            'cloud_validated': self.cloud_validated,
            'cloud_result': self.cloud_result,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

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