# DSH 更新工具包（0.2.1 起）

> 位置：`E:\output\_tools\dsh-update-kit`
> 用途：让 DSH Desktop 的「更新 → 启动」不再把插件配置搞崩。

## 1. 这次到底发生了什么

两个独立问题，别混在一起：

| # | 现象 | 根因 | 状态 |
|---|---|---|---|
| A | 更新安装时，DSH 关闭卡约 10 秒 | `cua-driver.exe`（computer-use）与 `media-bridge-win32-x64.exe`（壁纸引擎）是长驻 stdio 子进程，Host dispose 后仍持有管道，event loop 不退出 → 宿主 10s 超时 → SIGTERM/SIGKILL | 已定性（2026-10-17 隔离复现，见 `C:\Users\ROG\.dsh-repro\REPORT.md`） |
| B | 更新后启动崩溃：`startup failed: 1 required plugin did not activate / connection → webRuntime` | 0.2.1 把 `connection` 的依赖从 `[webRuntime]` 改成 `[webStartup]`，服务 `webRuntime` 改名 `webApp`；但 `@hr98w/dsh-memory@0.1.4` 与 `dsh-vision-router@3.0.3` 的 bundle patch 仍写死 `inject: [webRuntime, webServer]`，把官方依赖覆盖回去 | **已修**（本包兼容层） |

**关键点**：B 的修法不是在插件里改，而是在 **profile 的 `cordis.patch.yml` 末尾加一条覆盖**——profile patch 是最后应用的层，能把任何插件对官方行的过度覆盖压回官方值。插件升级后这行仍无害。

## 2. 四个脚本

| 脚本 | 什么时候双击 | 做什么 |
|---|---|---|
| `0-本次-恢复16插件.bat` | **现在**（本次修复用） | 把 `staged\` 里的恢复版 patch + package.json 应用到 profile，恢复 16 个插件 |
| `1-更新前-备份.bat` | 每次**更新前** | 备份 profile 三件套到 `_plugin-backups\<时间戳>-before-update`；检查并可选结束两个长驻子进程（解决 A） |
| `2-更新后-恢复.bat` | 更新后**启动前/启动失败后** | 从最近一次 `before-update` 备份还原配置，并自动补上 0.2.1 兼容层 |
| `3-紧急-精简配置.bat` | 任何启动崩溃时 | 一键把 bundles 重置为 `base + web-app`（等同崩溃界面的「禁用第三方插件」），先保证能进 GUI |

**共同前提**：脚本会检测 DSH 进程，**必须先完全退出 DSH（含托盘）**；`1-更新前-备份` 只读，可以在 DSH 运行时用。

## 3. 本次恢复步骤（照做）

1. 完全退出 DSH：任务栏托盘右键 → 退出；确认任务管理器里没有 `DeepSeek Harness.exe`
2. 双击 `0-本次-恢复16插件.bat`
3. 看到「完成」后重新打开 DSH
4. 新会话里检查：插件页有 13–16 个插件、侧边栏有市场/壁纸、余额挂件在

**如果启动仍失败**：
- 点崩溃界面的「Disable third-party plugins, back up profile patch, and restart」（已验证可用）
- 或关掉 DSH 后双击 `3-紧急-精简配置.bat`

## 4. 以后每次更新的标准流程

```
更新前：双击 1-更新前-备份.bat   （顺手处理掉两个长驻进程 → 安装不再卡）
更新中：DSH 内点「检查更新」→ 安装 → 它自己重启
更新后：如果起不来 → 完全退出 DSH → 双击 2-更新后-恢复.bat → 重开
兜底：  还不行 → 双击 3-紧急-精简配置.bat → 先能进 GUI，再排查
```

## 5. 兼容层是什么

`cordis.patch.yml` 末尾这几行（`staged\cordis.patch.yml` 已包含，`2-更新后-恢复` 会自动补）：

```yaml
- id: connection
  name: '@deepseek-ai/dsh-client-connection'
  inject: [webStartup]
```

它只在 **profile 层**生效，不修改任何插件包。官方升级后如果 `connection` 又变了，改这一行即可。

## 6. 回滚

- 每一步脚本都会先备份当前状态到 `E:\output\_plugin-backups\<时间戳>-<tag>\`
- 手动回滚：把备份目录里的 `cordis.patch.yml` / `package.json` / `cordis.yml` 复制回
  `C:\Users\ROG\.dsh\profiles\desktop\`
- 日志：`logs\yyyyMMdd.log`

---

## 7. ★2026-10-27 新增：`4-手动更新-静默安装` 与 `9-回滚-移除兜底插件`

**新报错**：`Host did not complete graceful task teardown (exit null, signal SIGTERM, shutdown acknowledged true, graceful deadline exceeded true)`

这不是下载失败，也不是配置崩了：安装包已完整下载（sha512 校验通过）。是**关闭阶段**没过关 —— 详见 `_DSH_OFFICE_STATE.md` §29。

| 脚本 | 什么时候双击 | 做什么 |
|---|---|---|
| `4-手动更新-静默安装.bat` | **应用内更新报上面这个错时** | 校验已下载的包 → 备份 profile → 优雅关 DSH（15s 超时强杀整棵树）→ NSIS `/S` 静默安装 → 校验 profile 与兼容层 → 重启 |
| `9-回滚-移除兜底插件.bat` | 装了兜底插件后启动异常 | 移除 `desktop-exit-fallback`，**保留** 0.2.1 兼容层 |

### 7.1 兜底插件是什么

`C:\Users\ROG\.dsh\profiles\desktop\desktop-exit-fallback.mjs`（本地文件，不是 npm 包；由 `cordis.patch.yml` 挂载）

作用：Host 收到 shutdown、完成 dispose、回了 IPC 回执之后，若还有残留活跃句柄导致进程不退，它会在 **3 秒后强制 `exit(0)`**，让主进程的 10 秒干净关闭检查通过。

隔离 A/B 实测（注入一个 dispose 后存活的长驻子进程）：无插件 **45 秒不退**、有插件 **3.0 秒退出**；正常情况下它零影响（ack 后 43ms vs 对照 47ms）。

### 7.2 使用顺序

```
应用内更新报优雅关闭错
  → 双击 4-手动更新-静默安装.bat        （装上新版本）
  → 若启动异常：双击 9-回滚-移除兜底插件.bat
  → 仍异常：崩溃界面「禁用第三方插件」或 3-紧急-精简配置.bat
```

### 7.3 ⚠ 注意

- `4-手动更新` 会**关闭整个 DSH**（含本会话）。别在长任务跑到一半时跑它。
- 安装完 DSH 会自动重启；目前脚本无开关参数，若要跳过启动请手动结束脚本窗口前先看提示。
- DryRun 体检：`pwsh -File lib\manual-update.ps1 -DryRun`（只读，可随时安全试跑）。
