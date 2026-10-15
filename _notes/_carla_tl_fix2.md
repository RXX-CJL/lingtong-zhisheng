试验灯 id=9

=== 试验 1：freeze(True) + set_state(Green) ===
  freeze 后状态 = Green
  时间: 绿=25.0 红=25.0

=== 试验 2：set_*_time 后强制切状态 ===
  回读: 绿=30.0 黄=4.0 红=30.0

=== 试验 3：解冻 ===
  freeze(False) 完成，状态=Red

=== 试验 4：环境信息 ===
  carla 模块: C:\Users\ROG\AppData\Local\Programs\Python\Python312\Lib\site-packages\carla\__init__.py
  已知: CARLA 0.9.x 的 set_green/red/yellow_time 在部分版本**只影响自动周期
        的下一次循环**，且 getter 始终返回初值；freeze+set_state 才是可靠手段。
