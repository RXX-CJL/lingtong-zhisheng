L550: for tl in traffic_lights:

=== 含 traffic_light / tl 的绘制段 ===
L7:   3. 红绿灯框：按颜色着色 + 标注"红灯/黄灯/绿灯"
L125: # 红绿灯颜色（BGR）
L145:         frame = r.render(frame, detections, tracked_vehicles, violations, traffic_light)
L262:                traffic_lights=None,
L273:             traffic_lights: [{'bbox','color','countdown'}, ...] 或 [{'bbox','state'}]
L286:         traffic_lights = traffic_lights or []
L400:             # 红绿灯单独处理
L401:             if cls in ("traffic light", "traffic_light", "red_light", "green_light",
L549:         # ---------------- 红绿灯框 ----------------
L550:         for tl in traffic_lights:
