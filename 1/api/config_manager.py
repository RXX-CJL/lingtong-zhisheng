# -*- coding: utf-8 -*-
"""
配置管理模块 - 管理 API Key 和调用统计
"""
import os
import json
from datetime import datetime

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config_runtime.json')

# 默认配置
DEFAULT_CONFIG = {
    "dashscope": {
        "api_key": "",
        "call_count": 0,
        "last_heartbeat_at": None,
        "last_ok": False,
        "last_error": None
    },
    "deepseek": {
        "api_key": "",
        "call_count": 0,
        "last_heartbeat_at": None,
        "last_ok": False,
        "last_error": None
    },
    "updated_at": None
}


def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        # 创建默认配置文件
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置文件"""
    try:
        config['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False


def get_masked_config():
    """获取打码后的配置（对前端安全）"""
    config = load_config()
    
    def mask_key(key):
        if not key or len(key) < 8:
            return key
        return key[:4] + '*' * (len(key) - 8) + key[-4:]
    
    return {
        "dashscope": {
            "api_key": mask_key(config['dashscope'].get('api_key', '')),
            "call_count": config['dashscope'].get('call_count', 0),
            "last_heartbeat_at": config['dashscope'].get('last_heartbeat_at'),
            "last_ok": config['dashscope'].get('last_ok', False),
            "last_error": config['dashscope'].get('last_error')
        },
        "deepseek": {
            "api_key": mask_key(config['deepseek'].get('api_key', '')),
            "call_count": config['deepseek'].get('call_count', 0),
            "last_heartbeat_at": config['deepseek'].get('last_heartbeat_at'),
            "last_ok": config['deepseek'].get('last_ok', False),
            "last_error": config['deepseek'].get('last_error')
        },
        "updated_at": config.get('updated_at')
    }


def set_api_key(provider, key):
    """设置 API Key"""
    if provider not in ['dashscope', 'deepseek']:
        return False, "Invalid provider"
    
    config = load_config()
    config[provider]['api_key'] = key
    save_config(config)
    return True, "API Key saved"


def increment_call_count(provider):
    """增加调用计数"""
    if provider not in ['dashscope', 'deepseek']:
        return
    
    config = load_config()
    config[provider]['call_count'] = config[provider].get('call_count', 0) + 1
    save_config(config)


def heartbeat(provider):
    """心跳验证 API Key 是否有效"""
    if provider not in ['dashscope', 'deepseek']:
        return False, "Invalid provider"
    
    config = load_config()
    api_key = config[provider].get('api_key', '')
    
    if not api_key:
        config[provider]['last_ok'] = False
        config[provider]['last_error'] = "API Key 未设置"
        config[provider]['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_config(config)
        return False, "API Key 未设置"
    
    if provider == 'dashscope':
        return _heartbeat_dashscope(config, api_key)
    elif provider == 'deepseek':
        return _heartbeat_deepseek(config, api_key)


def _heartbeat_dashscope(config, api_key):
    """用 qwen-turbo 文本模型验证 DashScope Key"""
    try:
        import dashscope
        from dashscope import Generation
        dashscope.api_key = api_key
        
        response = Generation.call(
            model='qwen-turbo',
            prompt='hi',
            max_tokens=5
        )
        
        if response.status_code == 200:
            # 心跳成功，增加调用计数
            try:
                increment_call_count('dashscope')
            except:
                pass
            config['dashscope']['last_ok'] = True
            config['dashscope']['last_error'] = None
            config['dashscope']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)
            return True, "心跳验证成功"
        else:
            error_msg = f"API Error {response.code}: {response.message}"
            config['dashscope']['last_ok'] = False
            config['dashscope']['last_error'] = error_msg
            config['dashscope']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)
            return False, error_msg
    except ImportError:
        # Generation 不存在，降级为基础配置验证
        if config['dashscope'].get('api_key'):
            config['dashscope']['last_ok'] = True
            config['dashscope']['last_error'] = None
            config['dashscope']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)
            return True, "Key 已配置（无法远程验证）"
        return False, "API Key 未设置"
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        config['dashscope']['last_ok'] = False
        config['dashscope']['last_error'] = error_msg
        config['dashscope']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_config(config)
        return False, error_msg


def _heartbeat_deepseek(config, api_key):
    """DeepSeek 心跳检测"""
    try:
        import requests
        
        response = requests.post(
            'https://api.deepseek.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': 'hi'}],
                'max_tokens': 5
            },
            timeout=10
        )
        
        if response.status_code == 200:
            # 心跳成功，增加调用计数
            try:
                increment_call_count('deepseek')
            except:
                pass
            config['deepseek']['last_ok'] = True
            config['deepseek']['last_error'] = None
            config['deepseek']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)
            return True, "心跳验证成功"
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            config['deepseek']['last_ok'] = False
            config['deepseek']['last_error'] = error_msg
            config['deepseek']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_config(config)
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Exception: {str(e)}"
        config['deepseek']['last_ok'] = False
        config['deepseek']['last_error'] = error_msg
        config['deepseek']['last_heartbeat_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        save_config(config)
        return False, error_msg


# 初始化：从环境变量或配置文件加载 DashScope API Key
def init_dashscope_key():
    """初始化 DashScope API Key"""
    config = load_config()
    
    # 优先使用配置文件中的 key
    if config['dashscope'].get('api_key'):
        return config['dashscope']['api_key']
    
    # 否则尝试从环境变量或 zhitong/config.py 获取
    try:
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'zhitong'))
        from config import Config
        if hasattr(Config, 'DASHSCOPE_API_KEY') and Config.DASHSCOPE_API_KEY:
            # 保存到配置文件
            set_api_key('dashscope', Config.DASHSCOPE_API_KEY)
            return Config.DASHSCOPE_API_KEY
    except:
        pass
    
    return None
