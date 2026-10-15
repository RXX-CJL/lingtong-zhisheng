  无标定            method=assumed_lanes   ppm=  30.0 px/s=600.0 -> 44.6 km/h [assumed]
  车道宽190px       method=lane_width      ppm=  50.7 px/s=600.0 -> 27.0 km/h [calibrated]
  显式ppm=30       method=explicit_ppm    ppm=  30.0 px/s=600.0 -> 50.9 km/h [calibrated]

=== 超速判定测试（600px/s）===
  无标定（应跳过）               未产生超速项（is_violation=False 被过滤，符合预期）
  显式ppm=30（应判定）          is_viol=True conf=0.66 kmh=72.0 calib=explicit_ppm
