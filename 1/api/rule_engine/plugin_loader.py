# -*- coding: utf-8 -*-
"""
规则引擎插件加载器
使用 importlib.import_module 动态加载 plugins/ 目录下所有插件模块
提供按 scenario_name 获取/启用/禁用插件的能力
"""

import os
import sys
import importlib
import logging
import inspect
from typing import Dict, List, Optional, Any

from .base_plugin import BaseRulePlugin

logger = logging.getLogger(__name__)


class PluginLoader:
    """插件加载器

    用法：
        loader = PluginLoader()
        loader.discover()                  # 扫描 plugins/ 目录并加载
        loader.initialize_all()            # 初始化所有已加载插件
        plugin = loader.get("traffic")     # 按场景名获取插件
        events = plugin.analyze(frame, ctx, tracker)
        loader.disable("traffic")          # 禁用某场景
        loader.shutdown_all()              # 释放全部资源
    """

    def __init__(self, plugins_dir: Optional[str] = None,
                 enabled_scenarios: Optional[List[str]] = None):
        # 默认指向本文件同级 plugins/ 目录
        if plugins_dir is None:
            plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
        self.plugins_dir = plugins_dir
        # scenario_name -> plugin instance
        self._plugins: Dict[str, BaseRulePlugin] = {}
        # scenario_name -> enabled flag
        self._enabled: Dict[str, bool] = {}
        # 显式启用清单（None 表示全部启用）
        self._enabled_scenarios = enabled_scenarios

    # ------------------------------------------------------------------
    # 发现与加载
    # ------------------------------------------------------------------
    def discover(self) -> List[str]:
        """扫描 plugins/ 目录，动态导入所有 plugin 模块并实例化插件类

        约定：每个插件模块中应存在且仅存在一个 BaseRulePlugin 子类，
              且模块文件名以 _plugin.py 结尾（如 traffic_plugin.py）

        Returns:
            成功加载的 scenario_name 列表
        """
        if not os.path.isdir(self.plugins_dir):
            logger.warning(f"[PluginLoader] plugins 目录不存在: {self.plugins_dir}")
            return []

        loaded: List[str] = []

        # 确保 rule_engine 包及其 plugins 子包可被 import
        # 规则引擎包名为 rule_engine，plugins 子包名为 rule_engine.plugins
        package_dir = os.path.dirname(os.path.abspath(__file__))
        package_parent = os.path.dirname(package_dir)
        if package_parent not in sys.path:
            sys.path.insert(0, package_parent)

        package_name = os.path.basename(package_dir)  # rule_engine
        plugins_pkg = f"{package_name}.plugins"

        for fname in sorted(os.listdir(self.plugins_dir)):
            if not fname.endswith(".py"):
                continue
            if fname.startswith("_") or not fname.endswith("_plugin.py"):
                continue

            module_short = fname[:-3]  # traffic_plugin
            module_full = f"{plugins_pkg}.{module_short}"

            try:
                if module_full in sys.modules:
                    module = importlib.reload(sys.modules[module_full])
                else:
                    module = importlib.import_module(module_full)
            except Exception as e:
                logger.error(f"[PluginLoader] 导入模块 {module_full} 失败: {e}")
                continue

            plugin_cls = self._find_plugin_class(module)
            if plugin_cls is None:
                logger.warning(f"[PluginLoader] 模块 {module_full} 未定义 BaseRulePlugin 子类，跳过")
                continue

            try:
                instance = plugin_cls()
            except Exception as e:
                logger.error(f"[PluginLoader] 实例化 {plugin_cls.__name__} 失败: {e}")
                continue

            scenario = getattr(instance, "scenario_name", "") or ""
            if not scenario:
                logger.warning(f"[PluginLoader] {plugin_cls.__name__} 未设置 scenario_name，跳过")
                continue

            self._plugins[scenario] = instance
            # 默认按启用清单决定是否启用
            if self._enabled_scenarios is None:
                self._enabled[scenario] = True
            else:
                self._enabled[scenario] = scenario in self._enabled_scenarios
            loaded.append(scenario)
            logger.info(f"[PluginLoader] 已加载插件: {scenario} ({plugin_cls.__name__})")

        return loaded

    @staticmethod
    def _find_plugin_class(module) -> Optional[type]:
        """在模块中查找 BaseRulePlugin 的子类（排除自身）"""
        candidate = None
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if obj is BaseRulePlugin:
                continue
            if issubclass(obj, BaseRulePlugin) and obj.__module__ == module.__name__:
                # 多个候选时取第一个，并记录警告
                if candidate is not None:
                    logger.warning(
                        f"[PluginLoader] 模块 {module.__name__} 存在多个插件类，"
                        f"使用 {candidate.__name__}，忽略 {obj.__name__}"
                    )
                    continue
                candidate = obj
        return candidate

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    def initialize_all(self) -> None:
        for scenario, plugin in self._plugins.items():
            if not self._enabled.get(scenario, False):
                continue
            try:
                if not plugin.is_initialized:
                    plugin.initialize()
            except Exception as e:
                logger.error(f"[PluginLoader] 初始化插件 {scenario} 失败: {e}")
                self._enabled[scenario] = False

    def shutdown_all(self) -> None:
        for scenario, plugin in self._plugins.items():
            try:
                if plugin.is_initialized:
                    plugin.shutdown()
            except Exception as e:
                logger.error(f"[PluginLoader] 关闭插件 {scenario} 失败: {e}")
        self._plugins.clear()
        self._enabled.clear()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get(self, scenario_name: str) -> Optional[BaseRulePlugin]:
        """按 scenario_name 获取插件实例，未加载或未启用时返回 None"""
        if not self._enabled.get(scenario_name, False):
            return None
        return self._plugins.get(scenario_name)

    def list_plugins(self) -> List[str]:
        """返回所有已加载插件的 scenario_name 列表"""
        return list(self._plugins.keys())

    def list_enabled(self) -> List[str]:
        """返回所有处于启用状态的 scenario_name 列表"""
        return [s for s, ok in self._enabled.items() if ok]

    def is_enabled(self, scenario_name: str) -> bool:
        return self._enabled.get(scenario_name, False)

    # ------------------------------------------------------------------
    # 启用 / 禁用
    # ------------------------------------------------------------------
    def enable(self, scenario_name: str) -> bool:
        """启用指定场景插件（如未初始化则自动 initialize）

        Returns:
            True 表示成功启用；False 表示插件未加载或初始化失败
        """
        plugin = self._plugins.get(scenario_name)
        if plugin is None:
            logger.warning(f"[PluginLoader] 启用失败：未加载插件 {scenario_name}")
            return False
        try:
            if not plugin.is_initialized:
                plugin.initialize()
        except Exception as e:
            logger.error(f"[PluginLoader] 启用 {scenario_name} 时初始化失败: {e}")
            self._enabled[scenario_name] = False
            return False
        self._enabled[scenario_name] = True
        return True

    def disable(self, scenario_name: str) -> bool:
        """禁用指定场景插件（如已初始化则调用 shutdown）

        Returns:
            True 表示成功禁用；False 表示插件未加载
        """
        plugin = self._plugins.get(scenario_name)
        if plugin is None:
            logger.warning(f"[PluginLoader] 禁用失败：未加载插件 {scenario_name}")
            return False
        try:
            if plugin.is_initialized:
                plugin.shutdown()
        except Exception as e:
            logger.error(f"[PluginLoader] 禁用 {scenario_name} 时关闭失败: {e}")
        self._enabled[scenario_name] = False
        return True

    # ------------------------------------------------------------------
    # 调度入口：让所有启用插件依次分析
    # ------------------------------------------------------------------
    def analyze_all(self, frame: Any, scene_context: Dict[str, Any],
                    tracker: Any) -> Dict[str, List[Any]]:
        """调用所有启用插件的 analyze，返回 {scenario_name: [ViolationEvent, ...]}"""
        results: Dict[str, List[Any]] = {}
        for scenario, plugin in self._plugins.items():
            if not self._enabled.get(scenario, False):
                continue
            if not plugin.is_initialized:
                continue
            try:
                events = plugin.analyze(frame, scene_context, tracker) or []
                results[scenario] = list(events)
            except Exception as e:
                logger.error(f"[PluginLoader] 插件 {scenario}.analyze 异常: {e}")
                results[scenario] = []
        return results


# ----------------------------------------------------------------------
# 默认全局实例（按 Config.PLUGINS_ENABLED 启用）
# ----------------------------------------------------------------------
_default_loader: Optional[PluginLoader] = None


def get_default_loader() -> PluginLoader:
    """获取全局默认 PluginLoader 实例（懒加载）

    首次调用时会读取 api/config.py 的 Config.PLUGINS_ENABLED 作为启用清单
    """
    global _default_loader
    if _default_loader is not None:
        return _default_loader

    enabled_scenarios: Optional[List[str]] = None
    try:
        # 延迟导入避免循环依赖
        import config as _cfg_mod  # type: ignore
        enabled_scenarios = list(getattr(_cfg_mod.Config, "PLUGINS_ENABLED", []))
    except Exception:
        enabled_scenarios = None

    _default_loader = PluginLoader(enabled_scenarios=enabled_scenarios)
    _default_loader.discover()
    _default_loader.initialize_all()
    return _default_loader
