# 小程序代码审计报告（Trae 产出核查）

> 2026-10-03 由 DSH 审计。审计对象：`E:\output\1\wechat-miniprogram`（Trae 产出）。
> 方法：**只读核查**，逐项对照后端真实接口与运行事实。
>
> **更新（同日）**：阶段一修复已完成，静态检查全部通过（见 §9）。

---

## 一、审计结论速览

| 维度 | 审计时 | 修复后 |
|---|---|---|
| **能否编译** | ❌ 不能（缺 app.json、5 页面不存在、tabBar 坏 2 个） | ✅ **静态检查通过** |
| **能否连通后端** | ❌ 不能（端口错 + 0/6 接口匹配 + 鉴权头错） | 🟡 **已修 app.js，页面 URL 待改** |
| 代码结构 | ❌ 三套并存 | 🟡 已定位，未清理 |
| 登录 | ❌ 调不存在的路由 | ✅ 已改为 `/login` |
| 图标 | ❌ 占位符 | 🟡 已改为纯文字 tabBar |

---

## 二、致命问题（阻塞编译/运行）

### P0-1　`src/` 缺 3 个必需文件
```
project.config.json: "srcMiniprogramRoot": "src/"
src/ 实际内容:        app.js + pages/{index,my,violation/list,violation/detail,appeal/list,appeal/submit}
src/ 缺失:            ❌ app.json      （页面注册表，必需）
                      ❌ app.wxss      （全局样式）
                      ❌ utils/        （api.js / format.js 在根目录，不在 src 下）
```
**后果**：微信开发者工具以 `src/` 为根，找不到 `app.json` → **无法编译**。

### P0-2　根 `app.json` 声明 5 个不存在的页面
```
✅ pages/index/index · submit/submit · list/list · detail/detail · statistics/statistics
❌ pages/my/index · violation/list · violation/detail · appeal/list · appeal/submit
```
**注意**：声明在根 `app.json` 的这 5 个页面，与 `src/pages/` 里的 6 个页面 **是两套完全不同的实现**。

### P0-3　`tabBar` 引用坏页面（编译必失败）
```json
{"pagePath": "pages/index/index",          "text": "首页"}      ✅
{"pagePath": "pages/violation/list",       "text": "违规记录"}  ❌ 文件不存在
{"pagePath": "pages/statistics/statistics","text": "统计"}      ✅
{"pagePath": "pages/my/index",             "text": "我的"}      ❌ 文件不存在
```
4 个 tab 里 **2 个指向不存在的页面** → 微信编译器直接报错。

### P0-4　端口错
```javascript
// src/app.js
apiBaseUrl: 'http://localhost:8000/api'    // ❌ 项目后端实际是 8001
```

---

## 三、接口契约不匹配（0/6）

| 小程序调用 | 后端实际 | 结论 |
|---|---|---|
| `POST /wechat/code2session` | `POST /api/wx/login` | ❌ 路由不存在 |
| `GET /violations/list` | `GET /api/wx/violations` | ❌ |
| `GET /statistics/overview` | `GET /api/wx/stats` | ❌ 路由不存在 |
| `GET /appeals/list` | `GET /api/wx/appeals` | ❌ |
| `POST /appeals/submit` | `POST /api/wx/appeals` | ❌ |
| `GET /appeals/statistics/summary` | `GET /api/wx/stats` | ❌ |

**鉴权方式也不一致**：
```javascript
// 小程序发的是
header: { 'Authorization': `Bearer ${token}` }
// 后端 /api/wx/* 要求的是
header: { 'X-Openid': openid }
```

---

## 四、代码结构混乱（三套并存）

| # | 位置 | 入口 | 特点 | 页面 |
|---|---|---|---|---|
| A | `src/` | `src/app.js`（`apiBaseUrl` + `app.request`） | **实现最完整**，有 wxml/wxss | 6 个（appeal/violation/my/index）|
| B | 根 `pages/` | 根无 app.js | 调后端但用另一套 `utils/api.js` | 5 个（index/submit/list/detail/statistics）|
| C | `miniprogram/` | `miniprogram/app.ts` | Taro 模板残留（`app.less`/`navigation-bar` 组件） | 2 个（index/logs）|

**更严重的是 `app.js` 有两个且不一致**：
```javascript
// src/app.js
globalData: { apiBaseUrl: 'http://localhost:8000/api', ... }

// utils/api.js 却读：
const { baseUrl = app.globalData.baseUrl } = app.globalData;   // ← baseUrl 从未被定义！
```
→ 即使修好端口，`app.globalData.baseUrl` 是 `undefined`，URL 会变成 `undefined/api/...`。

**另有 Taro 构建残留**：`miniprogram/dist/`（Taro 编译产物）与原生实现混在同一仓库。

---

