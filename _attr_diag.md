追踪车辆数=2 违规计数=10

当前追踪车辆 2 辆:
   id=109 bbox=[560, 122, 640, 161]
   id=112 bbox=[538, 102, 586, 130]

/vehicles 结果: 左栏=2 右栏=0 未归属=2

未归属条目（含 _stale_id 说明旧ID）:
   {"type": "speeding", "type_cn": "超速", "confidence": 0.95, "source": "behavior_engine", "age_sec": 11.8}
   {"type": "illegal_parking", "type_cn": "违规停车", "confidence": 0.7, "source": "behavior_engine", "age_sec": 6.1}

诊断：检查违规是否真的带 vehicle_id —— 需看后端日志
日志中归属相关 0 行
