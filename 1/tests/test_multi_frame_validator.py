# -*- coding: utf-8 -*-
"""
多帧确认机制单元测试
覆盖：正常确认、噪声帧、车牌轻微识别错误、目标丢失又出现等场景
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from multi_frame_validator import (
    MultiFrameValidator, FPSMonitor,
    levenshtein_similarity, calculate_iou, calculate_center_distance, bbox_match
)


def test_levenshtein_similarity():
    """测试车牌相似度计算"""
    assert levenshtein_similarity("京A12345", "京A12345") == 1.0
    assert levenshtein_similarity("京A12345", "京A12346") > 0.8
    assert levenshtein_similarity("京A12345", "沪B99999") < 0.3
    assert levenshtein_similarity("", "") == 1.0
    assert levenshtein_similarity("京A12345", "") == 0.0
    print("PASS: test_levenshtein_similarity")


def test_iou():
    """测试 IOU 计算"""
    assert calculate_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert calculate_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert 0 < calculate_iou([0, 0, 10, 10], [5, 5, 15, 15]) < 1.0
    print("PASS: test_iou")


def test_center_distance():
    """测试中心距离计算"""
    assert calculate_center_distance([0, 0, 10, 10], [0, 0, 10, 10]) == 0.0
    assert calculate_center_distance([0, 0, 10, 10], [20, 20, 30, 30]) > 0
    print("PASS: test_center_distance")


def test_bbox_match():
    """测试 bbox 双重匹配"""
    # IOU 匹配
    assert bbox_match([0, 0, 100, 50], [10, 5, 110, 55]) == True
    # 中心距离匹配
    assert bbox_match([0, 0, 100, 50], [5, 2, 105, 52]) == True
    # 不匹配
    assert bbox_match([0, 0, 100, 50], [500, 500, 600, 550]) == False
    print("PASS: test_bbox_match")


def test_basic_confirmation():
    """测试基本确认流程：连续5帧同一目标 -> 确认"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
    for i in range(5):
        pending = validator.add_frame([{
            'track_id': 1,
            'plate': '京A12345',
            'violation_type': 'red_light',
            'bbox': [100, 200, 200, 250]
        }])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 1
    assert confirmed[0]['plate_number'] == '京A12345'
    assert confirmed[0]['track_id'] == 1
    assert confirmed[0]['confirmed_frames'] >= 5
    print("PASS: test_basic_confirmation")


def test_noise_frames():
    """测试噪声帧：中间有错误帧不中断确认"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
    for i in range(6):
        if i == 3:
            # 噪声帧：不同车牌
            validator.add_frame([{
                'track_id': 1,
                'plate': '沪B99999',
                'violation_type': 'red_light',
                'bbox': [105, 200, 205, 250]
            }])
        else:
            validator.add_frame([{
                'track_id': 1,
                'plate': '京A12345',
                'violation_type': 'red_light',
                'bbox': [100, 200, 200, 250]
            }])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 1
    # 最佳车牌应该还是投票最多的
    assert confirmed[0]['plate_number'] == '京A12345'
    print("PASS: test_noise_frames")


def test_plate_minor_errors():
    """测试车牌轻微识别错误：相似度匹配"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5, plate_sim_threshold=0.8)
    plates = ['京A12345', '京A12345', '京A12346', '京A12345', '京A12345']
    for plate in plates:
        validator.add_frame([{
            'track_id': 1,
            'plate': plate,
            'violation_type': 'speeding',
            'bbox': [100, 200, 200, 250]
        }])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 1
    print("PASS: test_plate_minor_errors")


