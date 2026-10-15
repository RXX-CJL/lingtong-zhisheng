traffic_events 字段:
   id                       INTEGER
   event_id                 VARCHAR(64)
   event_type               VARCHAR(50)
   track_id                 INTEGER
   state                    VARCHAR(20)
   trigger_time             DATETIME
   vehicle_info             TEXT
   scene_context            TEXT
   trajectory               TEXT
   key_frames               TEXT
   event_video_path         VARCHAR(255)
   rule_judgment            TEXT
   ai_judgment              TEXT
   ai_confidence            FLOAT
   ai_explanation           TEXT
   evidence_chain           TEXT
   state_history            TEXT
   camera_id                VARCHAR(50)
   created_at               DATETIME
   updated_at               DATETIME

总行数: 541
状态分布: rejected=364, manual_review=139, pending_ai=34, triggered=4
类型分布: lane_departure=266, speeding=209, illegal_parking=58, wrong_way=8
