# 管理端 UI 优化 · 评估结论与交接（_ui_optimization_verdict.md）

> 生成日期：**2026-10-23** ｜ 执行：DSH（Team Lead）
> 状态：**评估完成，代码未改动**（等你拍板后由新会话实施）
> 证据等级：**三级**（真实浏览器截图 + 代码静态定位 + 三模型独立设计评审）

---

## 〇、给下一个会话的 5 分钟速览

**你要做三件事**：
1. 读本文 §三「待拍板三件事」，确认用户已选定的方案（A/B/C + 配色基线）
2. 按 §四「实施清单」改 **3 个文件**（1 个必改根因 + 1 个图表重写 + 1 个清理）
3. 改完必须**重新截图 + 读图自证**（命令见 §五），不能只看编译通过

**三个关键路径**：
- 前端根目录：`E:\output\1\web-admin`
- 出问题的页：`src/views/Dashboard.vue`
- 中文映射根因：`src/utils/format.js`

**不要做的事**：不要再去调 `avoidLabelOverlap` 试图救环形图——三个模型独立得出同一结论：**7 分类塞进 400×250 的环形是几何必然重叠，调参救不回来，必须换图型**。

---

## 一、问题诊断（全部为三级证据）

### 1.1 取证方式（可复现）

```powershell
# 前端 5173 / 后端 8001 均在运行
agent-browser open http://127.0.0.1:5173
agent-browser wait --load networkidle
Start-Sleep -Seconds 3
agent-browser screenshot dash.png
```

截图存于 `E:\output\dash.png`（1258×622）。

### 1.2 实测到的 4 个问题（比用户描述更严重）

| # | 现象 | 根因（含文件行号） |
|---|---|---|
| 1 | 外部标签互相重叠：「超速 / ing_yellow / 未戴头盔」三个标签压在一起 | `Dashboard.vue:348` `avoidLabelOverlap: false` |
| 2 | 图例 7 项折成两行挤占底部，环形被裁切 | `Dashboard.vue:344` `legend:{bottom:0}` + 容器仅 250px（`:455`） |
| 3 | 图例显示 `running_yellow`（英文），切片标签被截断成 `ing_yellow` | `utils/format.js:1-8` `TYPE_MAP` 缺该类 → `getTypeName` 回退返回英文原值 |
| 4 | 设备违规排行 TOP10 **完全空白**，只剩一条 x 轴线 | 后端**从不返回** `by_device`（见 1.3） |

### 1.3 设备违规排行：为何是空白的（已闭环验证）

- 全项目 grep `by_device`：**仅 1 处命中**，且是前端自己读 `Dashboard.vue:326` 的 `stats.value.by_device || []` 兜底
- `api/routers/statistics.py:93-100` 的返回体只有 `total / today / week / month / by_type / by_status`，**无 by_device**
- 结论：这不是 bug，而是**一个从未有数据源的空壳卡片**

### 1.4 中文名不统一的真正根因：**5 套映射表各自为政**

| 来源 | 覆盖类型数 | 是否含 running_yellow |
|---|---|---|
| `web-admin/src/utils/format.js:1-8` `TYPE_MAP` | **6** | ❌ 缺 ← **根因** |
| `api/behavior_engine.py:50-59` `BEHAVIOR_TYPE_CN` | 8 | ✅ |
| `api/rule_engine/plugins/traffic_plugin.py:41-52` `TRAFFIC_TYPE_CN` | 9 | ✅ |
| `web-admin/src/views/EventDetail.vue:612` `EXTRA_TYPE_CN` | 局部补丁 | ✅ |
| `api/rule_engine/plugins/urban_management_plugin.py:289` 内联 | `street_stall` 疑似占道经营 | — |
| `api/rule_engine/plugins/public_security_plugin.py:284` 内联 | `crowd_gathering` 人员聚集 | — |

**后端实际可产出的类型全集（10 类）**：
`red_light` 闯红灯 · `wrong_way` 逆行 · `illegal_parking` 违规停车 · `lane_departure` 压线行驶 · `speeding` 超速 · `running_yellow` 抢黄灯 · `illegal_turn` 违规掉头 · `pedestrian_crossing` 未礼让行人 · `street_stall` 疑似占道经营 · `crowd_gathering` 人员聚集
（另有 `no_helmet` 未戴头盔，仅 traffic_plugin 有）

**前端 `TYPE_MAP` 只有 6 类，缺 5 类** → 任何落在缺口里的类型都会在界面上显示成英文原值。

