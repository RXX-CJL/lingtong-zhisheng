[ 30s] processed=271 事件总数=5 pending_ai=2 confirmed=0
[ 60s] processed=438 事件总数=20 pending_ai=3 confirmed=0
[ 90s] processed=581 事件总数=32 pending_ai=1 confirmed=0
[120s] processed=722 事件总数=40 pending_ai=3 confirmed=0
[150s] processed=905 事件总数=42 pending_ai=0 confirmed=0

========================================================================
【修复 2】evidence_chain 是否已落库
========================================================================
  总事件 541，有证据链 0 条 (0.0%)   ← 修复前是 0%

========================================================================
【修复 1】未标定超速是否跳过 AI 复核
========================================================================
  事件类型 × 状态:
    illegal_parking    manual_review    32
    illegal_parking    pending_ai       16
    illegal_parking    rejected         10
    lane_departure     rejected         172
    lane_departure     manual_review    92
    lane_departure     triggered        1
    lane_departure     pending_ai       1
    speeding           rejected         178
    speeding           pending_ai       14
    speeding           manual_review    14
    speeding           triggered        3
    wrong_way          rejected         4
    wrong_way          pending_ai       3
    wrong_way          manual_review    1

    evt_1790968408877_287_3caf47 state=triggered      含'跳过AI'说明=False
    evt_1790968397107_276_5bdb84 state=rejected       含'跳过AI'说明=False
    evt_1790968387502_268_27cb0d state=rejected       含'跳过AI'说明=False
    evt_1790968364017_240_3b25a2 state=rejected       含'跳过AI'说明=False
    evt_1790968350477_224_e8759e state=rejected       含'跳过AI'说明=False
    evt_1790968338837_212_d9e990 state=rejected       含'跳过AI'说明=False

  最近 6 条 speeding 中，标明'未经标定跳过复核'的: 0 条
  （修复 1 生效的话，未标定的超速不应再出现 pending_ai / rejected-by-AI）
