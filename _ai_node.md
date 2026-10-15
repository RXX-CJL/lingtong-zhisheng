=== evt_1790968397107_276_5bdb84 (speeding, rejected)
  原始长度 1429
  顶层键: ['deepseek', 'doubao', 'final', 'version', 'yolo']
  --- yolo: {"violation_type": "speeding", "confidence": 0.0, "detections": [{"bbox": [525.314697265625, 223.253662109375, 579.626708984375, 271.8569641113281], "class_name": "car", "track_id": 276}], "duration_ms": 0}
  --- doubao: {"judgment": "rejected", "confidence": 0.15, "reasoning": "---分析结果---\n第一步·场景描述：画面为一处城市道路交叉口，时间显示为2022-06-21 19:04，一辆红色货车停在靠近人行横道的车道内，前方有排队车辆；右侧交通信号灯显示直行绿灯（右下角可见绿色箭头灯），上方限速标志明确标示“80”（单位km/h），另有“×80”禁令标志及红灯（可能为左转或待行区信号）。\n\n第二步·是否违规：【不确定】\n\n第三步·判断依据：\n1. 图片中仅提供瞬时静态画面，未包含任何速度测量数据（如雷达/激光测速、视频流速度计算等），无法直接得出车辆实际行驶速度；\n2. 车辆当前处于静止或缓行状态（结合其位置在停止线前、后方有排队车辆、且无明显运动模糊），而系统标注速度为37.8 km/h——但该速度值属于“本地检测/跟踪提供”，
  --- deepseek: {"judgment": "rejected", "confidence": 0.05, "review_summary": "--- 审核报告 ---\n第一步·你对场景的简要总结：图片显示城市道路交叉口，有一辆红色货车停在车道内，上方有限速80km/h标志，信号灯状态复杂，但无法从静态图片判断车辆实际速度。\n\n第二步·你对豆包推理的评价：\n  - 证据充分性：【不足】\n  - 逻辑严谨性：【严谨】\n\n第三步·你的独立判断：【无法确定·需人工】\n\n第四步·你给出的置信度：10\n\n第五步·风险评估：【低风险可信】\n\n第六步·给管理员的一句话建议：静态图无法测速，豆包结论保守合理，无需处罚。", "disagreement_flag": false, "duration_ms": 1239}
  --- final: {"judgment": "rejected", "confidence": 0.05, "method": "doubao_plus_deepseek", "evidence_count": 2, "explanation": "事件类型: speeding, 主模型判断: False, DeepSeek 判断: False, 最终: rejected", "risk_flag": false}

=== evt_1790968394985_276_23d082 (lane_departure, rejected)
  原始长度 1536
  顶层键: ['deepseek', 'doubao', 'final', 'version', 'yolo']
  --- yolo: {"violation_type": "lane_departure", "confidence": 0.0, "detections": [{"bbox": [565.123779296875, 158.89529418945312, 689.0211181640625, 365.1006164550781], "class_name": "truck", "track_id": 276}], "duration_ms": 0}
  --- doubao: {"judgment": "rejected", "confidence": 0.2, "reasoning": "---分析结果---\n第一步·场景描述：画面为十字路口，一辆红色货车停在直行车道停止线前（车头贴近人行横道），其前方有排队车辆；左侧一辆银灰色轿车与一辆两轮车在人行横道上发生碰撞，车身严重变形、碎片飞溅；右侧车道交通信号灯显示直行绿灯、右转红灯，路面上可见清晰的白色车道分界线及人行横道斑马线。\n\n第二步·是否违规：【不确定】\n\n第三步·判断依据：\n1. 图片中仅能清晰看到红色货车处于静止状态（根据结构化上下文“速度: 0.0 km/h”及车头位置未移动可确认），未见其在行驶过程中跨越或骑轧车道实线的行为；\n2. 银灰色轿车与两轮车位于交叉口中心区域，但其具体行驶轨迹（是否压线变道）因碰撞瞬间模糊、存在运动拖影且无连续帧/轨迹信息，无法判定其是否在变道时越线；\n
  --- deepseek: {"judgment": "rejected", "confidence": 0.05, "review_summary": "--- 审核报告 ---\n第一步·你对场景的简要总结：十字路口发生碰撞事故，一辆红色货车停在停止线前，左侧轿车与两轮车相撞，画面中未见任何车辆正在骑轧白色实线行驶。\n第二步·你对豆包推理的评价：\n  - 证据充分性：【充分】\n  - 逻辑严谨性：【严谨】\n第三步·你的独立判断：【无法确定·需人工】\n第四步·你给出的置信度：10\n第五步·风险评估：【低风险可信】\n第六步·给管理员的一句话建议：豆包结论保守合理，但事故场景无法判定压线，建议人工复核。\n\n（说明：豆包给出\"不确定\"并附置信度20，其依据——车辆均处于停止或碰撞状态、缺乏连续帧轨迹、无法确认\"行驶中\"越线——与结论一致，无逻辑跳跃。YOLO仅检测到一个置信度0.00的truck
  --- final: {"judgment": "rejected", "confidence": 0.05, "method": "doubao_plus_deepseek", "evidence_count": 2, "explanation": "事件类型: lane_departure, 主模型判断: False, DeepSeek 判断: False, 最终: rejected", "risk_flag": false}