> 📌 历史教训：`docs/REPORT_TASK-COORD-006A_DSH.md:419` **早就预警过**这个问题，但当时只在 `EventDetail.vue` 打了局部补丁，**没修根因 `format.js`**。本次必须修根因。

---

## 二、三模型独立设计评审（交叉验证）

### 2.1 评审方式

| 通道 | 模型 | 耗时 | 退出码 | 结果文件 |
|---|---|---|---|---|
| Codex CLI | **gpt-5.6-luna** | ~6 min | 0 | `_codex_review.txt` |
| Qoder CN CLI | **Qwen3.8-Max** | 319.7s | 0 | `_qoder_review.txt` |
| CodeBuddy CLI | **glm-5.1** | 339.3s | 0 | `_codebuddy_review.txt` |
| 本地设计库 | `ui-ux-pro-max` `charts.csv` | 即时 | — | 规则 No.3 Part-to-Whole |

**三模型结论高度一致，且各自补充了不同的落地细节。** 这是本次选型判断的可靠性来源——不是单一模型的意见。

### 2.2 三模型一致同意的结论

| 议题 | Codex (gpt-5.6-luna) | Qoder (Qwen3.8-Max) | CodeBuddy (glm-5.1) | 一致 |
|---|---|---|---|---|
| 环形图该不该保留 | **换成横向条形** | **换成横向条形** | **换成横向条形** | ✅ 三方一致 |
| 为何不用 100% 堆叠条 | 小类被压进同一条仍难读 | 7 段中非首尾无零基线，人眼无法比大小 | 尾部类目仅 10-27px，放不下"3%"三字 | ✅ 三方一致 |
| 图例怎么办 | 删除（类目已在 Y 轴） | 完全删除 | 删除，y 轴即图例 | ✅ 三方一致 |
| 排序 | 降序，最高在最上 | 降序 + `inverse:true` | 降序（注意：ECharts y 轴自下而上） | ✅ 三方一致 |
| 条尾标什么 | 百分比 | 百分比 | 百分比（计数进 tooltip） | ✅ 三方一致 |
| `running_yellow` 性质 | 数据层映射缺失，非图表问题 | 数据层 i18n 缺陷，别用图表配置盖 | 类目字典单一来源 + 兜底 | ✅ 三方一致 |
| 配色是否 7 彩 | 7 色固定映射（语义） | **建议单色渐变**（超 5-6 色上限） | **建议统一单色**（禁止 7 彩条） | ⚠ 有分歧 |

### 2.3 关键分歧：条形图要不要 7 种颜色

- **Codex**：给 7 色语义映射（红=闯红灯、琥珀=抢黄灯…）
- **Qoder / CodeBuddy**：**强烈建议单色**，理由：类目名已在 Y 轴 + 条尾已有百分比，**颜色是冗余编码**，且 7 色超出设计库 5-6 色上限
- **裁决建议**：**采用单色（推荐 Qoder 的"深→浅渐变"表达排名）**，仅把「闯红灯」用 `#D14343` 高亮。
  - 理由：条形图本身就编码了大小，再上 7 色会造成"颜色竞争注意力"
  - 但**保留 7 色语义表**（见 §2.4）供 `el-tag`、表格、环形降级方案复用

### 2.4 七类语义色（三模型建议的综合，供 tag / 表格复用）

| 类型 | 色值 | 语义 |
|---|---|---|
| 闯红灯 | `#D14343` | 信号红，全站唯一正红 |
| 超速 | `#ED7D31` | 警示橙，动态高危 |
| 抢黄灯 | `#F2C14E` | 黄灯语义 |
| 逆行 | `#9B5DE5` | 紫，严重但与暖色区分 |
| 未戴头盔 | `#2E9E8F` | 青绿（慎用正绿，避免"合规"误读） |
| 违规停车 | `#5B8DB8` | 蓝灰，静态低紧急 |
| 压线行驶 | `#98A2B3` | 中性灰，轻微违法 |
| 兜底「其他」 | `#C0C4CC` | 专用灰，真实类目禁用 |

结构逻辑：**暖色 = 动态危险驾驶，冷色 = 静态/轻微违法**，颜色本身成为严重度线索。

### 2.5 三模型给出的可落地参数（已合并去重）

**横向条形图方案**（三模型参数取交集/互补）：

