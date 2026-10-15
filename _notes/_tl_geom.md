世界里红绿灯 15 个
灯 id=9  杆 loc=(-119.23,5.09,0.26) yaw=-90.0
get_light_boxes -> 4 个:
  [0] loc=( -119.18,    4.72,  4.06)  ext=(0.201,0.484,0.704)  rot=Rotation(pitch=0.000000, yaw=-89.999596, roll=0.000000)
  [1] loc=( -118.80,   10.59,  5.16)  ext=(0.201,0.184,0.593)  rot=Rotation(pitch=0.000000, yaw=-89.999596, roll=0.000000)
  [2] loc=( -119.23,    4.83,  2.91)  ext=(0.359,0.098,0.256)  rot=Rotation(pitch=0.000000, yaw=-89.999596, roll=0.000000)
  [3] loc=( -119.14,    5.09,  1.34)  ext=(0.032,0.050,0.101)  rot=Rotation(pitch=0.000000, yaw=0.000403, roll=0.000000)

=== 杆坐标系 -> 世界（验证 bounding_box.location 需要变换）===
  bb.location(局部)=Location(x=-83.333183, y=14.580370, z=1.262776)
  tf.transform(bb.location)=Vector3D(x=-83.333183, y=14.580370, z=1.262776)
  -> 世界坐标差: dx=35.9 dy=9.5

=== 灯珠相对杆的方向（判断灯面朝向）===
  [0] 相对杆偏移=(   0.05,  -0.38,  3.80)
  [1] 相对杆偏移=(   0.43,   5.50,  4.90)
  [2] 相对杆偏移=(   0.00,  -0.26,  2.65)
  [3] 相对杆偏移=(   0.09,   0.00,  1.08)

=== Waypoint 提供的朝向（可能有更准的灯面方向）===
  waypoint road_id=735 lane_id=2 is_junction=True
  waypoint transform yaw=90.6
