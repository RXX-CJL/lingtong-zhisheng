=== 页面调用端点回归 ===
  [PASS] HTTP 200  /api/wx/statistics/overview                          (index.js loadStats) data 键=total,today,pending,confirmed,unread,bound_plates
  [PASS] HTTP 200  /api/wx/violations/list?page_size=5                  (index.js loadRecentViolations) data=数组(5) total=5
  [PASS] HTTP 200  /api/wx/violations/list?page=1&page_size=10          (violation/list.js) data=数组(5) total=5
  [PASS] HTTP 200  /api/wx/violations/list                              (fallback) data=数组(5) total=5
  [PASS] HTTP 200  /api/wx/appeals/list                                 (appeal/list.js) data=数组(0) total=0
  [PASS] HTTP 200  /api/wx/appeals/statistics/summary                   (appeal/list.js + my/index.js) data 键=total,pending,accepted,rejected,by_status
  [PASS] HTTP 200  /api/wx/bind/status                                  (我的页/绑定引导) data 键=has_binding,my_vehicles,suggest_plates
  [PASS] HTTP 200  /api/wx/notifications                                (通知中心) data=数组(0)
  [PASS] HTTP 200  /api/wx/overview                                     (首页看板(新)) data 键=total,today,pending,confirmed,unread,bound_plates
