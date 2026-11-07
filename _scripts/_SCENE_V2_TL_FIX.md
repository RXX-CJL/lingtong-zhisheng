【配时永久改写 bug：已补修 + 单测 + 实机验证 15 盏灯全部回到 10/3/2】

## 先认账
你说得对：我 §6 只查了 actor 和机位，**没查红绿灯配时**，漏报了这块残留。odr=960/961/962 正是我测 12/2/15 那一组（灯组 id 9/20/18），确实被我留在世界里了。感谢代为恢复。
你的根因定位我复核确认无误：`_tl_apply_phase` 的 `set_*_time()` 是**永久改写**服务器那盏灯，而 `stop_custom_timing` 收尾只做 `reset_group()`（只重置相位）。我也核对了 `.bak_20261023` 第 1854/1914 行，同样写法 —— **确认第 1 批遗留，不是本次引入**。

## 一、改了哪几行（文件 2711 → 2752 行）
| 位置 | 行号 | 改动 |
|---|---|---|
| `__init__` | 44-130 | 新增 `self.tl_original_durations = {}`（键为 light id，值为绿/黄/红三元组） |
| `start_custom_timing` | 2371-2413 | 设完 `self.tl_durations` 后插入 `self._tl_snapshot_durations()`（第 2409 行） |
| `stop_custom_timing` | 2415-2440 | `reset_group()` 之后新增 `self._tl_restore_durations()`（第 2438 行） |
| `_tl_snapshot_durations` | 2477-2492 | **新增**。逐灯 `get_green/yellow/red_time()` 存快照；已有快照则不覆盖（防二次启动把改过的值当原值）；单灯失败跳过 |
| `_tl_restore_durations` | 2494-2512 | **新增**。逐灯写回；无快照直接返回 0（不瞎写）；写回后清空快照；单灯写失败 `continue` 吞异常 |
| `_tl_apply_phase` | 2514-2538 | **未改**（保持原样，不是问题点） |

按你要求的三个语义都实现了：①启动前快照 ②停止时写回 ③快照不存在跳过、写回失败吞异常。

## 二、离线单测：mock PASS=103 FAIL=0（原 86 → +17 条）
命令：`py -3.12 -X utf8 E:\output\_scripts\_verify_scene_v2_mock.py`
新增 17 条断言，覆盖你要求的那条链路 + 边界：
```
PASS tl original snapshot starts empty
PASS snapshot captured 2 lights | {901: (10.0, 3.0, 2.0), 902: (10.0, 3.0, 2.0)}
PASS snapshot green/yellow/red original
PASS snapshot not overwritten on second call
PASS durations changed by apply_phase | (12.0, 2.0, 15.0)
PASS second light also changed | (12.0, 2.0, 15.0)
PASS restore wrote back 2 lights | 2
PASS light A restored to 10/3/2 | (10.0, 3.0, 2.0)
PASS light B restored to 10/3/2 | (10.0, 3.0, 2.0)
PASS snapshot cleared after restore
PASS restore with no snapshot returns 0
PASS restore with no snapshot leaves lights untouched | (10.0, 3.0, 2.0)
PASS stop_custom_timing restored light A | (10.0, 3.0, 2.0)
PASS stop_custom_timing restored light B | (10.0, 3.0, 2.0)
PASS restore swallows write errors | 0
```
注意 `stop_custom_timing` 那两条是**走真实函数**（不是只调子方法），证明端到端接上了。

## 三、实机验证：15 盏灯是否全部回到 10/3/2 —— **是**
命令：`py -3.12 -X utf8 E:\output\_scripts\_verify_workshop_scene_v2.py`　→ **PASS=85 FAIL=0**（原 82 → +3）
脚本开头先打基线，中途断言，finally 再兜底：
```
BASELINE tl durations: [(10.0, 3.0, 2.0)] (n=15)
PASS custom timing restored | True
PASS tl green/yellow/red secs restored | 12.0 / 2.0 / 15.0
PASS stop_custom_timing restored tl durations to baseline
PASS FINAL all traffic lights back to baseline durations (15 lights) | {'drift': {}, 'new': set(), 'baseline': [(10.0, 3.0, 2.0)], 'now': [(10.0, 3.0, 2.0)]}
PASS FINAL traffic light count unchanged | (15, 15)
```
即：加载时正确恢复成 12/2/15 → stop 之后 15 盏**全部**回到 10/3/2，drift={} 无新增。

## 四、现场状态（复核，未改坏）
```
15 盏灯全部 (10.0, 3.0, 2.0)  ← 与地图原值一致，无残留
total actors 23
spectator loc=(-172.196579, 183.859116, 27.638052) yaw=-45.592487 pitch=0.000000
no .tmp
```
机位 yaw 与你的 -45.592178 差 0.0003 度（浮点往返噪声，与 actor 位置同理），loc 完全一致。

## 五、其余验收项复查（全部仍绿）
| 项 | 结果 |
|---|---|
| py_compile | exit=0 |
| 离线 GUI/自动存档/最近项目 | PASS=68 FAIL=0 |
| 序列化 mock（含配时单测） | PASS=103 FAIL=0 |
| 既有 GUI 回归 | PASS=35 FAIL=0 |
| 实机 round-trip | PASS=85 FAIL=0 |

## 六、K2 合规复查（你关心过）
`enable_constant_velocity` 全文仅 2 处，均非本次引入：
- 1186 行：注释文字
- 2634 行：`apply_target_speed` 内，第 1 批既有代码，未动
本次新增代码中出现次数 = **0**。

## 七、我的教训（写进心里）
「世界干净」不能只看 actor 数量。凡是**写进服务器的世界状态**（配时、天气、世界设置、隐藏物体）都要在收尾逐项断言还原。我已把配时这一项固化成脚本里的硬断言，下次同类任务会照此办理。

## 八、遗留说明
这个修复只覆盖 `stop_custom_timing` 正常调用路径。如果**程序崩溃**导致 stop 没跑到，配时仍会留在世界里（客户端进程没了，无法再写回）。这是进程级限制，若要彻底解决需要服务端侧或启动时记录基线，属另一件事，不在本次范围 —— 是否要做请你定。