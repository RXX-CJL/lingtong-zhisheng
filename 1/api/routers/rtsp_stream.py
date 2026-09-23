from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import cv2
import numpy as np
import base64
import asyncio
import threading
import json
import os

from database import get_db

router = APIRouter(prefix="/api/stream", tags=["实时视频流"])

class CameraStreamData(BaseModel):
    device_id: str = Field(..., description="设备ID")
    frame_data: str = Field(..., description="Base64编码的帧数据")
    timestamp: Optional[str] = None

class StreamConfig(BaseModel):
    fps: int = Field(15, description="帧率")
    resolution: str = Field("640x480", description="分辨率")
    quality: int = Field(80, description="JPEG质量")

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

_stream_store = {}
_frame_lock = threading.Lock()

class CameraStreamManager:
    def __init__(self):
        self.streams = {}
        self.subscribers = {}
    
    def add_frame(self, device_id: str, frame: np.ndarray):
        with _frame_lock:
            if device_id not in self.streams:
                self.streams[device_id] = {
                    "frame": frame,
                    "timestamp": datetime.now(),
                    "fps": 0,
                    "frame_count": 0,
                    "last_fps_update": datetime.now()
                }
            else:
                self.streams[device_id]["frame"] = frame
                self.streams[device_id]["timestamp"] = datetime.now()
                self.streams[device_id]["frame_count"] += 1
                
                now = datetime.now()
                if (now - self.streams[device_id]["last_fps_update"]).total_seconds() >= 1:
                    self.streams[device_id]["fps"] = self.streams[device_id]["frame_count"]
                    self.streams[device_id]["frame_count"] = 0
                    self.streams[device_id]["last_fps_update"] = now
    
    def get_frame(self, device_id: str) -> Optional[np.ndarray]:
        with _frame_lock:
            if device_id in self.streams:
                return self.streams[device_id]["frame"].copy()
            return None
    
    def get_stream_info(self, device_id: str) -> Optional[dict]:
        with _frame_lock:
            if device_id in self.streams:
                info = self.streams[device_id].copy()
                info.pop("frame", None)
                info["timestamp"] = info["timestamp"].isoformat() if info["timestamp"] else None
                return info
            return None
    
    def list_streams(self) -> list:
        with _frame_lock:
            result = []
            for device_id, info in self.streams.items():
                stream_info = {
                    "device_id": device_id,
                    "fps": info["fps"],
                    "timestamp": info["timestamp"].isoformat() if info["timestamp"] else None
                }
                result.append(stream_info)
            return result
    
    def remove_stream(self, device_id: str):
        with _frame_lock:
            if device_id in self.streams:
                del self.streams[device_id]

stream_manager = CameraStreamManager()

