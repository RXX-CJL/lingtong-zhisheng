# -*- coding: utf-8 -*-
"""
数字孪生系统 Flask 服务器
M14: 新增真实数据订阅（轮询 /api/realtime/status 和 /api/violations），
     将最新违规事件经 WebSocket 推送到前端 3D 场景。
"""
import json
import threading
import time
import logging
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO, emit

from scripts.data_simulator import TrafficDataSimulator, ViolationDetector

logger = logging.getLogger("digital_twin")
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'zhitong_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

simulator = TrafficDataSimulator()
detector = ViolationDetector()

BACKEND_API_URL = 'http://127.0.0.1:8001'

latest_data = {
    'vehicles': [],
    'traffic_light': 'red',
    'timestamp': datetime.now().isoformat(),
    'total_vehicles': 0,
    'violating_vehicles': 0,
    'violations': []
}

violation_history = []

# --------------------------------------------------------------------------
# M14: 真实数据订阅状态
# --------------------------------------------------------------------------
# 已推送过的违规事件 ID 集合（避免重复推送）
_pushed_violation_ids: set = set()
# 已推送过的 track_id 集合（用于车牌绑定事件去重）
_pushed_track_ids: set = set()
# 最近一次真实违规事件（前端首次连接时回送）
latest_real_violation_events: list = []
# 最近一次实时检测状态快照
latest_realtime_status: dict = {}
# 真实违规分类计数（今日）
violation_type_counts: dict = {
    'red_light': 0, 'no_helmet': 0, 'wrong_way': 0,
    'illegal_parking': 0, 'speeding': 0, 'lane_departure': 0,
    'street_stall': 0, 'crowd_gathering': 0,
}
# 模拟数据源（按场景模式），用于在未启动后端时也能演示
_simulated_event_seq = 0


