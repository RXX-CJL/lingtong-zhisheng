=== 测试 1: get_inverse_matrix() 返回什么类型 ===
  类型: <class 'list'>
  值: [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, -0.0, 0.0], [-0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]]

=== 测试 2: inv @ carla.Location 是否可用 ===
  ❌ 失败: TypeError: unsupported operand type(s) for @: 'list' and 'Location'

=== 测试 3: 逐分量点积（替代方案）===
  ✅ 手动矩阵乘: [-64.645, 24.471, 0.6, 1.0]

=== 测试 4: transform 是否可直接逆变换点 ===
  Transform.inverse 存在: False
