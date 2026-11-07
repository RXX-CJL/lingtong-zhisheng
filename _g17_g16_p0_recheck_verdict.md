# 智瞳灵声 · 2026-11-01 本轮结论（P0 现状核实 + G17/G16 修复）

> 结论报告。**含「被推翻的旧结论」一节**（项目交接规范 v1.3）。
> 本轮性质：只读核实 + 两个已登记 bug 的修复。未起后端、未跑云端、未改业务逻辑。

---

## 一、P0 三项现状（实测，不照抄 9 月简报）

| 项 | 9 月简报说 | 今天实测 | 证据等级 |
|---|---|---|---|
| **P0-1** B1/B2 参数错位 | 3 参调 2 参 / 参数语义错位 | **代码已对齐** | [一] 签名 bind 实测 |
| **P0-2** 12 处明文密钥 | 12 处 + 无 .gitignore | **被 git 跟踪的文件里 0 处** | [一] git grep HEAD |
| **P0-3** event_videos 无产出 | 从未产出过 | **有产出**：10-23 当天 39 事件 / 39 视频 | [一] DB 按天统计 |

### P0-1 细节
```
analyze_with_claude(image_input, violation_type, context_prompt='')     ← 已支持 3 参
analyze_with_deepseek_judge(violation_type, yolo_result_dict, doubao_result_dict)  ← 已按 dict 收
inspect.signature().bind() 四种调用全部 OK
cloud_collaborator.py:1063-1097 注释明确写「修复 B2」
```
**但「签名对」≠「链路通」**：见下节。

### P0-2 细节（重要区分）
- 被 git 跟踪的文件：**0 处**（`git grep -I -E 'sk-[A-Za-z0-9]{20,}' HEAD` → 空）
- `beforeness/` 三文件：`API_KEY = ""`（空串）+ 读环境变量，**不是明文**
- 仍有真值的地方：`api/.env`（2 条）、`api/config_runtime.json`（2 条）——
  **两者都已被 `.gitignore` 正确排除**（`git check-ignore` 实测带出 `1/.gitignore:59/60`）
- **但 git 历史里有**：`git log -S'sk-'` 命中 2 个提交（`5bac816`、`da9dd6e`）
- ⚠️ 仓库**当前私有**（用户 2026-11-01 确认）→ 历史留密钥**不构成泄露**，本轮**未做历史重写**。
  若将来转公开，需 `filter-repo` 或迁仓 —— 这是唯一待办。

### P0-3 细节 + **本轮最重要的发现**
```
traffic_events: 3248 行
日期        事件 云端真结果  视频
2026-10-04  1101   1064    1098
2026-10-05   116    116      94
2026-10-06    50     49      50
2026-10-09     7      3       6
2026-10-10   102      3      98
2026-10-11   193      6     172
2026-10-23    39      0      39   ← 云端仲裁归零
```
**真因不是 B1/B2，是 `cloud_review: false`**（`api/output/runtime_settings.json` 实测）。
最近一条真结果 id=3206（10-11 16:05），`final.method=local_fallback`。

---

## 二、本轮修复（G17 / G16）

### G17 违规列表「设备位置」显示 x:undefined
- 位置：`web-admin/src/views/ViolationList.vue:337`
- **数据证据**：`violation_evidences` 抽样 500 条，**500/500 全是 `{bbox, center_x, center_y}`**，
  没有一条带 `x/y` → `pos.x` 必然 undefined
- 修法：复用后端 `routers/realtime.py:637 _by_point` 的既有兼容顺序
  （`x/y` → `center_x/center_y` → `cx/cy` → `point_x/point_y` → bbox 中心），**不另起一套口径**
- **验收 [三]**：真实 Edge 浏览器 + 真实 DB 样本注入
  ```
  表头命中「设备位置」列 index=6
  单元格: ["x:1070, y:455", "x:1040, y:347", "x:1015, y:254"]
  undefined=false  xNy=true  →  PASS
  ```

