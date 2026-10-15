=== 数据库现状 ===
  事件总数      751
  有证据链      207  (28%)
  有事件视频    745  (99%)
  有关键帧      745  (99%)

=== 接口 /api/realtime/events ===
  HTTP 200  顶层键=['data', 'page', 'size', 'success', 'total']  返回 20 条
    evt_1790975749999_950_821500       illegal_parking  triggered      video=无 chain=无
    evt_1790975749795_950_bf1f71       wrong_way        triggered      video=无 chain=无
    evt_1790975741212_944_213aa5       wrong_way        pending_ai     video=有 chain=无
    evt_1790975739133_942_731201       wrong_way        manual_review  video=有 chain=有
    evt_1790975738362_933_ba2db6       wrong_way        manual_review  video=有 chain=有

=== 接口 /api/realtime/events/active ===
  HTTP 200  返回 206 条活跃事件

=== 取一个最新事件的详情 ===
  event_id=evt_1790975749999_950_821500
  HTTP 200  键: ['ai_confidence', 'ai_explanation', 'ai_judgment', 'cooldown_until', 'created_at', 'event_id', 'event_type', 'event_video_path', 'evidence_chain', 'key_frames', 'rule_judgment', 'scene_context', 'state', 'state_history', 'track_id', 'trajectory']
    type=illegal_parking state=triggered conf=0.0
    证据链字段: ['ai_confidence', 'ai_explanation', 'ai_judgment', 'camera_id', 'event_video_path', 'final_status', 'key_frames', 'lane_id', 'location', 'plate_color', 'plate_number', 'rule_judgment', 'stop_line_relation', 'timestamp', 'traffic_light_state', 'trajectory']
      plate='' vehicle_id=950 key_frames=0 trajectory=1 final_status=pending
