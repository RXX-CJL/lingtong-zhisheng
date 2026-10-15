=== 1) POST /api/wx/login ===
  HTTP 200
  openid=dev_33dde5b23abea1ac23b0aa9d  dev_mode=True  note=未配置 WX_APPID/WX_SECRET，使用开发模式 openid

=== 2) 绑定车辆 ===
  HTTP 200  {"success": true, "data": {"ok": true, "plate_number": "苏W125K6"}}

=== 3) GET /vehicles ===
  HTTP 200  {"success": true, "data": [{"plate_number": "苏W125K6", "vin_tail": "123456", "relation": "owner", "verified": 0, "created_at": "2026-10-03 04:33:58"}]}

=== 4) GET /violations（我的违规）===
  HTTP 200  total=0  bound=['苏W125K6']
  hint=未匹配到违规记录；若你的车确有违规，可能是该记录未识别到车牌

=== 5) GET /profile ===
  HTTP 200  {"success": true, "data": {"openid": "dev_33dde5b23abea1ac23b0aa9d", "vehicles": [{"plate_number": "苏W125K6", "vin_tail": "123456", "relation": "owner", "verified": 0, "created_at": "2026-10-03 04:33:

=== 6) 无 X-Openid 应 401 ===
  HTTP 401  {"success":false,"message":"缺少 X-Openid 请求头（请先调用 /api/wx/login）","error_code":"HTTP_401"}

=== 7) GET /api/wx/stats ===
  HTTP 200  {"success": true, "data": {"users": 2, "bindings": 2, "notifications": 0, "appeals": 0, "appeals_by_status": {}, "configured": false, "dev_mode": true}}
