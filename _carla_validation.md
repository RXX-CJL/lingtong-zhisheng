=== 实测状态 ===
  processed=618 追踪=8 违规=55 平均fps=2.63
  左栏=6 右栏=2 未归属=0
  标定: assumed_lanes ppm=108.68

=== 实测车辆测速（左栏 + 右栏） ===
  ID   6 轿车    px=   0.13    0.0km/h [assumed/ok] 
  ID   9 轿车    px=   0.36    0.0km/h [assumed/ok] 
  ID  11 轿车    px=   1.01    0.0km/h [assumed/ok] 
  ID  16 轿车    px=   0.46    0.0km/h [assumed/ok] 
  ID  53 轿车    px=   1.39    0.0km/h [assumed/ok] 
  ID  73 轿车    px=   0.28    0.0km/h [assumed/ok] 
  ID   1 轿车    px=   0.54    0.0km/h [assumed/ok] 违规停车
  ID  14 轿车    px=   0.22    0.0km/h [assumed/ok] 逆行

=== 真值统计（CSV） ===
  对照组 12 辆，违规车 3 辆

  对照组各车真值:
    normal_0     n= 800  avg=   6.5  max=  29.6  min=  0.0 km/h
    normal_1     n= 800  avg=  12.9  max=  29.8  min=  0.0 km/h
    normal_2     n= 800  avg=   1.3  max=  16.6  min=  0.0 km/h
    normal_3     n= 800  avg=   0.0  max=   0.0  min=  0.0 km/h
    normal_4     n= 800  avg=   0.3  max=  16.8  min=  0.0 km/h
    normal_5     n= 800  avg=  23.6  max=  29.5  min=  0.0 km/h
    normal_6     n= 800  avg=   0.6  max=  19.0  min=  0.0 km/h
    normal_7     n= 800  avg=   0.0  max=   0.1  min=  0.0 km/h
    normal_8     n= 800  avg=  26.6  max=  28.9  min= 13.7 km/h
    normal_9     n= 800  avg=  16.6  max=  29.2  min=  0.0 km/h
    normal_10    n= 800  avg=   0.6  max=  16.1  min=  0.0 km/h
    normal_11    n= 800  avg=   1.1  max=  19.6  min=  0.0 km/h

  违规车真值:
    violation_parking    n= 800  avg=   0.0  max=   0.0 km/h
    violation_lane       n= 800  avg=   9.0  max=  15.0 km/h
    violation_redlight   n= 800  avg=  13.4  max=  59.6 km/h

=== 违规检出情况 ===
    违规停车                 1 次
    逆行                   1 次
  合计检出 2 辆违规车 + 0 条未归属告警

============================================================================
关键结论
============================================================================
  对照组（应无违规）: 12 辆正常行驶
  实测报告违规: 2 辆 / 追踪 8 辆
  累计违规计数: 55（含冷却期内的重复）

  ⚠ 注意：CARLA 场景中的车辆**全部靠左行驶/靠右行驶**规则由 TM 管理，
     而项目的 road_direction 默认是 'south'，可能与 CARLA 实际方向不符 ->
     会造成大量'逆行'误报。这本身就是有价值的发现。
