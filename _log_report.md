# 后端日志分析（api-boot4.err，247 行）


## 1) 唯一警告/错误（按次数排序）

- **[3x]** `2026-10-02 02:54:59 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[2x]** `2026-10-02 02:55:50 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[2x]** `2026-10-02 02:55:52 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:00 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:08 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:37 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:43 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:46 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:53 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:55:57 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`
- **[1x]** `2026-10-02 02:56:04 - zhitong_api - WARNING - [RealtimeDetector] �¼� evt_<ID> �ƶ� AI ����ʧ��: Unknown format code 'f' for object of type 'str'`

## 2) 云端协作 / 豆包 相关（最近 30 条）

命中 143 行

- `2026-10-02 02:55:59 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1131ms context_frames=4`
- `2026-10-02 02:55:59 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=wrong_way confidence=0.75`
- `2026-10-02 02:56:00 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1205ms context_frames=4`
- `2026-10-02 02:56:00 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:02 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1560ms context_frames=4`
- `2026-10-02 02:56:03 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:04 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1046ms context_frames=4`
- `2026-10-02 02:56:04 - zhitong_api - INFO - [CloudCollaborator] URGENT����: type=wrong_way confidence=0.75`
- `2026-10-02 02:56:04 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:56:05 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=urgent doubao_success=False deepseek_success=True duration=951ms context_frames=4`
- `2026-10-02 02:56:05 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=wrong_way confidence=0.75`
- `2026-10-02 02:56:06 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1071ms context_frames=4`
- `2026-10-02 02:56:07 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:08 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1188ms context_frames=4`
- `2026-10-02 02:56:08 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=wrong_way confidence=0.74`
- `2026-10-02 02:56:09 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=831ms context_frames=4`
- `2026-10-02 02:56:09 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:10 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=816ms context_frames=4`
- `2026-10-02 02:56:10 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=wrong_way confidence=0.74`
- `2026-10-02 02:56:11 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=965ms context_frames=4`
- `2026-10-02 02:56:11 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:12 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=914ms context_frames=4`
- `2026-10-02 02:56:13 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:14 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1026ms context_frames=4`
- `2026-10-02 02:56:14 - zhitong_api - INFO - [CloudCollaborator] URGENT����: type=wrong_way confidence=0.75`
- `2026-10-02 02:56:15 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=urgent doubao_success=False deepseek_success=True duration=1130ms context_frames=4`
- `2026-10-02 02:56:15 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:17 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1062ms context_frames=4`
- `2026-10-02 02:56:17 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:18 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=934ms context_frames=4`

## 3) 事件生命周期相关（最近 20 条）

- `2026-10-02 02:55:37 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880932165_6_627ee7 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880932165_6_627ee7.mp4`
- `2026-10-02 02:55:37 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=wrong_way clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:43 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880937717_3_ba1536 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880937717_3_ba1536.mp4`
- `2026-10-02 02:55:43 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=wrong_way clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:46 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880940913_59_e6760d ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880940913_59_e6760d.mp4`
- `2026-10-02 02:55:46 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=speeding clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:50 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880945296_77_b012b9 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880945296_77_b012b9.mp4`
- `2026-10-02 02:55:50 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880945296_76_0154b0 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880945296_76_0154b0.mp4`
- `2026-10-02 02:55:50 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=speeding clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:50 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=speeding clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:52 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880946886_69_40d4d3 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880946886_69_40d4d3.mp4`
- `2026-10-02 02:55:52 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=147 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:52 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880946886_75_f5c6c8 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880946886_75_f5c6c8.mp4`
- `2026-10-02 02:55:52 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=147 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:53 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880948235_68_5b2b1c ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880948235_68_5b2b1c.mp4`
- `2026-10-02 02:55:53 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=146 key_frames=5 trajectory_points=1`
- `2026-10-02 02:55:57 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880952556_72_c65c57 ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880952556_72_c65c57.mp4`
- `2026-10-02 02:55:57 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=147 key_frames=5 trajectory_points=1`
- `2026-10-02 02:56:04 - zhitong_api - INFO - [RealtimeDetector] �¼� evt_1790880959082_89_e7e47d ��Ƶ�ѱ���: E:\output\1\api\output\event_videos\20261002\evt_1790880959082_89_e7e47d.mp4`
- `2026-10-02 02:56:04 - zhitong_api - INFO - [CloudCollaborator] analyze_event ��ʼ: type=illegal_parking clip_frames=146 key_frames=5 trajectory_points=1`

## 4) 日志最后 15 行

- `2026-10-02 02:56:12 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=914ms context_frames=4`
- `2026-10-02 02:56:12 - zhitong_api - INFO - [RealtimeDetector] ֤���ѱ���: E:\output\1\api\uploads\realtime_illegal_parking_illegal_parking_illegal_parking_illegal_parking_illegal_parking_20261002_025612.jpg`
- `2026-10-02 02:56:13 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:14 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1026ms context_frames=4`
- `2026-10-02 02:56:14 - zhitong_api - INFO - [RealtimeDetector] ֤���ѱ���: E:\output\1\api\uploads\realtime_illegal_parking_illegal_parking_illegal_parking_illegal_parking_illegal_parking_20261002_025614.jpg`
- `2026-10-02 02:56:14 - zhitong_api - INFO - [CloudCollaborator] URGENT����: type=wrong_way confidence=0.75`
- `2026-10-02 02:56:15 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=urgent doubao_success=False deepseek_success=True duration=1130ms context_frames=4`
- `2026-10-02 02:56:15 - zhitong_api - INFO - [RealtimeDetector] ֤���ѱ���: E:\output\1\api\uploads\realtime_wrong_way_illegal_parking_illegal_parking_illegal_parking_illegal_parking_illegal_parking_20261002_025615.jpg`
- `2026-10-02 02:56:15 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:17 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=1062ms context_frames=4`
- `2026-10-02 02:56:17 - zhitong_api - INFO - [RealtimeDetector] ֤���ѱ���: E:\output\1\api\uploads\realtime_illegal_parking_illegal_parking_illegal_parking_illegal_parking_illegal_parking_20261002_025617.jpg`
- `2026-10-02 02:56:17 - zhitong_api - INFO - [CloudCollaborator] CONSULT����: type=illegal_parking confidence=0.70`
- `2026-10-02 02:56:18 - zhitong_api - INFO - [CloudCollaborator] ˫ͼ�ƶ�Э����� reason=consult doubao_success=False deepseek_success=True duration=934ms context_frames=4`
- `2026-10-02 02:56:18 - zhitong_api - INFO - [RealtimeDetector] ֤���ѱ���: E:\output\1\api\uploads\realtime_illegal_parking_illegal_parking_illegal_parking_illegal_parking_20261002_025618.jpg`
- `2026-10-02 02:56:18 - zhitong_api - INFO - [RealtimeDetector] �����ֹͣ`
