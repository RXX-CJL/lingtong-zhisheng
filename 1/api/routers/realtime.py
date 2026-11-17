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
from fastapi.responses import JSONResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
import logging
import os
import cv2

from image_recognizer import CLASS_CN_MAP
from violation_rules import VIOLATION_TYPE_CN

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
    # 必须在切换/释放采集源之前检查运行状态，避免重复点击先替换正在使用的数据源。
    if realtime_detector.running:
        return JSONResponse(
            content={"success": False, "message": "检测已在运行中，请先停止后再切换数据源"},
            status_code=409,
        )
    # 上一轮仍有事件正在提取证据时，不允许新一轮清空循环缓存。
    if getattr(realtime_detector, "_pending_event_evidence", None):
        return JSONResponse(
            content={"success": False, "message": "上一轮事件证据仍在保存，请稍后重试"},
            status_code=409,
        )
    # start_camera 内部 cv2.VideoCapture 为阻塞调用，放线程池执行
    try:
        # ★2026-11-07 由 DSH 修复（BUG-3，实测踩到）：
        #   原实现无条件调 start_camera()，而它内部会把 source_type 强制写成
        #   "camera" 或 "video"（realtime_detector.py:656 / :721），
        #   于是「先 POST /source {source_type:carla} 再 POST /start」这个顺序
        #   会把刚设好的 carla 源覆盖掉，转而去开本机摄像头。
        #   实测证据（8002 端口）：
        #     /source {carla} -> source_type=carla
        #     /start          -> source_type=camera, total_frames=124（录了本机摄像头）
        #   修法：当前源已是 carla 时跳过 start_camera()，直接启动检测循环；
        #   循环里 _detection_loop 的 carla 分支（:890）负责取帧。
        cur_src = getattr(realtime_detector, "source_type", None)
        if cur_src == "carla":
            cs = getattr(realtime_detector, "carla_source", None)
            if cs is None or not cs.is_connected():
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "当前数据源为 CARLA 但未连接，请先调用 /api/realtime/carla/connect",
                    },
                    status_code=409,
                )
        elif cur_src == "video":
            # ★2026-11-07 由 DSH 修复（BUG-3 的 video 分支，实测踩到）：
            #   上面只对 carla 做了跳过，video 落到 else -> start_camera(video_path=None)
            #   -> classify_source(None) 判成 camera -> 转而打开本机摄像头。
            #   实测证据：/source{video, video_path:X} 返回 success=true，
            #             /status 却报 source_type=camera、tracked_vehicle_count=0。
            #   修法：当前源已是 video 且已记住路径时，用记住的路径重开视频，
            #        而不是退化成摄像头。路径为空才回落到摄像头。
            _vp = getattr(realtime_detector, "video_path", None)
            if _vp:
                realtime_detector.start_camera(
                    request.camera_index, _vp)
            else:
                realtime_detector.start_camera(
                    request.camera_index, request.video_path)
        else:
            realtime_detector.start_camera(request.camera_index, request.video_path)
        result = realtime_detector.start_detection()
        status_code = 200 if result.get("success") else 409
        return JSONResponse(content=result, status_code=status_code)
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


# ==================================================================
# 检测类过滤模式（2026-11-17 新增）
#   traffic：只保留交通白名单，不画盆栽/椅子/运动球（默认，交管场景）
#   all    ：保留 YOLO 全部原生类别（演示时能看到人/手机/杯子等）
# ==================================================================
class ClassModeRequest(BaseModel):
    mode: str  # traffic | all


@router.post("/class-mode")
def set_class_mode(request: ClassModeRequest):
    try:
        mode = realtime_detector.set_class_filter_mode(request.mode)
        return JSONResponse(content={"success": True, "mode": mode})
    except ValueError as e:
        return JSONResponse(status_code=400,
                            content={"success": False, "message": str(e)})


@router.get("/class-mode")
def get_class_mode():
    return JSONResponse(content={
        "success": True,
        "mode": getattr(realtime_detector, 'class_filter_mode', 'traffic'),
    })

