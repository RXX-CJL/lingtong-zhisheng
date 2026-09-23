# 规则引擎插件开发指南

本指南说明如何为「智瞳智慧交管系统」开发一个新的场景规则插件。
新插件只需 **三步**：**继承 BaseRulePlugin → 放到 plugins/ → config 启用**。

---

## 一、整体架构

```
api/
└── rule_engine/
    ├── __init__.py
    ├── base_plugin.py        # BaseRulePlugin 基类 + ViolationEvent 数据类
    ├── plugin_loader.py      # PluginLoader：动态发现/加载/启用/禁用
    └── plugins/
        ├── __init__.py
        ├── traffic_plugin.py        # 交通场景插件（示例）
        ├── urban_management_plugin.py  # 城管场景插件（待开发）
        └── public_security_plugin.py   # 治安场景插件（待开发）
```

- **BaseRulePlugin**：所有插件的抽象基类，定义统一接口。
- **ViolationEvent**：违规事件统一数据结构，跨场景通用。
- **PluginLoader**：使用 `importlib.import_module` 动态加载 `plugins/` 目录下所有以 `_plugin.py` 结尾的模块。
- **Config.PLUGINS_ENABLED**：在 `api/config.py` 中通过环境变量 `PLUGINS_ENABLED` 控制启用的场景清单。

---

## 二、三步开发新插件

### 第 1 步：继承 BaseRulePlugin

在 `api/rule_engine/plugins/` 目录下新建文件 `xxx_plugin.py`（文件名必须以 `_plugin.py` 结尾，否则不会被加载器发现）。

定义一个 `BaseRulePlugin` 的子类，实现以下抽象成员：

| 成员 / 方法 | 类型 | 说明 |
| --- | --- | --- |
| `scenario_name` | 类属性 `str` | 场景唯一标识，如 `"urban_management"` |
| `detectable_types` | 类属性 `List[str]` | 可检测的违规类型英文标识列表 |
| `initialize()` | 方法 | 初始化资源（模型/缓存/连接），末尾将 `self._initialized = True` |
| `shutdown()` | 方法 | 释放资源，将 `self._initialized = False` |
| `analyze(frame, scene_context, tracker)` | 方法 | 核心分析逻辑，返回 `List[ViolationEvent]` |

### 第 2 步：放到 plugins/ 目录

将文件保存到 `api/rule_engine/plugins/xxx_plugin.py`。
PluginLoader 会自动扫描所有 `*_plugin.py` 文件并实例化其中唯一的 `BaseRulePlugin` 子类。

> 约定：每个插件模块**有且仅有一个** `BaseRulePlugin` 子类，且该类定义在本模块中（而非 import 进来）。

### 第 3 步：在 config 启用

编辑 `api/config.py`，将新场景名加入 `PLUGINS_ENABLED`，或通过环境变量覆盖：

```bash
# 启用交通 + 城管两个场景
set PLUGINS_ENABLED=traffic,urban_management
```

默认值已包含三大场景：`traffic,urban_management,public_security`。

---

## 三、代码模板

直接复制以下模板，替换 `<...>` 占位符即可：