def fetch_real_data():
    try:
        response = requests.get(f'{BACKEND_API_URL}/api/violations', timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
    except Exception:
        pass
    return []


def fetch_real_stats():
    try:
        response = requests.get(f'{BACKEND_API_URL}/api/stats', timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return {}


def fetch_realtime_status() -> dict:
    """M14: 轮询实时检测后端状态"""
    try:
        response = requests.get(f'{BACKEND_API_URL}/api/realtime/status', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', {})
    except Exception:
        pass
    return {}


def fetch_tracked_vehicles() -> list:
    """M14: 获取当前追踪车辆列表（含车牌）"""
    try:
        response = requests.get(f'{BACKEND_API_URL}/api/realtime/tracked-vehicles', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data.get('data', [])
    except Exception:
        pass
    return []


def _map_track_to_scene(track_id: int, bbox: list = None) -> dict:
    """M14: 将 track_id 映射到 3D 场景坐标（伪 GPS 映射）

    真实 GPS 接口位置预留，目前用"十字路口四个象限映射到固定坐标"。
    根据 track_id 哈希到四个象限之一，保证同一 track_id 始终在同一位置。
    """
    # 四个象限对应的场景坐标 (x, z)
    quadrants = [
        (15, 15),    # 东北象限
        (-15, 15),   # 西北象限
        (15, -15),   # 东南象限
        (-15, -15),  # 西南象限
    ]
    if track_id is None or track_id < 0:
        idx = 0
    else:
        idx = int(track_id) % 4
    x, z = quadrants[idx]
    # 在象限内做小范围偏移，避免多车重叠
    offset_x = ((int(track_id) * 7) % 5) - 2
    offset_z = ((int(track_id) * 11) % 5) - 2
    return {
        'x': x + offset_x,
        'y': 0.6,
        'z': z + offset_z,
        # 真实 GPS 字段预留
        'lat': 30.5728 + (x + offset_x) * 0.0001,
        'lng': 104.0668 + (z + offset_z) * 0.0001,
    }


def _build_violation_event(violation: dict, tracked_vehicle: dict = None) -> dict:
    """M14: 构造一条标准违规事件，供前端 3D 标注层使用"""
    track_id = violation.get('track_id') or (
        tracked_vehicle.get('id') if tracked_vehicle else None
    ) or -1
    plate = violation.get('plate_number') or (
        tracked_vehicle.get('plate_number') if tracked_vehicle else ''
    ) or ''
    vtype = violation.get('violation_type') or violation.get('type') or 'unknown'
    confidence = float(violation.get('confidence', 0.0) or 0.0)
    pos = _map_track_to_scene(track_id, violation.get('bbox'))
    return {
        'event_id': f"evt_{track_id}_{int(time.time()*1000)}",
        'track_id': int(track_id) if track_id is not None else -1,
        'plate_number': plate,
        'violation_type': vtype,
        'confidence': confidence,
        'position': pos,
        'timestamp': datetime.now().isoformat(),
        'source': 'backend_api' if tracked_vehicle is not None else 'simulated',
    }


def realtime_subscription_loop():
    """M14: 后台轮询后端 /api/realtime/status 和 /api/violations，
    检测到新违规事件则通过 WebSocket 推送到前端 3D 场景。
    """
    global latest_realtime_status, latest_real_violation_events, violation_type_counts
    poll_interval = 1.5  # 1.5 秒轮询一次
    while True:
        try:
            # 1) 拉取最新违规列表
            violations = fetch_real_data()
            for v in violations:
                vid = v.get('id') or v.get('violation_id')
                if vid is None:
                    continue
                if vid in _pushed_violation_ids:
                    continue
                _pushed_violation_ids.add(vid)
                # 限制缓存大小
                if len(_pushed_violation_ids) > 500:
                    _pushed_violation_ids.clear()

                # 2) 查询对应 track_id（违规记录中可能含车牌）
                tracked_vehicle = None
                plate = v.get('plate_number')
                track_id = v.get('track_id')
                if not plate or track_id is None:
                    # 尝试在 tracked_vehicles 中匹配
                    for tv in fetch_tracked_vehicles():
                        if plate and tv.get('plate_number') == plate:
                            tracked_vehicle = tv
                            break
                        if track_id is not None and tv.get('id') == track_id:
                            tracked_vehicle = tv
                            break

                event = _build_violation_event(v, tracked_vehicle)
                latest_real_violation_events.append(event)
                if len(latest_real_violation_events) > 50:
                    latest_real_violation_events = latest_real_violation_events[-50:]

                # 累加分类计数
                vtype = event['violation_type']
                violation_type_counts[vtype] = violation_type_counts.get(vtype, 0) + 1

                # 3) 推送事件到前端
                socketio.emit('real_violation_event', event)
                logger.info(f"[M14] 推送真实违规事件: {event['event_id']} type={vtype} plate={event['plate_number']}")

            # 4) 拉取实时检测状态，用于数字孪生仪表盘同步
            status = fetch_realtime_status()
            if status:
                latest_realtime_status = status
                socketio.emit('realtime_status_sync', {
                    'avg_fps': status.get('avg_fps', 0),
                    'processed_frames': status.get('processed_frames', 0),
                    'violation_count': status.get('violation_count', 0),
                    'tracked_vehicle_count': status.get('tracked_vehicle_count', 0),
                    'pending_count': status.get('pending_count', 0),
                    'confirmed_count': status.get('confirmed_count', 0),
                    'cache_size': status.get('cache_size', 0),
                    'running': status.get('running', False),
                    'timestamp': datetime.now().isoformat(),
                })
        except Exception as e:
            logger.warning(f"[M14] 轮询后端失败: {e}")

        time.sleep(poll_interval)


def simulation_loop():
    global latest_data, violation_history
    while True:
        data = simulator.simulate_step()
        violations = detector.detect_violations(data['vehicles'])
        data['violations'] = violations

        for v in violations:
            violation_history.append({
                'id': v['id'],
                'type': v['type'],
                'name': v['name'],
                'severity': v['severity'],
                'timestamp': datetime.now().isoformat()
            })

        if len(violation_history) > 100:
            violation_history = violation_history[-100:]

        latest_data = data

        socketio.emit('traffic_update', latest_data)

        time.sleep(0.5)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/traffic')
def get_traffic_data():
    return jsonify(latest_data)

@app.route('/api/violations')
def get_violations():
    return jsonify({
        'violations': latest_data.get('violations', []),
        'count': len(latest_data.get('violations', [])),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/stats')
def get_stats():
    vehicles = latest_data.get('vehicles', [])
    if vehicles:
        avg_speed = sum(v['speed'] for v in vehicles) / len(vehicles)
    else:
        avg_speed = 0
    
    return jsonify({
        'total_vehicles': latest_data.get('total_vehicles', 0),
        'violating_vehicles': latest_data.get('violating_vehicles', 0),
        'traffic_light': latest_data.get('traffic_light', 'red'),
        'average_speed': round(avg_speed, 2),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/real-violations')
def get_real_violations():
    real_items = fetch_real_data()
    return jsonify({
        'items': real_items,
        'count': len(real_items),
        'source': 'backend_api' if real_items else 'simulated'
    })

@app.route('/api/real-stats')
def get_real_stats():
    real_stats = fetch_real_stats()
    return jsonify({
        'data': real_stats,
        'source': 'backend_api' if real_stats else 'simulated'
    })

@app.route('/api/violation-history')
def get_violation_history():
    return jsonify({
        'history': violation_history,
        'count': len(violation_history),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/cameras')
def get_cameras():
    cameras = [
        {
            'id': 'cam1',
            'name': '东北角摄像头',
            'position': {'x': -30, 'y': 15, 'z': -30},
            'lookAt': {'x': 0, 'y': 0, 'z': 0}
        },
        {
            'id': 'cam2',
            'name': '东南角摄像头',
            'position': {'x': 30, 'y': 15, 'z': -30},
            'lookAt': {'x': 0, 'y': 0, 'z': 0}
        },
        {
            'id': 'cam3',
            'name': '西南角摄像头',
            'position': {'x': 30, 'y': 15, 'z': 30},
            'lookAt': {'x': 0, 'y': 0, 'z': 0}
        },
        {
            'id': 'cam4',
            'name': '西北角摄像头',
            'position': {'x': -30, 'y': 15, 'z': 30},
            'lookAt': {'x': 0, 'y': 0, 'z': 0}
        },
        {
            'id': 'cam5',
            'name': '高空俯瞰',
            'position': {'x': 0, 'y': 60, 'z': 0},
            'lookAt': {'x': 0, 'y': 0, 'z': 0}
        }
    ]
    return jsonify({'cameras': cameras})

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@socketio.on('connect')
def handle_connect():
    print('[WebSocket] 客户端已连接')
    emit('connected', {'message': '已连接到数字孪生系统'})

@socketio.on('disconnect')
def handle_disconnect():
    print('[WebSocket] 客户端已断开连接')

@socketio.on('subscribe_violations')
def handle_subscribe_violations():
    print('[WebSocket] 客户端订阅违规事件')

def trigger_violation_event(violation):
    """
    触发违规事件，推送给所有订阅的客户端
    
    参数:
        violation: 违规数据，格式如下：
        {
            'type': 'violation',
            'camera_id': 'cam_001',
            'violation_type': 'no_helmet',
            'confidence': 0.91,
            'position': {'x': 120, 'y': 80}
        }
    """
    print(f"[WebSocket] 推送违规事件: {violation}")
    socketio.emit('violation_detected', violation)

@app.route('/api/trigger-violation', methods=['POST'])
def api_trigger_violation():
    """API接口：手动触发违规事件"""
    import flask
    data = flask.request.get_json()
    if data:
        violation = {
            'type': 'violation',
            'camera_id': data.get('camera_id', 'cam_unknown'),
            'violation_type': data.get('violation_type', 'unknown'),
            'confidence': data.get('confidence', 0.0),
            'position': data.get('position', {})
        }
        trigger_violation_event(violation)
        return jsonify({'success': True, 'message': '违规事件已推送'})
    return jsonify({'success': False, 'message': '无效数据'}), 400


# ==========================================================================
# M14: 数字孪生真实数据联动接口
# ==========================================================================

# 演示违规类型 → 中文映射
DEMO_VIOLATION_TYPES = {
    'wrong_way': '逆行',
    'no_helmet': '未戴头盔',
    'red_light': '闯红灯',
    'illegal_parking': '违规停车',
    'speeding': '超速',
    'lane_departure': '压线行驶',
}


@app.route('/api/realtime/violation-events')
def get_realtime_violation_events():
    """M14: 获取最近推送过的真实违规事件（前端首次连接时回拉）"""
    return jsonify({
        'success': True,
        'events': latest_real_violation_events[-20:],
        'count': len(latest_real_violation_events),
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/realtime/status-sync')
def get_realtime_status_sync():
    """M14: 获取最近一次同步的实时检测状态"""
    return jsonify({
        'success': True,
        'status': latest_realtime_status,
        'violation_type_counts': violation_type_counts,
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/dashboard/today-stats')
def get_dashboard_today_stats():
    """M14: 仪表盘今日违规分类计数（与后端 stats 接口合并）

    优先使用真实违规分类计数，后端不可用时降级为模拟数据。
    """
    real_stats = fetch_real_stats() or {}
    today_counts = {
        'wrong_way': violation_type_counts.get('wrong_way', 0),
        'no_helmet': violation_type_counts.get('no_helmet', 0),
        'red_light': violation_type_counts.get('red_light', 0),
        'illegal_parking': violation_type_counts.get('illegal_parking', 0),
        'speeding': violation_type_counts.get('speeding', 0),
        'lane_departure': violation_type_counts.get('lane_departure', 0),
        'street_stall': violation_type_counts.get('street_stall', 0),
        'crowd_gathering': violation_type_counts.get('crowd_gathering', 0),
    }
    return jsonify({
        'success': True,
        'today_counts': today_counts,
        'total': sum(today_counts.values()),
        'real_stats': real_stats,
        'source': 'backend_api' if real_stats else 'simulated',
        'timestamp': datetime.now().isoformat(),
    })


@app.route('/api/demo/trigger-scene', methods=['POST'])
def api_demo_trigger_scene():
    """M14: 演示按钮 - 在场景中按规范生成一次违规事件

    请求体: {"scene_type": "wrong_way|red_light|no_helmet|illegal_parking"}
    1. 在数字孪生场景中通过 WebSocket 推送一条违规事件（红色旋转箭头+车牌标签）
    2. 同步调用后端 /api/realtime/consult 让后端产生一条示例违规（如果后端在线）
    3. 累加到 violation_type_counts
    """
    import flask
    data = flask.request.get_json() or {}
    scene_type = data.get('scene_type', 'wrong_way')
    if scene_type not in DEMO_VIOLATION_TYPES:
        return jsonify({'success': False, 'message': f'未知演示场景: {scene_type}'}), 400

    global _simulated_event_seq
    _simulated_event_seq += 1
    fake_track_id = 900 + _simulated_event_seq  # 演示用 track_id 从 900 起
    fake_plate = f"川A{(_simulated_event_seq % 99):02d}D{(65 + _simulated_event_seq % 25):c}"

    event = {
        'event_id': f"demo_{scene_type}_{int(time.time()*1000)}",
        'track_id': fake_track_id,
        'plate_number': fake_plate,
        'violation_type': scene_type,
        'confidence': 0.92,
        'position': _map_track_to_scene(fake_track_id),
        'timestamp': datetime.now().isoformat(),
        'source': 'demo',
    }

    # 1) 推送前端 3D 标注
    socketio.emit('real_violation_event', event)
    latest_real_violation_events.append(event)
    if len(latest_real_violation_events) > 50:
        latest_real_violation_events = latest_real_violation_events[-50:]

    # 2) 累加计数
    violation_type_counts[scene_type] = violation_type_counts.get(scene_type, 0) + 1

    # 3) 联动后端（如果在线则记录一条示例违规；不在线也允许）
    backend_ok = False
    try:
        # 调用一次 status 验证后端是否在线
        resp = requests.get(f'{BACKEND_API_URL}/api/realtime/status', timeout=2)
        backend_ok = resp.status_code == 200
    except Exception:
        pass

    logger.info(f"[M14] 演示事件触发: {scene_type} plate={fake_plate} backend={'online' if backend_ok else 'offline'}")

    return jsonify({
        'success': True,
        'event': event,
        'violation_type_cn': DEMO_VIOLATION_TYPES[scene_type],
        'backend_online': backend_ok,
        'message': f"已生成演示事件: {DEMO_VIOLATION_TYPES[scene_type]} - {fake_plate}"
    })


@app.route('/api/demo/scenes')
def get_demo_scenes():
    """M14: 列出所有可演示的违规场景"""
    scenes = [
        {'value': 'wrong_way', 'label': '演示逆行', 'color': '#FF9800'},
        {'value': 'red_light', 'label': '演示闯红灯', 'color': '#F44336'},
        {'value': 'no_helmet', 'label': '演示未戴头盔', 'color': '#00BCD4'},
        {'value': 'illegal_parking', 'label': '演示违停', 'color': '#9C27B0'},
    ]
    return jsonify({'success': True, 'scenes': scenes})


@socketio.on('subscribe_real_violations')
def handle_subscribe_real_violations():
    """M14: 客户端订阅真实违规事件，回送最近事件列表"""
    emit('real_violation_history', {
        'events': latest_real_violation_events[-20:],
        'count': len(latest_real_violation_events),
        'violation_type_counts': violation_type_counts,
    })


if __name__ == '__main__':
    threading.Thread(target=simulation_loop, daemon=True).start()
    # M14: 启动真实数据订阅线程
    threading.Thread(target=realtime_subscription_loop, daemon=True).start()
    print("=== 智慧交通数字孪生系统 (M14) ===")
    print("服务器启动中...")
    print("访问地址: http://localhost:5000")
    print("后端API地址:", BACKEND_API_URL)
    print("WebSocket端点: ws://localhost:5000/socket.io")
    print("M14 新增: /api/realtime/violation-events, /api/dashboard/today-stats, /api/demo/trigger-scene")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)