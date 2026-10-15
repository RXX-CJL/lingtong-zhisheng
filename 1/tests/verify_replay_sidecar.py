# -*- coding: utf-8 -*-
"""TASK-COORD-007 回放数据验证脚本（只读）

验证：
1. DB 中新事件（本轮真实视频重跑生成）的 event_video_path 有效
2. 对应 sidecar JSON 存在且结构完整（frames/track_id/bbox）
3. 视频可读取、帧数与 sidecar frame_count 一致
4. 抽样打印 bbox 样本与数据来源
"""
import os
import sys
import json
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(API_DIR, 'api', 'zhitong_violations.db')
NEW_IDS = [
    'evt_1790347063112_79_64e07b',
    'evt_1790347063112_80_32d423',
    'evt_1790347061580_75_613c3b',
]


def main():
    import cv2
    conn = sqlite3.connect(DB_PATH)
    ok = True
    for eid in NEW_IDS:
        row = conn.execute(
            'SELECT event_id, event_type, state, event_video_path, track_id FROM traffic_events WHERE event_id=?',
            (eid,)).fetchone()
        if not row:
            print(f'[FAIL] {eid}: DB 无记录')
            ok = False
            continue
        _, etype, state, vpath, track_id = row
        print(f'\n=== {eid} | type={etype} state={state} track_id={track_id}')
        print(f'video: {vpath} exists={os.path.isfile(vpath) if vpath else False}')
        if not vpath or not os.path.isfile(vpath):
            ok = False
            continue
        cap = cv2.VideoCapture(vpath)
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        fcc = ''.join(chr((fourcc >> 8 * i) & 0xFF) for i in range(4))
        vfc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        vw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        vh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        print(f'video: fourcc={fcc} frames={vfc} size={vw}x{vh}')
        spath = vpath + '.replay.json'
        if not os.path.isfile(spath):
            print(f'[FAIL] sidecar 不存在: {spath}')
            ok = False
            continue
        with open(spath, 'r', encoding='utf-8') as f:
            sc = json.load(f)
        frames = sc.get('frames', [])
        n_veh = sum(len(fr.get('vehicles', [])) for fr in frames)
        n_frames_with_veh = sum(1 for fr in frames if fr.get('vehicles'))
        track_ids = sorted({v.get('track_id') for fr in frames for v in fr.get('vehicles', [])
                            if v.get('track_id') is not None})
        print(f'sidecar: {spath}')
        print(f'  source={sc.get("source")} fps={sc.get("fps")} size={sc.get("video_width")}x{sc.get("video_height")}')
        print(f'  frame_count={sc.get("frame_count")} (视频实际帧数 {vfc}, 一致={sc.get("frame_count") == vfc})')
        print(f'  含车辆帧数={n_frames_with_veh}/{len(frames)} 车辆记录总数={n_veh} 去重track_id={track_ids}')
        # 抽样：打印含车辆的前 2 帧样本
        samples = [fr for fr in frames if fr.get('vehicles')][:2]
        for fr in samples:
            print(f'  样本 frame[{fr["index"]}] time={fr["time"]}:')
            for v in fr['vehicles'][:3]:
                print(f'    track_id={v["track_id"]} class={v["class_name"]} bbox={v["bbox"]} speed_px={v["speed_px"]} dir={v["direction"]}')
        if sc.get('frame_count') != vfc or not track_ids:
            ok = False
    conn.close()
    print('\nRESULT:', 'PASS' if ok else 'FAIL')


if __name__ == '__main__':
    main()
