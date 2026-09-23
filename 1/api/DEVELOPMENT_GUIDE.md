# 智瞳项目后端开发详细指南

## 📋 项目概述

**项目名称**: 智瞳智慧交管系统  
**开发目标**: 为国赛大创项目开发后端系统，支持微信小程序和网页平台接收违规证据  
**开发原则**: 暂时忽略安全考虑，优先功能实现，利用现有资源

## 🎯 核心功能需求

1. **违规证据接收**: 接收系统生成的违规捕获证据
2. **数据存储**: 安全存储违规信息
3. **微信小程序支持**: 完整的微信小程序API支持
4. **网页平台支持**: 网页平台API支持
5. **客户端互操作**: 微信小程序和网页平台数据互通

## 🛠️ 现有资源

### 可用API
1. **DashScope API** (阿里云千问大模型)
   - API Key: 通过环境变量 `DASHSCOPE_API_KEY` 或 `api/config_runtime.json` 配置
   - 用途: 云端图像分析和违规验证
   - 已实现模块: `zhitong/cloud.py`

2. **DeepSeek API**
   - API Key: 通过环境变量 `DEEPSEEK_API_KEY` 或 `api/config_runtime.json` 配置
   - 用途: 代码智能分析和开发辅助

### 现有项目基础
- `zhitong/cloud.py`: 云端图像分析功能
- `zhitong/logger.py`: 违规日志记录功能
- `zhitong/violation_detector.py`: 违规检测功能
- `zhitong/config.py`: 配置管理
- `api/main.py`: FastAPI后端基础框架

## 📝 详细开发任务分解

### 任务1: 完善违规证据数据模型 (预计时间: 30分钟)

**目标**: 创建完整的违规证据数据结构

**详细步骤**:

#### 步骤1.1: 创建数据模型文件
1. 打开文件 `e:\output\1\api\models.py`
2. 如果文件不存在，创建新文件
3. 复制以下代码到文件中：

```python
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
```

#### 步骤1.2: 验证文件创建
1. 检查文件 `e:\output\1\api\models.py` 是否存在
2. 确认文件内容正确
3. 保存文件

---

### 任务2: 创建Pydantic数据验证模型 (预计时间: 20分钟)

**目标**: 创建API请求和响应的数据验证模型

**详细步骤**:

#### 步骤2.1: 创建数据验证模型文件
1. 打开文件 `e:\output\1\api\schemas.py`
2. 如果文件不存在，创建新文件
3. 复制以下代码到文件中：

```python
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
```

#### 步骤2.2: 验证文件创建
1. 检查文件 `e:\output\1\api\schemas.py` 是否存在
2. 确认文件内容正确
3. 保存文件

---

### 任务3: 创建数据库配置和连接管理 (预计时间: 15分钟)

**目标**: 创建数据库连接和会话管理

**详细步骤**:

#### 步骤3.1: 创建数据库配置文件
1. 打开文件 `e:\output\1\api\database.py`
2. 如果文件不存在，创建新文件
3. 复制以下代码到文件中：

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

# 数据库配置
DATABASE_URL = "sqlite:///./zhitong_violations.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # 设置为True可以看到SQL语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功")

if __name__ == "__main__":
    init_db()
```

#### 步骤3.2: 初始化数据库
1. 打开命令行终端
2. 导航到 `e:\output\1\api` 目录
3. 执行命令: `python database.py`
4. 确认看到 "数据库表创建成功" 消息
5. 检查是否生成了 `zhitong_violations.db` 文件

---

### 任务4: 创建违规证据API路由 (预计时间: 45分钟)

**目标**: 创建完整的违规证据管理API

**详细步骤**:

#### 步骤4.1: 创建API路由文件
1. 打开文件 `e:\output\1\api\routers\violations.py`
2. 如果 `routers` 目录不存在，先创建目录
3. 复制以下代码到文件中：

```python
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
```

#### 步骤4.2: 创建routers目录
1. 检查 `e:\output\1\api\routers` 目录是否存在
2. 如果不存在，创建该目录
3. 在 `routers` 目录中创建 `__init__.py` 文件（空文件即可）

#### 步骤4.3: 验证文件创建
1. 检查文件 `e:\output\1\api\routers\violations.py` 是否存在
2. 确认文件内容正确
3. 保存文件

---

### 任务5: 创建微信小程序专用API (预计时间: 30分钟)

**目标**: 创建微信小程序专用的API接口

**详细步骤**:

#### 步骤5.1: 创建微信小程序API路由文件
1. 打开文件 `e:\output\1\api\routers\wechat.py`
2. 复制以下代码到文件中：

```python
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
```

#### 步骤5.2: 验证文件创建
1. 检查文件 `e:\output\1\api\routers\wechat.py` 是否存在
2. 确认文件内容正确
3. 保存文件

---

### 任务6: 创建主应用文件并集成所有路由 (预计时间: 20分钟)

**目标**: 创建主应用文件，集成所有API路由

**详细步骤**:

#### 步骤6.1: 创建主应用文件
1. 打开文件 `e:\output\1\api\app.py`
2. 复制以下代码到文件中：

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from routers import violations, wechat
from database import init_db

# 创建FastAPI应用
app = FastAPI(
    title="智瞳智慧交管系统API",
    description="为国赛大创项目提供的违规证据管理API",
    version="2.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(violations.router)
app.include_router(wechat.router)

# 静态文件服务
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print("正在初始化数据库...")
    init_db()
    print("智瞳API服务启动成功！")

# 健康检查
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "智瞳智慧交管系统API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "violations": "/api/violations",
            "wechat": "/api/wechat",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "zhitong-api",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

#### 步骤6.2: 验证文件创建
1. 检查文件 `e:\output\1\api\app.py` 是否存在
2. 确认文件内容正确
3. 保存文件

---

### 任务7: 创建启动脚本和测试文件 (预计时间: 15分钟)

**目标**: 创建启动脚本和API测试文件

**详细步骤**:

#### 步骤7.1: 创建启动脚本
1. 打开文件 `e:\output\1\api\start_api.bat`
2. 复制以下内容到文件中：

```batch
@echo off
chcp 65001
echo ========================================
echo 智瞳智慧交管系统API服务启动
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python环境
    pause
    exit /b 1
)

