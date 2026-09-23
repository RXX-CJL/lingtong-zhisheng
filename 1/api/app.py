from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import logging
from logging.handlers import RotatingFileHandler

from routers import violations, wechat, system, statistics, devices, appeals, auth
from routers import cloud_collab, rtsp_stream, realtime
from database import init_db

# 配置日志系统
def setup_logging():
    log_dir = "output/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建 logger
    logger = logging.getLogger("zhitong_api")
    logger.setLevel(logging.INFO)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 文件 handler（按大小轮转，最大 10MB，保留 5 个备份）
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "api.log"),
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 控制台 handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在初始化数据库...")
    init_db()
    
    # 初始化默认用户
    from database import SessionLocal
    from routers.auth import init_default_user
    db = SessionLocal()
    try:
        init_default_user(db)
    finally:
        db.close()
    
    logger.info("智瞳API服务启动成功！")
    yield
    # 关闭时执行
    logger.info("智瞳API服务正在关闭...")

# 创建FastAPI应用
app = FastAPI(
    title="智瞳智慧交管系统API",
    description="为国赛大创项目提供的违规证据管理API",
    version="2.0.0",
    lifespan=lifespan
)

# 统一异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "error_code": "INTERNAL_ERROR"
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "error_code": f"HTTP_{exc.status_code}"
        }
    )

# 配置CORS
# 注意：allow_origins=["*"] 与 allow_credentials=True 不能同时使用（CORS规范禁止）
# 开发环境用 * 即可，不需要 credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（开发环境）
    allow_credentials=False,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(violations.router)
app.include_router(wechat.router)
app.include_router(system.router)
app.include_router(statistics.router)
app.include_router(devices.router)
app.include_router(appeals.router)
app.include_router(auth.router)
app.include_router(cloud_collab.router)
app.include_router(rtsp_stream.router)
app.include_router(realtime.router)

# 静态文件服务
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# M07: 事件视频静态文件服务（GPT §10 证据链访问）
# 事件视频按 {EVENT_VIDEO_DIR}/{YYYYMMDD}/{event_id}.mp4 组织
try:
    from config import Config
    _event_video_dir = Config.EVENT_VIDEO_DIR
except Exception:
    _event_video_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     'output', 'event_videos')
os.makedirs(_event_video_dir, exist_ok=True)
app.mount("/event-videos", StaticFiles(directory=_event_video_dir), name="event-videos")

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
            "statistics": "/api/statistics",
            "devices": "/api/devices",
            "appeals": "/api/appeals",
            "wechat": "/api/wechat",
            "docs": "/docs",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查 + 关键组件状态"""
    try:
        from image_recognizer import YOLO_AVAILABLE, DASHSCOPE_AVAILABLE
        yolo_ok = YOLO_AVAILABLE
        dashscope_ok = DASHSCOPE_AVAILABLE
    except:
        yolo_ok = False
        dashscope_ok = False
    
    checks = {
        "status": "healthy",
        "version": "2.0.0",
        "yolo_available": yolo_ok,
        "dashscope_available": dashscope_ok,
        "uploads_dir_exists": os.path.exists("uploads"),
        "db_exists": os.path.exists("zhitong_violations.db")
    }
    checks["overall"] = "ok" if (yolo_ok and dashscope_ok) else "degraded"
    return checks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)