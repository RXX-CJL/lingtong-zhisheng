步骤1 完整标定后:
   crosswalk_zones     = [[[180, 429], [979, 425], [1079, 519], [79, 527]]]
   stop_line_y         = 415
   pixel_per_meter     = 10.0
   ppm_ref_y           = 470
   lane_width_px       = 190
   no_parking_zones    = [[[180, 429], [979, 425], [1079, 519], [79, 527]]]

步骤2 只画斑马线后（合并语义应保留标定）:
   crosswalk_zones     = [[[200, 440], [960, 435], [1060, 510], [100, 520]]]
   stop_line_y         = 415
   pixel_per_meter     = 10.0
   ppm_ref_y           = 470
   lane_width_px       = 190
   no_parking_zones    = [[[180, 429], [979, 425], [1079, 519], [79, 527]]]

结论: 标定参数已保留 ✅

最终恢复: 斑马线=1 禁停区=1 停止线=415 标定=10.0px/m@470