class WebSocketClientProxy:
    """WebSocket 的轻量代理（2026-10-23 由 DSH 从 ConnectionManager 内部类提出来）

    修的两个既有缺陷：
      ① 反注册永远匹配不上：原 _create_client_proxy() 每次调用都 **新建** 一个内部类实例，
         connect() 注册实例 A、disconnect() 反注册实例 B，而普通对象 a == b 恒为 False
         -> list.remove(B) 匹配不到 -> web_socket_clients **只增不减**，
         断开的死连接一直留在列表里被反复推送（每次 send 抛异常并让 push_failed +1）。
         实测现象：ws_clients=1 但前端其实早断了；push_failed 只增不减。
      ② 反注册语句被缩进在 if 块内：若 websocket 已不在 active_connections，
         整条反注册被跳过（见下面的 disconnect 注释）。
    修法：按底层 websocket 对象判等（__eq__/__hash__），并缓存同一个代理实例。
    """

    def __init__(self, ws):
        self.ws = ws

    async def send_json(self, data):
        await self.ws.send_text(json.dumps(data, ensure_ascii=False))

    def __eq__(self, other):
        return isinstance(other, WebSocketClientProxy) and other.ws is self.ws

    def __hash__(self):
        return hash(id(self.ws))


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        # websocket -> 代理实例，保证注册/反注册用的是**同一个对象**
        self._proxies: dict = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        proxy = self._get_client_proxy(websocket)
        realtime_detector.register_websocket_client(proxy)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # ★2026-10-23：反注册必须**在 if 之外**执行。
        #   原实现在 if 块内，连接一旦不在 active_connections 就整条跳过 -> 死连接残留。
        proxy = self._proxies.pop(websocket, None)
        realtime_detector.unregister_websocket_client(proxy or WebSocketClientProxy(websocket))

    def _get_client_proxy(self, websocket):
        proxy = self._proxies.get(websocket)
        if proxy is None:
            proxy = WebSocketClientProxy(websocket)
            self._proxies[websocket] = proxy
        return proxy

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
                # ★2026-11-18：改用帧级缓存的 JPEG。
                #   原先每个客户端、每一轮都调 get_annotated_frame 重画一次框、
                #   再各自 imencode；画框持 self.lock，直接和检测线程抢锁。
                #   实测端到端只有 2.43 fps，而四个模型本身只要 67ms —— 瓶颈就在这。
                #   现在同一帧只画一次、编码一次，所有客户端共用。
                jpg_bytes = await asyncio.to_thread(realtime_detector.get_annotated_jpeg, 80)
                if not jpg_bytes:
                    jpg_bytes = _fallback_diagnostic(
                        'DETECTOR RETURNED NONE',
                        'current_frame is None.\n'
                        'Please POST /api/realtime/start with camera_index.\n'
                        'If you are on /realtime page, use "开始检测" button instead.'
                    )
                if jpg_bytes:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n')
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

