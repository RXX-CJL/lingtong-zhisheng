# DSH Desktop 更新失败：Host 未优雅退出（graceful task teardown）— 结论报告

- 日期：2026-10-17
- 触发场景：点击「更新 / 安装并重启」（Desktop 0.2.0-rc.2 → 0.2.1-rc.2）
- 报错原文：`desktop update: Host did not complete graceful task teardown (exit null, signal SIGTERM, shutdown acknowledged true, graceful deadline exceeded true)`
- 验收标准：更新能够走完安装；报错不再出现

---

## 1. 根因（三层，全部有代码/实测证据）

### 1.1 直接原因（一级证据：隔离环境实测复现）

Host 端 `apps/desktop-host/src/index.ts:52-58`：

```js
const stop = () => stopping ??= (async () => {
  const running = await application.catch(() => undefined)
  await running?.shutdown.shutdown(0)      // 等全部插件 dispose 完成
  await send({ type: 'shutdown-complete' })// 回执
  if (process.connected) process.disconnect()
  // ← 没有 process.exit()，靠事件循环自然排空
})()
```

**只要 Host 里还有任何一个长驻子进程持着 stdio 管道、或任何未被 dispose 覆盖的句柄，事件循环就不空，进程不退出**；
Electron 主进程等 10 秒后发 SIGTERM（`apps/desktop/src/host-process.ts:295`），于是 `exit null / signal SIGTERM`，
`requireGraceful` 分支抛错 → **拒绝安装新版本**。

隔离实测（子代理，`C:\Users\ROG\.dsh-repro\REPORT.md`，可复跑）：

| 组 | 差异动作 | shutdown → close | 结果 |
|---|---|---|---|
| A1 / A2 | 只发 `{type:'shutdown'}` | 2958 / 2978 ms | exit 0（正常） |
| B | `inspect` → `lock` → `shutdown` | 2946 ms | exit 0（**lock 与失败无关**） |
| C | 浏览器侧长连接 | 无法建立（`/api` 无 WS upgrade 路由） | **假设证伪** |
| **E1 #1/#2** | **插件 spawn 长驻子进程、dispose 不 kill** | **>15000 ms 超时** | **收到 ack 后仍不退出 → 与线上现象逐字一致** |
| E2 | 同一子进程，dispose 时 kill | 3512 ms | exit 0（对照） |

### 1.2 上游缺陷（一级证据：实际运行代码）

`dsh/lib/profile-boot-*.js` 的 `createProcessShutdown`：

```js
const start = (code, forceAfterDispose) => {
  timeout = setTimeout(() => forceExitOnce(code), 5000)   // 唯一兜底
  pending = Promise.resolve().then(dispose).then(() => {
    if (forceAfterDispose) forceExitOnce(code)
    else completeOnce(code)   // completeOnce: clearExitTimeout() + process.exitCode = code
  }, () => forceExitOnce(code))
}
```

- `shutdown(0)` 的 **0 是退出码，不是超时**；内部 5 秒 watchdog 才是超时。
- **dispose 成功后，代码亲手清掉唯一兜底定时器，且只设 `exitCode`、不调 `process.exit()`** ⇒ 之后完全无保护。
- 反向推论：若 dispose 卡住，watchdog 会 `process.exit(0)`（exitCode 0、无信号）。**线上是 SIGTERM ⇒ dispose 正常返回了**，残留的是「不在 dispose 覆盖范围内的资源」。
- 旁证：`host-process.ts:204/306` 会把 Host stderr 拼进错误串；线上串**没有 stderr 后缀** ⇒ teardown 期间没有任何插件报错。

### 1.3 本机可疑资源（未被 dispose 覆盖，实测仍在跑）

真实 Host（pid 35352）下挂着两个长驻原生子进程：

1. `C:\Users\ROG\.local\bin\cua-driver\cua-driver.exe mcp`（stdio 长驻 MCP server）← **头号嫌疑**
2. `C:\Users\ROG\.dsh-wallpaper-engine\bin\media-bridge\v0.1.5\media-bridge-win32-x64.exe serve --poll-ms 1000`

旁证：另有一只 `cua-driver.exe serve`（pid 9868，16:10 启动）**父进程已死却仍存活**，说明本机确实发生过子进程泄漏。

---

## 2. 已排除（逐项查过实际打包代码）

