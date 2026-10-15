# -*- coding: utf-8 -*-
"""场景标注 API 路由

接口一览：
  GET    /api/scene                     列出所有已保存标注
  GET    /api/scene/config              读取指定源的标注（?source=...）
  POST   /api/scene/config              保存标注（人工描绘结果）
  POST   /api/scene/calibration-preview  ★测速标定预览（不落盘，供参数输入界面实时反馈）
  POST   /api/scene/auto-detect         AI 自动检测，返回建议（不落盘）
  GET    /api/scene/first-frame         取源的首帧（JPEG），供前端画布标注
  DELETE /api/scene/config              删除标注

说明：AI 自动检测结果为**建议**，必须经人工确认后通过 POST 保存。

★测速标定参数口径（2026-10-06 由 DSH 固化，前端必须与此一致）：
  camera_height_m   相机**离路面**高度（米）
  camera_pitch_deg  俯角，**向下为负**（如 -23.4）
  camera_yaw_deg    偏航角（度，0=+X 方向，逆时针为正）
  fov_deg           **水平**视场角（CARLA sensor.camera.rgb 的 fov 即水平）
  frame_width/height 画面像素尺寸
  ground_points     [{'u','v','x','y'} × ≥4]，人工点选已知地面坐标（可替代相机参数）
"""

import logging
import os
from typing import List, Optional

import cv2
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from scene_annotation import (auto_detect_all, list_scenes, load_scene,
                              save_scene, video_key)

logger = logging.getLogger("zhitong_api")
router = APIRouter(prefix="/api/scene", tags=["scene"])


class SceneSaveRequest(BaseModel):
    source: str                      # 视频路径 或 流 URL
    config: dict                     # 标注内容（白名单字段）
    annotated_by: Optional[str] = "manual"   # manual | ai


class CalibrationPreviewRequest(BaseModel):
    """测速标定预览请求（不落盘）"""
    source: Optional[str] = None          # 可选：以该源已保存的标注为基底
    config: Optional[dict] = None         # 候选标定参数（覆盖基底）
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    points: Optional[List[dict]] = None   # [{'u','v'}] 或 [{'u','v','x','y'}]，用于校核
    pairs: Optional[List[List[float]]] = None  # [[u1,v1,u2,v2]...] 量两点地面距离


@router.get("")
def get_scene_list():
    """列出所有已保存的场景标注"""
    try:
        return JSONResponse(content={"success": True, "data": list_scenes(),
                                     "dir": os.path.join("api", "output", "scene_configs")})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出标注失败: {str(e)}")