## 五、其他问题

| 问题 | 证据 | 影响 |
|---|---|---|
| 图标是占位符 | 全部 `127 B`，PNG 头正常但内容为 1×1 透明 | tabBar 图标不可见 |
| `appid` 是测试值 | `project.config.json: "appid": "wxtodo"` | 无法真机预览/上传 |
| 4 个 tab 只用 2 个真实页面 | 见 P0-3 | 导航残缺 |
| 无 `sitemap` 配置于 src | 根有 `sitemap.json`，`src/` 无 | 微信索引告警 |

---

## 六、修复方案（建议按此顺序）

### 阶段一：让它能编译（约 30 分钟）
1. 在 `src/` 下新建 `app.json`，页面清单**只注册实际存在的 6 个页面**：
   ```json
   {
     "pages": [
       "pages/index/index",
       "pages/violation/list", "pages/violation/detail",
       "pages/appeal/list", "pages/appeal/submit",
       "pages/my/index"
     ],
     "window": { "navigationBarTitleText": "智瞳交管", "navigationBarBackgroundColor": "#1D4ED8", "navigationBarTextStyle": "white" },
     "tabBar": {
       "color": "#8A9099", "selectedColor": "#1D4ED8",
       "list": [
         { "pagePath": "pages/index/index",          "text": "首页" },
         { "pagePath": "pages/violation/list",       "text": "违规" },
         { "pagePath": "pages/appeal/list",          "text": "申诉" },
         { "pagePath": "pages/my/index",             "text": "我的" }
       ]
     },
     "style": "v2", "sitemapLocation": "sitemap.json"
   }
   ```
   > **关键决策**：tabBar **先用纯文字**（不配 `iconPath`）—— 微信允许无图标 tab，
   > 避免被占位符图标卡住；图标后续再补。
2. 把 `utils/api.js`、`utils/format.js` 复制到 `src/utils/`（保持相对路径 `../../utils/` 可用）
3. `src/` 下新建 `app.wxss`（全局样式，可直接沿用根 `app.wxss`）
4. **删除根目录的 5 个遗留页面**（`pages/index|submit|list|detail|statistics`）与根 `app.json`，
   避免与 `src/` 混淆（**删除前建议先备份**）

### 阶段二：让它连通后端
5. 改 `src/app.js`：
   ```javascript
   apiBaseUrl: 'http://127.0.0.1:8001/api/wx'    // 端口 8001 + 我的路由前缀
   ```
6. 把 `app.request` 的鉴权头改为 `'X-Openid': this.globalData.openid`
7. 改登录：`POST /login`（body `{code}`），返回 `{openid, dev_mode}`
8. 改各页面 URL（对照表）：
   | 改前 | 改后 |
   |---|---|
   | `/violations/list` | `/violations` |
   | `/violations/detail?id=` | `/violations` 后在前端筛选（或我加 `/violations/{id}`）|
   | `/appeals/list` | `/appeals` |
   | `/appeals/submit` | `/appeals`（POST）|
   | `/appeals/statistics/summary` | `/stats` |
   | `/statistics/overview` | `/stats` |

### 阶段三：补业务能力（与我的后端对齐）
9. 新增**绑定车辆**流程（我的后端要求先绑定车牌才能查"我的违规"）
   —— 这是小程序能收到通知的前提，Trae 的版本**没有这个页面**
10. 新增**通知中心**页面（`GET /notifications`）
11. 补真实图标（或用纯文字 tabBar）

---

## 七、设计建议（供你决策）

### 建议 1：**只保留一套，删掉另外两套**
三套并存是最大隐患（改一处不知道改哪套）。建议**以 `src/` 为主体**（它页面最全、有真接口调用），
删除根 `pages/` 与 `miniprogram/`（Taro 残留）。

### 建议 2：**页面按"车主旅程"重组，而不是按"功能"堆**
你的定位是「收通知 + 申诉」，建议 4 个 tab：
```
首页       我的车辆状态卡片 + 最近违规 + 未读通知红点
违规      我的违规列表（带证据图缩略图）→ 详情
申诉      我要申诉（选违规 → 填理由 → 传图）+ 我的申诉进度
我的      绑定/解绑车辆 · 通知设置 · 关于
```
**Trae 版本的问题**：把"市民举报（submit）"和"车主申诉（appeal）"混在一起，
两者用户旅程完全不同，混放会让车主困惑。

### 建议 3：**绑定车辆这一步必须显式设计**
我的后端 `GET /api/wx/violations` 是**按绑定车牌**匹配的。
如果小程序不做"绑定车辆"，**车主永远看不到自己的违规**。
建议做成**引导流程**：首次进入 → 绑定车牌（支持输入车牌 + 车架号后 6 位双重校验）。

