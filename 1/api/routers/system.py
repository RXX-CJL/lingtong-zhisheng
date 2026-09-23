# -*- coding: utf-8 -*-
"""
系统管理路由 - API 额度监控
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from config_manager import (
    get_masked_config,
    set_api_key,
    heartbeat as do_heartbeat
)

try:
    from image_recognizer import (
        get_model_status,
        switch_model,
        unload_model,
        init_all_models,
        get_performance_stats,
        reset_performance_stats
    )
    RECOGNIZER_AVAILABLE = True
except ImportError:
    RECOGNIZER_AVAILABLE = False

router = APIRouter(prefix="/api/system", tags=["系统管理"])


class SetKeyRequest(BaseModel):
    """设置 API Key 请求"""
    api_key: str


@router.get("/quota")
async def get_quota():
    """获取 API 额度信息（打码后）"""
    try:
        config = get_masked_config()
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取配置失败: {str(e)}"
        }


@router.put("/quota/{provider}")
async def update_quota_key(provider: str, request: SetKeyRequest):
    """更新 API Key 并立即心跳验证"""
    if provider not in ['dashscope', 'deepseek']:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be 'dashscope' or 'deepseek'")
    
    try:
        # 保存 API Key
        success, message = set_api_key(provider, request.api_key)
        if not success:
            return {
                "success": False,
                "message": message
            }
        
        # 立即心跳验证
        hb_success, hb_message = do_heartbeat(provider)
        
        return {
            "success": True,
            "message": f"API Key 已保存，心跳验证: {'成功' if hb_success else '失败'}",
            "data": {
                "heartbeat_ok": hb_success,
                "heartbeat_message": hb_message
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"更新失败: {str(e)}"
        }


@router.post("/quota/{provider}/heartbeat")
async def trigger_heartbeat(provider: str):
    """手动触发心跳验证"""
    if provider not in ['dashscope', 'deepseek']:
        raise HTTPException(status_code=400, detail="Invalid provider. Must be 'dashscope' or 'deepseek'")
    
    try:
        success, message = do_heartbeat(provider)
        return {
            "success": success,
            "message": message,
            "data": get_masked_config()[provider]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"心跳验证失败: {str(e)}"
        }


class ModelSwitchRequest(BaseModel):
    """模型切换请求"""
    model_key: str


@router.get("/models")
async def get_models():
    """获取所有模型状态"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        status = get_model_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取模型状态失败: {str(e)}"
        }


@router.post("/models/switch")
async def switch_model_endpoint(request: ModelSwitchRequest):
    """热切换检测模型"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        result = switch_model(request.model_key)
        return {
            "success": result['success'],
            "message": result['message'],
            "data": {
                "current_model": result.get('current_model'),
                "available_models": result.get('available_models')
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"模型切换失败: {str(e)}"
        }


@router.delete("/models/{model_key}")
async def unload_model_endpoint(model_key: str):
    """卸载指定模型（释放内存）"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        result = unload_model(model_key)
        return {
            "success": result['success'],
            "message": result['message'],
            "data": {
                "available_models": result.get('available_models')
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"卸载模型失败: {str(e)}"
        }


@router.post("/models/init")
async def init_models_endpoint():
    """初始化所有模型"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        init_all_models()
        status = get_model_status()
        return {
            "success": True,
            "message": "所有模型初始化完成",
            "data": status
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"模型初始化失败: {str(e)}"
        }


@router.get("/performance")
async def get_performance():
    """获取性能统计"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        stats = get_performance_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"获取性能统计失败: {str(e)}"
        }


@router.post("/performance/reset")
async def reset_performance():
    """重置性能统计"""
    if not RECOGNIZER_AVAILABLE:
        return {
            "success": False,
            "message": "图像识别模块未加载"
        }
    
    try:
        result = reset_performance_stats()
        return {
            "success": result['success'],
            "message": result['message']
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"重置性能统计失败: {str(e)}"
        }