```js
// grid：left 需容下 4 字类目名，right 需容下百分比
grid: { left: 70, right: 55, top: 8, bottom: 8, containLabel: true }

yAxis: {
  type: 'category',
  inverse: true,              // 最大值置顶（Qoder 明确给出）
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { fontSize: 12, color: '#606266', margin: 8 }
}
xAxis: { type: 'value', show: false }   // 条尾已标值，x 轴纯冗余

series: [{
  type: 'bar',
  barWidth: 16,                          // Codex 说 12-14，CodeBuddy 说 16，取 16
  itemStyle: { borderRadius: [0, 3, 3, 0] },
  label: {
    show: true,
    position: 'right',
    distance: 6,
    fontSize: 12,
    color: '#606266',
    formatter: (p) => p.value + '%'      // 百分比；计数进 tooltip
  }
}]
// legend: 完全删除
```

**排序注意（CodeBuddy 独有提醒）**：ECharts y 类目轴**自下而上**渲染，数据按升序传入才能呈现"最大在顶"，或直接用 `inverse: true`。

**高度分配（4250 约束下）**：

| 区块 | 高度 | 依据 |
|---|---|---|
| 卡片标题 | 走 Element Plus `card header`（在 250px 之外） | Codex + Qoder 一致 |
| ECharts 画布 | 250px | — |
| grid top/bottom | 各 8px | CodeBuddy |
| 绘图净高 | ≈ 214-234px | — |
| 7 行每行 | ≈ 28-30px | Qoder 28 / CodeBuddy 30 |
| 字号纪律 | 标题 14-15/600 · 数据 12/400 · 辅助 12 灰 | 三模型一致 |

### 2.6 环形图降级方案（若用户坚持保留）

三模型都给了参数级抢救方案，**但三方都声明"仍不合规/不推荐"**：

```js
avoidLabelOverlap: true,                      // ← 首要 bug，现在是 false
labelLayout: { hideOverlap: true, moveOverlap: 'shiftY' },
label: { show: true, fontSize: 10, formatter: '{b} {d}%' },
labelLine: { length: 7, length2: 6 },
legend: { orient: 'vertical', right: 0, top: 'center' },  // 右侧纵向单列
radius: ['44%', '62%'],                       // 收外径防裁切
center: ['42%', '50%'],                       // 圆心左移给图例让位
minAngle: 6,                                  // 极小片仍可见
```

> ⚠ Codex 明确警告：`hideOverlap` 必然隐藏部分小片标签 → **仍违反"每片必须直标"规则**，只能算"能看但不合规"。

---

## 三、待用户拍板的三件事（下一个会话必须先确认）

### 决策 1：设备违规排行 TOP10 怎么处理

**背景**：该卡片**当前完全空白**（后端无 `by_device` 字段），不是故障而是从未有数据源。

| 选项 | 做法 | 代价 |
|---|---|---|
| **A（DSH 推荐）** | 换成「审核状态分布」环形图 | **零后端改动**，`by_status` 已在接口返回里 |
| B | 换成「近30天趋势」第二条折线 | 与中间卡片重复度高 |
| C | 只删不补，另两张卡改 `:span="12"` | 页面更宽松，信息密度下降 |

**推荐 A 的理由**：
1. 数据现成，零后端改动
2. 环形图适合 3 分类（待审核/已确认/已驳回）——**正好落在设计库"≤5 分类"的合规区**
3. 替换后 3 张卡片信息类型互补：**类型分布（条形）+ 时间趋势（折线）+ 状态分布（环形）**

### 决策 2：是否授权改代码

涉及 **3 个文件**，全部可回滚（改前会 `.bak_20261023` 备份）：
- `src/utils/format.js`（补全 11 类映射 — 根因）
- `src/views/Dashboard.vue`（图表重写 + 卡片替换）
- `src/views/EventDetail.vue`（删 `EXTRA_TYPE_CN` 局部补丁）

### 决策 3：配色基线

**发现的深层矛盾**：
- `src/styles/design-tokens.css` = **亮色**体系（`--zt-bg:#F6F7F9` 白卡片）
- `src/utils/echarts-theme.js` = **深色**体系（`backgroundColor:'transparent'` + 近黑 `#12151A`）
- `Dashboard.vue` **两者都没用** —— `echarts.init(el)` 未传主题参数

| 选项 | 做法 |
|---|---|
| **A（DSH 推荐）** | 统一走**亮色**，`echarts-theme.js` 改为亮色主题并在 Dashboard 注册 |
| B | 保留深色主题，另做暗色仪表盘 |