echo.
echo [2/3] 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
)

echo.
echo [3/3] 启动API服务...
echo 服务地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

python app.py

pause
```

#### 步骤7.2: 创建API测试文件
1. 打开文件 `e:\output\1\api\test_api.py`
2. 复制以下代码到文件中：

```python
import requests
import json
import base64
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查"""
    print("测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()

def create_test_image_base64():
    """创建测试图片的Base64数据"""
    # 这里使用一个简单的1x1像素的红色图片作为示例
    # 实际项目中应该使用真实的违规图片
    red_pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
    return base64.b64encode(red_pixel).decode('utf-8')

def test_submit_violation():
    """测试提交违规证据"""
    print("测试提交违规证据...")
    
    violation_data = {
        "violation_type": "red_light",
        "track_id": 1,
        "confidence": 0.95,
        "position": {
            "x": 100,
            "y": 200,
            "width": 50,
            "height": 100
        },
        "timestamp": datetime.now().isoformat(),
        "image_data": create_test_image_base64(),
        "additional_info": {
            "location": "北京市朝阳区",
            "camera_id": "CAM001"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/violations/submit", json=violation_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()
    return response.json()

def test_get_violation_list():
    """测试获取违规列表"""
    print("测试获取违规列表...")
    
    params = {
        "page": 1,
        "page_size": 10
    }
    
    response = requests.get(f"{BASE_URL}/api/violations/list", params=params)
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"总数: {result['total']}")
    print(f"当前页: {result['page']}")
    print(f"违规数量: {len(result['items'])}")
    print()

def test_get_statistics():
    """测试获取统计信息"""
    print("测试获取统计信息...")
    
    response = requests.get(f"{BASE_URL}/api/violations/statistics/summary")
    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"总违规数: {result['total_count']}")
    print(f"按类型统计: {result['by_type']}")
    print(f"按状态统计: {result['by_status']}")
    print()

def test_wechat_submit():
    """测试微信小程序提交"""
    print("测试微信小程序提交...")
    
    wechat_data = {
        "openid": "test_openid_123456",
        "violation_data": {
            "violation_type": "no_helmet",
            "track_id": 2,
            "confidence": 0.88,
            "position": {
                "x": 150,
                "y": 250,
                "width": 60,
                "height": 120
            },
            "timestamp": datetime.now().isoformat(),
            "image_data": create_test_image_base64(),
            "additional_info": {
                "location": "上海市浦东新区"
            }
        },
        "device_info": {
            "platform": "ios",
            "version": "1.0.0"
        }
    }
    
    response = requests.post(f"{BASE_URL}/api/wechat/violation/submit", json=wechat_data)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()

def main():
    """主测试函数"""
    print("=" * 50)
    print("智瞳API功能测试")
    print("=" * 50)
    print()
    
    try:
        # 基础测试
        test_health_check()
        
        # 违规证据测试
        test_submit_violation()
        test_get_violation_list()
        test_get_statistics()
        
        # 微信小程序测试
        test_wechat_submit()
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
        
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到API服务")
        print("请确保API服务已启动: python app.py")
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    main()
```

#### 步骤7.3: 验证文件创建
1. 检查文件 `e:\output\1\api\start_api.bat` 是否存在
2. 检查文件 `e:\output\1\api\test_api.py` 是否存在
3. 确认文件内容正确
4. 保存文件

---

### 任务8: 启动和测试API服务 (预计时间: 10分钟)

**目标**: 启动API服务并进行功能测试

**详细步骤**:

#### 步骤8.1: 安装依赖包
1. 打开命令行终端
2. 导航到 `e:\output\1\api` 目录
3. 执行命令: `pip install -r requirements.txt`
4. 等待所有依赖包安装完成

#### 步骤8.2: 启动API服务
1. 在命令行终端中执行: `python app.py`
2. 等待看到 "智瞳API服务启动成功！" 消息
3. 确认服务运行在 `http://localhost:8000`

#### 步骤8.3: 测试API功能
1. 打开新的命令行终端
2. 导航到 `e:\output\1\api` 目录
3. 执行命令: `python test_api.py`
4. 查看测试结果，确认所有功能正常

#### 步骤8.4: 访问API文档
1. 打开浏览器
2. 访问 `http://localhost:8000/docs`
3. 查看自动生成的API文档
4. 尝试在文档页面中测试各个API接口

---

## 📱 微信小程序集成指南

### 微信小程序API使用说明

#### 1. 提交违规证据
```javascript
// 微信小程序代码示例
wx.request({
  url: 'http://your-server.com/api/wechat/violation/submit',
  method: 'POST',
  data: {
    openid: 'user_openid',  // 用户的微信OpenID
    violation_data: {
      violation_type: 'red_light',
      track_id: 1,
      confidence: 0.95,
      position: { x: 100, y: 200, width: 50, height: 100 },
      timestamp: '2024-01-01T12:00:00',
      image_data: 'base64_encoded_image_data',
      additional_info: { location: '北京市朝阳区' }
    },
    device_info: { platform: 'ios', version: '1.0.0' }
  },
  success: function(res) {
    console.log('提交成功', res.data);
  }
});
```

#### 2. 获取违规列表
```javascript
wx.request({
  url: 'http://your-server.com/api/wechat/violation/list',
  method: 'GET',
  data: {
    openid: 'user_openid',
    page: 1,
    page_size: 10
  },
  success: function(res) {
    console.log('违规列表', res.data);
  }
});
```

#### 3. 获取统计信息
```javascript
wx.request({
  url: 'http://your-server.com/api/wechat/statistics/my',
  method: 'GET',
  data: {
    openid: 'user_openid'
  },
  success: function(res) {
    console.log('统计信息', res.data);
  }
});
```

---

## 🌐 网页平台集成指南

### 网页平台API使用说明

#### 1. 提交违规证据
```javascript
// 网页平台JavaScript代码示例
fetch('http://your-server.com/api/violations/submit', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    violation_type: 'red_light',
    track_id: 1,
    confidence: 0.95,
    position: { x: 100, y: 200, width: 50, height: 100 },
    timestamp: '2024-01-01T12:00:00',
    image_data: 'base64_encoded_image_data',
    additional_info: { location: '北京市朝阳区' }
  })
})
.then(response => response.json())
.then(data => console.log('提交成功', data));
```

#### 2. 获取违规列表
```javascript
fetch('http://your-server.com/api/violations/list?page=1&page_size=20')
  .then(response => response.json())
  .then(data => console.log('违规列表', data));
```

#### 3. 获取统计信息
```javascript
fetch('http://your-server.com/api/violations/statistics/summary')
  .then(response => response.json())
  .then(data => console.log('统计信息', data));
```

---

## 🔄 客户端互操作性

### 数据互通机制

1. **统一数据格式**: 微信小程序和网页平台使用相同的数据模型
2. **共享数据库**: 两个客户端访问同一个数据库，数据实时同步
3. **统一API接口**: 核心功能使用相同的API接口
4. **差异化处理**: 微信小程序有专门的API接口处理微信特有逻辑

### 互操作性保证

- **数据一致性**: 所有违规证据存储在同一个数据库表中
- **实时同步**: 两个客户端可以实时查看最新的违规数据
- **权限隔离**: 微信用户只能查看自己提交的数据，网页平台可以查看所有数据
- **功能对等**: 两个客户端的核心功能基本对等

---

## 📋 任务清单

### 已完成任务
- [ ] 任务1: 完善违规证据数据模型
- [ ] 任务2: 创建Pydantic数据验证模型
- [ ] 任务3: 创建数据库配置和连接管理
- [ ] 任务4: 创建违规证据API路由
- [ ] 任务5: 创建微信小程序专用API
- [ ] 任务6: 创建主应用文件并集成所有路由
- [ ] 任务7: 创建启动脚本和测试文件
- [ ] 任务8: 启动和测试API服务

### 待完成任务
- [ ] 集成DashScope云端验证功能
- [ ] 实现违规证据的云端验证
- [ ] 添加实时通知功能
- [ ] 完善错误处理和日志记录
- [ ] 添加数据导出功能
- [ ] 实现数据备份和恢复

---

## 🚀 快速开始

### 一键启动
```bash
# 1. 进入API目录
cd e:\output\1\api

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py

# 4. 测试功能（新终端）
python test_api.py
```

### 访问地址
- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 📞 技术支持

如遇到问题，请按以下步骤排查：

1. **依赖问题**: 确保所有依赖包已正确安装
2. **端口冲突**: 检查8000端口是否被占用
3. **数据库问题**: 删除 `zhitong_violations.db` 文件后重新启动
4. **文件权限**: 确保有权限创建 `uploads` 目录

---

**祝开发顺利！** 🎉