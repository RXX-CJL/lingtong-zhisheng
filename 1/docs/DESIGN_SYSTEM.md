# 智瞳灵声管理端 · 设计系统 MASTER

> 生成日期：2026-10-03 · 执行者：DSH
> 生成依据：`ui-ux-pro-max` 技能（query: *traffic enforcement admin dashboard data-dense monitoring*，dials: variance=5 balanced / motion=3 subtle / density=8 dashboard）
> 落地文件：`web-admin/src/styles/design-tokens.css`（已接入 `main.js`，实测生效）

---

## 一、"AI 味"根因诊断（实测，非猜测）

| 现象 | 证据 | 判定 |
|---|---|---|
| 主色直接用 EP 默认蓝 | 8 处硬编码 `#409eff`（`AppealList.vue:308`、`DeviceList.vue:541`、`EventCenter.vue:438/469/508`、`EventDetail.vue:394/1526`） | ⚠️ 默认值直出 |
| 未启用暗色主题 | 全项目无 `element-plus/theme-chalk/dark` 引入 | — |
| 卡片版式千篇一律 | KPI 卡全是"居中图标 + 大数字 + 标签" | ⚠️ **最大 AI 味来源** |
| 数字字体混用 | `Consolas` / `Monaco` / `monospace` 三处不同写法 | ⚠️ 无统一决策 |
| 底色/层次 | body `#f0f2f5`，卡片无阴影差异 | ⚠️ 无层次 |

**结论**：不是"配色丑"，而是**全部使用框架默认决策，没有任何设计选择**。这正是 AI 默认生成的特征。

---

## 二、设计方向（已采纳并落地）

| 维度 | 决策 | 理由 |
|---|---|---|
| 风格 | **亮色为主 + 科技感精修** | 全暗色会与 8 处硬编码浅色冲突，演示前风险高；暗色大屏作为 `html.dark` 可选模式保留 |
| 主色 | `#1D4ED8`（深邃交通蓝） | 比 EP 默认 `#409EFF` 更沉、更有权威感，适合执法类产品 |
| 语义色 | 绿=正常/已确认 · 橙=待复核 · 红=违规 · 青=信息 | 交通系统的状态即信息 |
| UI 字体 | `Inter → 系统黑体` | 现代、中性、屏幕可读性好 |
| **数字字体** | **`JetBrains Mono / Fira Code` + `tabular-nums`** | **数据可对齐**，比 Consolas 现代；车牌/ID/速度统一用它 |
| 密度 | `density=8`（紧凑） | 管理端信息密度优先 |
| 圆角 | 8px 基准 / 12px 卡片 | 比 EP 默认更克制 |
| 阴影 | 三级（xs/sm/lg）+ 主色光晕 | **层次感的关键**；EP 默认阴影太平 |
| 动效 | `motion=3`（subtle）：120/180/260ms + `prefers-reduced-motion` | 不喧宾夺主 |

---

## 三、已落地的令牌（`design-tokens.css`）

- **品牌/语义色** 13 个 + **中性色阶** 9 个
- **字体** 2 套（UI / 数字等宽）+ 8 档字号
- **间距** 8 档（4→32px）、**圆角** 4 档、**阴影** 4 档 + 光晕
- **动效** 3 档时长 + 缓动曲线
- **Element Plus 变量覆盖** 20+ 个（`--el-color-primary` 等）→ **EP 组件自动跟随，无需逐页改**
- **通用类**：`.zt-kpi` / `.zt-kpi-value` / `.zt-badge--{danger,success,warning,info}` / `.zt-mono` / `.zt-plate`
- **表格精修**：表头浅底、hover 主色浅底、去重边框
- **无障碍**：`focus-visible` 焦点环、`prefers-reduced-motion` 降级

**实测生效**（浏览器计算样式）：
```
--el-color-primary = #1D4ED8     (原 #409EFF)
body background    = rgb(246,247,249)
body font          = Inter, ..., "Microsoft YaHei"
```

---

## 四、待执行改造清单（交给 Trae 或后续 DSH）

### P1 — KPI 卡片版式重构（**最影响观感**）

**现状**：6 张卡全为「居中图标 + 大数字 + 标签」，等宽等高，无主次。

**改为**（两种可选版式，建议混用制造层次）：
1. **横向卡**：左侧 40×40 图标块（语义色浅底）→ 右侧上下两行（数字 34px + 标签 13px muted）
2. **主次卡**：最重要的 1-2 张放大（占 2 列），数字更大，右侧加趋势迷你图或同比标签

**验收**：KPI 区不再是 6 个相同方块；数字用 `.zt-kpi-value`（等宽 + tabular-nums）。

涉及文件：`src/views/Dashboard.vue`

### P1 — 状态语义色统一

把 8 处硬编码 `#409eff` / `#ecf5ff` 替换为令牌：
- `#409eff` → `var(--zt-primary)` 或语义色
- `#ecf5ff` → `var(--zt-primary-soft)`
- 状态标签改用 `.zt-badge--*`

涉及文件：`AppealList.vue`、`DeviceList.vue`、`EventCenter.vue`、`EventDetail.vue`

### P2 — 数字/车牌字体统一

把 `Consolas` / `Monaco` 三处替换为 `var(--zt-font-mono)`，并给速度/ID/车牌加 `tabular-nums`。

涉及文件：`DeviceList.vue:530`、`DisagreementList.vue:501`、`EventCenter.vue:501/507/516`

### P2 — 空状态与加载态

`设备违规排行 TOP10` 等空面板当前是**一条横线的空白**（截图可见），应给：图标 + 一句说明 + 可选操作。

---

## 五、预交付检查清单（来自技能，逐项打勾）

- [ ] 不用 emoji 当图标（用 SVG：Element Plus Icons / Lucide）
- [ ] 所有可点击元素 `cursor: pointer`
- [ ] hover 态有 150-300ms 过渡
- [ ] 亮色模式文字对比度 ≥ 4.5:1
- [ ] 键盘导航有可见焦点（已由 `.zt:focus-visible` 提供）
- [ ] 尊重 `prefers-reduced-motion`（已在令牌层处理）

---

## 六、回滚方式

- 令牌文件：删除 `web-admin/src/styles/design-tokens.css` 及 `main.js` 中对应的 1 行 import
- 无需改动其他文件即恢复原主题（所有覆盖都集中在令牌文件内）