| 资源 | 依据 |
|---|---|
| HTTP keep-alive | `dsh-host-webserver/lib/index.js:306-320`：`close()` + `closeAllConnections()` + 逐 destroy upgradedSockets + `await Promise.all` |
| 浏览器连接 | 浏览器侧是 **fetch/SSE 不是 WebSocket**（`dsh-web-app` patch 原文）；`dsh-client-connection` 不持有 socket |
| `update-tasks lock` | 实测 B 组 2946 ms 正常退出 |
| cordis 定时器 | `cordis-plugin-timer` 一律 `ctx.effect(... return ()=>clearTimeout)` |
| MCP stdio | `dsh-mcp-client`：`await close()` + `ctx.effect`，测试断言子进程 pid 必须 ESRCH（静态看是规范的） |
| 子进程/终端 | `dsh-subprocess-local`：Win32 Job，terminate + await 退出 |
| OTel / schedule / terminal 定时器 | 全部 `.unref()` |
| `dsh-connect-workbuddy` | `lib/index.js:1804 createServer` 有 `:2058 server.close()`，注册在 `ctx.effect` |
| `dshmarket` | 其 `createServer` 跑在 detached 恢复子进程里，不在 Host 内 |
| `dsh-plugin-wallpaper-engine` 的 media-bridge | dispose 已注册（`routes/now-playing.js:67`），且 `KILL_GRACE_MS=3000` 有 SIGKILL 兜底 → 残留嫌疑下降，但未排除 |

---

## 3. 被推翻的旧结论（重要，防止复读）

1. ~~「浏览器 WebSocket 长连接 hold 住 Host」~~ → **证伪**：浏览器走 fetch/SSE；隔离 C 组连 WS 都建不起来。
2. ~~「更新前的 `update-tasks lock` 是触发条件」~~ → **证伪**：B 组 lock 后 2946 ms 正常退出。
3. ~~「安装的是 0.1.7-rc.2」~~ → **纠正**：`app.asar` 内 `package.json` 实际版本是 **0.2.0-rc.2**；待装 0.2.1-rc.2。
4. ~~「升级到 0.2.1 就会修好」~~ → **不成立**：`dsh-v0.2.1-rc.2` 的 `apps/desktop-host/src/index.ts` 与现版本逐行相同，仍无 `process.exit()`。
5. ~~「给 app.asar 打补丁强制退出」~~ → **不可行**：asar `hasIntegrity=True`，改字节会被完整性校验拒绝。

---

## 4. 修复选项（按代价排序）

| 选项 | 做法 | 代价 | 能否根治 |
|---|---|---|---|
| **A. 手动安装已下载的 0.2.1** | 运行 `%LOCALAPPDATA%\@deepseek-aidsh-desktop-updater\pending\deepseek-harness-0.2.1-rc.2-win-x64.exe` | 一次重启 | 否（但完成本次升级） |
| **B. 更新前禁用可疑插件（二分）** | 设置→插件 关掉壁纸引擎/computer-use 后重试更新 | 每次一次重启（失败会自动恢复 Host，无损坏） | 规避；成功即可点名元凶 |
| **C. 探针插件（精准点名）** | 加一个探针 cordis 插件，在 shutdown-complete 后 dump `process.getActiveResourcesInfo()` 到文件 | 需重启加载，再触发一次更新 | 只诊断 |
| **D. 上游修** | `createProcessShutdown` 成功路径应 `process.exit(code)`，或保留 `.unref()` 兜底；`clearExitTimeout()` 是缺陷放大器 | 提 issue/PR | 是（需上游合并） |

---

## 5. 复跑与取证

```powershell
$env:ELECTRON_RUN_AS_NODE='1'
& 'F:\AI\DeepSeek-Harness\deepseek-harness-dsh-desktop\DeepSeek Harness.exe' C:\Users\ROG\.dsh-repro\harness.mjs A|B|C|E1|E2
```

- 隔离环境：`DSH_HOME=C:\Users\ROG\.dsh-repro\home`，`REPRO_PORT=0`（实测端口 63080–63727，从未占用 19387）
- 静态分析产物：`C:\Users\ROG\.dsh-repro\static\`（内核 287 包解包 + asar 读取器 + 报告）
- 未改动：`E:\deepseek-harness`、`C:\Users\ROG\.dsh\profiles\*`、`F:\AI\DeepSeek-Harness\*`；真实 Desktop 主进程 35788 / Host 35352 全程存活

---

## 5.5 现场实验（2026-10-17 22:4x，已执行）

在 `C:\Users\ROG\.dsh\profiles\desktop\cordis.patch.yml` 末尾追加（已备份为 `cordis.patch.yml.bak-before-teardown`）：

```yaml
- id: computer-use
  disabled: true