```python
# -*- coding: utf-8 -*-
"""
<场景名称> 规则插件
scenario_name = "<scenario_name>"
detectable_types = [<违规类型英文列表>]
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..base_plugin import BaseRulePlugin, ViolationEvent

logger = logging.getLogger(__name__)

# 行为类型 -> 中文
TYPE_CN: Dict[str, str] = {
    "<type_a>": "<中文A>",
    "<type_b>": "<中文B>",
}

# 行为类型 -> 可视化颜色 (B, G, R)
TYPE_COLOR: Dict[str, Any] = {
    "<type_a>": (0, 0, 255),
    "<type_b>": (0, 255, 0),
}


class <PluginName>Plugin(BaseRulePlugin):
    """<场景中文名> 违规检测插件"""

    scenario_name: str = "<scenario_name>"
    detectable_types: List[str] = ["<type_a>", "<type_b>"]

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config=config)
        # TODO: 在此声明私有资源句柄

    # ---------------- 生命周期 ----------------
    def initialize(self) -> None:
        # TODO: 加载模型 / 建立连接 / 初始化缓存
        self._initialized = True
        logger.info("[<PluginName>] 初始化完成")

    def shutdown(self) -> None:
        # TODO: 释放资源
        self._initialized = False
        logger.info("[<PluginName>] 已关闭")

    # ---------------- 核心分析 ----------------
    def analyze(self, frame: Any, scene_context: Dict[str, Any],
                tracker: Any) -> List[ViolationEvent]:
        if not self._initialized:
            return []

        events: List[ViolationEvent] = []

        # TODO: 实现场景特定的检测逻辑
        # 示例：从 scene_context / tracker 获取目标，逐个判定违规
        targets = scene_context.get("vehicles", []) or []
        for target in targets:
            # 伪代码：当满足违规条件时构造 ViolationEvent
            # if <some_condition(target)>:
            #     events.append(ViolationEvent(
            #         behavior_type="<type_a>",
            #         behavior_type_cn=TYPE_CN["<type_a>"],
            #         confidence=0.85,
            #         is_violation=True,
            #         evidence={"detail": "..."},
            #         vehicle_id=int(target.get("id", -1)),
            #         timestamp=datetime.now().isoformat(),
            #         color=TYPE_COLOR["<type_a>"],
            #     ))
            pass

        return events
```

---

## 四、ViolationEvent 字段说明

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `behavior_type` | `str` | 行为类型英文标识，如 `"red_light"` |
| `behavior_type_cn` | `str` | 行为类型中文描述，如 `"闯红灯"` |
| `confidence` | `float` | 置信度 `[0.0, 1.0]` |
| `is_violation` | `bool` | 是否判定为违规 |
| `evidence` | `Dict[str, Any]` | 证据字典（轨迹/速度/区域等结构化信息） |
| `vehicle_id` | `int` | 关联目标 track_id，无关联时填 `-1` |
| `timestamp` | `str` | ISO8601 时间字符串 |
| `color` | `Any` | 事件标注颜色（BGR 元组或颜色名），用于可视化 |

---

## 五、调用方式

### 5.1 通过 PluginLoader 调用

```python
from rule_engine.plugin_loader import get_default_loader

loader = get_default_loader()

# 列出已加载插件
print(loader.list_plugins())        # ['traffic', ...]
print(loader.list_enabled())        # ['traffic', ...]

# 按场景名获取插件
plugin = loader.get("traffic")
if plugin is not None:
    events = plugin.analyze(frame, scene_context, tracker)

# 一次性调用所有启用插件
all_events = loader.analyze_all(frame, scene_context, tracker)
# all_events: {"traffic": [ViolationEvent, ...], "urban_management": [...]}
```

### 5.2 启用 / 禁用某场景

```python
loader.enable("urban_management")   # 启用并自动 initialize
loader.disable("traffic")           # 调用 shutdown 并标记为禁用
loader.is_enabled("traffic")        # False
```

### 5.3 调整启用清单

```python
# 方式一：修改 api/config.py 默认值（影响所有进程）
# 方式二：设置环境变量（推荐，无需改代码）
#   Windows
set PLUGINS_ENABLED=traffic,urban_management
#   Linux / macOS
export PLUGINS_ENABLED=traffic,urban_management
```

---

## 六、参考实现：traffic_plugin.py

`api/rule_engine/plugins/traffic_plugin.py` 是一个完整可运行的示例：

- `scenario_name = "traffic"`
- `detectable_types = ["red_light", "wrong_way", "illegal_parking", "no_helmet", "speeding"]`
- `analyze` 内部调用 `behavior_engine.BehaviorEngine.analyze_all`，并将 `BehaviorResult` 转换为 `ViolationEvent` 返回。

新插件可参照其结构编写。

---

## 七、注意事项

1. 文件编码统一使用 `# -*- coding: utf-8 -*-`。
2. 插件类**不要**在模块顶层执行耗时操作（如加载模型），耗时初始化放到 `initialize()` 中。
3. `analyze` 方法应**幂等且无副作用**，异常应自行捕获并返回空列表，避免影响其他插件。
4. 插件之间的依赖应通过 `scene_context` 传递，避免直接互相 import。
5. 修改 `realtime_detector.py` 不在本指南范围；如需将插件接入主流程，请在调用方显式使用 `PluginLoader`。