推荐 A：与现有 8 个页面的浅色硬编码一致，改造风险最低。

---

## 四、实施清单（拍板后执行）

### 4.1 必做 — 根因修复

- [ ] **F1** `src/utils/format.js`：`TYPE_MAP` 由 6 类 → **11 类**，以 `behavior_engine.py:50-59` + 两个插件为准
  - 补：`running_yellow` 抢黄灯 / `illegal_turn` 违规掉头 / `pedestrian_crossing` 未礼让行人 / `street_stall` 疑似占道经营 / `crowd_gathering` 人员聚集
  - 加**未映射兜底**：返回「未知类型」并 `console.warn`，**禁止把英文 key 透给界面**
- [ ] **F2** `src/utils/format.js`：`TYPE_COLORS` 由 6 色 → 覆盖 11 类（用 §2.4 色表）
- [ ] **F3** `src/views/EventDetail.vue:612`：删除 `EXTRA_TYPE_CN`，统一走 `getTypeName()`

### 4.2 必做 — 图表重写

- [ ] **F4** `Dashboard.vue`：违规类型分布 环形 → **横向排序条形图**（参数见 §2.5）
- [ ] **F5** `Dashboard.vue`：删除该图 `legend`，删 `avoidLabelOverlap`
- [ ] **F6** `Dashboard.vue`：容器高度 `250px → 260px`（给 7 行 * 30px 留余量）

### 4.3 按决策 1 处理排行卡

- [ ] **F7**（若选 A）`Dashboard.vue`：`barChartRef` 卡片改为「审核状态分布」环形图，数据取 `res.by_status`
- [ ] **F7'**（若选 C）`Dashboard.vue`：删除该 `el-col`，另两张改 `:span="12"`

### 4.4 按决策 3 处理配色

- [ ] **F8**（若选 A）`echarts-theme.js` 改亮色 + `Dashboard.vue` 中 `echarts.init(el, 'zt-theme')`

### 4.5 收尾

- [ ] **F9** 更新 `E:\output\_PROJECT_MAP.md`（新增/变更模块须登记）
- [ ] **F10** 更新 `E:\output\_SESSION_HANDOFF.md`

---

## 五、验收标准（三级证据，不可降级）

**不接受"编译通过"作为完成标准。**

```powershell
# 1) 重启前端（若 Vite 热更新未生效）
cd E:\output\1\web-admin && npm run dev

# 2) 重新截图
agent-browser open http://127.0.0.1:5173
agent-browser wait --load networkidle
Start-Sleep -Seconds 3
agent-browser screenshot dash_after.png

# 3) 读图自证（必须真的看图，不能只看命令成功）
```

**必须逐条核对的 5 项**：
1. ☐ 7 个中文类型名**全部**可读，无重叠、无截断
2. ☐ **无任何英文 key 外露**（grep 截图确认无 `running_yellow` / `ing_yellow`）
3. ☐ 条形图 7 行完整显示，最高项在**最上方**
4. ☐ 每根条末端有百分比标签
5. ☐ 设备排行卡按决策结果处理完毕，**无空白卡片**

**补充校验**（命令级）：
```powershell
# 确认 TYPE_MAP 覆盖 11 类
Select-String -Path 'E:\output\1\web-admin\src\utils\format.js' -Pattern 'running_yellow|illegal_turn|pedestrian_crossing|street_stall|crowd_gathering' | Measure-Object | Select-Object Count
# 期望 >= 5

# 确认无残留局部补丁
Select-String -Path 'E:\output\1\web-admin\src\views\EventDetail.vue' -Pattern 'EXTRA_TYPE_CN'
# 期望 0 命中
```

---

## 六、模型能力评估与工具选型（用户明确要求）

### 6.1 本会话模型身份

**`deepseek-v4.1-flash`**（provider: `workbuddy`）

证据：`C:\Users\ROG\.dsh\storages\session_projcache\sessions\session-c334e9de-b727-4fb8-b451-f309d21fb56b.json` 中 `"model": "deepseek-v4.1-flash"`。这是运行时写入的实际值，非自述。

### 6.2 本次实测的模型能力矩阵（含真实耗时/退出码）