- id: computer-use-cua-driver-mcp
  disabled: true
```

**结果（二级证据：进程状态）**：改完 8 秒内，`cua-driver.exe mcp`（pid 33904）消失。

⚠️ **更正（22:47）**：这不是「热卸载单个插件」——旧 Host **35352 实际整体退出**，新 Host **10876** 重建，会话被新宿主恢复。子进程消失是宿主重建的副产物，不是 patch 热生效。

实验后 Host 子进程只剩：`media-bridge-win32-x64.exe`（壁纸引擎，pid 17284）与另一个 Node 子进程（pid 31200）。
另有无关孤儿 `cua-driver.exe serve`（pid 9868，父进程 6568 已死）。

**回滚**：恢复 `cordis.patch.yml.bak-before-teardown`，或删除文件末尾的 `disabled` 块，然后重启 Desktop。

---

## 5.6 第二次实验环境（2026-10-17 22:45–22:47）

已实施：
- `computer-use` / `computer-use-cua-driver-mcp`：disabled
- `wallpaper-engine`：disabled（`media-bridge` 子进程随之消失，实测确认）
- 观测插件 `dsh-teardown-probe`（`node_modules\dsh-teardown-probe\index.js`）→ 在 dispose 时把 `process.getActiveResourcesInfo()` 写入 `C:\Users\ROG\.dsh-repro\teardown-probe.log`

加载期基线快照（pid 10876，`plugin-loaded`）：

```
FSEventWrap=213, FSReqCallback=1, PipeWrap=8, ProcessWrap=2, TCPServerWrap=4, TCPSocketWrap=9, Timeout=8
```

→ 213 个文件监视器是数量最大的一类；若关机时未全部 close 即可独立 hold 住事件循环。
（已知瑕疵：`dsh-fs-local/lib/index.js:744-749` 的 `watcher.close()` 未 await。）

**回滚全部实验**：恢复 `cordis.patch.yml.bak-before-teardown`，删除 `node_modules\dsh-teardown-probe\`，重启 Desktop。

---

## 5.7 探针实测结果：元凶 = workbuddy 的两个 HTTP shim（2026-10-17 22:46）

**探针记录（pid 10876，一次真实的更新失败关闭）**：

| tag | 活跃资源 |
|---|---|
| `dispose-start` | FSEventWrap=213, TCPSocketWrap=7, PipeWrap=6, TCPServerWrap=4, ProcessWrap=1 |
| `t+400ms` | **FSEventWrap 213→0（全部关干净）**；仍剩 `Server=1, Socket=5, ChildProcess=1, PipeWrap=5` |
| `t+2000ms` | **完全不变**：`Server=1, Socket=5, ChildProcess=1` |

**端口指纹**：关闭失败后新 Host 监听 `19387`（主 webServer）+ `65257` + `65258`；
对两个随机端口请求 `/healthz`，**都返回 workbuddy shim 专属的 401**
（`{"error":{"message":"missing or invalid Authorization bearer",...}}`）
⇒ 65257/65258 就是 `dsh-connect-workbuddy` 为两个 region 各自 `server.listen(0, "127.0.0.1")` 开的 HTTP shim。

**代码缺陷（`dsh-connect-workbuddy/lib/index.js:6148-6152`）**：

```js
ctx.effect(() => () => {
  stopped = true;
  for (const region of REGION_KEYS) stacks[region].shim.close();  // 返回 Promise，但同步 disposer 不 await
  clearHostHeartbeat();
});
```

`shim.close()`（`:2057-2061`）= `server.close(cb)` + `server.closeAllConnections()`，本身是异步的；
disposer 不等待 ⇒ `shutdown(0)` 已返回、ack 已发，但 server/socket 仍在事件循环里。

**处置**：`- id: dsh-connect-workbuddy  disabled: true` 之后，65257/65258 实测消失。

---

## 6. 下一步唯一待定项

**到底是 `cua-driver.exe mcp` 还是别的资源残留**——静态无法定论，需要一次线上二分或探针。
最小成本验证：更新前先关掉 computer-use（或壁纸引擎），再点「安装并重启」，看是否仍报 `graceful deadline exceeded true`。
