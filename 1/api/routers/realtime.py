# -*- coding: utf-8 -*-
"""
实时检测API路由模块

说明：
- 凡是内部调用同步阻塞方法（cv2 操作 / threading.Lock / YOLO 推理 / 云端 HTTP）
  的路由，一律声明为普通 `def`，FastAPI 会将其放入线程池执行，
  从而避免阻塞主事件循环。
- 仅 StreamingResponse 与 WebSocket 这种必须用 await 的路由才用 `async def`。
- 之前的写法在 async def 路由里直接调用 realtime_detector.get_status()
  等同步方法（内部持有 threading.Lock），会阻塞事件循环，
  导致启动检测后整个后端 8001 卡死（curl 超时、数字孪生页面 pending）。
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging

from realtime_detector import realtime_detector

logger = logging.getLogger("zhitong_api")

router = APIRouter(prefix="/api/realtime", tags=["realtime"])

class StartDetectionRequest(BaseModel):
    camera_index: Optional[int] = 0
    video_path: Optional[str] = None

class StartDetectionResponse(BaseModel):
    success: bool
    message: str

class DetectFrameRequest(BaseModel):
    frame: str  # base64 编码的 JPEG 帧（前端 getUserMedia 截图）

@router.post("/start", response_model=StartDetectionResponse)
def start_detection(request: StartDetectionRequest):
    # start_camera 内部 cv2.VideoCapture 为阻塞调用，放线程池执行
    try:
        realtime_detector.start_camera(request.camera_index, request.video_path)
        result = realtime_detector.start_detection()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动检测失败: {str(e)}")

@router.post("/stop")
def stop_detection():
    result = realtime_detector.stop()
    return JSONResponse(content=result)

@router.get("/status")
def get_status():
    # get_status() 内部 with self.lock，同步阻塞，放线程池执行
    status = realtime_detector.get_status()
    return JSONResponse(content={"success": True, "data": status})

@router.get("/snapshot")
def get_snapshot():
    snapshot = realtime_detector.get_snapshot()
    if snapshot:
        return JSONResponse(content={
            "success": True,
            "image_base64": snapshot,
            "timestamp": realtime_detector.get_status()['total_frames']
        })
    return JSONResponse(content={"success": False, "message": "未获取到画面"}, status_code=404)

@router.post("/detect-frame")
def detect_frame(request: DetectFrameRequest):
    """接收前端 getUserMedia 采集的帧做检测（前端直接访问摄像头，后端只做检测）"""
    result = realtime_detector.detect_external_frame(request.frame)
    return JSONResponse(content=result)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        realtime_detector.register_websocket_client(self._create_client_proxy(websocket))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            realtime_detector.unregister_websocket_client(self._create_client_proxy(websocket))

    def _create_client_proxy(self, websocket):
        class WebSocketClientProxy:
            def __init__(self, ws):
                self.ws = ws

            async def send_json(self, data):
                await self.ws.send_text(json.dumps(data, ensure_ascii=False))

        return WebSocketClientProxy(websocket)

manager = ConnectionManager()

@router.websocket("/violations/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"[WebSocket] 收到消息: {data[:100]}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/camera/list")
def list_cameras():
    # cv2.VideoCapture / cap.read 均为阻塞调用，放线程池执行
    cameras = []
    for i in range(4):
        cap = None
        try:
            cap = __import__('cv2').VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    cameras.append({"index": i, "available": True})
                else:
                    cameras.append({"index": i, "available": False})
            else:
                cameras.append({"index": i, "available": False})
        except Exception:
            cameras.append({"index": i, "available": False})
        finally:
            if cap:
                cap.release()
    return JSONResponse(content={"success": True, "cameras": cameras})

@router.get("/stream")
async def video_stream():
    """MJPEG视频流接口（async 生成器 + to_thread，不阻塞事件循环）"""
    import numpy as np
    cv2 = __import__('cv2')
    from datetime import datetime

    def _fallback_diagnostic(title: str, msg: str):
        """当检测器或 OpenCV 出问题时，用明确的诊断帧代替空流（避免前端橙色异常）"""
        h, w = 720, 1280
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = (20, 20, 60)  # 深蓝背景，避免橙色误会
        cv2.rectangle(frame, (0, 0), (w, 96), (0, 90, 200), -1)
        cv2.putText(frame, 'ZhiTong LingSheng - Stream Diagnostic', (24, 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        cv2.putText(frame, title, (24, 84),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 100), 2)
        y = 160
        for line in msg.split('\n'):
            cv2.putText(frame, line, (40, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (220, 230, 255), 2)
            y += 32
        cv2.putText(frame, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), (24, h - 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 200, 255), 2)
        ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 78])
        return buf.tobytes() if ok else b''

    async def generate():
        while True:
            try:
                # get_annotated_frame 内部 with self.lock，用 to_thread 避免阻塞事件循环
                frame = await asyncio.to_thread(realtime_detector.get_annotated_frame)
                if frame is None:
                    # 兜底（理论上不该走到这里，但双重保险）
                    jpg_bytes = _fallback_diagnostic(
                        'DETECTOR RETURNED NONE',
                        'current_frame is None.\n'
                        'Please POST /api/realtime/start with camera_index.\n'
                        'If you are on /realtime page, use "开始检测" button instead.'
                    )
                    if jpg_bytes:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')
                else:
                    _, buffer = await asyncio.to_thread(
                        cv2.imencode, '.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80]
                    )
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            except Exception as e:
                logger.warning(f"[stream] 生成帧异常，输出诊断帧: {e}")
                jpg_bytes = _fallback_diagnostic(
                    'STREAM EXCEPTION',
                    f'{type(e).__name__}: {str(e)[:120]}\n'
                    'Check backend console logs for traceback.'
                )
                if jpg_bytes:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')
            await asyncio.sleep(0.05)

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.post("/consult")
def force_cloud_consult():
    """强制云端咨询接口（YOLO + 云端 HTTP，耗时较长，放线程池执行）"""
    try:
        snapshot = realtime_detector.get_snapshot()
        if not snapshot:
            return JSONResponse(content={"success": False, "message": "未获取到画面"}, status_code=400)

        result = realtime_detector.force_cloud_consult()
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"云端咨询失败: {str(e)}")

@router.get("/tracked-vehicles")
def get_tracked_vehicles():
    """获取当前追踪车辆列表"""
    vehicles = realtime_detector.get_tracked_vehicles()
    return JSONResponse(content={
        "success": True,
        "data": vehicles,
        "count": len(vehicles)
    })

@router.get("/behavior-stats")
def get_behavior_stats():
    """获取行为分析统计"""
    stats = realtime_detector.get_behavior_statistics()
    status = realtime_detector.get_status()
    return JSONResponse(content={
        "success": True,
        "data": {
            **stats,
            "running": status['running'],
            "tracked_vehicle_count": status['tracked_vehicle_count']
        }
    })


# ==================================================================
# M07: 规则引擎插件管理接口
# ==================================================================

# 场景模式常量
SCENE_PRESETS: Dict[str, List[str]] = {
    "traffic": ["traffic"],
    "urban_management": ["urban_management"],
    "public_security": ["public_security"],
    "all": ["traffic", "urban_management", "public_security"],
}

SCENE_PRESET_CN: Dict[str, str] = {
    "traffic": "交通模式",
    "urban_management": "城管模式",
    "public_security": "治安模式",
    "all": "全量模式",
}


def _get_plugin_loader():
    """懒加载全局 PluginLoader（来自 rule_engine.plugin_loader）"""
    try:
        from rule_engine.plugin_loader import get_default_loader
        return get_default_loader()
    except Exception as e:
        logger.warning(f"[plugins] 获取 PluginLoader 失败: {e}")
        return None


@router.get("/plugins")
def list_plugins():
    """M07: 列出所有已加载规则引擎插件及启用状态"""
    loader = _get_plugin_loader()
    if loader is None:
        return JSONResponse(content={
            "success": False,
            "message": "PluginLoader 不可用",
            "plugins": [],
            "scene_presets": SCENE_PRESETS,
            "scene_presets_cn": SCENE_PRESET_CN,
        })

    plugins_info = []
    for scenario in loader.list_plugins():
        plugin = loader._plugins.get(scenario)
        detectable_types = list(getattr(plugin, "detectable_types", [])) if plugin else []
        plugins_info.append({
            "scenario_name": scenario,
            "enabled": loader.is_enabled(scenario),
            "initialized": bool(getattr(plugin, "is_initialized", False)) if plugin else False,
            "detectable_types": detectable_types,
        })

    return JSONResponse(content={
        "success": True,
        "plugins": plugins_info,
        "enabled_scenarios": loader.list_enabled(),
        "scene_presets": SCENE_PRESETS,
        "scene_presets_cn": SCENE_PRESET_CN,
    })


class PluginSwitchRequest(BaseModel):
    """单插件启用/禁用请求"""
    scenario_name: str
    enabled: bool


@router.post("/plugins/switch")
def switch_plugin(request: PluginSwitchRequest):
    """M07: 启用/禁用单个插件"""
    loader = _get_plugin_loader()
    if loader is None:
        return JSONResponse(content={"success": False, "message": "PluginLoader 不可用"}, status_code=500)

    scenario = request.scenario_name
    if scenario not in loader.list_plugins():
        return JSONResponse(content={"success": False, "message": f"插件 {scenario} 未加载"}, status_code=404)

    if request.enabled:
        ok = loader.enable(scenario)
    else:
        ok = loader.disable(scenario)

    return JSONResponse(content={
        "success": ok,
        "scenario_name": scenario,
        "enabled": loader.is_enabled(scenario),
        "message": f"插件 {scenario} 已{'启用' if request.enabled else '禁用'}" if ok else f"插件 {scenario} 切换失败"
    })


class SceneModeRequest(BaseModel):
    """场景模式切换请求"""
    scene_mode: str  # traffic / urban_management / public_security / all


@router.post("/plugins/scene-mode")
def set_scene_mode(request: SceneModeRequest):
    """M07: 按预设场景模式批量切换插件启用清单

    scene_mode 取值：
        - traffic: 仅交通
        - urban_management: 仅城管
        - public_security: 仅治安
        - all: 全量启用
    """
    loader = _get_plugin_loader()
    if loader is None:
        return JSONResponse(content={"success": False, "message": "PluginLoader 不可用"}, status_code=500)

    mode = request.scene_mode
    if mode not in SCENE_PRESETS:
        return JSONResponse(content={
            "success": False,
            "message": f"未知场景模式: {mode}，可选: {list(SCENE_PRESETS.keys())}"
        }, status_code=400)

    target_scenarios = SCENE_PRESETS[mode]
    # 先禁用不在目标清单中的插件
    for scenario in loader.list_plugins():
        if scenario not in target_scenarios:
            loader.disable(scenario)
    # 再启用目标清单中的插件
    for scenario in target_scenarios:
        loader.enable(scenario)

    return JSONResponse(content={
        "success": True,
        "scene_mode": mode,
        "scene_mode_cn": SCENE_PRESET_CN.get(mode, mode),
        "enabled_scenarios": loader.list_enabled(),
        "message": f"已切换到 {SCENE_PRESET_CN.get(mode, mode)}"
    })


@router.get("/plugins/scene-modes")
def get_scene_modes():
    """M07: 获取可用的场景模式列表（供前端下拉框使用）"""
    modes = [
        {
            "value": key,
            "label": SCENE_PRESET_CN.get(key, key),
            "scenarios": scenarios,
        }
        for key, scenarios in SCENE_PRESETS.items()
    ]
    return JSONResponse(content={"success": True, "scene_modes": modes})


# ==================================================================
# M09/M10: 软件虚拟追踪管理接口
# ==================================================================

_virtual_tracker_instance = None


def _get_virtual_tracker():
    """懒加载全局 VirtualTracker 实例"""
    global _virtual_tracker_instance
    if _virtual_tracker_instance is not None:
        return _virtual_tracker_instance
    try:
        from virtual_tracker import VirtualTracker
        _virtual_tracker_instance = VirtualTracker()
        return _virtual_tracker_instance
    except Exception as e:
        logger.warning(f"[tracking] VirtualTracker 加载失败: {e}")
        return None


@router.post("/tracking/start")
def start_tracking(track_id: int = 0):
    """M09: 锁定追踪目标

    Query 参数:
        track_id: 要追踪的目标 track_id
    """
    tracker = _get_virtual_tracker()
    if tracker is None:
        return JSONResponse(content={"success": False, "message": "VirtualTracker 不可用"}, status_code=500)

    # 从 realtime_detector 获取该 track 的当前 bbox
    target_bbox = None
    try:
        for v in realtime_detector.get_tracked_vehicles():
            if v.get("id") == track_id:
                target_bbox = v.get("bbox", [0, 0, 0, 0])
                break
    except Exception:
        pass

    if target_bbox is None:
        return JSONResponse(content={"success": False, "message": f"未找到 track_id={track_id} 的目标"})

    ok = tracker.start_tracking(track_id, target_bbox)
    return JSONResponse(content={
        "success": ok,
        "track_id": track_id,
        "target_bbox": target_bbox,
        "message": f"已锁定追踪目标 ID={track_id}" if ok else "锁定失败"
    })


@router.post("/tracking/stop")
def stop_tracking():
    """M09: 取消追踪"""
    tracker = _get_virtual_tracker()
    if tracker is None:
        return JSONResponse(content={"success": False, "message": "VirtualTracker 不可用"}, status_code=500)
    tracker.stop_tracking()
    return JSONResponse(content={"success": True, "message": "已取消追踪"})


@router.get("/tracking/status")
def get_tracking_status():
    """M09: 获取追踪状态 + 画中画裁剪图（base64 JPEG）"""
    tracker = _get_virtual_tracker()
    if tracker is None:
        return JSONResponse(content={
            "success": True,
            "is_tracking": False,
            "track_id": None,
            "message": "VirtualTracker 不可用"
        })

    info = tracker.get_focus_indicator()
    crop_base64 = None
    if tracker.is_tracking():
        try:
            # 从 realtime_detector 获取当前帧
            frame = getattr(realtime_detector, "current_frame", None)
            if frame is not None:
                # 同步所有 tracks 给 VirtualTracker
                all_tracks = [
                    {
                        "track_id": v.get("id", -1),
                        "bbox": v.get("bbox", [0, 0, 0, 0]),
                        "class_name": v.get("class_name", "car"),
                        "confidence": v.get("confidence", 0.0),
                        "violation_type": v.get("violation_type"),
                        "status": v.get("status", "normal"),
                    }
                    for v in realtime_detector.get_tracked_vehicles()
                ]
                tracker.update(frame, all_tracks)
                crop_img = tracker.get_tracking_crop(frame, out_size=(480, 480))
                if crop_img is not None:
                    import cv2 as _cv2
                    ok, buf = _cv2.imencode('.jpg', crop_img, [_cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ok:
                        import base64 as _b64
                        crop_base64 = "data:image/jpeg;base64," + _b64.b64encode(buf.tobytes()).decode('ascii')
        except Exception as e:
            logger.warning(f"[tracking] 获取裁剪图失败: {e}")

    return JSONResponse(content={
        "success": True,
        "is_tracking": tracker.is_tracking(),
        "track_id": tracker.get_current_track_id(),
        "focus_indicator": info,
        "crop_image_base64": crop_base64,
        "tracked_vehicles": realtime_detector.get_tracked_vehicles()
    })


# ==================================================================
# M08: ONVIF 云台控制接口（PTZ）
# ==================================================================

_ptz_controller_instance = None


def _get_ptz_controller():
    """懒加载全局 PTZ 控制器实例（默认 Simulated，配置后切 ONVIF）"""
    global _ptz_controller_instance
    if _ptz_controller_instance is not None:
        return _ptz_controller_instance
    try:
        from ptz_controller import PTZFactory
        # 默认无配置 → SimulatedPTZController；真实摄像头通过 config 切 ONVIF
        try:
            from config import Config
            cfg = getattr(Config, "PTZ_CONFIG", None)
            _ptz_controller_instance = PTZFactory(cfg if isinstance(cfg, dict) else None)
        except Exception:
            _ptz_controller_instance = PTZFactory(None)
        return _ptz_controller_instance
    except Exception as e:
        logger.warning(f"[ptz] PTZController 加载失败: {e}")
        return None


class PTZMoveRequest(BaseModel):
    """云台绝对/相对移动请求"""
    pan: float = 0.0
    tilt: float = 0.0
    zoom: float = 0.0
    speed: float = 0.5
    relative: bool = False  # True=相对移动，False=绝对移动


class PTZZoomRequest(BaseModel):
    """云台变焦请求"""
    level: float = 1.0
    direction: str = "in"  # in / out


@router.get("/ptz/status")
def ptz_status():
    """M08: 获取云台当前位置"""
    ctl = _get_ptz_controller()
    if ctl is None:
        return JSONResponse(content={"success": False, "message": "PTZController 不可用"}, status_code=500)
    return JSONResponse(content={
        "success": True,
        "position": ctl.get_position(),
        "controller_type": type(ctl).__name__,
    })


@router.post("/ptz/move")
def ptz_move(request: PTZMoveRequest):
    """M08: 云台移动（绝对或相对）"""
    ctl = _get_ptz_controller()
    if ctl is None:
        return JSONResponse(content={"success": False, "message": "PTZController 不可用"}, status_code=500)
    if request.relative:
        ok = ctl.move_relative(request.pan, request.tilt, request.zoom, request.speed)
    else:
        ok = ctl.move_absolute(request.pan, request.tilt, request.zoom, request.speed)
    return JSONResponse(content={
        "success": ok,
        "mode": "relative" if request.relative else "absolute",
        "position": ctl.get_position(),
        "message": "移动指令已下发" if ok else "移动失败",
    })


@router.post("/ptz/zoom")
def ptz_zoom(request: PTZZoomRequest):
    """M08: 云台变焦"""
    ctl = _get_ptz_controller()
    if ctl is None:
        return JSONResponse(content={"success": False, "message": "PTZController 不可用"}, status_code=500)
    if request.direction == "out":
        ok = ctl.zoom_out(request.level)
    else:
        ok = ctl.zoom_in(request.level)
    return JSONResponse(content={
        "success": ok,
        "direction": request.direction,
        "level": request.level,
        "position": ctl.get_position(),
    })


@router.post("/ptz/home")
def ptz_home():
    """M08: 云台回中"""
    ctl = _get_ptz_controller()
    if ctl is None:
        return JSONResponse(content={"success": False, "message": "PTZController 不可用"}, status_code=500)
    ok = ctl.goto_home()
    return JSONResponse(content={
        "success": ok,
        "position": ctl.get_position(),
        "message": "已回中" if ok else "回中失败",
    })


# ==================================================================
# M17: CARLA 仿真数据源接口
# ==================================================================

_carla_source_instance = None


def _get_carla_source():
    """懒加载全局 CarlaSource 实例"""
    global _carla_source_instance
    if _carla_source_instance is not None:
        return _carla_source_instance
    try:
        from carla_source import CarlaSource
        _carla_source_instance = CarlaSource()
        return _carla_source_instance
    except Exception as e:
        logger.warning(f"[carla] CarlaSource 加载失败: {e}")
        return None


class SourceSwitchRequest(BaseModel):
    """数据源切换请求"""
    source_type: str  # camera / video / carla
    video_path: Optional[str] = None
    camera_index: Optional[int] = 0


class CarlaSpawnRequest(BaseModel):
    """CARLA 生成 actor 请求"""
    vehicles: int = 20
    walkers: int = 10


class CarlaSceneRequest(BaseModel):
    """CARLA 切换城镇/演示场景请求"""
    town: Optional[str] = None  # Town01..Town07 / Town10HD
    scene: Optional[str] = None  # town01 / town03 / violation


@router.post("/source")
def switch_source(request: SourceSwitchRequest):
    """M17: 切换实时检测数据源（camera/video/carla）"""
    try:
        ok = realtime_detector.set_source(
            source_type=request.source_type,
            video_path=request.video_path,
            camera_index=request.camera_index,
        )
        return JSONResponse(content={
            "success": ok,
            "source_type": request.source_type,
            "message": f"已切换数据源为 {request.source_type}" if ok else "切换失败",
        })
    except AttributeError:
        # realtime_detector 未实现 set_source 时，记录但返回友好提示
        return JSONResponse(content={
            "success": False,
            "message": "realtime_detector 暂不支持数据源切换接口 set_source",
            "hint": "请检查 realtime_detector.py 是否已集成 M17 source_type 字段",
        }, status_code=501)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"切换数据源失败: {str(e)}")


@router.get("/carla/status")
def carla_status():
    """M17: 获取 CARLA 连接状态、actor 数量、当前地图"""
    src = _get_carla_source()
    if src is None:
        return JSONResponse(content={
            "success": False,
            "connected": False,
            "message": "CarlaSource 不可用（carla 模块未安装或加载失败）",
        })
    connected = src.is_connected()
    return JSONResponse(content={
        "success": True,
        "connected": connected,
        "controller_type": type(src).__name__,
        "message": "CARLA 已连接" if connected else "CARLA 未连接，请先调用 /carla/connect",
    })


@router.post("/carla/connect")
def carla_connect():
    """M17: 连接 CARLA 服务器（localhost:2000）"""
    src = _get_carla_source()
    if src is None:
        return JSONResponse(content={"success": False, "message": "CarlaSource 不可用"}, status_code=500)
    ok = src.connect(host="127.0.0.1", port=2000)
    return JSONResponse(content={
        "success": ok,
        "connected": src.is_connected(),
        "message": "CARLA 连接成功" if ok else "CARLA 连接失败，请确认 CarlaUE4.exe 已启动",
    })


@router.post("/carla/spawn")
def carla_spawn(request: CarlaSpawnRequest):
    """M17: 在 CARLA 中生成车辆和行人"""
    src = _get_carla_source()
    if src is None or not src.is_connected():
        return JSONResponse(content={
            "success": False,
            "message": "CARLA 未连接，请先调用 /carla/connect",
        }, status_code=400)
    veh_ids = src.spawn_vehicles(request.vehicles) if request.vehicles > 0 else []
    walker_ids = src.spawn_walkers(request.walkers) if request.walkers > 0 else []
    return JSONResponse(content={
        "success": True,
        "vehicle_ids": veh_ids,
        "walker_ids": walker_ids,
        "vehicle_count": len(veh_ids),
        "walker_count": len(walker_ids),
    })


@router.post("/carla/next-scene")
def carla_next_scene(request: CarlaSceneRequest):
    """M17: 切换 CARLA 城镇或触发演示场景"""
    src = _get_carla_source()
    if src is None or not src.is_connected():
        return JSONResponse(content={
            "success": False,
            "message": "CARLA 未连接",
        }, status_code=400)
    if request.town:
        ok = src.load_town(request.town)
        return JSONResponse(content={
            "success": ok,
            "town": request.town,
            "message": f"已加载地图 {request.town}" if ok else f"加载地图 {request.town} 失败",
        })
    if request.scene == "violation":
        try:
            actor_id = src.spawn_red_light_violator()
            return JSONResponse(content={
                "success": True,
                "scene": "violation",
                "violator_actor_id": actor_id,
                "message": "已生成一辆闯红灯车辆",
            })
        except Exception as e:
            return JSONResponse(content={"success": False, "message": f"生成违规车辆失败: {e}"}, status_code=500)
    return JSONResponse(content={"success": False, "message": "未指定 town 或 scene"}, status_code=400)


@router.get("/carla/actors")
def carla_actors():
    """M17: 获取 CARLA 中所有车辆/行人位置（数字孪生联动用）"""
    src = _get_carla_source()
    if src is None or not src.is_connected():
        return JSONResponse(content={"success": False, "actors": [], "message": "CARLA 未连接"})
    actors = src.get_actors_state()
    lights = src.get_traffic_lights()
    return JSONResponse(content={
        "success": True,
        "actors": actors,
        "actor_count": len(actors),
        "traffic_lights": lights,
    })


# ============================================================
# M07: 交通事件系统路由（GPT §10 + §15.1）
# 共 6 个路由，覆盖事件列表/详情/视频/关键帧/人工复核/活跃事件
# ============================================================

# 终态集合（用于查询过滤）
_TERMINAL_STATES = {"confirmed", "rejected"}


def _sync_active_events_to_db():
    """将 realtime_detector.active_events 同步到 traffic_events 表（graceful degradation）

    每次列表/详情查询前调用一次，确保内存中的最新事件状态可被前端看到。
    """
    try:
        from database import SessionLocal
        from models import TrafficEventRecord
        from datetime import datetime

        db = SessionLocal()
        try:
            saved_count = 0
            for event_id, event in realtime_detector.active_events.items():
                # 内存中事件 dict 化
                evt_dict = event.to_dict() if hasattr(event, 'to_dict') else event
                # 查询是否已存在
                existing = db.query(TrafficEventRecord).filter_by(event_id=event_id).first()
                trigger_dt = None
                if evt_dict.get('trigger_time'):
                    try:
                        trigger_dt = datetime.fromtimestamp(float(evt_dict['trigger_time']))
                    except Exception:
                        trigger_dt = None

                common_fields = {
                    'event_type': evt_dict.get('event_type'),
                    'track_id': evt_dict.get('track_id'),
                    'state': evt_dict.get('state', 'detecting'),
                    'trigger_time': trigger_dt,
                    'vehicle_info': json.dumps(evt_dict.get('vehicle_info', {}), ensure_ascii=False),
                    'scene_context': json.dumps(evt_dict.get('scene_context', {}), ensure_ascii=False),
                    'trajectory': json.dumps(evt_dict.get('trajectory', []), ensure_ascii=False),
                    'key_frames': json.dumps(evt_dict.get('key_frames', []), ensure_ascii=False),
                    'event_video_path': evt_dict.get('event_video_path', '') or '',
                    'rule_judgment': json.dumps(evt_dict.get('rule_judgment', {}), ensure_ascii=False),
                    'ai_judgment': json.dumps(evt_dict.get('ai_judgment', {}), ensure_ascii=False),
                    'ai_confidence': float(evt_dict.get('ai_confidence', 0.0) or 0.0),
                    'ai_explanation': evt_dict.get('ai_explanation', '') or '',
                    'state_history': json.dumps(evt_dict.get('state_history', []), ensure_ascii=False),
                    'camera_id': f"cam_{realtime_detector.camera_index}",
                    'updated_at': datetime.utcnow(),
                }
                if existing:
                    for k, v in common_fields.items():
                        setattr(existing, k, v)
                else:
                    record = TrafficEventRecord(
                        event_id=event_id,
                        created_at=datetime.utcnow(),
                        **common_fields,
                    )
                    db.add(record)
                saved_count += 1
            db.commit()
            return saved_count
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[realtime.events] 同步活跃事件到数据库失败: {e}")
        return 0


@router.get("/events")
def list_events(state: Optional[str] = None, page: int = 1, size: int = 20,
                camera_id: Optional[str] = None):
    """M07: 事件列表（分页+状态筛选）

    优先返回内存活跃事件 + 数据库历史事件合并视图。
    """
    # 同步一次内存事件到数据库
    _sync_active_events_to_db()

    try:
        from database import SessionLocal
        from models import TrafficEventRecord
        db = SessionLocal()
        try:
            query = db.query(TrafficEventRecord)
            if state and state.lower() != "all":
                query = query.filter(TrafficEventRecord.state == state.lower())
            if camera_id:
                query = query.filter(TrafficEventRecord.camera_id == camera_id)

            total = query.count()
            # 按创建时间倒序
            items = query.order_by(TrafficEventRecord.created_at.desc()) \
                .offset((page - 1) * size) \
                .limit(size) \
                .all()
            return JSONResponse(content={
                "success": True,
                "data": [it.to_dict() for it in items],
                "total": total,
                "page": page,
                "size": size,
            })
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[realtime.events] 列表查询失败: {e}")
        return JSONResponse(content={"success": False, "message": f"查询失败: {e}"},
                           status_code=500)


@router.get("/events/active")
def list_active_events():
    """M07: 当前活跃事件列表（state 不是 confirmed/rejected 的事件）

    优先从内存读取，确保实时性。
    """
    try:
        active = []
        # 1) 优先从内存读取（实时性最高）
        for event_id, event in realtime_detector.active_events.items():
            evt_dict = event.to_dict() if hasattr(event, 'to_dict') else event
            state_val = evt_dict.get('state', 'detecting')
            if state_val in _TERMINAL_STATES:
                continue
            active.append(evt_dict)
        # 2) 若内存为空，则查询数据库
        if not active:
            from database import SessionLocal
            from models import TrafficEventRecord
            db = SessionLocal()
            try:
                records = db.query(TrafficEventRecord) \
                    .filter(~TrafficEventRecord.state.in_(list(_TERMINAL_STATES))) \
                    .order_by(TrafficEventRecord.created_at.desc()) \
                    .limit(50) \
                    .all()
                active = [r.to_dict() for r in records]
            finally:
                db.close()
        return JSONResponse(content={
            "success": True,
            "data": active,
            "count": len(active),
        })
    except Exception as e:
        logger.error(f"[realtime.events] 活跃事件查询失败: {e}")
        return JSONResponse(content={"success": False, "message": f"查询失败: {e}"},
                           status_code=500)


@router.get("/events/{event_id}")
def get_event_detail(event_id: str):
    """M07: 事件详情（含完整证据链）

    优先从内存读取（实时性），否则查数据库（历史）。
    """
    # 1) 内存查找
    event = realtime_detector.active_events.get(event_id)
    if event is not None:
        evt_dict = event.to_dict() if hasattr(event, 'to_dict') else event
        # 同时构造证据链
        try:
            from evidence_chain import EvidenceChain
            evidence = EvidenceChain.from_traffic_event(event, camera_id=f"cam_{realtime_detector.camera_index}")
            evt_dict['evidence_chain'] = evidence.to_dict()
        except Exception as e:
            logger.warning(f"[realtime.events] 构建证据链失败: {e}")
        return JSONResponse(content={"success": True, "data": evt_dict})

    # 2) 数据库查找
    try:
        from database import SessionLocal
        from models import TrafficEventRecord
        db = SessionLocal()
        try:
            record = db.query(TrafficEventRecord).filter_by(event_id=event_id).first()
            if record is None:
                return JSONResponse(content={"success": False, "message": f"事件不存在: {event_id}"},
                                    status_code=404)
            return JSONResponse(content={"success": True, "data": record.to_dict()})
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[realtime.events] 事件详情查询失败: {e}")
        return JSONResponse(content={"success": False, "message": f"查询失败: {e}"},
                           status_code=500)


@router.get("/events/{event_id}/video")
def get_event_video(event_id: str):
    """M07: 事件视频文件（FileResponse）

    优先从内存读取路径，否则查数据库。
    """
    import os
    from fastapi.responses import FileResponse

    video_path = ""
    # 1) 内存查找
    event = realtime_detector.active_events.get(event_id)
    if event is not None:
        video_path = getattr(event, 'event_video_path', '') or ''

    # 2) 数据库查找
    if not video_path:
        try:
            from database import SessionLocal
            from models import TrafficEventRecord
            db = SessionLocal()
            try:
                record = db.query(TrafficEventRecord).filter_by(event_id=event_id).first()
                if record and record.event_video_path:
                    video_path = record.event_video_path
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[realtime.events] 视频路径查询失败: {e}")

    if not video_path or not os.path.exists(video_path):
        return JSONResponse(content={"success": False, "message": "事件视频不存在或尚未生成"},
                           status_code=404)

    return FileResponse(video_path, media_type="video/mp4",
                        filename=f"{event_id}.mp4")


@router.get("/events/{event_id}/frames")
def get_event_frames(event_id: str):
    """M07: 事件关键帧列表

    返回关键帧路径列表（前端可逐个加载）。
    """
    key_frames = []
    event = realtime_detector.active_events.get(event_id)
    if event is not None:
        key_frames = getattr(event, 'key_frames', []) or []

    if not key_frames:
        try:
            from database import SessionLocal
            from models import TrafficEventRecord
            db = SessionLocal()
            try:
                record = db.query(TrafficEventRecord).filter_by(event_id=event_id).first()
                if record and record.key_frames:
                    try:
                        key_frames = json.loads(record.key_frames)
                    except Exception:
                        key_frames = []
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[realtime.events] 关键帧查询失败: {e}")

    return JSONResponse(content={
        "success": True,
        "event_id": event_id,
        "key_frames": key_frames,
        "count": len(key_frames),
    })


class EventReviewRequest(BaseModel):
    """人工复核请求"""
    confirmed: bool  # True=确认违法 False=排除事件
    reviewer: Optional[str] = "commander"
    comment: Optional[str] = ""


@router.post("/events/{event_id}/review")
def review_event(event_id: str, request: EventReviewRequest):
    """M07: 人工复核事件（MANUAL_REVIEW → CONFIRMED/REJECTED）

    同时更新内存事件状态和数据库记录。
    """
    # 1) 内存事件
    event = realtime_detector.active_events.get(event_id)
    if event is None:
        # 数据库可能存在历史事件
        try:
            from database import SessionLocal
            from models import TrafficEventRecord
            from datetime import datetime
            db = SessionLocal()
            try:
                record = db.query(TrafficEventRecord).filter_by(event_id=event_id).first()
                if record is None:
                    return JSONResponse(content={"success": False, "message": f"事件不存在: {event_id}"},
                                       status_code=404)
                record.state = "confirmed" if request.confirmed else "rejected"
                record.updated_at = datetime.utcnow()
                record.state_history = json.dumps([{
                    "timestamp": datetime.utcnow().isoformat(),
                    "old_state": record.state,
                    "new_state": record.state,
                    "reason": f"人工复核 reviewer={request.reviewer} comment={request.comment}",
                }], ensure_ascii=False)
                db.commit()
                return JSONResponse(content={
                    "success": True,
                    "event_id": event_id,
                    "new_state": record.state,
                    "message": "已更新数据库事件状态",
                })
            finally:
                db.close()
        except Exception as e:
            logger.error(f"[realtime.events] 数据库人工复核失败: {e}")
            return JSONResponse(content={"success": False, "message": f"复核失败: {e}"},
                               status_code=500)

    # 2) 内存事件：调用事件引擎 manual_review
    try:
        if realtime_detector.event_engine is None:
            return JSONResponse(content={"success": False, "message": "事件引擎未初始化"},
                               status_code=500)
        realtime_detector.event_engine.manual_review(
            event_id=event_id,
            confirmed=request.confirmed,
            reviewer=request.reviewer or "",
            comment=request.comment or "",
        )
        # 同步到数据库
        _sync_active_events_to_db()
        new_state = "confirmed" if request.confirmed else "rejected"
        return JSONResponse(content={
            "success": True,
            "event_id": event_id,
            "new_state": new_state,
            "message": "人工复核完成",
        })
    except ValueError as e:
        return JSONResponse(content={"success": False, "message": f"状态转换非法: {e}"},
                           status_code=400)
    except KeyError as e:
        return JSONResponse(content={"success": False, "message": f"事件不存在: {e}"},
                           status_code=404)
    except Exception as e:
        logger.error(f"[realtime.events] 人工复核异常: {e}")
        return JSONResponse(content={"success": False, "message": f"复核失败: {e}"},
                           status_code=500)
