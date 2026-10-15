=== 检测状态 ===
  running                  = True
  source_kind              = file
  processed_frames         = 773
  tracked_vehicle_count    = 8
  violation_count          = 109
  avg_fps                  = 2.14
  video_path = E:\output\_carla_video\carla_scene_2k.mp4

============================================================================
逐车测速细节（关键：samples 有几个点？）
============================================================================
     ID 类型         px/s    km/h      原始 质量         可信度            帧率
    792 轿车         0.17     0.0     0.0 ok         assumed      2.55
    796 轿车         0.26     0.0     0.0 ok         assumed      2.55
    799 轿车         0.12     0.0     0.0 ok         assumed      2.55
    802 轿车         0.72     0.0     0.0 ok         assumed      2.55
    828 轿车         1.01     0.0     0.0 ok         assumed      2.55
    835 轿车          0.2     0.0     0.0 ok         assumed      2.55
    788 轿车         0.34     0.0     0.0 ok         assumed      2.55
    793 轿车         0.35     0.0     0.0 ok         assumed      2.55

=== 车辆对象里都有哪些字段（找轨迹/采样信息）===
  16 个字段:
     bbox                       = [1390.9744567871094, 699.1000137329102, 1454.4164123535156, 774.539024
     class_name                 = car
     class_name_cn              = 轿车
     direction                  = right
     frame_count                = 30
     is_wrong_way               = False
     plate                      = None
     speed_compensation         = 1.0
     speed_confidence           = assumed
     speed_fps                  = 2.55
     speed_kmh                  = 0.0
     speed_kmh_raw              = 0.0
     speed_method               = assumed_lanes
     speed_px                   = 0.17
     speed_quality              = ok
     track_id                   = 792

=== 标定信息 ===
  method                     = assumed_lanes
  note                       = 无标定：按画面宽高比 1.78 推断约 5.9 条车道 ≈ 23.6m（108.7 px/m），误差可能达 ±50%，仅供演示；正式使用请标注一条车道线
  ppm_ref                    = 108.68
  y_ref                      = 1080.0
  y_horizon                  = 432.0
  lane_width_m               = 3.75

=== 汇总判定 ===
  px/s 范围: 0.12 ~ 1.01
  质量分布: {'ok': 6}

  ⚠ px/s 全部 <2 -> 两种可能：
     A) 追踪的是静止车辆（CARLA 场景里确实有停车）
     B) 跟踪器频繁换 ID，轨迹点数太少
