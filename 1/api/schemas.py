from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 违规证据相关模型
class ViolationEvidenceCreate(BaseModel):
    """创建违规证据请求模型"""
    violation_type: str = Field(..., description="违规类型")
    track_id: int = Field(..., description="跟踪ID")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    position: Dict[str, Any] = Field(..., description="位置信息")
    timestamp: str = Field(..., description="时间戳")
    image_data: Optional[str] = Field(None, description="图片Base64数据")
    video_data: Optional[str] = Field(None, description="视频Base64数据")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="附加信息")
    # M04: 车牌绑定字段
    plate_number: Optional[str] = Field(None, description="车牌号")
    plate_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="车牌识别置信度")
    plate_image_data: Optional[str] = Field(None, description="车牌小图Base64数据")
    plate_color: Optional[str] = Field(None, description="车牌颜色: blue/green/yellow/unknown")
    confirmed_frames: Optional[int] = Field(None, ge=0, description="多帧确认命中数")

class ViolationEvidenceResponse(BaseModel):
    """违规证据响应模型"""
    id: int
    violation_type: str
    # 2026-11-18：允许为空。云协作/手工录入的记录没有 track_id，
    # 原定义 int 会让整个分页请求 500（实测 GET /api/violations/list?page=5 崩）。
    track_id: Optional[int] = None
    confidence: float
    position: Dict[str, Any]
    timestamp: str
    image_path: Optional[str]
    video_path: Optional[str]
    additional_info: Optional[Dict[str, Any]]
    cloud_validated: bool
    cloud_result: Optional[str]
    yolo_detection_result: Optional[Dict[str, Any]]
    status: str
    # M04: 车牌绑定字段
    plate_number: Optional[str] = ''
    plate_confidence: Optional[float] = 0.0
    plate_image_path: Optional[str] = ''
    plate_color: Optional[str] = 'unknown'
    confirmed_frames: Optional[int] = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class ViolationEvidenceUpdate(BaseModel):
    """更新违规证据请求模型"""
    status: Optional[str] = Field(None, description="状态")
    cloud_validated: Optional[bool] = Field(None, description="是否云端验证")
    cloud_result: Optional[str] = Field(None, description="云端验证结果")

# 批量操作模型
class BatchViolationCreate(BaseModel):
    """批量创建违规证据请求模型"""
    violations: List[ViolationEvidenceCreate] = Field(..., description="违规证据列表")

class BatchViolationResponse(BaseModel):
    """批量创建违规证据响应模型"""
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(..., description="失败数量")
    results: List[Dict[str, Any]] = Field(..., description="详细结果")

# 查询模型
class ViolationQuery(BaseModel):
    """违规查询请求模型"""
    violation_type: Optional[str] = Field(None, description="违规类型")
    track_id: Optional[int] = Field(None, description="跟踪ID")
    status: Optional[str] = Field(None, description="状态")
    start_time: Optional[str] = Field(None, description="开始时间")
    end_time: Optional[str] = Field(None, description="结束时间")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")

class ViolationListResponse(BaseModel):
    """违规列表响应模型"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    items: List[ViolationEvidenceResponse] = Field(..., description="违规证据列表")

# 微信小程序专用模型
class WeChatViolationSubmit(BaseModel):
    """微信小程序违规提交模型"""
    openid: str = Field(..., description="微信用户OpenID")
    violation_data: ViolationEvidenceCreate = Field(..., description="违规数据")
    device_info: Optional[Dict[str, Any]] = Field(None, description="设备信息")

class WeChatViolationListResponse(BaseModel):
    """微信小程序违规列表响应模型"""
    total: int
    has_more: bool
    items: List[ViolationEvidenceResponse]

# 统计模型
class ViolationStatistics(BaseModel):
    """违规统计响应模型"""
    total_count: int = Field(..., description="总违规数")
    by_type: Dict[str, int] = Field(..., description="按类型统计")
    by_status: Dict[str, int] = Field(..., description="按状态统计")
    by_date: Dict[str, int] = Field(..., description="按日期统计")

# 通用响应模型
class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(None, description="响应数据")
    error_code: Optional[str] = Field(None, description="错误码")

# 用户认证模型
class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")

class UserUpdate(BaseModel):
    """更新用户请求模型"""
    role: Optional[str] = Field(None, description="角色")
    is_active: Optional[bool] = Field(None, description="是否激活")
    name: Optional[str] = Field(None, max_length=50, description="姓名")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")

class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    name: str
    role: str
    email: Optional[str]
    is_active: bool
    created_at: str

class LoginResponse(BaseModel):
    """登录响应模型"""
    access_token: str
    token_type: str
    user: UserResponse

# 设备管理模型
class DeviceCreate(BaseModel):
    """创建设备请求模型"""
    device_id: str = Field(..., description="设备ID")
    name: str = Field(..., description="设备名称")
    device_type: str = Field(..., description="设备类型")
    location: Optional[str] = Field(None, description="位置描述")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")

class DeviceUpdate(BaseModel):
    """更新设备请求模型"""
    name: Optional[str] = Field(None, description="设备名称")
    status: Optional[str] = Field(None, description="状态")
    location: Optional[str] = Field(None, description="位置描述")
    latitude: Optional[float] = Field(None, description="纬度")
    longitude: Optional[float] = Field(None, description="经度")

# 申诉管理模型
class AppealCreate(BaseModel):
    """创建申诉请求模型"""
    violation_id: int = Field(..., description="违规记录ID")
    reason: str = Field(..., description="申诉理由")
    contact: Optional[str] = Field(None, description="联系方式")

class AppealProcess(BaseModel):
    """处理申诉请求模型"""
    status: str = Field(..., description="处理结果")
    result: str = Field(..., description="处理备注")