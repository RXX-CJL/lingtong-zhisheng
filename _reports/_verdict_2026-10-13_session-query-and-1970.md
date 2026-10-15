# 跨会话检索修复 + 1970 脏数据复核 — 结论报告

> **日期**：2026-10-13（第二轮）｜**执行**：DSH｜**用户决策**：重启 Desktop、批准改 patch、确认不回填
> **证据等级**：一级（命令结果）+ 三级（真实调用成功 / 用户可观察）

---

## 一、跨会话检索：❌ → ✅

| 阶段 | 结果 |
|---|---|
| 修复前 | 工具 `session_search` **已注册**（`cordis_inspect` 工具表可见），但调用返回 `SESSION_QUERY_SEARCH_DISABLED`（*configures the session-query index with `openAt "never"`*） |
| 根因 | `<profile>\cordis.yml` **只有 4 行**（空数组 + "别改这个文件"的注释），配置由 bundle 组合；上游默认 `path: ':memory:'` + `openAt: never`（见 `cordis.yml.bak-before-session-query:89-93`） |
| 修复 | `cordis.patch.yml` 末尾新增 `- id: session-query-sqlite` 覆盖项：`path: !!js dshHomePath('session-query-index.sqlite')` + `openAt: first-search` |
| 修复后 | 用户重启 Desktop → 实测 `{"ok": true, "mode": "sessions", "returned": 3, "hasMore": true}`，命中 3 个不同历史会话 |

**被推翻的旧结论**：

1. ~~"`openAt` 已改为 `first-search`"~~ —— **假的**。`cordis.patch.yml:77` 那句只是**注释**，patch 里根本没有该覆盖项，改动从未落盘。上一轮据此宣称"等重启即可"，实际白等一轮。
2. ~~"改 `cordis.yml` 就能生效"~~ —— 该文件现在是空壳，**patch 才是覆盖点**。
3. ~~"`vision_describe` 是我的视觉工具"~~ —— 工具表里**没有**这个名字；视觉走 `read_image`。能力正常，名字要改。

---

## 二、1970 脏数据：复核确认 566，且**不建议回填**

脚本：`E:\output\_scripts\audit_1970.py`（`mode=ro` 只读打开，物理上无法写入）
DB：`E:\output\1\api\zhitong_violations.db`（28.83 MB）

| 项 | 实测 |
|---|---|
| `traffic_events` 总行数 | **3209** |
| `trigger_time` 年份 | 2026: **2642** / **1970: 566（17.6%）** / NULL: 1 |
| 脏数据 id 区间 | **2338 – 3013**（created_at 2026-10-05 16:13 ~ 2026-10-10 15:57）= **封闭区间** |
| 脏数据之后新增的 1970 行 | **0** ⇒ 新增写入路径**确已修好** |
| 最新 8 条（id 3202–3209） | `trigger_time` 全是正确墙钟 |
| `created_at` 中的 1970 | 0 |
| 成因验证 | id 2338 = `1970-01-01 08:00:10.85` —— `1970-01-01 08:00:00` 本地 = epoch 0，`+10.85s` 正是**视频第 10.85 秒**，与 T93 根因完全吻合 |

**⚠ 另发现一处文档与实际的矛盾**：`traffic_events` **没有 `wall_time` 列**（实际列见 §26.9.3），而 `_PROJECT_MAP.md` T93 与手册 §26.7 都写"事件新增 `wall_time` 字段并落库用它"。**修的实际是别处**，这句话需要核实后更正（可能落在 `vehicle_info` / `scene_context` 两个 JSON 列里）。

**决策**：**不回填**。用户 2026-10-11 已拍板（"这个问题其实不大，很多事件是没用的……不要为此投入时间"），2026-10-13 再次确认"先不用动"。脏数据封闭、新数据正确，回填收益低且属改历史数据。

---

## 三、顺带修复的两份文档

- `E:\output\_DSH_OFFICE_STATE.md`：§1 / §2 / §3 **按实测值重写**（原"旧数字作废"警告已删）；新增 **§26.9**；§26.8.1 的假结论已就地标注更正。
- 工作区记忆 `dsh-session-recall` 已更正（原先记着"已改 first-search"）。

---

## 四、下一步（待用户定）

| # | 事项 | 卡点 |
|---|---|---|
| 1 | 「每日开工巡检」定时任务现挂在**旧会话** `session-22c9f27b`，不在当前会话 | 需用户决定：保留 / 改挂当前会话 / 删除 |
| 2 | 核实 `wall_time` 说法（T93） | 需追代码 `traffic_event_engine.py` |
| 3 | `created_at` 用 UTC 而 `trigger_time` 用本地，同屏差 8 小时 | 独立小问题，未修 |
