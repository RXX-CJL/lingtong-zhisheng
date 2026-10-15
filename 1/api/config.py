# -*- coding: utf-8 -*-
"""
统一配置管理模块 - 管理所有系统配置
"""

import os
import json
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# --- .env 加载（必须早于任何 os.environ.get 执行）-----------------------------
# 让 api/.env 真正生效：此前 .env.example 已写明"复制为 .env 填入 Key"，但项目
# 没有加载器，导致环境变量拿不到值、明文 Key 只能留在 config_runtime.json。
# 显式按路径加载，避免依赖 load_dotenv 的向上查找行为；dotenv 缺失或 .env 不
# 存在时静默跳过，行为与未改动前完全一致（已由 DSH 于 2026-09-27 补充）。
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(os.path.join(BASE_DIR, '.env'))
except Exception:
    pass
# -----------------------------------------------------------------------------

class Config:
    DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    PORT = int(os.environ.get('PORT', 8001))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # ★2026-10-06 由 DSH 修正（G12）：原来指向 PROJECT_ROOT，而 database.py 用的是
    # 本文件所在目录（api/）——项目根那个是 **0 字节空壳**，凡是读 Config.DB_PATH
    # 做存在性/大小判断的地方（如 app.py 健康检查）都会得出假结论。
    # 现与 database.py 的 _DB_FILE 对齐（两者必须指向同一个文件）。
    DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'zhitong_violations.db'))
    
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

    # ===== TASK-COORD-009A: 采集/推理时间轴与可观测性（只新增） =====
    # 文件源按源时间推进（按源 fps 节流读取）；摄像头源不受影响
    CAPTURE_PACING_ENABLED = os.environ.get(
        'CAPTURE_PACING_ENABLED', 'true').lower() == 'true'
    # 单次节流等待上限（秒），防止异常源 fps 导致长时间挂起
    CAPTURE_PACING_MAX_SLEEP_SEC = float(
        os.environ.get('CAPTURE_PACING_MAX_SLEEP_SEC', 1.0))
    # 事件视频输出 fps 从源时间跨度推导（否则沿用 FRAME_BUFFER_FPS）
    EVENT_VIDEO_FPS_FROM_SOURCE = os.environ.get(
        'EVENT_VIDEO_FPS_FROM_SOURCE', 'true').lower() == 'true'
    # 指标滑动窗口样本数（采集/推理 FPS）
    METRICS_WINDOW_SIZE = int(os.environ.get('METRICS_WINDOW_SIZE', 60))
    # 判定"沿用最近一次检测观测"是否已陈旧的阈值（秒）
    STALE_OBSERVATION_SEC = float(os.environ.get('STALE_OBSERVATION_SEC', 0.3))

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
        # TASK-COORD-009A
        'capture_pacing_enabled': Config.CAPTURE_PACING_ENABLED,
        'capture_pacing_max_sleep_sec': Config.CAPTURE_PACING_MAX_SLEEP_SEC,
        'event_video_fps_from_source': Config.EVENT_VIDEO_FPS_FROM_SOURCE,
        'metrics_window_size': Config.METRICS_WINDOW_SIZE,
        'stale_observation_sec': Config.STALE_OBSERVATION_SEC,
    }