@router.get("/zoom-frame")
def get_zoom_frame(track_id: Optional[int] = None,
                   cx: Optional[int] = None, cy: Optional[int] = None,
                   scale: float = 2.0, quality: int = 88):
    """按目标裁剪并放大当前帧（2026-10-03 由 DSH 新增）

    用途：支撑直播页的"拉近-定格-拉远"抓拍动画。
    前端无法从 MJPEG 流拿到原始帧，故由后端按目标框裁剪返回 JPEG。

    参数：
      track_id: 优先——按该追踪车辆的 bbox 裁剪
      cx, cy  : 退而求其次——按画面坐标为中心裁剪
      scale   : 放大倍数（1.0~4.0，只影响裁剪范围，不改变分辨率上限）
      quality : JPEG 质量

    注意（重要）：本接口仅供**展示层**使用。
      落盘证据（uploads/realtime_*.jpg）始终是**原始整帧**，不做任何裁剪放大，
      以保证证据链完整性与可追溯性。
    """
    try:
        d = realtime_detector
        with d.lock:
            frame = None if d.current_frame is None else d.current_frame.copy()
            tracked = dict(d.tracked_vehicles or {})
        if frame is None:
            raise HTTPException(status_code=404, detail="当前无画面")

        H, W = frame.shape[:2]
        bbox = None
        if track_id is not None:
            veh = tracked.get(track_id) or tracked.get(str(track_id))
            if veh and len(veh.get("bbox") or []) >= 4:
                bbox = [float(v) for v in veh["bbox"][:4]]
        if bbox is None:
            if cx is None or cy is None:
                # 没有目标：返回整帧（前端可据此平滑回退）
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
                return Response(content=buf.tobytes(), media_type="image/jpeg")
            bbox = [cx - 40, cy - 40, cx + 40, cy + 40]

        x1, y1, x2, y2 = bbox
        w, h = max(8.0, x2 - x1), max(8.0, y2 - y1)
        # 放大倍数 -> 裁剪范围收缩：scale 越大，取的区域越小（越"近"）
        s = max(1.0, min(4.0, float(scale)))
        pad = 0.6                      # 目标周围留白比例
        half_w = (w / 2.0) * (1.0 + pad) / s
        half_h = (h / 2.0) * (1.0 + pad) / s
        cxp, cyp = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        nx1 = int(max(0, cxp - half_w)); nx2 = int(min(W, cxp + half_w))
        ny1 = int(max(0, cyp - half_h)); ny2 = int(min(H, cyp + half_h))
        if nx2 - nx1 < 16 or ny2 - ny1 < 16:
            raise HTTPException(status_code=400, detail="裁剪区域过小")
        crop = frame[ny1:ny2, nx1:nx2]
        ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise HTTPException(status_code=500, detail="编码失败")
        return Response(content=buf.tobytes(), media_type="image/jpeg",
                        headers={"X-Crop": f"{nx1},{ny1},{nx2},{ny2}",
                                 "Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取裁剪帧失败: {str(e)}")


@router.get("/evidence")
def list_realtime_evidence(limit: int = 24, violation_type: Optional[str] = None):
    """列出实时抓拍的证据图（2026-10-03 由 DSH 新增）

    数据来源：Config.UPLOAD_DIR 下的 realtime_{类型}_{时间戳}.jpg
    这些是**原始整帧**（未裁剪、未放大），用于证据留存。

    返回：[{name, url, type, type_cn, time, size_kb, mtime}]
    """
    try:
        from config import Config
        d = Config.UPLOAD_DIR
        if not os.path.isdir(d):
            return JSONResponse(content={"success": True, "data": [], "dir": d,
                                         "message": "证据目录不存在"})
        import re as _re
        # ★★2026-10-06 由 DSH 修复（实测性能问题，很可能是用户反馈"刷新页面卡住"的元凶）：
        #   原实现 `glob(realtime_*.jpg)` -> 对**每一个**文件 os.stat() -> 排序 -> 才切片 limit。
        #   现场实测：uploads/ 下有 4526 个文件（其中 4513 张实时抓拍），
        #   于是**每次请求要 stat 4513 次、却只返回 24 条** -> 稳定 **500ms**；
        #   而前端每 1.5 秒轮询一次，还顺带加载 24 张 2MB 级原图。
        #   现改为 os.scandir 单次遍历（DirEntry 自带 stat 缓存，比 os.stat 快一个量级），
        #   并按 mtime 取前 N 再建对象 —— 仍保证"最新的在前"语义不变。
        limit_n = max(1, min(200, int(limit)))
        entries = []
        with os.scandir(d) as it:
            for e in it:
                nm = e.name
                if not (nm.startswith("realtime_") and nm.endswith(".jpg")):
                    continue
                # ★2026-10-10 由 DSH 放宽：文件名的时间戳现在带**毫秒**，且用 `-` 与
                #   秒部分分隔（`realtime_{类型}_{YYYYmmdd}_{HHMMSS}-{mmm}.jpg`）。
                #   用 `-` 而不是 `_` 是为了让"最后一段下划线后是时间戳"的
                #   类型解析规则继续成立（否则类型会变成 red_light_221353）。
                #   老文件（无毫秒）与新文件都要认。
                m = _re.match(r"realtime_(.+?)_(\d{8}_\d{6}(?:-\d{3})?)\.jpg$", nm)
                vtype = m.group(1) if m else "unknown"
                if violation_type and violation_type not in vtype:
                    continue
                try:
                    st = e.stat()          # DirEntry.stat() 复用 scandir 已取到的信息
                except OSError:
                    continue
                entries.append((st.st_mtime, nm, vtype,
                                m.group(2) if m else "", st.st_size))
        entries.sort(key=lambda x: x[0], reverse=True)   # 新的在前
        total = len(entries)

        # ★★2026-10-10 由 DSH 新增：**给抓拍证据补上关键信息**（用户要求
        #   "只要下方的违规抓拍证据能有记录就行，而且最好要有违法时间等关键信息"）。
        #   原先这里只回 文件名/类型/大小/时间(来自文件名)，看不出：
        #     · 违法时间（精确到秒的真实时间，而不是文件名里的紧凑格式）
        #     · 是哪辆车（track_id）、置信度、车牌
        #   这些都在 `violation_evidences` 表里（`_persist_violation` 落库时写了）。
        #   做法：只对**本次要返回的那些行**（≤ limit）按 image_path 批量查一次，
        #   避免 T68 那类"先做重活再切片"的性能坑。
        _detail = {}
        try:
            import sqlite3
            from config import Config
            names = [nm for (_m, nm, _t, _s, _z) in entries[:limit_n]]
            if names:
                marks = ",".join("?" * len(names))
                cx = sqlite3.connect(Config.DB_PATH, timeout=5)
                try:
                    cx.row_factory = sqlite3.Row
                    for r in cx.execute(
                            f"select image_path, id, violation_type, track_id, confidence, "
                            f"timestamp, plate_number, status "
                            f"from violation_evidences where image_path in ({marks})",
                            names):
                        _detail[r["image_path"]] = r
                finally:
                    cx.close()
        except Exception as e:
            logger.debug(f"[evidence] 查询证据详情失败（仅影响附加信息）: {e}")

        items = []
        for (mtime, nm, vtype, stamp, size) in entries[:limit_n]:
            row = _detail.get(nm)
            # 文件名里的时间戳：YYYYmmdd_HHMMSS[-mmm] -> YYYY-MM-DD HH:MM:SS(.mmm)
            cap_time = ""
            try:
                _s = stamp.replace("_", "")
                if len(_s) >= 14:
                    cap_time = (f"{_s[0:4]}-{_s[4:6]}-{_s[6:8]} "
                                f"{_s[8:10]}:{_s[10:12]}:{_s[12:14]}"
                                + (f".{stamp.split('-')[1]}" if '-' in stamp else ""))
            except Exception:
                cap_time = stamp
            items.append({
                "name": nm,
                "url": f"/uploads/{nm}",
                "type": vtype,
                "type_cn": VIOLATION_TYPE_CN.get(vtype, vtype),
                "time": stamp.replace("_", " "),
                # ↓ 关键信息（可能为空：早期抓拍未落库 / 查询失败）
                "captured_at": cap_time,                       # 抓拍时间（文件名，最可靠）
                "violation_at": (str(row["timestamp"]) if row and row["timestamp"] else None),
                "record_id": (int(row["id"]) if row else None),
                "track_id": (int(row["track_id"]) if row and row["track_id"] is not None else None),
                "confidence": (round(float(row["confidence"]), 3)
                               if row and row["confidence"] is not None else None),
                "plate_number": (row["plate_number"] if row else None),
                "review_status": (row["status"] if row else None),
                "size_kb": round(size / 1024.0, 1),
                "mtime": mtime,
            })
        return JSONResponse(content={"success": True, "data": items,
                                     "total": total, "dir": d})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出证据失败: {str(e)}")


@router.get("/settings")
def get_settings():
    """读取运行时设置（检测开关 / 置信度门槛 / 冷却期 / 云端开关）"""
    try:
        from realtime_detector import get_runtime_settings
        return JSONResponse(content={"success": True, "data": get_runtime_settings()})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取设置失败: {str(e)}")


@router.post("/settings")
def update_settings(patch: dict):
    """更新运行时设置（无需重启，立即生效）

    请求体示例：
      {
        "enabled_types": {"red_light": false},          // 关掉某类检测
        "min_confidence": {"illegal_parking": 0.75},    // 调高门槛
        "hold_sec": 2.0, "cooldown_sec": 10,
        "cloud_consult": false                          // 暂停云端咨询（省 token）
      }
    返回更新后的完整设置。
    """
    try:
        from realtime_detector import update_runtime_settings
        data = update_runtime_settings(patch or {})
        logger.info(f"[settings] 运行时设置已更新: {list((patch or {}).keys())}")
        return JSONResponse(content={"success": True, "data": data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新设置失败: {str(e)}")


@router.get("/vehicles")
def get_vehicles_split():
    """车辆左右分流列表（2026-10-03 由 DSH 新增，供直播页三栏布局使用）

    返回：
      clean     - 未违规车辆（左栏）：ID / 类型 / 速度 / 方向 / 车牌
      violators - 违规车辆（右栏）：上述信息 + 违规类型 + 置信度
      summary   - 计数与阈值快照

    分流依据：当前帧违规列表（_last_violations）按 track_id 归属。
    车辆若从违规变为未违规，会自动出现在 clean 中（满足"动态迁移"需求）。
    """
    try:
        d = realtime_detector
        with d.lock:
            tracked = dict(d.tracked_vehicles or {})
            plates = dict(getattr(d, "_plate_cache", {}) or {})
            violations = list(getattr(d, "_last_violations", []) or [])
            # 带时效的最近违规优先（2026-10-03 由 DSH 新增）
            # _last_violations 在有违规的帧才非空，且无违规帧立刻清空；
            # 违规受确认时长/冷却期抑制，导致页面几乎读不到 -> 右栏恒空。
            recent = []
            try:
                recent = list(d.get_recent_violations() or [])
            except Exception:
                recent = []
            if recent:
                # 合并去重：最近违规 + 本帧违规（本帧优先）
                seen = set()
                merged = []
                for v in violations + recent:
                    k = (v.get("violation_type"),
                         v.get("vehicle_id") or v.get("track_id"),
                         round(float(v.get("confidence", 0) or 0), 3))
                    if k in seen:
                        continue
                    seen.add(k)
                    merged.append(v)
                violations = merged
            lights = list(getattr(d, "_last_traffic_lights", []) or [])

        viol_map = {}
        _unassigned = []          # 无几何依据、未归属到任何车辆的告警
        # 先尝试直接按 track_id / vehicle_id 归属（行为引擎的违规带此字段）
        _unmatched = []
        def _extract_tid(v):
            """从违规对象里挖出 track_id（2026-10-03 由 DSH 重写）

            踩坑记录：ID 可能藏在多处，实测 wrong_way 的 ID 在
              evidence.wrong_way_details[0].vehicle_id
            原先只看顶层与 evidence 直接字段，导致提取率 0%。
            现在按优先级：顶层 -> evidence 直接 -> evidence 下的明细列表。
            """
            keys = ("track_id", "vehicle_id", "id")
            # ① 顶层 / evidence 直接字段
            for src in (v, v.get("evidence") or {}):
                if isinstance(src, dict):
                    for k in keys:
                        if src.get(k) is not None:
                            try:
                                return int(float(src[k]))
                            except (TypeError, ValueError):
                                pass
            # ② evidence 下的明细列表（wrong_way_details / details / vehicles ...）
            ev = v.get("evidence") or {}
            if isinstance(ev, dict):
                for val in ev.values():
                    if isinstance(val, list):
                        for item in val:
                            if isinstance(item, dict):
                                for k in keys:
                                    if item.get(k) is not None:
                                        try:
                                            return int(float(item[k]))
                                        except (TypeError, ValueError):
                                            pass
            return None

        # 当前有效追踪 ID 集合（用于校验提取出的 ID 是否仍然有效）
        _valid_ids = set()
        for _k in tracked.keys():
            try:
                _valid_ids.add(int(_k))
            except (TypeError, ValueError):
                pass

        # ★★2026-10-10 由 DSH 记录一次"做了又按用户口径改回"的取舍：
        #   用户反馈"违规告警栏没有反应"，我先做成"车辆驶出画面后仍保留告警卡片
        #   （stale=True，前端标「已离开画面」）"。用户随后明确口径：
        #     **"其实汽车离开画面后就不用显示了（之前是完全不显示，所以问题很大），
        #       只要下方的违规抓拍证据能有记录就行，而且最好要有违法时间等关键信息"**
        #   -> 即：**告警栏只服务于"画面里正在发生的违规"**；已经离开的由
        #      **下方的抓拍证据（带时间等关键信息）**承担留痕职责。
        #   所以这里不再生成 stale 卡片；ID 失效就照旧跳过（车辆已不在画面）。
        #   ⚠ 真正修掉"没反应"的是另一件事：**重复违规（loop_dedup 命中）仍然喂展示缓存**
        #      （见 realtime_detector._push_repeat_alert）—— 那一层保留。
        for v in violations:
            tid = _extract_tid(v)
            entry = {
                "type": v.get("violation_type"),
                "type_cn": v.get("violation_type_cn") or v.get("violation_type"),
                "confidence": round(float(v.get("confidence", 0) or 0), 3),
                "source": v.get("source", "rule_engine"),
                "age_sec": v.get("_age_sec"),
                # ★2026-10-10：跨圈重复抑制命中的"重复出现"（只展示、不存证、不计费）
                "repeat": bool(v.get("repeat")),
            }
            # 2026-10-03 由 DSH 修正：提取到的 ID 必须**仍在当前追踪集合里**。
            # 实测 wrong_way 的 evidence 里写着 vehicle_id=3，但当时追踪只有
            # ID1/ID2 —— ID3 是已消失车辆的旧 ID，直接采纳会指向不存在的车
            # （前端右栏因此永远匹配不上）。失效则退化为几何匹配。
            if tid is not None and tid not in _valid_ids:
                # 该车已驶出画面 / tracker 已丢弃它 —— 按用户口径**不进告警栏**
                # （留痕由下方的抓拍证据承担，见 /evidence 的关键信息）
                entry["_stale_id"] = tid
                tid = None
            if tid is not None:
                viol_map.setdefault(tid, []).append(entry)
            else:
                _unmatched.append((v, entry))

        # 规则引擎的违规**不带 track_id**（只有 location/evidence），
        # 用空间匹配归属到追踪车辆（2026-10-03 由 DSH 修复）：
        #   ① evidence/location 里的 bbox 与车辆框做 IoU
        #   ② location 是点 -> 判断落在哪个车辆框内
        #   ③ 退化：全场仅一辆车时直接归属
        if _unmatched:
            tb = []
            for tid, veh in tracked.items():
                try:
                    ti = int(tid)
                except (TypeError, ValueError):
                    continue
                bb = veh.get("bbox") or []
                if len(bb) >= 4:
                    tb.append((ti, [float(x) for x in bb[:4]]))

            def _by_iou(bb):
                if not bb or len(bb) < 4:
                    return None
                ax1, ay1, ax2, ay2 = [float(x) for x in bb[:4]]
                a_area = max(1.0, (ax2 - ax1) * (ay2 - ay1))
                best, best_iou = None, 0.0
                for ti, t in tb:
                    ix1, iy1 = max(ax1, t[0]), max(ay1, t[1])
                    ix2, iy2 = min(ax2, t[2]), min(ay2, t[3])
                    if ix2 <= ix1 or iy2 <= iy1:
                        continue
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    b_area = max(1.0, (t[2] - t[0]) * (t[3] - t[1]))
                    iou = inter / (a_area + b_area - inter)
                    if iou > best_iou:
                        best, best_iou = ti, iou
                return best if best_iou >= 0.2 else None

            def _by_point(pt):
                """按 location 判断归属（2026-10-03 由 DSH 扩展）

                兼容两种 location 结构：
                  ① {'x': .., 'y': ..}
                  ② {'bbox': [x1,y1,x2,y2], 'center_x': .., 'center_y': ..}  ← 实测常见
                原实现只读 x/y，对 ② 永远拿不到坐标，导致违规全部落入"未归属"。
                """
                if not isinstance(pt, dict):
                    return None
                px = py = None
                for kx, ky in (("x", "y"), ("center_x", "center_y"),
                               ("cx", "cy"), ("point_x", "point_y")):
                    try:
                        if pt.get(kx) is not None and pt.get(ky) is not None:
                            px, py = float(pt[kx]), float(pt[ky])
                            break
                    except (TypeError, ValueError):
                        continue
                if px is None:
                    bb = pt.get("bbox") or pt.get("target_bbox")
                    if isinstance(bb, (list, tuple)) and len(bb) >= 4:
                        try:
                            px = (float(bb[0]) + float(bb[2])) / 2.0
                            py = (float(bb[1]) + float(bb[3])) / 2.0
                        except (TypeError, ValueError):
                            return None
                if px is None:
                    return None
                for ti, t in tb:
                    if t[0] <= px <= t[2] and t[1] <= py <= t[3]:
                        return ti
                return None

            for v, entry in _unmatched:
                tid = None
                for src in (v.get("evidence") or {}, v.get("location") or {}, v):
                    if isinstance(src, dict):
                        bb = src.get("bbox") or src.get("target_bbox") or src.get("vehicle_bbox")
                        if isinstance(bb, (list, tuple)) and len(bb) >= 4:
                            tid = _by_iou(bb)
                            if tid is not None:
                                break
                if tid is None:
                    tid = _by_point(v.get("location"))
                # 不再"全场仅一辆车就硬归给它"（2026-10-03 由 DSH 修正）：
                # 无几何依据的归属会造成"违规挂到无关车辆"（实测红灯违规
                # 被挂到画面中央卡车）。宁可留空，由前端显示为未归属告警。
                if tid is not None:
                    viol_map.setdefault(tid, []).append(entry)
                else:
                    _unassigned.append(entry)

        clean, violators = [], []
        # 速度标定器（视频测速：像素位移 -> km/h）
        # 2026-10-03 由 DSH 新增：把 tracker 的"像素/秒"换算成"km/h"，
        # 并标注可信度（calibrated / assumed），供超速判定与人工复核参考。
        try:
            from speed_calibration import SpeedCalibrator, speed_from_history
            scene = getattr(d, "_scene_annotation", None) or {}
            _frame = None
            with d.lock:
                if d.current_frame is not None:
                    _frame = d.current_frame
            _h, _w = (_frame.shape[:2] if _frame is not None else (576, 1280))
            calib = SpeedCalibrator(scene, frame_width=_w, frame_height=_h)
            _speed_info = calib.info()
        except Exception as _calib_err:
            # ★2026-11-07 由 WorkBuddy 修正（静默失败 -> 可见）：
            #   原来这里是裸 `except Exception:`，**不留任何日志**。
            #   实测后果：/vehicles 的 speed_calibration 变成 {}、
            #   所有车辆都没有 speed_kmh —— 现场表现为「测速永远没有数据」，
            #   却查不到任何原因（本次任务排查测速时撞上）。
            #   保留原有降级行为（不拖垮接口），但把异常打出来。
            logger.warning(f"[realtime.vehicles] 测速标定初始化失败（降级：不显示测速）: "
                           f"{type(_calib_err).__name__}: {_calib_err}")
            SpeedCalibrator = None
            speed_from_history = None
            calib = None
            # ★把失败原因**放进响应体**：项目日志只落 INFO 级，warning 进不了日志文件，
            #   光靠日志仍然查不到（实测：改完 warning 后日志里仍是 0 条 WARNING）。
            #   现在接口直接告诉调用方「为什么没有测速」。
            _speed_info = {
                "error": f"{type(_calib_err).__name__}: {_calib_err}",
                "calibrated": False,
                "method": "unavailable",
            }

        for tid, veh in tracked.items():
            try:
                tid_i = int(tid)
            except (TypeError, ValueError):
                continue
            sp = veh.get("speed")
            item = {
                "track_id": tid_i,
                "class_name": veh.get("class_name"),
                "class_name_cn": CLASS_CN_MAP.get(veh.get("class_name"), veh.get("class_name")),
                "speed_px": round(float(sp), 2) if isinstance(sp, (int, float)) else None,
                "direction": veh.get("direction"),
                "bbox": veh.get("bbox"),
                "plate": plates.get(tid_i) or veh.get("plate_number") or None,
                "is_wrong_way": bool(veh.get("is_wrong_way")),
                "frame_count": veh.get("frame_count"),
            }
            # 真实车速估算（基于轨迹历史 + 标定）
            if speed_from_history is not None and calib is not None:
                try:
                    est = speed_from_history(veh.get("history") or [], calib)
                    item["speed_kmh"] = est.get("kmh")
                    item["speed_method"] = est.get("method")
                    item["speed_confidence"] = est.get("confidence")
                    # 补充测速细节（2026-10-03 由 DSH 新增）
                    # measurement_quality: ok / sparse / broken —— 采样质量
                    # kmh_raw: 未做帧率补偿的原始值（便于复核与对比）
                    item["speed_quality"] = est.get("measurement_quality")
                    item["speed_kmh_raw"] = est.get("kmh_raw")
                    item["speed_fps"] = est.get("fps")
                    item["speed_compensation"] = est.get("fps_compensation")
                except Exception:
                    item["speed_kmh"] = None
            vs = viol_map.get(tid_i)
            if vs:
                item["violations"] = vs
                item["primary_violation"] = vs[0]["type_cn"]
                item["confidence"] = vs[0]["confidence"]
                violators.append(item)
            else:
                clean.append(item)

        clean.sort(key=lambda x: x["track_id"])
        violators.sort(key=lambda x: -x.get("confidence", 0))

        return JSONResponse(content={
            "success": True,
            "data": {
                "clean": clean,
                "violators": violators,
                "unassigned": _unassigned,
                "traffic_lights": lights,
                "speed_calibration": _speed_info,
                "summary": {
                    "clean_count": len(clean),
                    "violator_count": len(violators),
                    "tracked_total": len(tracked),
                    "violation_hold_sec": float(os.environ.get("VIOLATION_HOLD_SEC", "1.5")),
                    "violation_cooldown_sec": float(os.environ.get("VIOLATION_COOLDOWN_SEC", "8")),
                    "min_report_default": float(os.environ.get("MIN_REPORT_DEFAULT", "0.65")),
                },
            },
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取车辆分流失败: {str(e)}")


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
                # ★2026-11-07 由 WorkBuddy 新增：把违规车的真实世界证据返回，
                #   便于外部脚本核对「它是否真的朝受控红灯开过停止线」。
                "violator": src.get_violator_state(),
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
    # ★2026-11-07 由 WorkBuddy 新增：违规车会话 + 受控红灯进口（取证用）
    violator = {}
    approach = {}
    try:
        violator = src.get_violator_state() or {}
        ap = src.get_controlled_approach() or {}
        approach = {
            "light_id": ap.get("light_id"),
            "lane": ap.get("lane"),
            "stop_point_world": ap.get("stop_point"),
            "stop_line_pixel": ap.get("stop_pixel"),
            "stop_depth_m": ap.get("stop_depth_m"),
        }
    except Exception as e:
        approach = {"error": str(e)[:120]}
    return JSONResponse(content={
        "success": True,
        "actors": actors,
        "actor_count": len(actors),
        "traffic_lights": lights,
        "violator": violator,
        "controlled_approach": approach,
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
                # trigger_time 是源视频内的相对秒数，不能转换成 Unix 时间。
                # 仅使用独立的 wall_time 更新真实发生时间；旧事件缺少 wall_time 时保留数据库原值。
                from traffic_event_engine import wall_time_to_datetime
                trigger_dt = wall_time_to_datetime(evt_dict.get('wall_time'))

                common_fields = {
                    'event_type': evt_dict.get('event_type'),
                    'track_id': evt_dict.get('track_id'),
                    'state': evt_dict.get('state', 'detecting'),
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
                # 没有可信墙钟时间时，不要用 None 或视频相对时间覆盖既有真实时间。
                if trigger_dt is not None:
                    common_fields['trigger_time'] = trigger_dt
                elif not existing:
                    # 仅用于缺少 wall_time 的旧事件首次建档，使用数据库创建时刻，
                    # 不伪造“视频第 N 秒”对应的现实时间。
                    common_fields['trigger_time'] = datetime.utcnow()

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
                camera_id: Optional[str] = None, event_type: Optional[str] = None):
    """M07: 事件列表（分页、状态与类型筛选）

    优先返回内存活跃事件 + 数据库历史事件合并视图。
    """    # 同步一次内存事件到数据库
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
            if event_type:
                query = query.filter(TrafficEventRecord.event_type == event_type)

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


@router.get("/events/{event_id}/replay")
def get_event_replay(event_id: str):
    """逐帧回放数据接口（TASK-COORD-007）

    数据来源：事件录制时随视频一并写出的 sidecar JSON
    （{event_video_path}.replay.json），内容为本地 YOLO/Tracking 的
    真实逐帧 bbox/track_id，不含任何云端 AI 结论。

    - 有 sidecar → success=true + data（frames 数组）
    - 无 sidecar（历史事件）→ success=false + code=no_frame_replay_data，
      前端据此诚实降级为事件级标注，不显示伪造框
    """
    import os

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
            logger.warning(f"[realtime.events] 回放视频路径查询失败: {e}")

    if not video_path or not os.path.exists(video_path):
        return JSONResponse(content={
            "success": False,
            "code": "no_frame_replay_data",
            "message": "事件视频不存在或尚未生成，无逐帧回放数据",
        }, status_code=404)

    sidecar_path = video_path + '.replay.json'
    if not os.path.exists(sidecar_path):
        return JSONResponse(content={
            "success": False,
            "code": "no_frame_replay_data",
            "message": "该事件无逐帧回放数据（历史事件未采集逐帧检测框）",
        })

    try:
        with open(sidecar_path, 'r', encoding='utf-8') as f:
            sidecar = json.load(f)
        return JSONResponse(content={
            "success": True,
            "event_id": event_id,
            "data": sidecar,
        })
    except Exception as e:
        logger.error(f"[realtime.events] 回放数据读取失败: {e}")
        return JSONResponse(content={"success": False, "message": f"回放数据读取失败: {e}"},
                           status_code=500)


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
                old_state = record.state
                new_state = "confirmed" if request.confirmed else "rejected"
                reviewed_at = datetime.utcnow()
                record.state = new_state
                record.updated_at = reviewed_at
                try:
                    history = json.loads(record.state_history) if record.state_history else []
                    if not isinstance(history, list):
                        history = []
                except (TypeError, ValueError):
                    history = []
                history.append({
                    "timestamp": reviewed_at.isoformat(),
                    "old_state": old_state,
                    "new_state": new_state,
                    "reason": f"人工复核 reviewer={request.reviewer} comment={request.comment}",
                })
                record.state_history = json.dumps(history, ensure_ascii=False)
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
