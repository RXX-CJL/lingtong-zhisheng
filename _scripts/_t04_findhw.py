# -*- coding: utf-8 -*-
"""Town04：定位真正的高速环线（找长距离连续行驶的道路点）。"""
import carla, math
from collections import defaultdict
c = carla.Client('127.0.0.1', 2000); c.set_timeout(60.0)
w = c.get_world(); m = w.get_map()
print('地图:', w.get_map().name)

# 采样全图，按 lane_id + 方向聚合成连续路径
pts = []
for wp in m.generate_waypoints(10.0):
    if wp.lane_type != carla.LaneType.Driving: continue
    t = wp.transform
    pts.append((t.location.x, t.location.y, t.location.z, t.rotation.yaw, wp.lane_id, wp.road_id, wp.lane_width))
print('采样点:', len(pts))

# 找 lane_width 较大的（高速车道更宽）
widths = sorted(set(round(p[6],2) for p in pts))
print('车道宽度分布:', widths[:12])

# 找 road_id 上点数最多的（长路）
byroad = defaultdict(list)
for p in pts: byroad[p[5]].append(p)
top = sorted(byroad.items(), key=lambda kv: -len(kv[1]))[:6]
print()
print('=== 最长的 6 条 road ===')
for rid, arr in top:
    xs = [a[0] for a in arr]; ys = [a[1] for a in arr]; zs = [a[2] for a in arr]
    span = math.dist((min(xs),min(ys)), (max(xs),max(ys)))
    print('road %-6s 点数%-5d 跨度%.0fm  高度%.1f~%.1f  车道宽%.2f' % (rid, len(arr), span, min(zs), max(zs), arr[0][6]))

# 高架 = z 明显高于地面的
high = [p for p in pts if p[2] > 8.0]
print()
print('=== 高架点（z>8m）数量:', len(high))
if high:
    hz = [p[2] for p in high]
    print('  高度范围: %.1f ~ %.1f' % (min(hz), max(hz)))
    hbyroad = defaultdict(list)
    for p in high: hbyroad[p[5]].append(p)
    for rid, arr in sorted(hbyroad.items(), key=lambda kv:-len(kv[1]))[:4]:
        xs=[a[0] for a in arr]; ys=[a[1] for a in arr]
        print('  road %-6s 高架点数%-4d 范围 x[%.0f,%.0f] y[%.0f,%.0f]' % (rid, len(arr), min(xs),max(xs),min(ys),max(ys)))