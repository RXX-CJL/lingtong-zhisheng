# handoff README（新主对话必读）

> 这个文件被 `dsh-handoff-bus` 的 `briefingFiles` 自动读取并注入新会话。
> **完整台账在 [main.md](main.md)** —— 先读它。

## 恢复步骤（新主对话照着做）

1. `bus_register(role="main")` —— 接管 main，各子线绑定与编号不变
2. 读 `E:/output/handoff/main.md` —— 当前状态 / 各线进度 / 待拍板 / 产物路径
3. 读 `C:/Users/ROG/.memory/index.md` —— 记忆路由表（已由 dsh-plugin-memory 自动注入，可不重复读）
4. 瑶光状态已在 `index.md` 的 YAO-GUANG 块里，**不要重新跑一遍诊断**
5. 瑶光服务若没起：`node F:/AI/DSH-HQ/bin/yaoguang-boot.mjs`

## 当前最重要的事

**把日常对话与工作流接进瑶光**，确保换对话不失忆。
进度与已查清的事实见 `main.md` 第四节。

## 上线状态一句话

瑶光感知层 + 体征链路 + 星云 + 自动启动全部打通并验证；视觉层（相机/层级/LOD）仍待办；跨会话记忆正在补「对话进度」这一环。
