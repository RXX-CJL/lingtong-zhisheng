=== 新增事件 类型 × 状态 ===
   illegal_parking    manual_review    10
   illegal_parking    recording        1
   illegal_parking    pending_ai       1
   lane_departure     rejected         5
   lane_departure     manual_review    4
   lane_departure     triggered        1
   speeding           rejected         7
   speeding           triggered        1
   wrong_way          manual_review    43
   wrong_way          triggered        3
   wrong_way          pending_ai       3
   wrong_way          rejected         1

=== 新增 speeding 事件的 state_history ===
  --- evt_1790968408877_287_3caf47 state=triggered
      None -> triggered: 事件创建
      vehicle_info.calibration=None speed_method=None speed=37.939098610879064
  --- evt_1790968397107_276_5bdb84 state=rejected
      None -> triggered: 事件创建
      triggered -> recording: 开始录制事件视频
      recording -> pending_ai: 提交云端 AI 分析
      pending_ai -> ai_reviewed: 云端 AI 返回结果
      ai_reviewed -> rejected: AI 排除 conf=0.05
      vehicle_info.calibration=None speed_method=None speed=37.84492288138696
  --- evt_1790968387502_268_27cb0d state=rejected
      None -> triggered: 事件创建
      triggered -> recording: 开始录制事件视频
      recording -> pending_ai: 提交云端 AI 分析
      pending_ai -> ai_reviewed: 云端 AI 返回结果
      ai_reviewed -> rejected: AI 排除 conf=0.05
      vehicle_info.calibration=None speed_method=None speed=110.77486301200997
  --- evt_1790968364017_240_3b25a2 state=rejected
      None -> triggered: 事件创建
      triggered -> recording: 开始录制事件视频
      recording -> pending_ai: 提交云端 AI 分析
      pending_ai -> ai_reviewed: 云端 AI 返回结果
      ai_reviewed -> rejected: AI 排除 conf=0.05
      vehicle_info.calibration=None speed_method=None speed=113.43073785011936
  --- evt_1790968350477_224_e8759e state=rejected
      None -> triggered: 事件创建
      triggered -> recording: 开始录制事件视频
      recording -> pending_ai: 提交云端 AI 分析
      pending_ai -> ai_reviewed: 云端 AI 返回结果
      ai_reviewed -> rejected: AI 排除 conf=0.05
      vehicle_info.calibration=None speed_method=None speed=34.78755103237799

=== 新增事件里所有含「跳过」或「未经场景标定」的记录 ===
   （无 —— 说明本次没有触发该门禁，需确认是否有未标定超速事件）

=== 新增事件类型汇总 ===
   wrong_way          50
   illegal_parking    12
   lane_departure     10
   speeding           8