@router.post("/push-frame", response_model=ApiResponse)
async def push_frame(data: CameraStreamData):
    """推送视频帧（K230设备端调用）"""
    try:
        frame_data = data.frame_data.split(",")[-1]
        frame_bytes = base64.b64decode(frame_data)
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(frame_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            return ApiResponse(success=False, message="无法解码帧数据")
        
        stream_manager.add_frame(data.device_id, frame)
        
        return ApiResponse(
            success=True,
            message="帧接收成功",
            data={"device_id": data.device_id, "frame_shape": list(frame.shape)}
        )
    except Exception as e:
        return ApiResponse(success=False, message=f"处理失败: {str(e)}")

async def generate_mjpeg_stream(device_id: str):
    """生成MJPEG视频流（无帧时输出诊断帧，避免前端橙色或空白异常画面）"""
    no_frame_count = 0
    while True:
        frame = stream_manager.get_frame(device_id)
        if frame is None:
            no_frame_count += 1
            if no_frame_count % 5 == 0:  # 每 0.25s 左右生成一次诊断帧，避免无谓CPU占用
                h, w = 480, 640
                diag = np.zeros((h, w, 3), dtype=np.uint8)
                diag[:, :] = (30, 30, 80)  # 深蓝
                cv2.rectangle(diag, (0, 0), (w, 70), (0, 90, 200), -1)
                cv2.putText(diag, f'STREAM: NO FRAME for device_id={device_id}',
                            (16, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.putText(diag, 'POST /api/stream/start-local with camera_index first.',
                            (16, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 120), 2)
                cv2.putText(diag, f'no_frame_count={no_frame_count}  |  {datetime.now().strftime("%H:%M:%S")}',
                            (16, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 200, 255), 1)
                ret, buf = cv2.imencode('.jpg', diag, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            await asyncio.sleep(0.05)
            continue
        no_frame_count = 0

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            await asyncio.sleep(0.05)
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        await asyncio.sleep(0.05)

@router.get("/mjpeg/{device_id}")
async def mjpeg_stream(device_id: str):
    """获取MJPEG视频流"""
    return StreamingResponse(
        generate_mjpeg_stream(device_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/snapshot/{device_id}")
async def get_snapshot(device_id: str):
    """获取当前帧快照"""
    frame = stream_manager.get_frame(device_id)
    if frame is None:
        raise HTTPException(status_code=404, detail="未找到视频流")
    
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ret:
        raise HTTPException(status_code=500, detail="无法生成快照")
    
    return StreamingResponse(
        buffer.tobytes(),
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"inline; filename={device_id}_{datetime.now().timestamp()}.jpg"
        }
    )

@router.get("/info/{device_id}", response_model=ApiResponse)
async def get_stream_info(device_id: str):
    """获取视频流信息"""
    info = stream_manager.get_stream_info(device_id)
    if info is None:
        return ApiResponse(success=False, message="未找到视频流")
    
    return ApiResponse(
        success=True,
        message="获取成功",
        data=info
    )

@router.get("/list", response_model=ApiResponse)
async def list_streams():
    """获取所有视频流列表"""
    streams = stream_manager.list_streams()
    return ApiResponse(
        success=True,
        message=f"获取到{len(streams)}个视频流",
        data={"streams": streams, "total": len(streams)}
    )

@router.delete("/{device_id}", response_model=ApiResponse)
async def stop_stream(device_id: str):
    """停止视频流"""
    stream_manager.remove_stream(device_id)
    return ApiResponse(
        success=True,
        message="视频流已停止",
        data={"device_id": device_id}
    )

class LocalCameraConfig(BaseModel):
    camera_index: int = Field(0, description="摄像头索引")
    fps: int = Field(15, description="帧率")
    width: int = Field(640, description="宽度")
    height: int = Field(480, description="高度")

_local_camera_thread = None
_local_camera_running = False
_local_camera_device_id = "local_camera"

def _local_camera_worker(config: LocalCameraConfig):
    """本地摄像头工作线程（Windows 优先 CAP_DSHOW，并在采集失败时写入带诊断文字的占位帧，避免前端橙色/空白）"""
    global _local_camera_running

    is_windows = os.name == 'nt'
    cap = None
    # Windows 下先尝试 DirectShow，再回退默认后端
    backends = [cv2.CAP_DSHOW, 0] if is_windows else [0]
    for be in backends:
        cap = cv2.VideoCapture(config.camera_index, be) if be else cv2.VideoCapture(config.camera_index)
        if cap.isOpened():
            # 读一帧验证真的可用（部分摄像头 isOpened=True 但读取失败）
            ret_test, _ = cap.read()
            if ret_test:
                break
            cap.release()
            cap = None
    if cap is None or not cap.isOpened():
        print(f"[rtsp_stream] 无法打开摄像头索引 {config.camera_index}（后端 {backends}）")
        # 关键修复：摄像头打不开不要直接 return，进入"诊断占位帧"模式，让前端看到明确错误提示而不是橙色画面
        import time as _time
        while _local_camera_running:
            h, w = config.height, config.width
            diag = np.zeros((h, w, 3), dtype=np.uint8)
            diag[:, :] = (25, 25, 70)  # 深蓝背景
            cv2.rectangle(diag, (0, 0), (w, 80), (0, 90, 200), -1)
            cv2.putText(diag, 'LOCAL CAMERA FAILED TO OPEN', (20, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(diag, f'idx={config.camera_index}', (20, 68),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 120), 2)
            tips = [
                'Close WeChat / Zoom / Teams (camera occupied)',
                'Or use "/realtime" page with browser getUserMedia instead',
                'Or try different camera_index in start-local request',
                f'Backend tried: {backends}',
            ]
            for i, t in enumerate(tips):
                cv2.putText(diag, t, (20, 140 + i * 34),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 230, 255), 2)
            cv2.putText(diag, datetime.now().strftime('%H:%M:%S'), (20, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 255), 2)
            stream_manager.add_frame(_local_camera_device_id, diag)
            _time.sleep(0.1)
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
    cap.set(cv2.CAP_PROP_FPS, config.fps)

    while _local_camera_running:
        ret, frame = cap.read()
        if ret:
            stream_manager.add_frame(_local_camera_device_id, frame)

        cv2.waitKey(1)

    cap.release()

@router.post("/start-local", response_model=ApiResponse)
async def start_local_camera(config: LocalCameraConfig = LocalCameraConfig()):
    """启动本地摄像头"""
    global _local_camera_thread, _local_camera_running
    
    if _local_camera_running:
        return ApiResponse(success=False, message="本地摄像头已在运行")
    
    _local_camera_running = True
    _local_camera_thread = threading.Thread(
        target=_local_camera_worker,
        args=(config,),
        daemon=True
    )
    _local_camera_thread.start()
    
    return ApiResponse(
        success=True,
        message="本地摄像头启动成功",
        data={"device_id": _local_camera_device_id, "config": config.model_dump()}
    )

@router.post("/stop-local", response_model=ApiResponse)
async def stop_local_camera():
    """停止本地摄像头"""
    global _local_camera_running
    
    _local_camera_running = False
    
    if _local_camera_thread:
        _local_camera_thread.join(timeout=2)
    
    stream_manager.remove_stream(_local_camera_device_id)
    
    return ApiResponse(
        success=True,
        message="本地摄像头已停止",
        data={"device_id": _local_camera_device_id}
    )

@router.get("/detect-cameras", response_model=ApiResponse)
async def detect_cameras(max_check: int = 4):
    """检测可用摄像头"""
    available = []
    for i in range(max_check):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                available.append({
                    "index": i,
                    "width": int(width),
                    "height": int(height),
                    "fps": int(fps)
                })
            cap.release()
    
    return ApiResponse(
        success=True,
        message=f"检测到{len(available)}个可用摄像头",
        data={"cameras": available, "total": len(available)}
    )

class FrameAnalysisRequest(BaseModel):
    device_id: str = Field(..., description="设备ID")
    violation_type: Optional[str] = None

@router.post("/analyze-frame", response_model=ApiResponse)
async def analyze_frame(request: FrameAnalysisRequest, db: Session = Depends(get_db)):
    """分析当前帧"""
    try:
        frame = stream_manager.get_frame(request.device_id)
        if frame is None:
            return ApiResponse(success=False, message="未找到视频流")
        
        from image_recognizer import analyze_with_collaboration
        
        result = analyze_with_collaboration(frame, violation_type=request.violation_type)
        
        return ApiResponse(
            success=True,
            message="分析完成",
            data=result
        )
    except Exception as e:
        return ApiResponse(success=False, message=f"分析失败: {str(e)}")