# purge 换装 1.3.6 · 交接单

> 状态：**准备完成，未执行换装**。2026-11-04 18:1x
> 上一轮我把 Desktop 弄崩过一次（见 §5 教训），现在环境已回滚到安全状态。

---

## 1. 目标

把 `dsh-purge-community@1.6.69` 换成 `dsh-purge@1.3.6`（555bbbAAA 维护版）。

**理由（都是实测，不是感觉）**：

| 项 | 社区版 1.6.69（现在） | 1.3.6（目标） |
|---|---|---|
| 补丁数 | 81 | **83** |
| rc.5 支持 | README 说「已验证」 | README 写**「49 个补丁目标文件上游一个没改，桌面外壳五条注入结果与 rc.3 逐字节一致」**——证据等级更高 |
| `dshTarget` | 未声明 | `>=0.2.1-rc.3 <0.3.0` —— **覆盖我们当前的 rc.5** |
| `presets-plugin` 模块 | ✅ 有 | ❌ **没有** |
| `presets/unrestricted/` | ✅ 自带 | ❌ **没有** |

**代价（用户已知情并选择）**：换过去后，unrestricted 预设不再随插件自动更新，冻结在 `C:/Users/ROG/.dsh/.agent-presets/unrestricted/`（现 15255 B）。#76 软补丁仍会清理其身份句。

---

## 2. 已完成的准备（可直接用）

| 项 | 路径 | 校验 |
|---|---|---|
| 安装包 | `C:/Users/ROG/.dsh/profiles/desktop/vendor/dsh-purge-1.3.6.tgz` | SHA256 = `ab8acdd81728d8f1a974a6b81f3eba126331884ddecd3bc84fc261f2069c6340` ✅ 与官方 SHA256SUMS 一致 |
| 完整备份 | `F:/AI/dsh-purge-backup/20261104-173756/` | 5 项：`dsh-purge-community/`、`dsh-purge-state/`、`dsh-purge-community-state/`、`package.json.bak`、`cordis.patch.yml.bak` |
| 原始下载 | `F:/AI/dsh-purge-download/v1.3.6/` | tgz + SHA256SUMS + unpaked/ |

**tgz 内容验证（已实测）**：
- 117 条目，关键文件齐全：`package/package.json`、`package/lib/core.js`、`package/cordis.patch.yml`、`package/lib/index.js`
- **隔离目录实际安装成功**（`pnpm add` → 5s，+4 packages，`dsh-purge 1.3.6`）
- **模块可加载**（`import('./lib/core.js')` → 146 个导出符号，含 `findShimDir` / `dirHasDshLauncher` / `ALL_PATCHES` / `isDesktopCommandRuntimeDir`）

**前置条件核对**：
- cordis 版本 `4.0.5`，满足两个包共同要求的 `^4.0.1` ✅
- 新旧包 peerDeps **完全相同**（都是 `{"@deepseek-ai/cordis":"^4.0.1"}`）✅

---

## 3. ⚠️ 上一轮崩在哪（**别重复**）

我犯的错：**先改 `package.json` 指向新包，但 pnpm 还没装**。中间有「配置已改、包未到」的空窗期，Desktop 读到新配置找不到模块 → 启动崩。

正确顺序是**反的**：

```
① 先装包（node_modules 里出现 dsh-purge）
② 再改 package.json 的依赖与 bundles
③ 最后重启
```

而且注意：`dsh plugin` **只是转发 pnpm 参数**，没有 `--no-save`：

```
Usage: dsh plugin [options] [args...]
Arguments: args    pnpm arguments, forwarded verbatim (add <pkg>, remove <pkg>, why <pkg>, ...)
```

**所以 `plugin add` 会自己改 package.json。** 手改 package.json 再装 = 制造空窗。

---

## 4. 推荐执行步骤

### 方案 A：一条命令原子完成（**推荐**）

```bash
D="F:/AI/DeepSeek-Harness/deepseek-harness-dsh-desktop/resources/runtime/cli/bin/dsh.cmd"
"$D" plugin --profile desktop add "file:C:/Users/ROG/.dsh/profiles/desktop/vendor/dsh-purge-1.3.6.tgz"
```

pnpm 会先把包落进 `node_modules`，最后才写 `package.json` —— **无空窗**。

装完先验（**重启前**）：

```bash
ls -d "C:/Users/ROG/.dsh/profiles/desktop/node_modules/dsh-purge"
node -e "console.log(require('C:/Users/ROG/.dsh/profiles/desktop/node_modules/dsh-purge/package.json').version)"
"$D" plugin --profile desktop list | grep -i purge
```

期望：目录存在、版本 `1.3.6`、list 里出现 `dsh-purge@1.3.6`。

### 方案 B：接管 bundles（步 A 之后还有一步）

装完后 `package.json` 的 `dependencies` 会有 `dsh-purge`，但 **`dsh.profile.bundles` 数组里仍是 `dsh-purge-community`**。要让新插件真正生效，需要把 bundles 第 64 行附近的 `"dsh-purge-community"` 改成 `"dsh-purge"`。