### 建议 4：**通知要有"红点 + 列表 + 详情"三层**
微信订阅消息是"一次性"的（用户每次授权只能收 1 条），
所以**站内通知列表才是主渠道**，订阅消息只做提醒。我的后端已按此设计（`wx_notifications` 表）。

### 建议 5：**先做"演示可用"而不是"功能齐全"**
演示时最需要的是：登录 → 绑定车牌 → 看到违规（带证据图）→ 提交申诉 → 看到状态变化。
建议优先这 5 步的闭环，其余（统计图表、市民举报）后置。

---

## 八、可复现的核查命令

```powershell
# 1) 页面声明 vs 实际文件
Get-Content E:\output\1\wechat-miniprogram\app.json | Select-String pagePath

# 2) 真源码根的配置
Select-String -Path E:\output\1\wechat-miniprogram\project.config.json -Pattern 'SrcMiniprogramRoot|appid'

# 3) 后端实际提供的接口
curl http://127.0.0.1:8001/openapi.json   # 搜 "/wx"

# 4) 小程序调用的接口
Select-String -Path E:\output\1\wechat-miniprogram\src\**\*.js -Pattern "request\("
```

---

## 九、阶段一修复记录（2026-10-03，DSH 执行）

### 新增文件（补齐编译必需项）
| 文件 | 大小 | 说明 |
|---|---|---|
| `src/app.json` | 894 B | **只注册实际存在的 6 个页面**；tabBar 改为**纯文字**（避开占位符图标）|
| `src/app.wxss` | 2643 B | 全局样式，沿用项目设计语言（智瞳蓝 `#1D4ED8`）|
| `src/sitemap.json` | 210 B | 微信索引配置 |
| `src/utils/api.js` | 4874 B | 从根 `utils/` 复制（页面 `require('../../utils/api.js')` 需要）|
| `src/utils/format.js` | 2104 B | 同上 |
| `src/pages/*/*.json` ×6 | ~105 B | 每个页面补 `usingComponents` + 标题 |

### 修改文件
| 文件 | 改动 |
|---|---|
| `src/app.js` | ① 端口 `8000` → `8001` ② 前缀 → `/api/wx` ③ **补 `baseUrl` 字段**（原只有 `apiBaseUrl`，而 `utils/api.js` 读 `baseUrl`，不一致会让 URL 变成 `undefined/api/...`）④ 登录路径 `/wechat/code2session` → `/login` ⑤ 鉴权头 `Authorization: Bearer` → **`X-Openid`** ⑥ 冷启动用 `wx.getStorageSync('openid')` 兜底 |

### 验证结果（静态检查脚本 `_scripts/_miniapp_compile_check.py`）
```
app.json 声明 6 个页面
[PASS] 6 个页面 4 文件齐全
[PASS] tabBar 4 个 pagePath 全部存在
[PASS] 所有相对引用均可解析
[PASS] globalData 键一致（api.js 读的 baseUrl 已定义）
总体: 静态检查全部通过 ✅
```

> **说明**：本脚本模拟微信编译器的关键检查项（页面完整性 / tabBar 一致性 /
> 引用可解析 / globalData 一致性）。**它的通过不等同于真机编译通过** ——
> 最终仍需在微信开发者工具里打开验证（三级证据）。

---

## 十、阶段二：连通后端（**已完成** 2026-10-03）

### 采用策略：**后端适配前端**，而不是改 6 个页面
原计划改页面 URL，但页面里有字段映射逻辑（`by_status`、`items`、分页等），
逐个改风险高。改为**在后端增加兼容别名**，让 Trae 的页面**一行不改**即可连通。

### 新增后端接口（`/api/wx`）
| 接口 | 用途 | 备注 |
|---|---|---|
| `GET /overview` | 首页看板（按绑定车辆聚合）| 字段名对齐小程序既有代码 |
| `GET /violations/list` | 违规列表兼容别名 | **必须定义在 `/violations/{id}` 之前**，否则被参数路由吃掉 → 422 |
| `GET /violations/{id}` | 违规详情 | 含证据图/视频路径 |
| `GET /statistics/overview` | 看板兼容别名 | 页面 `index.js` 调的就是这个 |
| `GET /appeals/list` | 申诉列表别名 | |
| `GET /appeals/statistics/summary` | 申诉统计别名 | |
| `GET /bind/status` | 绑定状态 + **可绑定车牌建议** | 从近期违规记录提取车牌，演示时可直接点选 |
| `POST /vehicles/bind-by-suggest` | **一键绑定**识别到过的车牌 | 校验"该车牌必须在违规记录里出现过"，防随意绑定他人车牌 |

