登录: HTTP 200 openid=dev_e6d2f105ae0793c2bad8bf7d

=== 1) GET /bind/status（未绑定时应 has_binding=false + 给建议）===
  HTTP 200 has_binding=False 建议车牌 12 个
     沪1X1111  (出现 5 次)
     陕A721U8  (出现 4 次)
     桂E2X172  (出现 4 次)
     沪B89W55  (出现 3 次)
     粤1416T1  (出现 3 次)

=== 2) POST /vehicles/bind-by-suggest（一键绑定）===
  绑定 沪1X1111: HTTP 200  {"success": true, "data": {"ok": true, "plate_number": "沪1X1111"}}

=== 3) GET /overview（小程序首页看板）===
  HTTP 200
     total         = 5
     today         = 5
     pending       = 5
     confirmed     = 0
     unread        = 0
     bound_plates  = ['沪1X1111']
     by_type = [{"type": "illegal_parking", "count": 5}]

=== 4) GET /violations/{id}（详情）===
  列表 total=5 首条 violation_id=69
  详情 HTTP 200: type=illegal_parking plate=沪1X1111 img=realtime_illegal_parking_20261003_044033.jpg conf=0.7
