DB: E:\output\1\api\zhitong_violations.db  2813952 B
表 8 个: api_logs, collaboration_sessions, sqlite_sequence, system_configs, system_statistics, traffic_events, users, violation_evidences
  api_logs                         0 行  字段: id, client_type, endpoint, method, request_data, response_data, status_code, execution_time, timestamp
  collaboration_sessions           0 行  字段: id, session_id, violation_type, local_confidence, final_confidence, judgment_result, disagreement, resolved, resolver_id, ai_trace_json, image_path, created_at
  sqlite_sequence                  0 行  字段: name, seq
  system_configs                   1 行  字段: id, config_key, config_value, description, created_at, updated_at
  system_statistics                0 行  字段: id, stat_date, total_detections, consultations, confirmations, disagreements, accuracy_before, accuracy_after, saved_cost, created_at
  traffic_events                 541 行  字段: id, event_id, event_type, track_id, state, trigger_time, vehicle_info, scene_context, trajectory, key_frames, event_video_path, rule_judgment
  users                            1 行  字段: id, username, password_hash, role, email, name, is_active, created_at, updated_at
  violation_evidences             20 行  字段: id, violation_type, track_id, confidence, position, timestamp, image_path, video_path, additional_info, cloud_validated, cloud_result, status
