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

class ViolationEvidenceResponse(BaseModel):
    """违规证据响应模型"""
    id: int
    violation_type: str
    track_id: int
    confidence: float
    position: Dict[str, Any]
    timestamp: str
    image_path: Optional[str]
    video_path: Optional[str]
    additional_info: Optional[Dict[str, Any]]
    cloud_validated: bool
    cloud_result: Optional[str]
    status: str
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