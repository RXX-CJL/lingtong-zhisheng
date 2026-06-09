#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
交通违规视频采集与预处理脚本

该脚本用于从互联网获取交通违规相关视频资源，筛选符合训练要求的高质量视频素材，
按照系统指定的格式和规范进行预处理，然后将处理后的视频数据导入到检测训练系统中，
以用于模型的训练和优化。

功能特性：
1. 从互联网搜索和下载交通违规视频
2. 支持多种违规类型：闯红灯、未戴头盔、逆行、违停、压线、超速
3. 视频预处理：尺寸调整、直方图均衡化、去雾处理、数据增强
4. 生成YOLO格式的数据集配置文件
5. 自动生成训练/测试集分割
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from video_downloader import TrafficViolationVideoCollector
from video_dataset import VideoDatasetManager, PreprocessingConfig

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='交通违规视频采集与预处理脚本')
    
    parser.add_argument('--collect', action='store_true', 
                        help='是否采集视频（从互联网下载）')
    parser.add_argument('--preprocess', action='store_true', 
                        help='是否预处理视频')
    parser.add_argument('--violation-types', type=str, nargs='+',
                        default=['red_light', 'no_helmet', 'wrong_way', 
                                'illegal_parking', 'lane_departure', 'speeding'],
                        help='要采集的违规类型列表')
    parser.add_argument('--count-per-type', type=int, default=3,
                        help='每种违规类型采集的视频数量')
    parser.add_argument('--frame-interval', type=int, default=2,
                        help='帧提取间隔')
    parser.add_argument('--max-frames', type=int, default=50,
                        help='每个视频最多提取的帧数')
    parser.add_argument('--target-width', type=int, default=640,
                        help='目标帧宽度')
    parser.add_argument('--target-height', type=int, default=640,
                        help='目标帧高度')
    parser.add_argument('--enable-augmentation', action='store_true', default=True,
                        help='是否启用数据增强')
    parser.add_argument('--enable-dehazing', action='store_true', default=True,
                        help='是否启用去雾处理')
    parser.add_argument('--skip-downloaded', action='store_true', default=True,
                        help='是否跳过已下载的视频')
    
    return parser.parse_args()

def collect_videos(collector, violation_types, count_per_type):
    """采集视频"""
    print("\n" + "="*60)
    print("开始采集交通违规视频")
    print("="*60)
    
    downloaded_files = []
    
    for violation_type in violation_types:
        print(f"\n--- 采集 {violation_type} 类型视频 ---")
        
        try:
            files = collector.collect_videos(
                violation_types=[violation_type],
                count_per_type=count_per_type
            )
            downloaded_files.extend(files)
            print(f"成功采集 {len(files)} 个视频")
        except Exception as e:
            print(f"采集 {violation_type} 视频失败: {str(e)}")
    
    print(f"\n视频采集完成，共采集 {len(downloaded_files)} 个视频")
    return downloaded_files

def preprocess_videos(dataset_manager, preprocess_config):
    """预处理视频"""
    print("\n" + "="*60)
    print("开始预处理视频")
    print("="*60)
    
    # 扫描视频文件
    videos = dataset_manager.scan_videos()
    print(f"发现 {len(videos)} 个视频文件")
    
    if not videos:
        print("未找到视频文件，请先采集视频")
        return []
    
    # 打印视频信息
    print("\n视频列表:")
    for i, video in enumerate(videos, 1):
        status = "已处理" if video.processed else "未处理"
        print(f"{i}. {video.video_name} | 时长: {video.duration:.2f}s | "
              f"分辨率: {video.width}x{video.height} | 违规类型: {video.violation_type} | {status}")
    
    # 预处理视频
    processed_files = dataset_manager.preprocess_videos(videos, preprocess_config)
    print(f"\n预处理完成，共处理 {len(processed_files)} 帧")
    
    return processed_files

def generate_dataset(dataset_manager):
    """生成数据集配置"""
    print("\n" + "="*60)
    print("生成数据集配置")
    print("="*60)
    
    # 获取数据集统计
    stats = dataset_manager.get_dataset_statistics()
    print("\n数据集统计:")
    total_frames = 0
    for violation_type, count in stats.items():
        print(f"  {violation_type}: {count} 帧")
        total_frames += count
    print(f"  总计: {total_frames} 帧")
    
    # 创建数据集yaml文件
    yaml_path = dataset_manager.create_dataset_yaml()
    print(f"\n数据集配置文件已创建: {yaml_path}")
    
    # 生成训练/测试集分割
    split = dataset_manager.generate_train_test_split(train_ratio=0.8)
    print(f"\n训练集: {len(split['train'])} 帧")
    print(f"测试集: {len(split['test'])} 帧")
    
    # 保存分割信息
    split_info = {
        'train': [{'path': frame[0], 'label': frame[1]} for frame in split['train']],
        'test': [{'path': frame[0], 'label': frame[1]} for frame in split['test']],
        'timestamp': datetime.now().isoformat(),
        'train_ratio': 0.8
    }
    
    split_file = os.path.join(dataset_manager.config.DATA_DIR, 'train_test_split.json')
    import json
    with open(split_file, 'w', encoding='utf-8') as f:
        json.dump(split_info, f, ensure_ascii=False, indent=2)
    
    print(f"训练/测试集分割信息已保存: {split_file}")
    
    return stats

def main():
    """主函数"""
    args = parse_arguments()
    
    # 初始化配置
    config = Config()
    config.create_dirs()
    
    print("\n" + "*"*60)
    print("智瞳交通违规视频采集与预处理系统")
    print("*"*60)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"项目目录: {config.BASE_DIR}")
    print(f"原始视频目录: {config.RAW_VIDEO_DIR}")
    print(f"处理后帧目录: {config.PROCESSED_FRAMES_DIR}")
    print("*"*60)
    
    # 创建视频采集器
    collector = TrafficViolationVideoCollector(config)
    
    # 创建数据集管理器
    dataset_manager = VideoDatasetManager(config)
    
    # 采集视频
    if args.collect:
        collect_videos(collector, args.violation_types, args.count_per_type)
    
    # 预处理视频
    if args.preprocess:
        preprocess_config = PreprocessingConfig(
            target_width=args.target_width,
            target_height=args.target_height,
            frame_interval=args.frame_interval,
            augment_enabled=args.enable_augmentation,
            histogram_equalization=True,
            dehazing_enabled=args.enable_dehazing,
            max_frames_per_video=args.max_frames
        )
        preprocess_videos(dataset_manager, preprocess_config)
    
    # 生成数据集
    if args.preprocess:
        generate_dataset(dataset_manager)
    
    print("\n" + "*"*60)
    print("任务完成！")
    print("*"*60)

if __name__ == '__main__':
    main()