登录: HTTP 200 openid=dev_6d67c090493b81ed40407233
库中高频车牌: [('浙BZXX11', 3), ('京A07321', 3), ('桂JC7321', 3)]
绑定 浙BZXX11: HTTP 200 {"success": true, "data": {"ok": true, "plate_number": "浙BZXX11"}}

GET /api/wx/violations: HTTP 200 total=3
    #45 wrong_way plate=浙BZXX11 conf=0.791 img=realtime_wrong_way_20261003_043823
    #42 wrong_way plate=浙BZXX11 conf=0.7961 img=realtime_wrong_way_20261003_043811
    #41 no_helmet plate=浙BZXX11 conf=0.647 img=realtime_no_helmet_20261003_043811

通知数: 0