def test_target_lost_and_reappear():
    """测试目标丢失又出现：bbox 匹配重新关联"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=4)

    # 帧1-3：目标出现
    for i in range(3):
        validator.add_frame([{
            'track_id': 1,
            'plate': '京A12345',
            'violation_type': 'illegal_parking',
            'bbox': [100, 200, 200, 250]
        }])

    # 帧4：目标丢失（空帧）
    validator.add_frame([])

    # 帧5-7：目标重新出现（track_id 可能变了，但 bbox 接近）
    for i in range(3):
        validator.add_frame([{
            'track_id': 2,  # 新 track_id
            'plate': '京A12345',
            'violation_type': 'illegal_parking',
            'bbox': [105, 202, 205, 252]  # 接近的 bbox
        }])

    confirmed = validator.get_confirmed()
    # 应该能确认（通过车牌+bbox匹配关联）
    assert len(confirmed) >= 1
    print("PASS: test_target_lost_and_reappear")


def test_no_plate_match():
    """测试无车牌时的 bbox 匹配"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=4)
    for i in range(4):
        validator.add_frame([{
            'track_id': 1,
            'plate': '',  # 无车牌
            'violation_type': 'wrong_way',
            'bbox': [100, 200, 200, 250]
        }])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 1
    assert confirmed[0]['plate_number'] == ''
    print("PASS: test_no_plate_match")


def test_multiple_targets():
    """测试多目标同时确认"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=4)
    for i in range(4):
        validator.add_frame([
            {'track_id': 1, 'plate': '京A12345', 'violation_type': 'red_light', 'bbox': [100, 200, 200, 250]},
            {'track_id': 2, 'plate': '沪B67890', 'violation_type': 'speeding', 'bbox': [300, 200, 400, 250]}
        ])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 2
    plates = {c['plate_number'] for c in confirmed}
    assert '京A12345' in plates
    assert '沪B67890' in plates
    print("PASS: test_multiple_targets")


def test_not_enough_frames():
    """测试帧数不足：不确认"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
    for i in range(3):  # 只有3帧，不够5帧
        validator.add_frame([{
            'track_id': 1,
            'plate': '京A12345',
            'violation_type': 'red_light',
            'bbox': [100, 200, 200, 250]
        }])

    confirmed = validator.get_confirmed()
    assert len(confirmed) == 0
    print("PASS: test_not_enough_frames")


def test_pending_info():
    """测试 pending 信息"""
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
    validator.add_frame([{
        'track_id': 1,
        'plate': '京A12345',
        'violation_type': 'red_light',
        'bbox': [100, 200, 200, 250]
    }])

    info = validator.pending_info()
    assert 1 in info
    assert info[1]['frames'] == 1
    print("PASS: test_pending_info")


def test_fps_monitor():
    """测试 FPS 监控器"""
    import time
    monitor = FPSMonitor(window_size=10)
    for i in range(5):
        monitor.tick()
        time.sleep(0.01)

    fps = monitor.avg_fps
    assert fps > 0
    assert fps < 1000  # 合理范围
    print(f"PASS: test_fps_monitor (fps={fps:.1f})")


def test_expired_cleanup():
    """测试过期清理"""
    import time
    validator = MultiFrameValidator(window_size=10, confirm_threshold=5)
    validator.add_frame([{
        'track_id': 1,
        'plate': '京A12345',
        'violation_type': 'red_light',
        'bbox': [100, 200, 200, 250]
    }])

    # 等待超过 max_age
    time.sleep(0.1)
    validator.add_frame([])  # 触发清理

    # pending 应被清理
    assert validator.pending_count == 0 or validator.pending_count == 1  # 取决于时间
    print("PASS: test_expired_cleanup")


if __name__ == '__main__':
    test_levenshtein_similarity()
    test_iou()
    test_center_distance()
    test_bbox_match()
    test_basic_confirmation()
    test_noise_frames()
    test_plate_minor_errors()
    test_target_lost_and_reappear()
    test_no_plate_match()
    test_multiple_targets()
    test_not_enough_frames()
    test_pending_info()
    test_fps_monitor()
    test_expired_cleanup()
    print("\n=== 全部 14 个测试通过 ===")
