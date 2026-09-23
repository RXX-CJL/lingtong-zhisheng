# -*- coding: utf-8 -*-
"""
规则引擎插件基础接口
定义插件基类 BaseRulePlugin 与违规事件数据类 ViolationEvent
所有场景插件（交通 / 城管 / 治安 等）均继承 BaseRulePlugin 并实现 analyze 方法
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ViolationEvent:
    """违规事件数据结构

    Attributes:
        behavior_type: 行为类型英文标识，如 "red_light"
        behavior_type_cn: 行为类型中文描述，如 "闯红灯"
        confidence: 置信度 [0.0, 1.0]
        is_violation: 是否判定为违规
        evidence: 证据字典（轨迹/速度/区域等结构化信息）
        vehicle_id: 关联的车辆/目标 track_id，无关联时为 -1
        timestamp: ISO8601 时间字符串
        color: 事件标注颜色（BGR 元组或颜色名），用于可视化
    """
    behavior_type: str
    behavior_type_cn: str
    confidence: float
    is_violation: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    vehicle_id: int = -1
    timestamp: str = ""
    color: Any = (0, 0, 255)


class BaseRulePlugin(ABC):
    """规则插件基类

    子类必须实现以下属性/方法：
        - scenario_name: 场景标识
        - detectable_types: 可检测的违规类型列表
        - initialize(): 资源初始化
        - shutdown(): 资源释放
        - analyze(frame, scene_context, tracker): 执行分析并返回 ViolationEvent 列表
    """

    # 场景标识，例如 "traffic" / "urban_management" / "public_security"
    scenario_name: str = "base"

    # 可检测的违规类型列表，例如 ["red_light", "wrong_way"]
    detectable_types: List[str] = []

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._initialized = False

    @abstractmethod
    def initialize(self) -> None:
        """初始化插件资源（模型/缓存/外部连接等）

        子类应实现该方法并在末尾将 self._initialized 置为 True
        """
        self._initialized = True

    @abstractmethod
    def shutdown(self) -> None:
        """释放插件资源"""
        self._initialized = False

    @abstractmethod
    def analyze(self, frame: Any, scene_context: Dict[str, Any],
                tracker: Any) -> List[ViolationEvent]:
        """对单帧画面执行违规分析

        Args:
            frame: 当前视频帧（numpy ndarray / PIL Image 等）
            scene_context: 场景上下文（红绿灯状态、禁停区、车道线等）
            tracker: 车辆/目标追踪器实例

        Returns:
            ViolationEvent 列表（仅包含 is_violation=True 的事件）
        """
        raise NotImplementedError

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def __repr__(self) -> str:
        return (f"<{self.__class__.__name__} scenario={self.scenario_name} "
                f"types={self.detectable_types} initialized={self._initialized}>")
