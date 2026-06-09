#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
视频预处理功能测试脚本
"""

import os
import sys
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from video_dataset import VideoDatasetManager, PreprocessingConfig

def create_test_video(output_path, duration=3, fps=10):
    """创建测试视频"""
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        print(f"无法创建视频文件: {output_path}")
        return None
    
    # 生成渐变帧模拟视频
    for i in range(duration * fps):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 创建渐变效果
        for y in range(height):
            for x in range(width):
                frame[y, x] = [
                    int(255 * (x / width)),
                    int(255 * (y / height)),
                    int(128 + 127 * np.sin(i / 10.0))
                ]
        
        # 添加一些模拟的车辆和违规标记
        cv2.putText(frame, f'Frame {i}', (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"创建测试视频: {output_path}")
    return output_path

def test_preprocessing():
    """测试视频预处理功能"""
    print("="*60)
    print("测试视频预处理功能")
    print("="*60)
    
    # 初始化配置
    config = Config()
    config.create_dirs()
    
    # 创建测试视频
    test_videos = []
    violation_types = ['red_light', 'no_helmet', 'wrong_way']
    
    for violation_type in violation_types:
        video_path = os.path.join(config.RAW_VIDEO_DIR, f'test_{violation_type}.mp4')
        result = create_test_video(video_path)
        if result:
            test_videos.append(video_path)
    
    print(f"\n创建了 {len(test_videos)} 个测试视频")
    
    # 创建数据集管理器
    dataset_manager = VideoDatasetManager(config)
    
    # 扫描视频
    videos = dataset_manager.scan_videos()
    print(f"\n扫描到 {len(videos)} 个视频文件")
    
    # 打印视频信息
    for video in videos:
        print(f"视频: {video.video_name}, 时长: {video.duration:.2f}s, "
              f"分辨率: {video.width}x{video.height}, 违规类型: {video.violation_type}")
    
    # 设置预处理配置
    preprocess_config = PreprocessingConfig(
        target_width=640,
        target_height=640,
        frame_interval=2,
        augment_enabled=True,
        histogram_equalization=True,
        dehazing_enabled=True,
        max_frames_per_video=10
    )
    
    # 预处理视频
    print("\n开始预处理视频...")
    processed_files = dataset_manager.preprocess_videos(videos, preprocess_config)
    print(f"预处理完成，共处理 {len(processed_files)} 帧")
    
    # 获取数据集统计
    stats = dataset_manager.get_dataset_statistics()
    print("\n数据集统计:")
    for violation_type, count in stats.items():
        print(f"  {violation_type}: {count} 帧")
    
    # 创建数据集yaml文件
    yaml_path = dataset_manager.create_dataset_yaml()
    print(f"\n数据集配置文件已创建: {yaml_path}")
    
    # 读取并打印yaml内容
    with open(yaml_path, 'r', encoding='utf-8') as f:
        print("\n数据集配置内容:")
        print(f.read())
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == '__main__':
    test_preprocessing()