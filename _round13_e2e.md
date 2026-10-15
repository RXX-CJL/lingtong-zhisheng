登录 openid=dev_220d8c518727149bc03c87ce

======================================================================
【bind 页面】流程
======================================================================
1. onLoad /bind/status     HTTP 200  has_binding=False 建议=12 my=0
2. 点击建议车牌 沪1X1111    HTTP 200  {"success": true, "data": {"ok": true, "plate_number": "沪1X1111"}}
3. 刷新 /bind/status       HTTP 200  has_binding=True my=['沪1X1111']
4. 绑定不存在的车牌 京99999 HTTP 400  {"success":false,"message":"车牌 京99999 未在系统记录中出现过，无法一键绑定","error_code":"HTTP_400"}
5. 手动绑定 测A12345      HTTP 200  {"success": true, "data": {"ok": true, "plate_number": "测A12345"}}
6. 解绑 测A12345          HTTP 200  {"success": true, "data": {"ok": true, "deleted": 1}}

======================================================================
【notifications 页面】流程
======================================================================
1. onLoad /notifications   HTTP 200  条数=0
2. 触发一条通知           HTTP 200  {"success": true, "data": {"sent": 3, "detail": [{"id": 2, "pushed": false, "push_result": "未配置 WX_TMPL_VIOLATION，仅站内信"}, {"id": 3
3. 再查 /notifications     HTTP 200  共 1 条，未读 1 条
     #4 违规通知 plate=沪1X1111 is_read=0 pushed=0
4. 标记 #4 已读        HTTP 200  {"success": true, "data": {"ok": true, "updated": 1}}
5. 只看未读               HTTP 200  条数=0
6. 全部标记已读           HTTP 200  {"success": true, "data": {"ok": true, "updated": 1}}
7. 确认未读清零           HTTP 200  条数=0
8. /overview unread       HTTP 200  unread=0
