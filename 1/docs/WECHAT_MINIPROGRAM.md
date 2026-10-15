# 微信小程序设计（车主端：通知 + 申诉）

> 2026-10-03 由 DSH 编写。本文档说明小程序的**定位、后端地基、接口契约**与**待办**。
> 后端服务层与接口**已实现并验证**（见 §5），**只差 AppID/Secret 与前端页面**。

---

## 一、定位澄清（重要）

项目里**已有两套"微信"相关代码**，用途不同，不要混淆：

| 模块 | 视角 | 用途 | 状态 |
|---|---|---|---|
| `routers/wechat.py` | **市民** | 市民随手拍举报违规 | 已有骨架，但 `verify_wechat_user` 是**假实现** |
| `wechat_miniapp.py` + `routers/wx_miniapp.py` | **车主** | 收到"我的车违规了"通知 + 提交申诉 | **本次新建，已验证** |

**你的需求（收通知 + 申诉）属于第二套**。第一套可保留作为"市民举报"扩展功能。

---

## 二、原状盘点：小程序落地的三个地基缺口

| # | 缺口 | 证据 | 影响 |
|---|---|---|---|
| 1 | **微信登录是假的** | `routers/wechat.py:16` `verify_wechat_user` 只判断 `len(openid) > 10` | 任何人都能伪造 openid |
| 2 | **没有"用户↔车辆"关系** | 数据库 8 张表里无任何绑定表 | **车主无从知道"哪条违规是我的"** |
| 3 | **违规记录无车牌、申诉无处存** | `violation_evidences` 无 plate 字段；申诉塞在 `system_configs` 的 `appeal:violation:{id}` JSON | 无法按用户查询、无法统计 |

**结论**：小程序不是"写几个页面"就行，**必须先把这三件事补上**。本次已完成。

---

## 三、新增数据模型（4 张表，独立于既有表）

```sql
wx_users               -- 微信用户
  id, openid(唯一), unionid, nickname, avatar, phone, session_key,
  created_at, last_login

wx_vehicle_bindings    -- 用户↔车辆绑定
  id, openid, plate_number, vin_tail, relation, verified,
  created_at, UNIQUE(openid, plate_number)
  INDEX(plate_number)             -- 按车牌反查车主

wx_notifications       -- 站内通知（订阅消息的落地副本）
  id, openid, kind, title, body, plate_number, violation_id, event_id,
  payload, is_read, pushed, push_result, created_at
  INDEX(openid, is_read)

wx_appeals             -- 申诉（替代原来的 system_configs JSON 方案）
  id, openid, violation_id, event_id, plate_number, reason, description,
  evidence_urls, status(pending/accepted/rejected), reviewer, review_note,
  reviewed_at, created_at
  INDEX(openid, status), INDEX(violation_id)
```

---

## 四、接口契约（前缀 `/api/wx`）

鉴权：所有需登录接口携带请求头 **`X-Openid`**。

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/login` | `{code}` -> `{openid, dev_mode}` |
| GET | `/profile` | 用户信息 + 绑定车辆 + 未读数 |
| GET | `/vehicles` | 我的车辆列表 |
| POST | `/vehicles/bind` | `{plate_number, vin_tail?, relation?}` |
| POST | `/vehicles/unbind` | `{plate_number}` |
| GET | `/violations` | **我的违规**（按绑定车牌匹配）|
| GET | `/notifications` | 通知列表（`only_unread`）|
| POST | `/notifications/read` | `{notification_id?}` 或 `{all_read:true}` |
| POST | `/appeals` | 提交申诉（**校验违规属于本人车辆**）|
| GET | `/appeals` | 我的申诉列表 |
| POST | `/appeals/review` | 管理端审核（accepted/rejected）|
| GET | `/stats` | 统计（管理端）|
| POST | `/notify-test` | 给绑定某车牌的用户发通知（联调/演示用）|

### 小程序端最小流程
```
1. wx.login()                    -> code
2. POST /api/wx/login {code}     -> openid（存 storage）
3. POST /api/wx/vehicles/bind    -> 绑定车牌（首次）
4. GET  /api/wx/violations       -> 我的违规列表
5. GET  /api/wx/notifications    -> 通知
6. POST /api/wx/appeals          -> 申诉
```

---

## 五、已实现并验证（2026-10-03）

```
POST /api/wx/login            HTTP 200  openid=dev_33dde5b2...  dev_mode=true
POST /api/wx/vehicles/bind    HTTP 200  {"ok":true,"plate_number":"苏W125K6"}
GET  /api/wx/vehicles         HTTP 200  [{"plate_number":"苏W125K6","vin_tail":"123456",...}]
GET  /api/wx/violations       HTTP 200  total=0  bound=['苏W125K6']
GET  /api/wx/profile          HTTP 200  vehicles + unread
GET  /api/wx/vehicles (无头)   HTTP 401  ✅ 鉴权生效
GET  /api/wx/stats            HTTP 200  users=2 bindings=2 configured=false dev_mode=true
```

**登录实现要点**：真实调用 `https://api.weixin.qq.com/sns/jscode2session`；
未配置 `WX_APPID/WX_SECRET` 时进入**开发模式**（openid 由 code 派生，稳定可复现），
并**显式返回 `dev_mode: true`** —— 避免"以为在跑真登录"。

---

## 六、待办（按优先级）

| # | 事项 | 依赖 | 说明 |
|---|---|---|---|
| **P0** | **给违规记录补车牌** | 无 | `violation_evidences.additional_info` 里写 `plate_number`，`traffic_events.vehicle_info` 写 `plate`。**这是"我的违规"能匹配的前提** —— 当前实测匹配 0 条，就是因为记录里没车牌（车牌识别模块已就绪，只是没落库）|
| **P0** | **配置 AppID/Secret** | **需要你** | 在 `.env` 加 `WX_APPID` / `WX_SECRET`，重启后端即生效 |
| P1 | 订阅消息模板 | 需要你 | 微信公众平台申请"违规通知"模板，把模板 id 填到 `WX_TMPL_VIOLATION` |
| P1 | 小程序前端页面 | AppID | 违规列表 / 详情 / 申诉表单 / 通知中心 |
| P2 | 违规发生时自动通知 | P0 | 在证据落盘处按车牌反查绑定用户并 `create_notification` |
| P2 | 管理员审核页 | 无 | 可先复用 `/api/wx/appeals/review` |
| P2 | 服务器域名 + HTTPS | 需要你 | 微信要求 request 域名必须 HTTPS 且备案 |

---

## 七、给用户的行动清单（我需要你做的）

1. **注册小程序** → [mp.weixin.qq.com](https://mp.weixin.qq.com) → 拿 **AppID + AppSecret**
2. 把这两个值给我（或你自己写进 `E:\output\1\api\.env`）：
   ```
   WX_APPID=wx................
   WX_SECRET=..................
   ```
3. （可选）申请订阅消息模板，把模板 id 给我填 `WX_TMPL_VIOLATION`
4. （上线前）准备 HTTPS 域名 + 备案

**没有 AppID 也能继续的**：P0 的"给违规补车牌"、P2 的管理员审核页、小程序页面骨架。