### 回归验证（9/9 PASS）
```
[PASS] /api/wx/statistics/overview            data 键=total,today,pending,confirmed,unread,bound_plates
[PASS] /api/wx/violations/list?page_size=5    data=数组(5) total=5
[PASS] /api/wx/violations/list?page=1&...     data=数组(5) total=5
[PASS] /api/wx/violations/list                data=数组(5) total=5
[PASS] /api/wx/appeals/list                   data=数组(0)
[PASS] /api/wx/appeals/statistics/summary     data 键=total,pending,accepted,rejected,by_status
[PASS] /api/wx/bind/status                    data 键=has_binding,my_vehicles,suggest_plates
[PASS] /api/wx/notifications                  data=数组(0)
[PASS] /api/wx/overview                       data 键=total,today,pending,confirmed,unread,bound_plates
```

### 一键绑定实测
```
GET /bind/status → has_binding=False  建议车牌 12 个（沪1X1111 出现5次 / 陕A721U8 4次 ...）
POST /vehicles/bind-by-suggest?plate_number=沪1X1111 → {"ok":true,"plate_number":"沪1X1111"}
GET /overview → total=5 pending=5 bound_plates=['沪1X1111']
GET /violations/69 → plate=沪1X1111 img=realtime_illegal_parking_20261003_044033.jpg
```

### 剩余（阶段四）
| # | 事项 | 说明 |
|---|---|---|
| 1 | **真机编译验证** | **必须在微信开发者工具里打开**（静态检查通过 ≠ 真机通过）|
| 2 | AppID | `project.config.json` 仍是 `"wxtodo"`，需替换为真实 AppID |
| 3 | 后端地址 | 真机预览需把 `127.0.0.1` 改为电脑局域网 IP，并勾选"不校验合法域名" |
| 4 | 图标 | 当前 tabBar 用纯文字（已避开占位符图标问题）|
| 5 | 清理另两套遗留代码 | 根 `pages/` 与 `miniprogram/`（Taro 残留）—— **建议先备份再删** |
| 6 | 违规列表页接上"通知"入口 | 可在 `violation/list` 页加未读红点 |

---

## 十一、阶段三：补页面（**已完成** 2026-10-03）

### 新增 2 个页面（各 4 文件）

| 页面 | 路径 | 作用 |
|---|---|---|
| **车辆绑定** | `pages/my/bind` | **必做**：后端按绑定车牌匹配违规，不绑定则永远看不到违规 |
| **通知中心** | `pages/notifications/index` | 站内通知列表（订阅消息是一次性的，列表才是主渠道）|

### 绑定页交互设计
```
① 说明卡片      为什么必须绑定（收通知 + 查违规 + 申诉）
② 我的车辆      已绑定列表 + 解绑（二次确认弹窗）
③ 建议车牌      来自 /bind/status，数据源是"系统识别到过的车牌"
                —— 演示时直接点选，避免手输出错
④ 手动输入      真实场景车主自己输车牌（不校验是否在系统记录中）
⑤ 下一步引导    已绑定时提示去查看违规/申诉
```

### 顺带修复：`my/index` 菜单指向 2 个不存在的页面
```javascript
// 修前（点击必然报错）
{ title: '设备绑定', path: '/pages/my/devices'    }   // 不存在
{ title: '设置',     path: '/pages/my/settings'   }   // 不存在
// 修后
{ title: '车辆绑定', path: '/pages/my/bind' }              // 新建
{ title: '通知中心', path: '/pages/notifications/index' }  // 新建
{ title: '我的申诉', path: '/pages/appeal/list' }
```
并新增 `loadBindInfo()`：显示车辆数与未读通知数。

### 验证结果

**静态检查（8 页面）**
```
app.json 声明 8 个页面
[PASS] 8 个页面 4 文件齐全
[PASS] tabBar 4 个 pagePath 全部存在
[PASS] 所有相对引用均可解析
[PASS] globalData 键一致
总体: 静态检查全部通过 ✅
```

**导航可达性（新增检查）**
```
[PASS] index/index.js        -> /pages/violation/list
[PASS] my/bind.js            -> /pages/appeal/list
[PASS] notifications/index.js-> /pages/my/bind
[PASS] violation/detail.js   -> /pages/my/index
导航路径总体: 全部可达 ✅
```

**两个新页面的数据流（端到端）**
```
【bind】1. /bind/status   has_binding=False 建议=12
        2. 点建议车牌     绑定成功
        3. 刷新           has_binding=True my=['沪1X1111']
        4. 绑不存在车牌    HTTP 400 安全校验生效
        5. 手动绑定        HTTP 200
        6. 解绑            deleted=1
【notifications】1. 首次查询 0 条
        2. 触发通知       sent=3
        3. 再查           1 条，未读 1 条
        4. 标记已读       updated=1
        5. 只看未读       0 条
        6. 全部已读       updated=1
        7. 确认清零       0 条
        8. /overview unread=0 前后端一致
```
