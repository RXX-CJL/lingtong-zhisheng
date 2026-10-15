=== 最新 rejected 样本 ===
   event_id        = evt_1790968397107_276_5bdb84
   event_type      = speeding
   state           = rejected
   ai_confidence   = 0.05
   rule_judgment   = {"behavior_type": "speeding", "confidence": 0.8097, "is_violation": true, "evidence": {"pixel_speed": 231.19, "real_speed_kmh": 83.23, "speed_limit": 60, "excess_ratio": 
   ai_judgment     = {"version": "v3", "yolo": {"violation_type": "speeding", "confidence": 0.0, "detections": [{"bbox": [525.314697265625, 223.253662109375, 579.626708984375, 271.85696411132
   ai_explanation  = 事件类型: speeding, 主模型判断: False, DeepSeek 判断: False, 最终: rejected
   state_history   = [{"timestamp": 1790968397.1078527, "old_state": null, "new_state": "triggered", "reason": "事件创建"}, {"timestamp": 1790968402.1093097, "old_state": "triggered", "new_state"
   evidence_chain  = None

=== 最新 manual_review 样本 ===
   event_id        = evt_1790968371537_250_b00804
   event_type      = lane_departure
   state           = manual_review
   ai_confidence   = 0.05
   rule_judgment   = {"behavior_type": "lane_departure", "confidence": 0.65, "is_violation": true, "evidence": {"overlap_count": 1, "lane_lines_count": 1, "overlap_details": [{"lane_type": "a
   ai_explanation  = AI 无法确认，证据不足或主辅模型存在分歧，需人工复核

=== 各状态 ai_confidence 统计 ===
   manual_review  n=139   avg=0.05 min=0.05 max=0.05
   pending_ai     n=34    avg=0.0 min=0.0 max=0.0
   rejected       n=364   avg=0.05 min=0.05 max=0.05
   triggered      n=4     avg=0.0 min=0.0 max=0.0

=== 证据链完整度 ===
   总事件 541
   无关键帧  4  (0.7%)
   无事件视频 4  (0.7%)
   无证据链  541  (100.0%)
