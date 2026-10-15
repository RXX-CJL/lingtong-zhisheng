# 云端 AI 事件判定审计（364 条 rejected 的根因）

> 2026-10-03 由 DSH 审计。回答一个关键疑问：**为什么 541 条事件里 364 条被驳回？**

---

## 一、初始怀疑与证据

```
traffic_events 状态分布:
   rejected=364  manual_review=139  pending_ai=34  triggered=4

各状态 ai_confidence 统计:
   manual_review  n=139  avg=0.05  min=0.05  max=0.05   ← min==max，疑似硬编码
   rejected       n=364  avg=0.05  min=0.05  max=0.05   ← min==max
   pending_ai     n=34   avg=0.0   min=0.0   max=0.0
```

`min == max` 一度让人怀疑 `ai_confidence` 是**固定默认值**。

## 二、查证：不是默认值，是 **DeepSeek 的真实回答**

解析 `ai_judgment` 后发现云端确实返回了完整推理：

```json
{
  "version": "v3",
  "yolo":     {"violation_type":"speeding","confidence":0.0,"duration_ms":0},
  "doubao":   {"judgment":"rejected","confidence":0.15,
               "reasoning":"...图片中仅提供瞬时静态画面，未包含任何速度测量数据
                            （如雷达/激光测速、视频流速度计算等），
                            无法直接得出车辆实际行驶速度..."},
  "deepseek": {"judgment":"rejected","confidence":0.05,
               "review_summary":"...静态图无法测速，豆包结论保守合理，无需处罚"},
  "final":    {"judgment":"rejected","confidence":0.05,
               "method":"doubao_plus_deepseek"}
}
```

**结论**：`0.05` 是 **DeepSeek 对"不确定"场景的稳定输出**，不是硬编码。
**364 条 rejected 在"当前输入"下是合理判定** —— AI 没有错。

---

## 三、真正的根因：**管线只给了 AI 一张静态图**

### 缺陷 1：`context_frames` 接收了但完全没用

```python
# cloud_collaborator.py 原实现
def _analyze_with_dual_images(self, original, annotated, violation_type, context_frames):
    result = analyze_with_doubao(annotated, violation_type)   # ← 只用了 annotated
    return result
```

**上游明明传了上下文帧**（`realtime_detector.get_context_frames()` 返回最近 4 帧 base64），
**函数签名也接收了**，但**函数体完全没用**。

**后果**：让 AI 用**单帧**验证**动态行为**（超速、压线行驶）—— 物理上不可能。

### 缺陷 2：prompt 只给一个孤立数字

```python
# _build_event_context_prompt 原实现
f"速度: {_as_float(vehicle_info.get('speed', 0.0)):.1f} km/h",   # ← 无来源、无标定、无推导
```

AI 拿到「速度: 37.9 km/h」，**无从判断这个数字可不可信**，只能回答"无法验证"。

---

## 四、修复（本日已完成）

### 修复 1：多帧拼图真正送进 AI
`_analyze_with_dual_images` 现在：
- 取 `CLOUD_CONTEXT_FRAMES`（默认 3）帧
- 统一高度后**横向拼接成一张图**（避免多图上传的接口兼容问题，且不增加调用次数）
- 实战验证：`3 帧 × 960x432 → 2880x432`，`used_frames=3`，AI 自己在回复里
  描述出「该图为**三张连续时间点**的十字路口监控画面」→ **确实看到了时间维度**
- 合并失败自动退回单张标注图（保持可用性）

### 修复 2：prompt 补全数值推理链 + 明确职责分工
新增内容：
- 测速的**方法**（`assumed_lanes` / `lane_width` / `explicit_ppm`）与**可信度**
- 未标定时**显式警告**："误差可能达 ±50%，不可作为处罚依据"
- **轨迹位移与时长** → 让 AI 理解"这个速度是怎么来的"
  （例：`轨迹: 8 个点，首尾像素位移 210.0px，历时 1.40s，平均 150.0 px/s`）
- **职责分工**（关键）：
  ```
  1. 数值类结论（车速/是否超速）已由本地标定计算给出，不需要你复核数字；
  2. 你的任务是语义核对：判断「该类行为是否真的在画面中发生」
  3. 一致 → confirmed；矛盾 → rejected 并指出画面依据；
  4. 无法判断 → uncertain 并说明缺什么信息
  ```

---

## 五、修复后的实测（仍待观察）

**修复 1 已实测生效**：
```
success=True  used_frames=3
result_text: "该图为三张连续时间点的十字路口监控画面..."
```

**但 AI 仍答"不确定"**，理由是：
```
1. 未见限速标志，无法确认法定限速值
2. 缺乏参照物，无法准确估算实际行驶速度
3. 无雷达/激光测速读数或视频帧间位移计算数据
```

**这揭示了更深的设计原则**（值得写进答辩材料）：

| 判断类型 | 应由谁负责 | 理由 |
|---|---|---|
| **数值类**（车速、是否超速）| **本地标定 + 轨迹计算** | 这是测量问题，AI 从图像无法完成 |
| **语义类**（是否违停、是否闯红灯、是否压线）| **云端 AI** | 这是理解问题，视觉模型强项 |

**所以正确的分工不是"让 AI 复核一切"，而是"AI 只做它擅长的语义核对"。**
这也是本项目"AI 不作仲裁者"红线的一种具体落实。

---

## 六、待办

| # | 事项 | 说明 |
|---|---|---|
| **P0** | **标定超速类事件的处置策略** | 未标定时超速**不应送 AI 复核**（AI 必然说无法测速，白白消耗 token 并造成 rejected）。建议：未标定 → 事件标记为"数值待标定"，不进入 AI 复核队列 |
| P1 | 按事件类型决定是否送云端 | 语义类（违停/闯红灯/压车线）送；数值类（超速）仅在已标定时送 |
| P1 | 重新验证 364 条 rejected | 修复后用同样视频重跑，观察 rejected 比例是否下降（**需要真实违规素材**） |
| P2 | 关键帧/证据链落库 | 实测「无证据链 541 条 (100%)」—— `evidence_chain` 字段从未写入 |
| P2 | `yolo` 节点置信度恒为 0 | `ai_trace.yolo.confidence = 0.0`，应写入真实检测置信度 |

---

## 七、可复现命令

```powershell
# 1) 看状态分布与 ai_confidence 是否 min==max
& C:\miniconda\envs\zhitong-gpu\python.exe -c "..."   # 见 _scripts 下审计脚本

# 2) 解析 ai_judgment 看云端真实回答
#    注意：ai_judgment 是"字符串套字符串"，需二次 json.loads

# 3) 验证多帧合并
& C:\miniconda\envs\zhitong-gpu\python.exe E:\output\_scripts\_verify_context_frames.py
```

产出文件：
- `E:\output\_events_audit2.md` — 状态分布与证据链完整度
- `E:\output\_ai_node.md` — 云端真实回答解析
- `E:\output\_context_frames_test.md` — 多帧合并与云端调用实测
- `E:\output\_prompt_test.md` — 新 prompt 生成效果
- `E:\output\_screens\context_merged.jpg` — 合并后的多帧图（2880x432）
