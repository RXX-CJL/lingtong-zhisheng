class Translation:
    CLASS_NAMES = {
        'person': '行人',
        'bicycle': '自行车',
        'car': '汽车',
        'motorcycle': '摩托车',
        'bus': '公交车',
        'truck': '货车',
        'traffic light': '红绿灯',
        'stop sign': '停止标志',
        'unknown': '未知'
    }
    
    VIOLATION_TYPES = {
        'red_light': '闯红灯',
        'no_helmet': '未戴头盔',
        'wrong_way': '逆行',
        'illegal_parking': '违停',
        'lane_departure': '压线',
        'speeding': '超速'
    }
    
    WARNING_LEVELS = {
        1: '轻度提示',
        2: '正式警告',
        3: '严厉警告'
    }
    
    UI_ELEMENTS = {
        'title': '智瞳灵声智慧交管系统',
        'subtitle': '基于视觉识别与云端推理的智慧交管系统',
        'tracks': '跟踪目标',
        'violations': '违规数量',
        'help_space': '空格: 本地播报',
        'help_c': 'C: 云端分析',
        'help_q': 'Q: 退出',
        'camera_detection': '正在检测可用摄像头...',
        'camera_available': '索引 {index}: 可用',
        'camera_not_found': '未检测到可用摄像头',
        'camera_auto_select': '自动选择摄像头索引 {index}',
        'camera_select_prompt': '请选择摄像头索引:',
        'roi_setup': '设置检测区域 (按ESC跳过，按Space确认)',
        'roi_points_prompt': '选择停车线点 (左键点击，Space完成):',
        'roi_point_added': '点 {index}: ({x}, {y})',
        'roi_skip': '跳过区域设置',
        'roi_complete': '设置完成，共 {count} 个点',
        'roi_insufficient': '点不足，跳过区域设置',
        'system_init': '初始化系统...',
        'system_ready': '系统初始化完成',
        'local_announcement': '[本地播报]',
        'cloud_analysis': '[云端分析] 正在请求...',
        'cloud_result': '[云端分析结果]',
        'level': '级别',
        'speed': '速度',
        'speed_limit': '限速'
    }
    
    @classmethod
    def translate_class(cls, class_name: str) -> str:
        return cls.CLASS_NAMES.get(class_name, class_name)
    
    @classmethod
    def translate_violation(cls, violation_type: str) -> str:
        return cls.VIOLATION_TYPES.get(violation_type, violation_type)
    
    @classmethod
    def translate_warning_level(cls, level: int) -> str:
        return cls.WARNING_LEVELS.get(level, str(level))
    
    @classmethod
    def get_ui_text(cls, key: str) -> str:
        return cls.UI_ELEMENTS.get(key, key)
