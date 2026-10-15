"""
直接证明「预测框在两次检测之间持续移动」（2026-10-06 由 DSH 编写）

背景：框预测只作用于**绘制**，所以 /api/realtime/vehicles 看不到它。
      /api/realtime/status 现在暴露 predicted_boxes（最近一次预测后的框），
      本脚本以 150ms 间隔采样它 —— 远小于一个检测周期（约 378ms）。
      若同一 track 的框在这段时间内持续变化，即证明预测生效。

注意：全部输出用纯 ASCII。本机控制台是 GBK，前面把结果直接内联进
      `python -c` 时因为打印 '✓' 直接 UnicodeEncodeError 崩掉，
      统计结果一个字都没出来（教训：日志/输出避免非 ASCII 符号）。
"""
import json
import threading
import time
import urllib.request

BASE = 'http://127.0.0.1:8001'
SAMPLES = 16
GAP = 0.15

# ★必须一边消费 MJPEG 流、一边采样：
#   _predict_boxes() 只在**绘制**时被调用（get_annotated_frame），
#   而 get_annotated_frame 由流接口驱动。第一版只查 /status 不拉流，
#   结果 predicted_boxes 恒为空 -> 误判成 FAIL。
#   真实场景里浏览器一直在拉流，这里必须复现这一点。
_stop = threading.Event()
_frames = {'n': 0}


def stream_consumer():
    while not _stop.is_set():
        try:
            req = urllib.request.Request(BASE + '/api/realtime/stream',
                                         headers={'User-Agent': 'dsh-probe'})
            with urllib.request.urlopen(req, timeout=20) as r:
                buf = b''
                while not _stop.is_set():
                    chunk = r.read(4096)
                    if not chunk:
                        break
                    buf += chunk
                    a = buf.find(b'\xff\xd8')
                    b = buf.find(b'\xff\xd9')
                    if a >= 0 and b > a:
                        _frames['n'] += 1
                        buf = buf[b + 2:]
        except Exception:
            time.sleep(0.3)


def status():
    with urllib.request.urlopen(BASE + '/api/realtime/status', timeout=20) as r:
        return json.loads(r.read().decode())['data']


t = threading.Thread(target=stream_consumer, daemon=True)
t.start()
time.sleep(1.5)                       # 等流跑起来

s0 = status()
print('tuning   : frame_rate=%s  yolo_imgsz=%s  box_prediction=%s'
      % (s0.get('frame_rate'), s0.get('yolo_imgsz'), s0.get('box_prediction')))
print('models   : %s' % ', '.join(s0.get('model_sequence') or []))

hist = {}
t_start = time.time()
for i in range(SAMPLES):
    d = status()
    for pb in (d.get('predicted_boxes') or []):
        hist.setdefault(pb['track_id'], []).append(
            (round(time.time() - t_start, 3), tuple(pb['bbox']), pb.get('predicted')))
    time.sleep(GAP)

print('')
print('sampling window: %.1fs, %d samples @ %.0fms (detection period ~378ms)'
      % (time.time() - t_start, SAMPLES, GAP * 1000))
print('')
moved_any = False
for tid, seq in sorted(hist.items()):
    uniq = []
    for _, bb, _p in seq:
        if not uniq or uniq[-1][0] != bb:
            uniq.append((bb, _p))
    n_pred = sum(1 for _, _, p in seq if p)
    print('track %-6s samples=%-3d bbox_changes=%-3d flagged_predicted=%d'
          % (tid, len(seq), len(uniq), n_pred))
    if len(uniq) >= 2:
        moved_any = True
        a, b = uniq[0][0], uniq[-1][0]
        print('        first=%s' % (a,))
        print('        last =%s   delta=(%+.1f, %+.1f) px' % (b, b[0] - a[0], b[1] - a[1]))
        for t, bb, p in seq[:4]:
            print('          t=%.2fs %s pred=%s' % (t, bb, p))

print('')
print('RESULT: %s' % ('PASS - predicted boxes move between detections'
                      if moved_any else 'FAIL - no movement observed'))
print('stream frames consumed: %d' % _frames['n'])
_stop.set()
