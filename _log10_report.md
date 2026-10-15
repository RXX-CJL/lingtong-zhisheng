# 解耦验证日志分析（1526 行）


## 1) 关键事件计数

| 事件 | 次数 |
|---|---|
| 云端 worker 启动 | **0** |
| 云端咨询完成 | **0** |
| 云端咨询失败 | **0** |
| 入队失败 | **0** |
| 格式化错误(format code) | **0** |
| 帧处理异常 | **0** |
| 检测循环异常 | **0** |
| 画框失败 | **0** |

## 2) 日志级别统计

- INFO: 1520
- WARNING: 1

## 3) 云端相关样本（最多 8 条）

- `2026-10-03 00:21:10 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=True deepseek_success=True duration=5480ms context_frames=4`
- `2026-10-03 00:21:11 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=speeding clip_frames=0 key_frames=0 trajectory_points=1`
- `2026-10-03 00:21:11 - zhitong_api - INFO - [CloudCollaborator] analyze_event ���: type=speeding judgment=rejected confidence=0.05 elapsed=4909ms`
- `2026-10-03 00:21:11 - zhitong_api - INFO - [CloudCollaborator] analyze_event ���: type=wrong_way judgment=uncertain confidence=0.05 elapsed=5084ms`
- `2026-10-03 00:21:12 - zhitong_api - INFO - [CloudCollaborator] analyze_event ���: type=speeding judgment=rejected confidence=0.05 elapsed=1149ms`
- `2026-10-03 00:21:12 - zhitong_api - INFO - [CloudCollaborator] analyze_event ���: type=speeding judgment=rejected confidence=0.05 elapsed=6042ms`
- `2026-10-03 00:21:16 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=True deepseek_success=True duration=5623ms context_frames=4`
- `2026-10-03 00:21:21 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=True deepseek_success=True duration=5579ms context_frames=0`

## 4) WARNING/ERROR 样本（最多 10 条）

- [1x] `2026-10-03 00:21:11 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> ��Ƶ����ʧ��`

## 5) 最后 5 行

- `2026-10-03 00:21:12 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790958061193_202_499271 AI ������� state=rejected`
- `2026-10-03 00:21:16 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=True deepseek_success=True duration=5623ms context_frames=4`
- `2026-10-03 00:21:16 - zhitong_api - INFO - [RealtimeDetector] �ƶ���ѯ��ɣ��첽��: illegal_parking ��16��`
- `2026-10-03 00:21:21 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=True deepseek_success=True duration=5579ms context_frames=0`
- `2026-10-03 00:21:21 - zhitong_api - INFO - [RealtimeDetector] �ƶ���ѯ��ɣ��첽��: illegal_parking ��17��`
