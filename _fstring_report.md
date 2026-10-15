# f-string 浮点格式化清单（共 45 处）


重点：对**可能是字符串**的值做 f 格式化会抛 `Unknown format code 'f' for object of type 'str'`。


## 1) 数值语义最强（最可疑）

- `backend_evaluation.py:517` 函数 `generate_report`
  - 表达式: `self.evaluation_results['overall_score']`   格式: `.1f`
- `backend_evaluation.py:534` 函数 `generate_report`
  - 表达式: `arch['total_score']`   格式: `.1f`
- `backend_evaluation.py:544` 函数 `generate_report`
  - 表达式: `api['total_score']`   格式: `.1f`
- `backend_evaluation.py:554` 函数 `generate_report`
  - 表达式: `db['total_score']`   格式: `.1f`
- `backend_evaluation.py:565` 函数 `generate_report`
  - 表达式: `security['total_score']`   格式: `.1f`
- `backend_evaluation.py:575` 函数 `generate_report`
  - 表达式: `error['total_score']`   格式: `.1f`
- `backend_evaluation.py:585` 函数 `generate_report`
  - 表达式: `business['total_score']`   格式: `.1f`
- `backend_evaluation.py:615` 函数 `generate_report`
  - 表达式: `score`   格式: `.1f`
- `backend_evaluation.py:671` 函数 `main`
  - 表达式: `results['overall_score']`   格式: `.1f`
- `cloud_collaborator.py:109` 函数 `should_consult_cloud`
  - 表达式: `confidence`   格式: `.2f`
- `cloud_collaborator.py:118` 函数 `should_consult_cloud`
  - 表达式: `confidence`   格式: `.2f`
- `cloud_collaborator.py:685` 函数 `analyze_event`
  - 表达式: `ai_trace.get('final', {}).get('confidence', 0.0)`   格式: `.2f`
- `cloud_collaborator.py:721` 函数 `_build_event_context_prompt`
  - 表达式: `vehicle_info.get('speed', 0.0)`   格式: `.1f`
- `evidence_chain.py:106` 函数 `summary`
  - 表达式: `self.ai_confidence`   格式: `.2f`
- `image_recognizer.py:2040` 函数 `analyze_image`
  - 表达式: `d['confidence']`   格式: `.2f`
- `image_recognizer.py:2043` 函数 `analyze_image`
  - 表达式: `d['confidence']`   格式: `.2f`
- `image_recognizer.py:2059` 函数 `analyze_image`
  - 表达式: `doubao_result.get('confidence_adjusted', 0)`   格式: `.2f`
- `image_recognizer.py:2239` 函数 `(module)`
  - 表达式: `d['confidence']`   格式: `.2f`
- `image_recognizer.py:2247` 函数 `(module)`
  - 表达式: `d['confidence']`   格式: `.2f`
- `image_recognizer.py:2255` 函数 `(module)`
  - 表达式: `d['confidence']`   格式: `.2f`
- `realtime_detector.py:782` 函数 `_draw_detection_boxes`
  - 表达式: `speed`   格式: `.1f`
- `realtime_detector.py:784` 函数 `_draw_detection_boxes`
  - 表达式: `confidence`   格式: `.2f`
- `realtime_detector.py:851` 函数 `get_annotated_frame`
  - 表达式: `vio.get('confidence', 0)`   格式: `.2f`
- `realtime_detector.py:855` 函数 `get_annotated_frame`
  - 表达式: `status['current_fps']`   格式: `.1f`
- `traffic_event_engine.py:452` 函数 `apply_ai_result`
  - 表达式: `confidence`   格式: `.2f`
- `traffic_event_engine.py:454` 函数 `apply_ai_result`
  - 表达式: `confidence`   格式: `.2f`
- `traffic_event_engine.py:457` 函数 `apply_ai_result`
  - 表达式: `confidence`   格式: `.2f`
- `traffic_event_engine.py:460` 函数 `apply_ai_result`
  - 表达式: `confidence`   格式: `.2f`

## 2) 其余 17 处

- `circular_frame_buffer.py:138` `trigger_time` :.3f  （extract_event_clip）
- `circular_frame_buffer.py:139` `start_time` :.3f  （extract_event_clip）
- `circular_frame_buffer.py:139` `end_time` :.3f  （extract_event_clip）
- `circular_frame_buffer.py:165` `trigger_time` :.3f  （extract_event_clip_with_meta）
- `circular_frame_buffer.py:166` `start_time` :.3f  （extract_event_clip_with_meta）
- `circular_frame_buffer.py:166` `end_time` :.3f  （extract_event_clip_with_meta）
- `cloud_collaborator.py:722` `vehicle_info.get('direction', 0.0)` :.1f  （_build_event_context_prompt）
- `cloud_collaborator.py:731` `first.get('x', 0)` :.0f  （_build_event_context_prompt）
- `cloud_collaborator.py:731` `first.get('y', 0)` :.0f  （_build_event_context_prompt）
- `cloud_collaborator.py:732` `last.get('x', 0)` :.0f  （_build_event_context_prompt）
- `cloud_collaborator.py:732` `last.get('y', 0)` :.0f  （_build_event_context_prompt）
- `ptz_controller.py:646` `dx` :.2f  （(module)）
- `ptz_controller.py:646` `dy` :.2f  （(module)）
- `ptz_controller.py:646` `dz` :.2f  （(module)）
- `rule_engine\plugins\public_security_plugin.py:335` `elapsed` :.1f  （(module)）
- `virtual_tracker.py:549` `ind['target_center_x']` :.1f  （(module)）
- `virtual_tracker.py:549` `ind['target_center_y']` :.1f  （(module)）