@router.get("/config")
def get_scene_config(source: str):
    """读取指定源的标注"""
    try:
        cfg = load_scene(source)
        return JSONResponse(content={"success": True, "key": video_key(source),
                                     "data": cfg, "exists": bool(cfg)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取标注失败: {str(e)}")


@router.post("/config")
def post_scene_config(req: SceneSaveRequest):
    """保存标注（人工描绘或已确认的 AI 结果）

    请求体示例：
      {
        "source": "E:/.../video.mp4",
        "config": {
          "crosswalk_zones": [[[100,300],[300,300],[300,360],[100,360]]],
          "lane_lines": [[[400,200],[380,500]]],
          "stop_line_y": 320,
          "no_parking_zones": [{"x1":0,"y1":350,"x2":640,"y2":576}]
        },
        "annotated_by": "manual"
      }
    """
    try:
        if not req.source:
            raise HTTPException(status_code=400, detail="source 不能为空")
        if not isinstance(req.config, dict):
            raise HTTPException(status_code=400, detail="config 必须是对象")
        saved = save_scene(req.source, req.config, req.annotated_by or "manual")
        logger.info(f"[scene] 标注已保存 key={video_key(req.source)} "
                    f"by={req.annotated_by} 字段={[k for k in saved if not k.startswith('_')]}")
        return JSONResponse(content={"success": True, "key": video_key(req.source),
                                     "data": saved})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存标注失败: {str(e)}")


@router.delete("/config")
def delete_scene_config(source: str):
    """删除指定源的标注"""
    try:
        from scene_annotation import _path_for
        p = _path_for(source)
        if os.path.exists(p):
            os.remove(p)
            return JSONResponse(content={"success": True, "deleted": p})
        return JSONResponse(content={"success": False, "message": "标注不存在"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除标注失败: {str(e)}")


@router.post("/calibration-preview")
def post_calibration_preview(req: CalibrationPreviewRequest):
    """★测速标定预览（不落盘）—— 供前端"参数输入界面"实时反馈

    典型用法（前端拖滑块 / 填数字时反复调用）：
      POST /api/scene/calibration-preview
      {
        "source": "E:/output/_dual_cam_demo/dual_cam_demo_lossless.mkv",   // 可选
        "frame_width": 1920, "frame_height": 1080,
        "config": {"camera_height_m": 5.0, "camera_pitch_deg": -23.4,
                   "fov_deg": 90.0, "camera_yaw_deg": 179.5},
        "pairs": [[960, 1080, 960, 900]]        // 可选：量像素间的地面距离
      }

    返回：
      method / calibrated    标定来源与是否可信
      horizon_y              地平线行（俯角/视场角填错时一眼看出）
      rows                   y=.. 处的 ppm 与地面距离
      solvable_ratio         可反解像素比例（参数填反会明显下降）
      warnings               参数合理性提示
      pair_distances         每个 pairs 的地面距离（配"车道宽 3.75m"校验）
      point_errors           若 points 带 x/y：与反投影的偏差（米）
    """
    try:
        from speed_calibration import SpeedCalibrator
        cfg = {}
        base = {}
        if req.source:
            base = load_scene(req.source) or {}
        cfg.update({k: v for k, v in base.items() if not k.startswith("_")})
        if req.config:
            cfg.update({k: v for k, v in req.config.items() if v is not None})
        W = int(req.frame_width or cfg.get("frame_width") or 1280)
        H = int(req.frame_height or cfg.get("frame_height") or 576)
        cal = SpeedCalibrator(cfg, frame_width=W, frame_height=H)
        data = cal.preview()
        data["info"] = cal.info()

        # 两点地面距离（车道宽/斑马线校验用）
        if req.pairs:
            dists = []
            for i, pr in enumerate(req.pairs):
                try:
                    u1, v1, u2, v2 = [float(t) for t in pr[:4]]
                except (TypeError, ValueError, IndexError):
                    continue
                d = cal.ground_distance((u1, v1), (u2, v2))
                item = {"pair": [u1, v1, u2, v2], "ground_distance_m": None}
                if d is not None:
                    item["ground_distance_m"] = round(d, 3)
                    px = ((u2 - u1) ** 2 + (v2 - v1) ** 2) ** 0.5
                    item["pixel_distance"] = round(px, 2)
                    item["ppm"] = round(px / d, 2) if d > 1e-9 else None
                dists.append(item)
            data["pair_distances"] = dists

        # 已知地面坐标点校核
        if req.points:
            errs = []
            for p in req.points:
                try:
                    u, v = float(p["u"]), float(p["v"])
                except (KeyError, TypeError, ValueError):
                    continue
                g = cal.ground_point(u, v)
                it = {"u": u, "v": v, "ground": (round(g[0], 2), round(g[1], 2)) if g else None}
                if g and p.get("x") is not None and p.get("y") is not None:
                    try:
                        it["error_m"] = round(
                            ((g[0] - float(p["x"])) ** 2 + (g[1] - float(p["y"])) ** 2) ** 0.5, 3)
                    except (TypeError, ValueError):
                        pass
                errs.append(it)
            data["point_errors"] = errs
        return JSONResponse(content={"success": True, "data": data,
                                     "key": video_key(req.source) if req.source else None})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"标定预览失败: {str(e)}")


@router.post("/auto-detect")
def post_auto_detect(source: Optional[str] = None, use_current: bool = True):
    """AI 自动检测（返回建议，不落盘）

    - use_current=true 且检测器有画面时：用当前帧
    - 否则用 source 指定的视频首帧
    """
    try:
        import numpy as np
        from realtime_detector import realtime_detector as _rd

        frame = None
        if use_current:
            with _rd.lock:
                if _rd.current_frame is not None:
                    frame = _rd.current_frame.copy()

        if frame is None:
            if not source:
                raise HTTPException(status_code=400,
                                    detail="无当前画面且未指定 source，无法检测")
            if str(source).lower().startswith(("http://", "https://", "rtsp://")):
                cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
            else:
                cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                raise HTTPException(status_code=400, detail=f"无法打开源: {source}")
            ok, frame = cap.read()
            cap.release()
            if not ok or frame is None:
                raise HTTPException(status_code=400, detail="无法读取首帧")

        result = auto_detect_all(frame)
        return JSONResponse(content={"success": True, "data": result,
                                     "source": source,
                                     "note": "建议仅供参考，请人工确认后保存"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"自动检测失败: {str(e)}")


@router.get("/first-frame")
def get_first_frame(source: str, quality: int = 88):
    """取源的首帧（JPEG），供前端在画布上做人工标注"""
    try:
        if str(source).lower().startswith(("http://", "https://", "rtsp://")):
            cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail=f"无法打开源: {source}")
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise HTTPException(status_code=400, detail="无法读取首帧")
        ok2, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok2:
            raise HTTPException(status_code=500, detail="编码失败")
        return Response(content=buf.tobytes(), media_type="image/jpeg",
                        headers={"X-Frame-Size": f"{frame.shape[1]}x{frame.shape[0]}",
                                 "Cache-Control": "no-store"})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取首帧失败: {str(e)}")
