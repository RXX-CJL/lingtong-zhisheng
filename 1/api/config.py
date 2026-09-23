# -*- coding: utf-8 -*-
"""
统一配置管理模块 - 管理所有系统配置
"""

import os
import json
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

class Config:
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    PORT = int(os.environ.get('PORT', 8001))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    DB_PATH = os.environ.get('DB_PATH', os.path.join(PROJECT_ROOT, 'zhitong_violations.db'))
    
    UPLOAD_DIR = os.environ.get('UPLOAD_DIR', os.path.join(BASE_DIR, 'uploads'))
    LOG_DIR = os.environ.get('LOG_DIR', os.path.join(BASE_DIR, 'output/logs'))
    
    MODEL_DIR = os.environ.get('MODEL_DIR', os.path.join(PROJECT_ROOT, 'zhitong/training/models'))
    
    FRAME_RATE = int(os.environ.get('FRAME_RATE', 3))
    FRAME_CACHE_SIZE = int(os.environ.get('FRAME_CACHE_SIZE', 10))
    CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5))
    CONSULT_THRESHOLD = float(os.environ.get('CONSULT_THRESHOLD', 0.7))
    
    API_TIMEOUT = int(os.environ.get('API_TIMEOUT', 10))
    API_RETRY_TIMES = int(os.environ.get('API_RETRY_TIMES', 2))
    
    DASHSCOPE_API_KEY = os.environ.get('DASHSCOPE_API_KEY', '')
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY', '')
    CLAUDE_API_URL = os.environ.get('CLAUDE_API_URL', 'https://api.anthropic.com/v1/messages')
    
    YOLO_BATCH_SIZE = int(os.environ.get('YOLO_BATCH_SIZE', 1))

    # M02: 视频循环缓存配置（GPT §5）
    FRAME_BUFFER_DURATION = int(os.environ.get('FRAME_BUFFER_DURATION', 30))  # 缓存时长秒
    FRAME_BUFFER_FPS = int(os.environ.get('FRAME_BUFFER_FPS', 10))  # 预期帧率
    EVENT_CLIP_BEFORE_SEC = int(os.environ.get('EVENT_CLIP_BEFORE_SEC', 5))  # 事件前秒数
    EVENT_CLIP_AFTER_SEC = int(os.environ.get('EVENT_CLIP_AFTER_SEC', 5))  # 事件后秒数
    # 事件视频输出目录
    EVENT_VIDEO_DIR = os.environ.get('EVENT_VIDEO_DIR', os.path.join(BASE_DIR, 'output', 'event_videos'))

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # 规则引擎插件启用清单（逗号分隔的场景名）
    # 默认启用：交通 / 城管 / 治安 三大场景
    PLUGINS_ENABLED = os.environ.get(
        'PLUGINS_ENABLED', 'traffic,urban_management,public_security'
    ).split(',')
    
    @classmethod
    def init_dirs(cls):
        for dir_path in [cls.UPLOAD_DIR, cls.LOG_DIR, cls.MODEL_DIR]:
            os.makedirs(dir_path, exist_ok=True)
    
    @classmethod
    def load_api_keys(cls):
        config_file = os.path.join(BASE_DIR, 'config_runtime.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if not cls.DASHSCOPE_API_KEY:
                    cls.DASHSCOPE_API_KEY = config.get('dashscope', {}).get('api_key', '')
                if not cls.DEEPSEEK_API_KEY:
                    cls.DEEPSEEK_API_KEY = config.get('deepseek', {}).get('api_key', '')
                if not cls.CLAUDE_API_KEY:
                    cls.CLAUDE_API_KEY = config.get('claude', {}).get('api_key', '')
            except Exception:
                pass
        
        if not cls.DASHSCOPE_API_KEY:
            try:
                sys.path.insert(0, os.path.join(PROJECT_ROOT, 'zhitong'))
                from config import Config as ZConfig
                cls.DASHSCOPE_API_KEY = getattr(ZConfig, 'DASHSCOPE_API_KEY', '')
            except Exception:
                pass
    
    @classmethod
    def get_model_path(cls, model_name: str) -> Optional[str]:
        model_path = os.path.join(cls.MODEL_DIR, f'{model_name}.pt')
        if os.path.exists(model_path):
            return model_path
        return None


def get_config() -> Dict:
    return {
        'debug': Config.DEBUG,
        'port': Config.PORT,
        'host': Config.HOST,
        'db_path': Config.DB_PATH,
        'upload_dir': Config.UPLOAD_DIR,
        'log_dir': Config.LOG_DIR,
        'model_dir': Config.MODEL_DIR,
        'frame_rate': Config.FRAME_RATE,
        'frame_cache_size': Config.FRAME_CACHE_SIZE,
        'confidence_threshold': Config.CONFIDENCE_THRESHOLD,
        'consult_threshold': Config.CONSULT_THRESHOLD,
        'api_timeout': Config.API_TIMEOUT,
        'api_retry_times': Config.API_RETRY_TIMES,
        'yolo_batch_size': Config.YOLO_BATCH_SIZE,
        'log_level': Config.LOG_LEVEL,
        'frame_buffer_duration': Config.FRAME_BUFFER_DURATION,
        'frame_buffer_fps': Config.FRAME_BUFFER_FPS,
        'event_clip_before_sec': Config.EVENT_CLIP_BEFORE_SEC,
        'event_clip_after_sec': Config.EVENT_CLIP_AFTER_SEC,
    }