# -*- coding: utf-8 -*-
"""TASK-COORD-005 f5 迁移脚本：为现有 7 个事件生成 H.264 兼容副本 + 真实 JPG 关键帧 + 更新 DB

规则：
- 原始 FMP4 文件必须保留（兼容副本用 {event_id}_h264.mp4 新文件名）
- 关键帧从原视频真实帧提取（首/中/尾），命名 {event_id}_frame_{idx}.jpg 与新代码约定一致
- DB 更新：event_video_path → H.264 副本绝对路径；key_frames → event-videos/ 相对路径 JSON
- 幂等：已是 _h264.mp4 或副本已存在的事件跳过
"""
import os
import sys
import json
import sqlite3
import subprocess

def main():
    import cv2
    import imageio_ffmpeg

    DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api', 'zhitong_violations.db')
    DB = os.path.abspath(DB)
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

    conn = sqlite3.connect(DB)
    rows = conn.execute(
        'SELECT event_id, event_video_path, key_frames FROM traffic_events ORDER BY created_at'
    ).fetchall()
    print(f'[init] 共 {len(rows)} 行事件记录')

    ok_count, skip_count, fail_count = 0, 0, 0
    for event_id, vpath, kf in rows:
        print(f'--- {event_id}')
        if not vpath:
            print('    SKIP: event_video_path 为空')
            skip_count += 1
            continue
        vpath_abs = os.path.abspath(vpath)
        if not os.path.exists(vpath_abs):
            print(f'    FAIL: 原视频不存在 {vpath_abs}')
            fail_count += 1
            continue
        if vpath_abs.endswith('_h264.mp4'):
            print('    SKIP: 已是 H.264 副本路径')
            skip_count += 1
            continue

        date_dir = os.path.dirname(vpath_abs)
        h264_path = vpath_abs[:-len('.mp4')] + '_h264.mp4'
        orig_size = os.path.getsize(vpath_abs)

        # 1) 转码（副本已存在则复用）
        if not (os.path.exists(h264_path) and os.path.getsize(h264_path) > 0):
            cmd = [FFMPEG, '-y', '-i', vpath_abs,
                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                   '-pix_fmt', 'yuv420p',
                   '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',
                   '-movflags', '+faststart', h264_path]
            proc = subprocess.run(cmd, capture_output=True, timeout=180, creationflags=creationflags)
            if proc.returncode != 0 or not os.path.exists(h264_path) or os.path.getsize(h264_path) == 0:
                print(f'    FAIL: 转码失败 rc={proc.returncode} '
                      f'stderr={proc.stderr[-200:] if proc.stderr else "N/A"}')
                fail_count += 1
                continue
        else:
            print('    转码副本已存在，复用')

        # 2) 验证副本编码
        cap = cv2.VideoCapture(h264_path)
        fourcc_int = int(cap.get(cv2.CAP_PROP_FOURCC))
        fourcc = ''.join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if fourcc not in ('avc1', 'H264', 'h264'):
            print(f'    FAIL: 副本编码异常 fourcc={fourcc}')
            fail_count += 1
            continue

        # 3) 从原视频提取首/中/尾真实 JPG（与视频同目录）
        src = cv2.VideoCapture(vpath_abs)
        n = int(src.get(cv2.CAP_PROP_FRAME_COUNT))
        indices = [0, n // 2, n - 1] if n > 3 else list(range(max(n, 0)))
        key_frames_rel = []
        cur = 0
        for idx in sorted(set(indices)):
            src.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = src.read()
            if not ret or frame is None:
                print(f'    WARN: 第 {idx} 帧读取失败，跳过')
                continue
            filename = f'{event_id}_frame_{idx}.jpg'
            abs_path = os.path.join(date_dir, filename)
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
            if not ok or buf is None:
                continue
            with open(abs_path, 'wb') as f:
                f.write(buf.tobytes())
            key_frames_rel.append(f"event-videos/{os.path.basename(date_dir)}/{filename}")
        src.release()
        if not key_frames_rel:
            print('    FAIL: 关键帧全部提取失败')
            fail_count += 1
            continue

        # 4) 更新 DB（原始 FMP4 保留不动）
        conn.execute('UPDATE traffic_events SET event_video_path=?, key_frames=? WHERE event_id=?',
                     (h264_path, json.dumps(key_frames_rel), event_id))
        conn.commit()
        print(f'    OK: 原始保留({orig_size}B) 副本={os.path.getsize(h264_path)}B fourcc={fourcc} '
              f'frames={frame_count} 关键帧={len(key_frames_rel)}')
        ok_count += 1

    conn.close()

    # 5) 终态验证输出
    print('=== 终态验证 ===')
    conn = sqlite3.connect(DB)
    for eid, vpath, kf in conn.execute(
            'SELECT event_id, event_video_path, key_frames FROM traffic_events ORDER BY created_at'):
        vp_ok = os.path.exists(vpath) if vpath else False
        frames = json.loads(kf) if kf else []
        files_ok = all(os.path.exists(os.path.join(os.path.dirname(vpath) if vp_ok else '',
                                                   os.path.basename(p))) for p in frames) if frames else False
        placeholder = any(not p.startswith('event-videos/') for p in frames)
        print(f'{eid} | video_exists={vp_ok} | frames={len(frames)} files_ok={files_ok} '
              f'placeholder={placeholder} | {kf}')
    conn.close()
    print(f'=== SUMMARY: ok={ok_count} skip={skip_count} fail={fail_count} ===')
    return 0 if fail_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