此时两个包**同时存在于 node_modules**，所以改 bundles 指向谁都不会崩。

也可以顺手把旧的卸掉：

```bash
"$D" plugin --profile desktop remove dsh-purge-community
```

（卸旧之前确认 bundles 已不含它，否则读不到。）

### 最后：重启 Desktop

**只有用户能重启。** 重启后验：

```bash
cat "C:/Users/ROG/.dsh/dsh-purge/applied.json"
"$D" plugin --profile desktop list | grep -i purge
```

---

## 5. 回滚（一条命令）

```bash
cp "F:/AI/dsh-purge-backup/20261104-173756/package.json.bak" \
   "C:/Users/ROG/.dsh/profiles/desktop/package.json"
```

然后重启。如需连插件目录一起回滚：

```bash
rm -rf "C:/Users/ROG/.dsh/profiles/desktop/node_modules/dsh-purge"
cp -r "F:/AI/dsh-purge-backup/20261104-173756/dsh-purge-community" \
      "C:/Users/ROG/.dsh/profiles/desktop/node_modules/"
```

---

## 6. 残留物（清理前先确认）

| 路径 | 说明 | 建议 |
|---|---|---|
| `~/.dsh/dsh-purge/` | 上一轮崩之前新插件短暂跑过留下的状态目录，`applied.json` 里 `version: 1.6.69`（是旧插件写的） | **先别删**。装 1.3.6 后它会被复用；如果换装失败要回滚，删了反而少一份现场 |
| `~/.dsh/dsh-purge-community/` | 旧插件状态（含 3 个 tgz 缓存、backups、install-recovery） | 换装成功并稳定运行几天后再归档 |

---

## 7. 未验证的事（诚实标注）

1. **1.3.6 在 rc.5 上能否真正跑通，我不知道。** 只做了静态核对 + 隔离安装 + 模块加载，**没跑过真实链路**。
2. **两个包的 cordis.patch.yml 都注册了 `inject: [systemPrompt, tools]`**（id 分别是 `dsh-purge-community` 和 `dsh-purge`）。两者并存时磁盘上有两份 patch 声明。宿主不重启不重读 bundles，所以只要「改配置」和「重启」之间不插入别的重启，这个窗口是安全的。
3. **卸载旧包后 restricted 预设的行为** —— 不确定 unresticted 预设文件是否仍被 #76 正常清理，需重启后看 `~/.dsh/.agent-presets/unrestricted/agent.cordis.yml` 的 `prefix:` 是否被改写。

---

## 8. 我这边停在哪

- 已做：下载 → 校验 → 解包 → 静态对比 → **隔离安装验证** → **模块加载验证** → 备份
- 未做：**改 profile 配置 / 装到真实 node_modules / 重启**
- 原因：**我是 Desktop 的子进程**。一旦 Desktop 崩，我随它一起死，没有机会汇报或回滚。
  这不是谦虚，是机制约束 —— 我看不到 Desktop 何时读配置，上次就崩在这个盲区。

---

## 9. 交给谁做 · 交付前环境状态（2026-11-04 18:2x 实测）

| 检查项 | 实测值 |
|---|---|
| `package.json:25` 依赖 | `"dsh-purge-community": "file:C:/Users/ROG/.dsh/dsh-purge-community/pkgs/f0723586…/dsh-purge-community-1.6.69.tgz"` |
| `package.json:64` bundles | `"dsh-purge-community"` |
| `node_modules` | 只有 `dsh-purge-community` |
| `dsh plugin list` | `├── dsh-purge-community@1.6.69` |

**结论：环境完全干净，和换装前一模一样。可以放心接手。**

---

## 10. 给接手者的三条硬提醒

1. **别手改 `package.json` 的 `dependencies` 再装。** 我上次就是这么崩的 —— 配置指向新包、包还没落盘，宿主读到配置找不到模块。**一律用 `dsh plugin add`，让 pnpm 自己管顺序。**
2. **每次改完 `package.json`，等至少 30 秒再重启**，给宿主任何可能的文件监听一个缓冲。
3. **重启由用户做。** 你无法重启 Desktop，装完告诉用户「可以重启了」。

---

## 11. 一条容易踩的路径坑（我实测踩到了）

`C:` 开头的 Windows 路径在**某些命令行上下文里会被当远程主机**：

```
tar -tzf "C:/Users/..."  →  tar: Cannot connect to C: resolve failed
```

**解法**：在 bash 里用 POSIX 形式 `/c/Users/...`；pnpm/npm 用 `file:C:/Users/...`（Windows 形式）。

另外 `/tmp` 在 Git Bash 里映射到 `F:/Temp`，**Node 会把它当 `E:\tmp`** —— 跨工具传路径时注意，别用 `/tmp` 做 Node 的 cwd 参数。
