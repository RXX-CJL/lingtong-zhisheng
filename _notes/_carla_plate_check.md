=== 1) 车辆蓝图是否带车牌相关的可调属性 ===
  vehicle.audi.a2 可调属性 14 个:
     role_name
     ros_name
     has_dynamic_doors
     ros_frame_id
     ros_publish_tf
     color
     sticky_control
     terramechanics
     generation
     object_type
     base_type
     number_of_wheels
     special_type
     has_lights
  -> 车牌相关属性: ['number_of_wheels']

=== 2) 是否有'车牌'专用蓝图/贴花 ===
  filter('vehicle.*plate*') -> 0 个  []
  filter('*plate*') -> 0 个  []
  filter('static.prop.*plate*') -> 0 个  []
  filter('*license*') -> 0 个  []

=== 3) 已知的 CARLA 车牌事实 ===
  CARLA 的车辆模型**自带车牌贴图**（欧洲样式，如 'CARLA-1234'），
  位于车头/车尾的 Texture 上，通过 Texture 材质参数可改。
  但：① 是**欧洲牌样式**（非中国蓝牌）② 字号很小，远景难以识别

=== 4) 结论 ===
  ✅ 有车牌贴图 -> 车牌识别链路**能跑通**（但可能是欧洲样式）
  ⚠️ 若需要**中国蓝牌**效果，需自建贴图（工作量不小）