### G16 Statistics.vue 三处 echarts.init 未传主题
- 位置：`web-admin/src/views/Statistics.vue:181/184/187`（原）
- 修法：与 `Dashboard.vue:458/493/512` 完全一致的写法（`registerZtTheme(echarts)` + 传 `ZT_THEME_NAME`）
- **验收 [三]**：像素级比对
  ```
  柱状图主色 209,67,67  = #D14343  ← ZT_THEME 第 1 色
  环形图主色 237,125,49 = #ED7D31  ← ZT_THEME 第 2 色
  命中 ZT_THEME 色板: true | 命中 echarts 默认色板: false
  ```
  对照：echarts 默认首色是 `#5470c6`（84,112,198），**未出现**。

### 构建验收 [一]
```
✓ 2256 modules transformed.
✓ built in 6.58s
ViolationList-CBpPTVfO.js  10.60 kB
```

---

## 三、被推翻的旧结论（务必不要再犯）

1. **❌「P0-1 修好 = 事件闭环就能跑」**
   → 错。签名对齐只证明**不崩**。云端真因是 `cloud_review=false`，与 B1/B2 无关。
   **验证法：看 `traffic_events.ai_judgment` 有没有非空真结果，不看代码。**

2. **❌「拿 git status 的 M 就当成本轮改的」**
   → 我自己差点犯。`git status` 显示 4 个 M，实际只有 2 个是本轮（`Statistics`/`ViolationList`，
   备份 `.bak_20261101`）；`Dashboard`/`EventDetail` 是 10-23 那轮（备份 `.bak_20261023`，mtime 10-23）。
   **验证法：比对 `.bak_<日期>` 后缀 + mtime，不用 git status 单独判。**

3. **❌「表头取到了 = 表格渲染成功」**
   → 三次假阴性。第一次 `**/*` 拦了模块请求、第二次 `**/api/**` 拦了 `/src/api/index.js`。
   **验证法：Playwright 拦截必须按 `new URL(u).pathname.startsWith('/api/')` 判，不用 glob。**

---

## 四、本轮遗留（诚实交代）

| 项 | 状态 | 原因 |
|---|---|---|
| **A 云端闭环真跑** | **阻塞** | 用户明确：**豆包没额度了，未接新 API**。没有额度跑一定失败，**不拿 mock 冒充真跑** |
| B git 历史密钥 | 不处理 | 仓库私有 → 不构成泄露。仅记录，转公开前需处理 |
| `Statistics` 第三个图（每日趋势） | 显示 No Data | 我注入的假数据字段名与组件期望不匹配，**不是主题问题**；真后端起来后由真数据决定 |
| 后端 8001 / CARLA 2000 | 未启动 | 本轮只需前端验证；未擅自起长跑服务 |

---

## 五、复现命令（全部可重跑）

```bash
# 1. 数据形态核查（证明 pos.x 必然 undefined）
cd E:/output/1/api && python -c "
import sqlite3, json
from collections import Counter
c=sqlite3.connect('zhitong_violations.db'); cur=c.cursor()
rows=cur.execute(\"SELECT position FROM violation_evidences WHERE position NOT IN ('','{}') ORDER BY id DESC LIMIT 500\").fetchall()
print(Counter(tuple(sorted(json.loads(p).keys())) for (p,) in rows))"

# 2. 构建
cd E:/output/1/web-admin && npm run build

# 3. G17 真实浏览器验证（需先 npm run dev）
cd E:/output/_uicheck && node verify_g17d.mjs

# 4. 回滚（任意时刻）
cd E:/output/1/web-admin/src/views
cp ViolationList.vue.bak_20261101 ViolationList.vue
cp Statistics.vue.bak_20261101 Statistics.vue
```

---

## 六、改动文件清单

| 文件 | 备份 | 改了什么 |
|---|---|---|
| `1/web-admin/src/views/ViolationList.vue` | `.bak_20261101` | 337 行位置解析：读 center_x/center_y + bbox 兜底 |
| `1/web-admin/src/views/Statistics.vue` | `.bak_20261101` | 81 行 import 主题；181 行 registerZtTheme；183/186/189 传 ZT_THEME_NAME |
| `_uicheck/verify_g17d.mjs` | — | 新增验证脚本（可复跑） |

**未改动**：任何后端代码、任何配置、任何数据、任何其他前端文件。