| 通道 | 模型 | 本次实测 | 设计能力表现 | 成本 |
|---|---|---|---|---|
| **Codex CLI** | gpt-5.6-luna | exit 0，~6min，**主动联网查 ECharts 官方文档** | ★★★★★ 唯一引用官方文档佐证；论证"为何不选堆叠条"最完整；给了精确像素分配 | ChatGPT 账号额度 |
| **Qoder CN CLI** | Qwen3.8-Max | exit 0，**319.7s** | ★★★★★ 参数最细（含 `inverse:true`）；明确提出"超 5-6 色上限"并给出单色渐变替代；警告 `hideOverlap` 仍不合规 | credits |
| **CodeBuddy CLI** | glm-5.1 | exit 0，**339.3s** | ★★★★☆ 唯一做了**几何计算**（"外径只剩约 85px，环带宽 37px，标签需 110px→数学必然重叠"）；提醒 y 轴自下而上渲染的坑 | credits |
| **DSH 本体** | deepseek-v4.1-flash | 本会话 | ★★★☆☆ 工程定位/跨文件根因/取证闭环强；**纯设计层判断建议外借** | 0 增量 |

**结论：三模型对该问题的判断完全一致（都判"换横向条形"），可靠性高。差异在落地细节，可互补。**

### 6.3 Trae vs DSH+CLI 通道

| 维度 | Trae（你手动操作） | DSH + CLI 通道（我操作） |
|---|---|---|
| 看到真实渲染 | ✅ 强 | ✅ **本轮已证明**（截图+读图+定位到行号） |
| 自动循环验证 | ❌ 需你手动点 | ✅ 改→截图→读图→再改 |
| 跨文件一致性重构 | ⭕ 逐文件，易漏 | ✅ 全仓 grep + 批量 |
| 多模型并行评审 | ❌ | ✅ **本轮三模型并行，15 分钟内出齐** |
| 动手的人 | **你**（你不写代码） | 我 |
| 成本 | 已付费 | 0 增量 |

### 6.4 最终选型建议

**主线：DSH 执行 + 三模型设计评审（已完成）；Trae 仅做审美终审。**

理由（按权重）：
1. **你不写代码** —— Trae 是交互式 IDE，价值需人盯着。UI 优化是高频小步迭代，交给我闭环更合适。
2. **本轮已闭环证明**：截图 → 发现 4 处问题 → 三模型评审 → 参数级方案，全程无人工介入。
3. **根因是跨文件一致性**（5 套中文映射表），需全仓 grep + 批量改。IDE 逐文件改易再打局部补丁——**历史上已经犯过这个错**（只修 EventDetail 没修 format.js）。
4. **成本零增量**。

**Trae 保留位置**：改完后的**主观审美终审**（排版疏密、留白节奏），你是最终决策者。

### 6.5 PDCA 分工

```
Plan   ✅ DSH 定位根因（已完成，三级证据）
Do     ⏳ DSH 执行 F1-F10（待拍板）
Check  ⏳ DSH 截图 + 读图自证 + grep 校验
Act    ⏳ Trae/用户：审美终审 + 小屏适配微调
```

---

## 七、被推翻的旧结论（协议 v1.3 要求必填）

| # | 旧结论 | 现状 | 证据 |
|---|---|---|---|
| **O1** | 设备违规排行只是"暂时没数据，接上后端即可" | ❌ **推翻**：后端 schema 根本无 `by_device` 字段，是设计时就没做数据源 | 全项目 grep 仅 1 处（前端自读）；`statistics.py:93-100` 返回体 |
| **O2** | 标签重叠调 `avoidLabelOverlap: true` 即可解决 | ❌ **推翻**：三模型独立判定，7 分类塞 400×250 环形是**几何必然**重叠，必须换图型 | Codex/Qoder/CodeBuddy 独立结论一致 + 本地 `charts.csv` 规则 No.3 |
| **O3** | 中文名不统一是"某处少配一个字段" | ❌ **修正**：实际有 **5 套映射表**各自为政，前端 6 类 vs 后端 10-11 类，是系统性缺陷 | §1.4 表格逐一定位到行号 |
| **O4** | `echarts-theme.js` 已被使用 | ❌ **推翻**：`Dashboard.vue` `echarts.init(el)` 未传主题参数，该主题文件**从未生效** | `Dashboard.vue:341,357,368` 三处 init 均无第二参数 |
| **O5** | Trae 是本项目 UI 开发的必然主力 | ⭕ **修正**：本轮三模型并行评审 + 截图闭环证明，DSH+CLI 在**诊断与一致性重构**上更优；Trae 更适合审美终审 | §6.3-6.4 |

