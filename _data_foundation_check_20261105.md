# 智瞳灵声 · 数据地基核查（2026-11-05 第二轮）

> 上一轮结论：[`_innovation_research_20261105.md`](_innovation_research_20261105.md)
> 本轮目的：验证「设施归因」这个创新点是否真的能算出来。
> 结论：**能算，但数据地基现在是空的——必须先修 4 个 bug，否则任何分析都是在空表上做文章。**

---

## 一、致命发现：轨迹只有 1 个点

### 实测

```
事件总数 2674   有 trajectory 字段 2674 (100%)
轨迹点数量: min=1  max=1  avg=1.0
```

**2674 条事件，每条的轨迹都只有 1 个点。** 这不是抽样，是全量。

### 根因（代码级确认）

`traffic_event_engine.py:479-486`：

```python
def _extract_trajectory(self, vehicle_info: Dict) -> List[Dict[str, Any]]:
    """从车辆信息提取轨迹点（简化版，真实场景从 tracker 获取）"""
    bbox = vehicle_info.get('bbox', [])
    if not bbox or len(bbox) < 4:
        return []
    cx = (bbox[0] + bbox[2]) / 2
    cy = (bbox[1] + bbox[3]) / 2
    return [{'x': cx, 'y': cy, 'timestamp': time.time()}]
```

**注释自己写了「简化版，真实场景从 tracker 获取」——但从来没接上。**

上游其实有完整数据。`vehicle_tracker.py` 里：

```python
MAX_HISTORY = 30          # 最多 30 个点
...
new_vehicles[self.next_id] = {
    ...
    'history': history,   # 每个车都带着完整轨迹历史
}
```

但 `_extract_vehicle_info`（`traffic_event_engine.py:302-334`）**只取了 7 个字段**，没有 `history`：

```python
return {
    'track_id': ..., 'bbox': ..., 'class_name': ...,
    'confidence': ..., 'speed': ..., 'direction': ..., 'plate_number': ...
    # ← 没有 history
}
```

**数据在追踪器里有，在事件引擎门口被丢了。** 修法：加一行 `'history': v_info.get('history', [])`，再让 `_extract_trajectory` 用它。

### 为什么这卡死创新点

候选 A 的「必然压线度」和「视距充分性」两个判据，**都依赖多帧轨迹**：
- 视距充分性 = 从车辆入画到停止线，有多少帧可反应 → 需要轨迹序列
- 必然压线度 = 轨迹到 lane_lines 的距离序列 → 需要轨迹序列

**1 个点算不出「序列」。**

---

## 二、第二个发现：lane_lines 全部缺失

### 实测（4 个标定场景全查）

| 场景 | crosswalk | **lane_lines** | stop_line_y | road_zones | pixel_per_meter | 帧宽 |
|---|---|---|---|---|---|---|
| dual_cam_h264（演示主力） | 1 项 | **缺** | 511 | 1 项 | **缺** | 1920 |
| dual_cam_lossless | 1 项 | **缺** | 511 | 1 项 | **缺** | 1920 |
| ea1ca6cb（旧B站视频） | 1 项 | **缺** | 415 | **缺** | 10.0 | 1280 |
| test1 | 0 项 | **缺** | 220 | 1 项 | **缺** | 960 |

**`lane_lines` 四个场景全缺。** 而「必然压线度」判据必须靠它。

同时：**只有 1 个场景（ea1ca6cb）有 `pixel_per_meter` 和 `lane_width_px`**，但那正是**色调有问题的旧素材**（项目手册明写「勿用于演示」）。演示主力 `dual_cam_h264` 两个都没有 → 车速只能走 `assumed` 粗估。

### 这意味着什么

「必然压线度」现在**算不了**。补它需要人工在 CalibrationPanel 里点车道线——**这是只有你能做的 GUI 操作**（按 AGENTS 第 6 条，你有眼睛、能操作界面，我没有）。

---

## 三、上一轮结论的修正

| 上一轮我说的 | 本轮实测 | 修正 |
|---|---|---|
| 「轨迹数据存在，可算判据」 | 只有 1 个点 | ❌ **错了**，需要先修 bug |
| 「标定数据存在（crosswalk/stop_line/road_zones）」 | 对，但这些不足以算「必然违章」 | ⚠️ **不完整**，缺 lane_lines 和 ppm |
| 「2674 条事件可聚类做点位分析」 | 能聚类，但聚类只能算「哪里违章多」，**算不出「为什么」** | ⚠️ 降级为「热点统计」，不是「设施归因」 |

**诚实交代**：上一轮我把「字段存在」当成了「数据可用」。这是同一个病——**没量到具体值就下结论**（对应我的 R5「静态值当运行值」）。

---

## 四、四个 bug 的完整清单（全部免费修）

| # | Bug | 影响 | 修法 | 工作量 |
|---|---|---|---|---|
| **B1** | 证据链键名读错（`traffic_light` vs `traffic_light_state`） | 2674/2674 条证据链的灯态/停止线/车道/地点/车牌**全空** | 改 3 个键名 | 10 分钟 |
| **B2** | 轨迹只有 1 个点 | 所有轨迹分析失效 | `_extract_vehicle_info` 加 `history` + 重写 `_extract_trajectory` | 1 小时 |
| **B3** | 申诉 0 条 | 「申诉闭环」卖点是空的 | 端到端跑通一次 | 半天 |
| **B4** | 逆行判定只用画面级 `road_direction` | 逆行占 39.5%（异常高），大概率误判 | 加车道级方向配置 | 1 天 |

