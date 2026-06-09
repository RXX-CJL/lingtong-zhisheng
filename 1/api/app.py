from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from routers import violations, wechat
from database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("正在初始化数据库...")
    init_db()
    print("智瞳API服务启动成功！")
    yield
    # 关闭时执行
    print("智瞳API服务正在关闭...")

# 创建FastAPI应用
app = FastAPI(
    title="智瞳智慧交管系统API",
    description="为国赛大创项目提供的违规证据管理API",
    version="2.0.0",
    lifespan=lifespan
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