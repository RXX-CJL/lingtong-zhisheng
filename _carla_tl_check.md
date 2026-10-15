=== 1) TrafficLight 可调方法 ===
   actor_state
   add_angular_impulse
   add_force
   add_impulse
   add_torque
   attributes
   bounding_box
   destroy
   disable_constant_velocity
   enable_constant_velocity
   freeze
   get_acceleration
   get_affected_lane_waypoints
   get_angular_velocity
   get_bone_names
   get_bone_relative_transforms
   get_bone_world_transforms
   get_component_names
   get_component_relative_transform
   get_component_world_transform
   get_elapsed_time
   get_green_time
   get_group_traffic_lights
   get_light_boxes
   get_location
   get_opendrive_id
   get_pole_index
   get_red_time
   get_socket_names
   get_socket_relative_transforms
   get_socket_world_transforms
   get_state
   get_stop_waypoints
   get_transform
   get_velocity
   get_world
   get_yellow_time
   id
   is_active
   is_alive
   is_dormant
   is_frozen
   parent
   reset_group
   semantic_tags
   set_collisions
   set_enable_gravity
   set_green_time
   set_location
   set_red_time
   set_simulate_physics
   set_state
   set_target_angular_velocity
   set_target_velocity
   set_transform
   set_yellow_time
   state
   trigger_volume
   type_id

   -> 周期/状态相关: ['actor_state', 'get_elapsed_time', 'get_green_time', 'get_red_time', 'get_state', 'get_yellow_time', 'set_green_time', 'set_red_time', 'set_state', 'set_yellow_time', 'state']

=== 2) 当前世界的红绿灯 ===
   红绿灯数量: 15
   id=9  状态=Red  类型=traffic.traffic_light
      get_green_time() = 10.0
      get_yellow_time() = 3.0
      get_red_time() = 2.0
      get_elapsed_time() = 0.0
   id=10  状态=Green  类型=traffic.traffic_light
      get_green_time() = 10.0
      get_yellow_time() = 3.0
      get_red_time() = 2.0
      get_elapsed_time() = 2.6967034339904785
   id=11  状态=Red  类型=traffic.traffic_light
      get_green_time() = 10.0
      get_yellow_time() = 3.0
      get_red_time() = 2.0
      get_elapsed_time() = 0.0

=== 3) 车辆控制 API（制造压线/逆行的基础）===
   VehicleControl 字段: ['brake', 'gear', 'hand_brake', 'manual_gear_shift', 'reverse', 'steer', 'throttle']