**B1+B2 是地基**：修完，「证据链完整可追溯」这个核心卖点才第一次成立。

---

## 五、修完之后，创新点还剩什么

### 判据可行性重排（基于真实数据）

| 判据 | 需要什么 | 现状 | 修 B1+B2 后 | 还需补什么 |
|---|---|---|---|---|
| **视距充分性** | stop_line_y ✅ + 多帧轨迹 | 轨迹 1 点 ❌ | ✅ **可算** | 无 |
| **可辨识度** | crosswalk_zones ✅ + 帧尺寸 ✅ | ✅ | ✅ **可算** | 无 |
| **必然压线度** | lane_lines ❌ + 多帧轨迹 | 全缺 ❌ | ❌ | **需你标车道线** |

**结论：修完 B1+B2，三个判据里两个立刻可算。** 第三个需要你花 10 分钟在界面上点几条车道线。

### 但「设施归因」的说服力有个硬上限

只有 **4 个场景**，其中 3 个是同一个点位（dual_cam 的两版 + test1），实际独立点位 **≤2 个**。

**2 个点位的「设施风险分」在答辩时说服力很弱**——评委一句「你就一个路口，怎么证明这是通用方法」就穿了。

**要么补点位，要么换叙事**：
- 补点位：需要更多视频素材（你的资源，我没有）
- 换叙事：不讲「诊断设施」，讲「**同一套数据既能判违章、又能反查设置问题**」——这是**方法可迁移性**，不是统计显著性

---

## 六、我的建议：先修地基，再谈创新

### 为什么顺序必须是这样

```
现在：数据看起来有，实际是空的
  ↓
修 B1+B2（半天）
  ↓
第一次拥有「完整证据链 + 真实轨迹」
  ↓
这时才能：
  ① 验证创新点成不成立
  ② 答辩时说「证据链完整」（这本身就是加分项）
  ③ 让 AI 复核有真材料可看（现在送审的都是空壳）
```

**反过来说**：不修地基就直接做「设施归因」，等于在空表上做统计——**做出来的东西自己都不敢信**。

### 分三步走

| 步 | 内容 | 工作量 | 谁做 |
|---|---|---|---|
| **1** | 修 B1（证据链键名）+ B2（轨迹） | 半天 | 我 |
| **2** | 重跑一段演示视频，看真实轨迹长什么样 | 半小时 | 我（跑）+ 你看结果 |
| **3** | 用真实轨迹算「视距充分性」，看有没有区分度 | 半天 | 我 |
| — | **如果第 3 步算不出区分度 → 候选 A 不成立，我当场告诉你** | — | — |

**第 3 步是关键闸门。** 我不会在没验证的情况下往下做。

---

## 七、需要你定的

### 决策 1：先修地基，还是先补创新点？

- **A（推荐）先修 B1+B2**：半天，让数据第一次变真。修完才谈创新。
- B 直接做创新点：在空数据上做，做出来的东西不可信。
- C 先补点位（更多视频素材）：需要你提供素材，且不解决「数据是空的」这个根本问题。

### 决策 2：车道线标注谁来做？

「必然压线度」需要 `lane_lines`，四个场景全缺。补它有两条路：
- **你在 CalibrationPanel 点**（约 10 分钟/场景，4 个场景 40 分钟）——你有 GUI 操作能力，我没有
- 我写自动检测（`scene_annotation.auto_detect_*` 已有 `auto_detect_crosswalk` / `auto_detect_stop_line`，**但没有车道线检测**）——要新写，且准确率未知

**我推荐你先点一个场景**，看效果再决定其余三个。

### 决策 3：点位只有 2 个，叙事怎么办？

- 补素材（你提供更多路口的视频）
- 改讲「方法可迁移」而不是「统计显著」

我倾向后者——**在只有 2 个点位的情况下硬讲统计，是给自己挖坑。**

---

## 八、可复跑命令

```bash
# 轨迹点数（核心证据）
cd E:/output/1/api && PYTHONIOENCODING=utf-8 C:/miniconda/envs/zhitong-gpu/python.exe -c "
import sqlite3, json
c=sqlite3.connect('zhitong_violations.db')
lens=[]
for (ec,) in c.execute('select evidence_chain from traffic_events where evidence_chain is not null'):
    d=json.loads(ec); t=d.get('trajectory') or []
    if t: lens.append(len(t))
print('有轨迹', len(lens), '点数 min/max/avg:', min(lens), max(lens), sum(lens)/len(lens))"

# 各场景几何完整度
cd E:/output/1/api/output/scene_configs && for f in *.json; do
  echo "$f"; python -c "import json;d=json.load(open('$f',encoding='utf-8'));
[print(' ',k,'=',('缺' if d.get(k) is None else d[k])) for k in ['lane_lines','stop_line_y','pixel_per_meter','lane_width_px']]"
done

# 轨迹 bug 位置
sed -n '479,486p' E:/output/1/api/traffic_event_engine.py
sed -n '302,334p' E:/output/1/api/traffic_event_engine.py
```