---

## 八、产物清单（本次新建，可删）

| 文件 | 用途 |
|---|---|
| `E:\output\dash.png` | 取证截图（**建议保留**作 before 对照） |
| `E:\output\_codex_review.txt` | Codex/gpt-5.6-luna 完整评审 |
| `E:\output\_qoder_review.txt` | Qoder/Qwen3.8-Max 完整评审 |
| `E:\output\_codebuddy_review.txt` | CodeBuddy/glm-5.1 完整评审 |

> 注：评审用的临时 prompt 文件（`_tmp_codex_prompt.txt`）已在收尾时删除，如需复现三模型评审，按本文 §2.1 重写即可。

---

## 九、可直接复制的提示词

> 三种场景各一份，复制后按需填空。**推荐用 A（已预填好推荐选项）**。

### A. 直接实施版（推荐 — 已按推荐选项预填）

```
读 E:\output\_ui_optimization_verdict.md，这是管理端 UI 优化的评估结论。

我已拍板：
- 决策1（设备违规排行）：选 A —— 换成「审核状态分布」环形图，数据取接口已有的 by_status
- 决策2（授权改代码）：已授权
- 决策3（配色基线）：选 A —— 统一走亮色，与 design-tokens.css 一致

请按 §四「实施清单」执行 F1-F10。要求：
1. 改前先备份，后缀 .bak_20261023
2. 每改完一个文件，告诉我改了哪几行、为什么改
3. F1 的 TYPE_MAP 必须补全到 11 类，以 behavior_engine.py:50-59 + 两个插件为准，并加"未映射兜底"（禁止英文 key 外露）
4. 图表按 §2.5 的横向排序条形图参数做，注意 yAxis 要 inverse:true 才能让最大值置顶
5. 全部改完后，按 §五 重新截图 + 读图自证，把前后对比图给我看
6. 验收 5 项要逐条核对，不接受"编译通过"当完成

动手前先复述一遍你的计划，等我确认。
```

### B. 想先看方案再定版

```
读 E:\output\_ui_optimization_verdict.md，这是管理端 UI 优化的评估结论。

先不要改代码。请先向我汇报：
1. 你从这份文件里读到的 4 个问题分别是什么，根因在哪个文件哪一行
2. §三「待拍板三件事」里，三个选项各自的代价是什么，你推荐哪个、为什么
3. §四 实施清单里，哪几个是"必做"，哪几个取决于我的决策

我看完再告诉你选哪个。
```

### C. 分步实施版（先只修根因，风险最低）

```
读 E:\output\_ui_optimization_verdict.md。

这一轮只做 §4.1「根因修复」的 F1、F2、F3，暂时不动图表：
- F1: format.js 的 TYPE_MAP 从 6 类补到 11 类（以 behavior_engine.py:50-59 + 两个 rule 插件为准）
- F2: TYPE_COLORS 同步覆盖 11 类，颜色用 §2.4 的表
- F3: 删掉 EventDetail.vue:612 的 EXTRA_TYPE_CN，统一走 getTypeName()

要求：
1. 改前备份 .bak_20261023
2. 加"未映射兜底"——查不到就返回「未知类型」并 console.warn，禁止把英文 key 透给界面
3. 改完用这条命令自检，期望 Count >= 5：
   Select-String -Path 'E:\output\1\web-admin\src\utils\format.js' -Pattern 'running_yellow|illegal_turn|pedestrian_crossing|street_stall|crowd_gathering' | Measure-Object | Select-Object Count
4. 确认 EventDetail.vue 里 EXTRA_TYPE_CN 已 0 命中

图表改动留到下一轮。
```

### D. 给 Trae 的审美终审版（实施完成后用）

```
管理端仪表盘刚做了一次图表改造（E:\output\1\web-admin\src\views\Dashboard.vue）：
- 「违规类型分布」从环形图换成了横向排序条形图
- 「设备违规排行 TOP10」换成了「审核状态分布」环形图
- 配色统一走亮色，对齐 src/styles/design-tokens.css

代码逻辑和功能已经验证过，不需要你改功能。请你只做视觉层面的终审：
1. 三张卡片（类型分布 / 近7天趋势 / 状态分布）的视觉重量是否平衡
2. 留白节奏、字号层级是否有问题
3. 1440px 和 1920px 两种宽度下是否都正常
4. 小屏（1280px）下有没有挤压

只提视觉问题，不要动数据逻辑。
```

