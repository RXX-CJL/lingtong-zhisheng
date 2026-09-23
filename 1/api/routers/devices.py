"""
设备管理路由模块
提供K230设备的管理API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import json

from database import get_db

router = APIRouter(prefix="/api/devices", tags=["设备管理"])

# ============== 数据模型 ==============

class DeviceCreate(BaseModel):
    """创建设备请求"""
    device_id: str = Field(..., description="设备唯一标识")
    name: str = Field(..., description="设备名称")
    device_type: str = Field("k230", description="设备类型: k230/fixed_camera")
    location: Optional[str] = Field(None, description="位置描述")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")
    config: Optional[dict] = Field({}, description="设备配置")

class DeviceUpdate(BaseModel):
    """更新设备请求"""
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: Optional[str] = None
    config: Optional[dict] = None

class DeviceResponse(BaseModel):
    """设备响应"""
    id: int
    device_id: str
    name: str
    device_type: str
    location: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    status: str  # online/offline/error
    last_seen: Optional[str]
    config: dict
    created_at: str
    updated_at: str

class DeviceHeartbeat(BaseModel):
    """设备心跳"""
    device_id: str
    status: str = "online"
    location: Optional[dict] = None
    battery_level: Optional[int] = None
    temperature: Optional[float] = None

class ApiResponse(BaseModel):
    """通用响应"""
    success: bool
    message: str
    data: Optional[dict] = None

# ============== 设备注册表（内存存储，生产环境应使用数据库）==============

# 设备注册表
_device_registry = {}

def _get_device_by_id(db, device_id: str):
    """从数据库获取设备"""
    from models import SystemConfig
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == f"device:{device_id}"
    ).first()
    if config and config.config_value:
        return json.loads(config.config_value)
    return None

def _save_device(db, device_id: str, device_data: dict):
    """保存设备到数据库"""
    from models import SystemConfig
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == f"device:{device_id}"
    ).first()
    if config:
        config.config_value = json.dumps(device_data)
        config.updated_at = datetime.utcnow()
    else:
        config = SystemConfig(
            config_key=f"device:{device_id}",
            config_value=json.dumps(device_data),
            description=f"设备配置: {device_id}"
        )
        db.add(config)
    db.commit()

# ============== API接口 ==============

@router.post("/register", response_model=ApiResponse)
async def register_device(
    device: DeviceCreate,
    db: Session = Depends(get_db)
):
    """注册新设备"""
    # 检查设备是否已存在
    existing = _get_device_by_id(db, device.device_id)
    if existing:
        return ApiResponse(
            success=False,
            message="设备已存在",
            data={"device_id": device.device_id}
        )
    
    # 创建设备记录
    now = datetime.utcnow().isoformat()
    device_data = {
        "device_id": device.device_id,
        "name": device.name,
        "device_type": device.device_type,
        "location": device.location,
        "latitude": device.latitude,
        "longitude": device.longitude,
        "status": "offline",
        "last_seen": now,
        "config": device.config,
        "created_at": now,
        "updated_at": now
    }
    
    _save_device(db, device.device_id, device_data)
    
    return ApiResponse(
        success=True,
        message="设备注册成功",
        data={"device_id": device.device_id}
    )

@router.get("/list", response_model=ApiResponse)
async def list_devices(
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """获取设备列表"""
    from models import SystemConfig
    
    query = db.query(SystemConfig).filter(
        SystemConfig.config_key.like("device:%")
    )
    
    devices = []
    for config in query.all():
        device_data = json.loads(config.config_value)
        if device_type and device_data.get("device_type") != device_type:
            continue
        if status and device_data.get("status") != status:
            continue
        devices.append(device_data)
    
    return ApiResponse(
        success=True,
        message=f"获取到{len(devices)}个设备",
        data={"devices": devices, "total": len(devices)}
    )

@router.get("/{device_id}", response_model=ApiResponse)
async def get_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """获取设备详情"""
    device_data = _get_device_by_id(db, device_id)
    if not device_data:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    return ApiResponse(
        success=True,
        message="获取设备成功",
        data=device_data
    )

@router.put("/{device_id}", response_model=ApiResponse)
async def update_device(
    device_id: str,
    update: DeviceUpdate,
    db: Session = Depends(get_db)
):
    """更新设备信息"""
    device_data = _get_device_by_id(db, device_id)
    if not device_data:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    # 更新字段
    update_dict = update.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        if value is not None:
            device_data[key] = value
    device_data["updated_at"] = datetime.utcnow().isoformat()
    
    _save_device(db, device_id, device_data)
    
    return ApiResponse(
        success=True,
        message="设备更新成功",
        data=device_data
    )

@router.delete("/{device_id}", response_model=ApiResponse)
async def delete_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """删除设备"""
    from models import SystemConfig
    
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == f"device:{device_id}"
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="设备不存在")
    
    db.delete(config)
    db.commit()
    
    return ApiResponse(
        success=True,
        message="设备删除成功",
        data={"device_id": device_id}
    )

@router.post("/heartbeat", response_model=ApiResponse)
async def device_heartbeat(
    heartbeat: DeviceHeartbeat,
    db: Session = Depends(get_db)
):
    """设备心跳（更新设备在线状态）"""
    device_data = _get_device_by_id(db, heartbeat.device_id)
    if not device_data:
        # 自动注册新设备
        device_data = {
            "device_id": heartbeat.device_id,
            "name": f"K230_{heartbeat.device_id}",
            "device_type": "k230",
            "status": "online",
            "last_seen": datetime.utcnow().isoformat(),
            "config": {},
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    # 更新状态
    device_data["status"] = heartbeat.status
    device_data["last_seen"] = datetime.utcnow().isoformat()
    if heartbeat.location:
        device_data["latitude"] = heartbeat.location.get("lat")
        device_data["longitude"] = heartbeat.location.get("lng")
    if heartbeat.battery_level is not None:
        device_data["battery_level"] = heartbeat.battery_level
    if heartbeat.temperature is not None:
        device_data["temperature"] = heartbeat.temperature
    device_data["updated_at"] = datetime.utcnow().isoformat()
    
    _save_device(db, heartbeat.device_id, device_data)
    
    return ApiResponse(
        success=True,
        message="心跳接收成功",
        data={"device_id": heartbeat.device_id, "server_time": datetime.utcnow().isoformat()}
    )

@router.get("/{device_id}/violations", response_model=ApiResponse)
async def get_device_violations(
    device_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """获取设备关联的违规记录"""
    from models import ViolationEvidence
    
    # 查询该设备最近的违规记录
    violations = db.query(ViolationEvidence).filter(
        ViolationEvidence.additional_info.contains(device_id)
    ).order_by(
        ViolationEvidence.timestamp.desc()
    ).limit(limit).all()
    
    violation_list = []
    for v in violations:
        violation_list.append({
            "id": v.id,
            "violation_type": v.violation_type,
            "confidence": v.confidence,
            "timestamp": v.timestamp.isoformat() if v.timestamp else None,
            "status": v.status
        })
    
    return ApiResponse(
        success=True,
        message=f"获取到{len(violation_list)}条记录",
        data={"violations": violation_list, "total": len(violation_list)}
    )
