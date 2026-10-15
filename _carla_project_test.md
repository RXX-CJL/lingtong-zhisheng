路口: (-64.6,24.5)
相机已建 id=24
生成 2 辆车

========================================================================
测试 1: camera.project() —— 世界坐标 -> 像素
========================================================================
  camera 有 project 方法: False

========================================================================
测试 2: 3D bbox 8 角点 -> 像素外接矩形（真正要用的方法）
========================================================================
  id=25 失败: AttributeError: 'ServerSideSensor' object has no attribute 'project'
  id=26 失败: AttributeError: 'ServerSideSensor' object has no attribute 'project'

========================================================================
测试 3: 车辆是否落在画面范围内（1280x720）
========================================================================
  id=25 失败: 'ServerSideSensor' object has no attribute 'project'
  id=26 失败: 'ServerSideSensor' object has no attribute 'project'

已清理
