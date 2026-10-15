===== 第 3 帧违规样本 =====
车辆检测框（带 track_id 的）:
   class=truck track_id=None bbox=[565, 157, 688, 364]
   class=car track_id=None bbox=[1191, 415, 1210, 443]
   class=car track_id=None bbox=[1223, 404, 1270, 460]
   class=car track_id=None bbox=[1231, 404, 1279, 460]
追踪车辆:
   ID1 car bbox=[627, 261, 750, 467]
   ID2 car bbox=[1200, 429, 1220, 457]
违规对象完整内容:
   {"violation_type": "wrong_way", "violation_type_cn": "逆行", "confidence": 0.5682, "is_violation": true, "evidence": {"vehicle_count": 1, "vehicle_confidence": 0.668459415435791, "wrong_way_count": 1, "lane_line_count": 0, "tracked_vehicles": 4, "has_wrong_way": true, "wrong_way_details": [{"vehicle_id": 3, "class_name": "car", "direction": "stationary", "speed": 8.61, "frame_count": 8}]}, "location": {"bbox": [565.7020263671875, 157.9401397705078, 688.4244384765625, 364.19146728515625], "center_x": 627.063232421875, "center_y": 261.06580352783203}, "timestamp": "2026-10-03T03:47:47.090808", "message": "检测到 1 辆逆行车辆"}

===== 第 17 帧违规样本 =====
车辆检测框（带 track_id 的）:
   class=truck track_id=None bbox=[564, 158, 689, 365]
追踪车辆:
   ID1 car bbox=[627, 261, 751, 468]
违规对象完整内容:
   {"violation_type": "red_light", "violation_type_cn": "闯红灯", "confidence": 0.3263, "is_violation": true, "evidence": {"has_vehicle": true, "has_traffic_light": true, "vehicle_confidence": 0.6526129245758057, "traffic_light_confidence": 0.6844115853309631, "note": "通用模型检测到红绿灯，需结合灯色确认"}, "location": {"bbox": [564.6435546875, 158.1083984375, 689.65283203125, 365.38946533203125], "center_x": 627.148193359375, "center_y": 261.7489318847656}, "timestamp": "2026-10-03T03:47:48.100964", "message": "检测到车辆和红绿灯，疑似闯红灯"}

