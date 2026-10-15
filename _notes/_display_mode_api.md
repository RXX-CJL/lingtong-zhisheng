1) GET /settings -> HTTP 200  display_mode=minimal
2) POST display_mode=standard  -> HTTP 200  回读=standard
2) POST display_mode=full      -> HTTP 200  回读=full
2) POST display_mode=minimal   -> HTTP 200  回读=minimal
3) 渲染器实例 mode = minimal  (期望 minimal)
