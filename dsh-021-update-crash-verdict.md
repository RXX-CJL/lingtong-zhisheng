# DSH 0.2.1-rc.2 更新后启动崩溃 — 定案报告

> 日期：2026-10-17 23:20（+08）
> 结论等级：**三级（源码 + 日志 + 用户实测互相印证）**
> 相关文件：`_DSH_OFFICE_STATE.md` §28、`_tools\dsh-update-kit\README.md`

## 1. 结论

**崩溃不是插件损坏，而是 0.2.1 的接口改名与两个第三方插件的补丁覆盖相撞。**

DSH 0.2.1-rc.2：
- `connection` 行的依赖从 `inject: [webRuntime]` 改为 `inject: [webStartup]`
- `web-app` 提供的服务从 `webRuntime` **改名** `webApp`（`web-runtime` 行 id 未变）

但：
- `@hr98w/dsh-memory@0.1.4` 的 `cordis.patch.yml` 写死 `inject: [webRuntime, webServer]`
- `dsh-vision-router@3.0.3` 的 `cordis.patch.yml` 写死同样内容

它们属于 **bundle 层，先于 profile patch 应用**，于是把 0.2.1 的官方依赖覆盖回一个**已不存在**的服务名。`webRuntime` 永远不出现 → `connection` 是 required → 启动审计抛：

```
dsh: startup failed: 1 required plugin did not activate
Plugins waiting for services (9):
  connection (required)  webRuntime
```

崩溃界面点「Disable third-party plugins, back up profile patch, and restart」后，`sanitizeProfile` 把 bundles 重置为 `[base, web-app]`，那两个 patch 不再加载，`connection` 回到官方 `[webStartup]`，所以能启动——但所有第三方功能同时消失。

## 2. 证据（可复核）

| # | 证据 | 位置 |
|---|---|---|
| 1 | 崩溃错误与 waiting 列表 | `%APPDATA%\@deepseek-ai\dsh-desktop\logs\crash-2026-10-17T14-49-53-322Z-host.log` |
| 2 | 0.2.1 官方 `connection` 依赖 | `resources\app.asar` → `dsh/node_modules/@deepseek-ai/dsh-web-app/cordis.patch.yml`：`- id: connection` / `inject: [webStartup]` |
| 3 | `webRuntime` 已改名 `webApp` | 同包 `lib/index.js`：`ctx.provide("webApp", …)`，全文无 `webRuntime` |
| 4 | 第三方覆盖 | `node_modules/@hr98w/dsh-memory/cordis.patch.yml:4-6`、`node_modules/dsh-vision-router/cordis.patch.yml:32-34` |
| 5 | 全库仅这两处 | `grep webRuntime *.yml` 于 profile `node_modules`，命中仅上述 2 个文件 |
| 6 | 恢复按钮的真实行为 | `apps/desktop/src/project-manager.ts:76` → `packages/boot/app-boot/src/profile-sanitize.ts`：改名备份 patch + 重写 bundles，不动 dependencies |
| 7 | 时间线吻合 | teardown 探针日志：`14:49:50.374 server-listen` → `14:49:51.217 server-close` → `14:49:51.226 dispose-start` → `14:49:53` 崩溃（webserver 起得来，是 web-app 侧的 `webRuntime` 缺失拖垮 connection） |

## 3. 修复

**不改插件、不删功能**：在 profile 的 `cordis.patch.yml` 末尾追加兼容层（profile 层最后应用）：

```yaml
- id: connection
  name: '@deepseek-ai/dsh-client-connection'
  inject: [webStartup]
```

任何插件再覆盖官方行，都会被这一行压回官方值；插件升级后这行仍幂等无害。

**已落地**：`E:\output\_tools\dsh-update-kit\`
- `staged\cordis.patch.yml`（400 行干净版 + 兼容层，已验证前 400 行与原文件逐行一致）
- `staged\package.json`（16 个 bundles，剔除 0.2.1 已删除的 `dsh-experimental-schedule-bundle`）
- 4 个 bat（本次恢复 / 更新前备份 / 更新后恢复 / 紧急精简）
- `README.md`（原理、流程、回滚）

## 4. 被推翻的旧结论

| 旧结论 | 状态 | 更正 |
|---|---|---|
| "更新后崩溃是第三方插件坏了，所以要禁插件" | ❌ 错 | 插件没坏；是它们对**官方行**的 `inject` 覆盖了 0.2.1 已改名的依赖 |
| "`webRuntime` 是 `connection` 的必需依赖" | ❌ 0.2.1 起作废 | 0.2.1 官方改为 `webStartup`，`webRuntime` 服务已改名 `webApp` |
| "更新安装卡 10 秒 = 插件导致启动失败" | ⚠ 两件事 | 卡 10 秒是长驻子进程（cua-driver / media-bridge）让 Host 退不干净；启动崩溃是本文 §1 |
| "`cordis.patch.yml.bak-1792248709643` 是用户之前的完整配置" | ⚠ 只对一半 | 它是崩溃前版本（417 行），但含 22:18 加的临时诊断块；**干净版是 `.bak-before-teardown`（400 行）** |
| "`@deepseek-ai/dsh-experimental-schedule-bundle` 必须恢复" | ❌ 错 | 0.2.1 已无此包；schedule 工具由 base 提供，当前简化会话仍有 `schedule` 工具 |

## 5. 操作四件套

**① 命令**（可复制的顺序）
1. 完全退出 DSH：托盘图标 → 退出；任务管理器确认无 `DeepSeek Harness.exe`
2. 双击 `E:\output\_tools\dsh-update-kit\0-本次-恢复16插件.bat`
3. 重新打开 DSH（桌面快捷方式）

**② 预期结果**
- 脚本输出：`[OK] 兼容层存在（connection → webStartup）`、`[OK] bundles 数量：16`
- DSH 正常进主界面，不再出现崩溃对话框
- 插件页显示 13–16 个第三方插件

**③ 判断标准**
- 成功：主界面出现 + 插件页有插件（壁纸/余额挂件/市场页可见）
- 失败：仍弹「DeepSeek Harness is unavailable」→ 看 `%APPDATA%\@deepseek-ai\dsh-desktop\logs\crash-*.log` 最新一条

**④ 下一步分支**
- 成功 → 新会话里验证：`session_search` 可用、视觉工具在、插件市场能开
- 失败 → 点崩溃界面「禁用第三方插件」回退，或关掉 DSH 后双击 `3-紧急-精简配置.bat`；把新 crash log 发我，我再定位

## 6. 限制与未验证

1. **未做离线启动验证**：`C:\Users\ROG\.dsh-repro\` 的隔离 launcher 无法解析第三方插件的 `@deepseek-ai/*` 导入（REPORT §5），不能可靠复现真实 host；因此本次修复靠**源码证据 + 重启实测**闭环。
2. **`dsh-vision-router@3.0.3` 与 `@hr98w/dsh-memory@0.1.4` 在 0.2.1 下的其余兼容性未验证**（如 `attachment-local` 的 config 字段、`dsh-tools` 接口）。它们失败只会是 warning，不会阻止启动。
3. **`@deepseek-ai/dsh-computer-use@0.2.0-rc.2` 是旧版**（shell 已 0.2.1）；若加载失败也只是非 required 警告。
4. 更新安装本身的 10 秒卡顿需脚本 1 在**下次更新前**处理，本次未实测关闭子进程后的安装耗时。
