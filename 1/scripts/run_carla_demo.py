# -*- coding: utf-8 -*-
"""
CARLA 仿真一键演示脚本。

流程：
    1. 连接 CARLA 服务器
    2. 根据场景加载地图并生成交通流
    3. 切换数据源为 carla（CarlaSource）
    4. 启动检测循环（红绿灯违规 + 车牌识别）
    5. 输出违规日志与车牌识别结果

用法示例::

    py -3 scripts/run_carla_demo.py --scene town01
    py -3 scripts/run_carla_demo.py --scene town03 --host 127.0.0.1 --port 2000
    py -3 scripts/run_carla_demo.py --scene violation

注意：CARLA 未启动时脚本不会崩溃，会以降级模式输出提示并退出。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

# 将项目根目录加入 sys.path，便于复用 api / zhitong 下的模块
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    import cv2  # type: ignore
except ImportError:  # pragma: no cover
    cv2 = None  # type: ignore

import numpy as np

from api.carla_source import CarlaSource

# 可选依赖：车牌识别 + 违规检测。缺失时降级运行
try:
    from api.license_plate_recognizer import detect_and_recognize_plate  # type: ignore
    _PLATE_RECOGNIZER_AVAILABLE = True
except Exception:  # noqa: BLE001
    detect_and_recognize_plate = None  # type: ignore
    _PLATE_RECOGNIZER_AVAILABLE = False

try:
    from zhitong.violation_detector import ViolationDetector, ViolationType  # type: ignore
    _VIOLATION_DETECTOR_AVAILABLE = True
except Exception:  # noqa: BLE001
    ViolationDetector = None  # type: ignore
    ViolationType = None  # type: ignore
    _VIOLATION_DETECTOR_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger('carla_demo')

# 场景 → 地图映射
SCENE_TOWN = {
    'town01': 'Town01',
    'town03': 'Town03',
    'violation': 'Town03',  # 复杂路口含红绿灯，便于演示闯红灯
}


def build_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='CARLA 仿真一键演示')
    p.add_argument('--scene', choices=list(SCENE_TOWN.keys()), default='town01',
                   help='演示场景：town01 城镇交通流 / town03 复杂路口 / violation 闯红灯')
    p.add_argument('--host', default='localhost', help='CARLA 服务器地址')
    p.add_argument('--port', type=int, default=2000, help='CARLA 服务器端口')
    p.add_argument('--vehicles', type=int, default=20, help='生成车辆数')
    p.add_argument('--walkers', type=int, default=10, help='生成行人数')
    p.add_argument('--frames', type=int, default=200, help='检测循环帧数')
    p.add_argument('--width', type=int, default=640, help='摄像头宽度')
    p.add_argument('--height', type=int, default=480, help='摄像头高度')
    p.add_argument('--fov', type=int, default=90, help='摄像头视场角')
    p.add_argument('--sync', action='store_true', default=True, help='使用同步模式')
    p.add_argument('--out', default=os.path.join(_PROJECT_ROOT, 'output', 'carla_demo_result.json'),
                   help='结果输出路径')
    return p.parse_args()


def setup_scene(src: CarlaSource, scene: str, n_vehicles: int, n_walkers: int) -> Dict[str, Any]:
    """加载地图并生成交通流，返回场景元信息。"""
    town = SCENE_TOWN.get(scene, 'Town01')
    info: Dict[str, Any] = {'scene': scene, 'town': town, 'violator_id': None}
    src.load_town(town)

    if scene == 'violation':
        # 先生成背景交通，再插入闯红灯车辆
        src.spawn_vehicles(max(n_vehicles - 1, 5))
        src.spawn_walkers(n_walkers)
        info['violator_id'] = src.spawn_red_light_violator()
    else:
        src.spawn_vehicles(n_vehicles)
        src.spawn_walkers(n_walkers)
    return info


def detect_red_light_violations(lights: List[Dict[str, Any]],
                                actors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """简易红绿灯违规判定：红灯状态下仍在路口高速移动的车辆记为违规。"""
    violations: List[Dict[str, Any]] = []
    red_lights = [tl for tl in lights if tl.get('state') == 'red']
    if not red_lights:
        return violations
    red_locs = np.array([[tl['location']['x'], tl['location']['y']] for tl in red_lights])
    for a in actors:
        if a['type'] != 'vehicle':
            continue
        if a['velocity'] < 5.0:  # 高速才算冲红灯
            continue
        pos = np.array([a['location']['x'], a['location']['y']])
        dist = np.linalg.norm(red_locs - pos, axis=1).min()
        if dist < 25.0:  # 距红灯 25m 内
            violations.append({
                'type': 'red_light',
                'vehicle_id': a['id'],
                'speed_mps': round(a['velocity'], 2),
                'location': a['location'],
                'nearest_light_id': int(red_lights[int(np.argmin(np.linalg.norm(red_locs - pos, axis=1)))]['id']),
                'distance_m': round(float(dist), 2),
            })
    return violations


def run_detection_loop(src: CarlaSource, total_frames: int, scene_info: Dict[str, Any]) -> Dict[str, Any]:
    """检测主循环：取帧 → 车牌识别 → 红绿灯违规 → 记录。"""
    violation_log: List[Dict[str, Any]] = []
    plate_log: List[Dict[str, Any]] = []
    detector = None
    if _VIOLATION_DETECTOR_AVAILABLE:
        try:
            detector = ViolationDetector()
        except Exception as exc:  # noqa: BLE001
            logger.warning('ViolationDetector 初始化失败: %s', exc)

    processed = 0
    for i in range(total_frames):
        if src.is_connected and src._synchronous:  # noqa: SLF001
            src.tick()
        frame = src.get_frame()
        if frame is None:
            time.sleep(0.02)
            continue
        processed += 1

        # 1) 车牌识别
        if _PLATE_RECOGNIZER_AVAILABLE:
            try:
                result = detect_and_recognize_plate(frame)
                if result and result.get('plate'):
                    plate_log.append({
                        'frame': i,
                        'plate': result.get('plate'),
                        'confidence': round(float(result.get('confidence', 0.0)), 3),
                        'box': result.get('box'),
                    })
            except Exception as exc:  # noqa: BLE001
                logger.debug('车牌识别异常: %s', exc)

        # 2) 红绿灯违规（基于仿真状态，比纯视觉更稳定）
        lights = src.get_traffic_lights()
        actors = src.get_actors_state()
        if scene_info['scene'] == 'violation':
            violations = detect_red_light_violations(lights, actors)
            for v in violations:
                v['frame'] = i
                violation_log.append(v)

        # 可视化预览（可选）
        if cv2 is not None and (i % 20 == 0):
            try:
                cv2.imshow('CARLA Demo', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except Exception:  # noqa: BLE001
                pass

        # 每 50 帧汇报一次
        if i % 50 == 0:
            logger.info('帧 %d/%d  已处理 %d  红绿灯=%d  车辆=%d  违规=%d  车牌=%d',
                        i, total_frames, processed, len(lights),
                        len([a for a in actors if a['type'] == 'vehicle']),
                        len(violation_log), len(plate_log))

    if cv2 is not None:
        try:
            cv2.destroyAllWindows()
        except Exception:  # noqa: BLE001
            pass

    return {
        'scene': scene_info,
        'frames_planned': total_frames,
        'frames_processed': processed,
        'violations': violation_log,
        'plates': plate_log,
    }


def main() -> int:
    args = build_args()
    logger.info('=== CARLA 演示启动 ===')
    logger.info('场景=%s 主机=%s 端口=%d 车辆=%d 行人=%d 帧数=%d',
                args.scene, args.host, args.port, args.vehicles, args.walkers, args.frames)

    src = CarlaSource()
    if not src.connect(args.host, args.port):
        logger.warning('无法连接 CARLA（%s:%d），演示以降级模式结束。', args.host, args.port)
        logger.warning('请先启动 CarlaUE4.exe，再运行本脚本。')
        result = {
            'status': 'degraded',
            'reason': 'CARLA 服务器未连接',
            'host': args.host,
            'port': args.port,
            'violations': [],
            'plates': [],
        }
        _write_result(result, args.out)
        return 0

    try:
        if args.sync:
            src.set_synchronous_mode(0.05)
        scene_info = setup_scene(src, args.scene, args.vehicles, args.walkers)
        ok = src.attach_camera(args.width, args.height, args.fov)
        if not ok:
            logger.error('摄像头挂载失败，终止演示。')
            result = {'status': 'fail', 'reason': 'attach_camera 失败',
                      'violations': [], 'plates': []}
            _write_result(result, args.out)
            return 1

        logger.info('场景就绪：town=%s violator=%s', scene_info['town'], scene_info['violator_id'])
        logger.info('开始检测循环（共 %d 帧）...', args.frames)
        result = run_detection_loop(src, args.frames, scene_info)
        result['status'] = 'ok'
        _write_result(result, args.out)

        logger.info('=== 演示完成 ===')
        logger.info('违规数=%d  车牌识别数=%d  处理帧数=%d',
                    len(result['violations']), len(result['plates']), result['frames_processed'])
        logger.info('结果已写入: %s', args.out)
        return 0
    finally:
        src.disconnect()


def _write_result(result: Dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    sys.exit(main())
