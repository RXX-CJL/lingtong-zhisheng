# 事件闭环修复验证

- 启动前事件数: **26**


## 启动检测（修复后）

- HTTP 200: `{'success': True, 'message': '检测已启动'}`


## 观察 100 秒

| 时刻 | running | total | processed | 违规 | 事件数 |
|---|---|---|---|---|---|
| 10s | True | 146 | 8 | 5 | 31 |
| 20s | True | 292 | 15 | 12 | 32 |
| 30s | True | 438 | 22 | 19 | 32 |
| 40s | True | 585 | 30 | 27 | 32 |
| 50s | True | 731 | 37 | 34 | 33 |
| 60s | True | 878 | 46 | 41 | 38 |
| 70s | True | 1024 | 54 | 49 | 42 |
| 80s | True | 1170 | 61 | 56 | 43 |
| 90s | True | 1317 | 64 | 59 | 43 |
| 100s | True | 1464 | 64 | 59 | 43 |

- processed 增长: 8 -> 64 (+56)


## 新增事件的状态分布（关键指标）

- 新增 17 条，状态分布: `{'rejected': 17}`


| 事件ID | 类型 | 状态 | AI置信度 | 视频 |
|---|---|---|---|---|
| `evt_1790881278128_83_582bcf` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881268696_68_aca30d` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881267572_71_ef43dc` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881267572_66_31c698` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881267572_65_780db4` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881264649_57_251e1b` | speeding | **rejected** | 0.05 | Y |
| `evt_1790881264649_5_be341b` | speeding | **rejected** | 0.05 | Y |
| `evt_1790881261704_57_6834ea` | wrong_way | **rejected** | 0.05 | Y |
| `evt_1790881258933_7_32c611` | wrong_way | **rejected** | 0.05 | Y |
| `evt_1790881257629_3_00c0e5` | wrong_way | **rejected** | 0.05 | Y |
| `evt_1790881252609_6_8203e0` | wrong_way | **rejected** | 0.05 | Y |
| `evt_1790881223873_22_729f28` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881212570_9_487b2d` | illegal_parking | **rejected** | 0.05 | Y |
| `evt_1790881212570_5_3f05af` | illegal_parking | **rejected** | 0.05 | Y |

## 后端日志：'AI 分析失败' 是否消失

- 日志行数: 256
- **AI 分析失败 次数: 0** （修复前为 11 次）
- **format code 错误次数: 0** （修复前多次）
