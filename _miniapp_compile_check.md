app.json 声明 8 个页面

=== 页面文件完整性 ===
  [PASS] pages/index/index            缺: 无
  [PASS] pages/violation/list         缺: 无
  [PASS] pages/violation/detail       缺: 无
  [PASS] pages/appeal/list            缺: 无
  [PASS] pages/appeal/submit          缺: 无
  [PASS] pages/my/index               缺: 无
  [PASS] pages/my/bind                缺: 无
  [PASS] pages/notifications/index    缺: 无

=== tabBar 一致性 ===
  [PASS] pages/index/index            首页
  [PASS] pages/violation/list         违规
  [PASS] pages/appeal/list            申诉
  [PASS] pages/my/index               我的

=== 模块引用可解析性 ===
  [PASS] 所有相对引用均可解析

=== globalData 字段一致性（易踩坑）===
  app.js globalData 定义的键: ['apiBaseUrl', 'baseUrl', 'http', 'openid', 'token', 'userInfo']
  utils/api.js 读取的键:      ['baseUrl']
  [PASS] 键一致

==================================================================
总体: 静态检查全部通过 ✅
