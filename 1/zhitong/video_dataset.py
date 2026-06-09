import os
import cv2
import numpy as np
import json
import glob
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class VideoInfo:
    """视频信息数据类"""
    file_path: str
    video_name: str
    duration: float
    fps: float
    width: int
    height: int
    frame_count: int
    violation_type: str = None
    source_url: str = None
    processed: bool = False

@dataclass
class PreprocessingConfig:
    """预处理配置"""
    target_width: int = 640
    target_height: int = 640
    frame_interval: int = 1  # 每隔多少帧提取一帧
    output_format: str = 'jpg'  # jpg, png
    augment_enabled: bool = True
    histogram_equalization: bool = True
    dehazing_enabled: bool = False
    rainy_night_augmentation: bool = False
    max_frames_per_video: int = 100

class VideoDatasetManager:
    """视频数据集管理类"""
    
    def __init__(self, config):
        self.config = config
        self.raw_dir = config.RAW_VIDEO_DIR
        self.processed_dir = config.PROCESSED_FRAMES_DIR
        self.metadata_file = config.METADATA_FILE
        
        self._create_directories()
        self.metadata = self._load_metadata()
    
    def _create_directories(self):
        """创建必要的目录"""
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
    
    def _load_metadata(self):
        """加载视频元数据"""
        if os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_metadata(self):
        """保存视频元数据"""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def scan_videos(self, directory: Optional[str] = None) -> List[VideoInfo]:
        """扫描目录中的视频文件"""
        scan_dir = directory if directory else self.raw_dir
        video_extensions = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.flv']
        videos = []
        
        for ext in video_extensions:
            pattern = os.path.join(scan_dir, ext)
            for filepath in glob.glob(pattern):
                info = self._extract_video_info(filepath)
                if info:
                    videos.append(info)
        
        return videos
    
    def _extract_video_info(self, filepath: str) -> Optional[VideoInfo]:
        """提取视频文件信息"""
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return None
        
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            video_name = os.path.splitext(os.path.basename(filepath))[0]
            
            # 尝试从文件名推断违规类型
            violation_type = self._infer_violation_type(video_name)
            
            return VideoInfo(
                file_path=filepath,
                video_name=video_name,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                frame_count=frame_count,
                violation_type=violation_type
            )
        finally:
            cap.release()
    
    def _infer_violation_type(self, video_name: str) -> str:
        """从文件名推断违规类型"""
        violation_keywords = {
            'red_light': ['闯红灯', 'red_light', 'redlight', '红灯'],
            'no_helmet': ['未戴头盔', 'no_helmet', 'helmet', '头盔'],
            'wrong_way': ['逆行', 'wrong_way', 'reverse', 'opposite'],
            'illegal_parking': ['违停', '停车', 'parking', 'illegal_park'],
            'lane_departure': ['压线', '变道', 'lane', 'departure'],
            'speeding': ['超速', 'speeding', 'speed']
        }
        
        video_name_lower = video_name.lower()
        for violation_type, keywords in violation_keywords.items():
            for keyword in keywords:
                if keyword.lower() in video_name_lower:
                    return violation_type
        return 'unknown'
    
    def preprocess_videos(self, videos: List[VideoInfo], config: PreprocessingConfig) -> List[str]:
        """批量预处理视频"""
        processed_files = []
        
        for video in videos:
            if video.processed:
                continue
            
            try:
                result = self._preprocess_single_video(video, config)
                processed_files.extend(result)
                video.processed = True
                
                # 更新元数据
                self.metadata[video.video_name] = {
                    'file_path': video.file_path,
                    'violation_type': video.violation_type,
                    'processed': True,
                    'processed_frames': len(result),
                    'timestamp': datetime.now().isoformat()
                }
                self._save_metadata()
            except Exception as e:
                print(f"处理视频 {video.video_name} 失败: {str(e)}")
        
        return processed_files
    
    def _preprocess_single_video(self, video: VideoInfo, config: PreprocessingConfig) -> List[str]:
        """预处理单个视频"""
        cap = cv2.VideoCapture(video.file_path)
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video.file_path}")
        
        try:
            frames = []
            frame_count = 0
            saved_count = 0
            
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 按间隔提取帧
                if frame_count % config.frame_interval == 0:
                    # 调整尺寸
                    frame = self._resize_frame(frame, config.target_width, config.target_height)
                    
                    # 直方图均衡化
                    if config.histogram_equalization:
                        frame = self._apply_histogram_equalization(frame)
                    
                    # 去雾处理
                    if config.dehazing_enabled:
                        frame = self._apply_dehazing(frame)
                    
                    frames.append(frame)
                    saved_count += 1
                    
                    if saved_count >= config.max_frames_per_video:
                        break
                
                frame_count += 1
            
            # 数据增强
            if config.augment_enabled:
                frames = self._apply_augmentation(frames)
            
            # 保存帧
            return self._save_frames(frames, video.video_name, video.violation_type, config)
        
        finally:
            cap.release()
    
    def _resize_frame(self, frame: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
        """调整帧尺寸，保持宽高比并居中裁剪"""
        h, w = frame.shape[:2]
        scale = min(target_width / w, target_height / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        frame = cv2.resize(frame, (new_w, new_h))
        
        # 居中裁剪或填充
        pad_top = (target_height - new_h) // 2
        pad_bottom = target_height - new_h - pad_top
        pad_left = (target_width - new_w) // 2
        pad_right = target_width - new_w - pad_left
        
        return cv2.copyMakeBorder(frame, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT)
    
    def _apply_histogram_equalization(self, frame: np.ndarray) -> np.ndarray:
        """应用直方图均衡化"""
        if len(frame.shape) == 3:
            # 转换为YUV颜色空间
            yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            return cv2.equalizeHist(frame)
    
    def _apply_dehazing(self, frame: np.ndarray) -> np.ndarray:
        """应用去雾算法"""
        # 使用暗通道先验去雾
        dark_channel = self._get_dark_channel(frame, 15)
        atmospheric_light = self._estimate_atmospheric_light(frame, dark_channel)
        transmission = self._estimate_transmission(frame, atmospheric_light, 15, 0.95)
        return self._recover_scene(frame, transmission, atmospheric_light, 0.1)
    
    def _get_dark_channel(self, frame: np.ndarray, size: int) -> np.ndarray:
        """计算暗通道"""
        min_channel = cv2.min(cv2.min(frame[:, :, 0], frame[:, :, 1]), frame[:, :, 2])
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))
        return cv2.erode(min_channel, kernel)
    
    def _estimate_atmospheric_light(self, frame: np.ndarray, dark_channel: np.ndarray) -> float:
        """估计大气光"""
        h, w = dark_channel.shape
        num_pixels = h * w
        num_top_pixels = int(max(num_pixels * 0.001, 1))
        
        flat_dark = dark_channel.flatten()
        flat_frame = frame.reshape(-1, 3)
        
        indices = np.argpartition(flat_dark, -num_top_pixels)[-num_top_pixels:]
        top_pixels = flat_frame[indices]
        
        return np.mean(top_pixels, axis=0)
    
    def _estimate_transmission(self, frame: np.ndarray, atmospheric_light: float, size: int, omega: float) -> np.ndarray:
        """估计透射率"""
        normalized_frame = frame / atmospheric_light
        dark_channel = self._get_dark_channel(normalized_frame, size)
        return 1 - omega * dark_channel
    
    def _recover_scene(self, frame: np.ndarray, transmission: np.ndarray, atmospheric_light: float, t0: float) -> np.ndarray:
        """恢复场景"""
        transmission = np.maximum(transmission, t0)
        recovered = ((frame - atmospheric_light) / transmission[..., np.newaxis]) + atmospheric_light
        return np.clip(recovered, 0, 255).astype(np.uint8)
    
    def _apply_augmentation(self, frames: List[np.ndarray]) -> List[np.ndarray]:
        """应用数据增强"""
        augmented = []
        
        for frame in frames:
            augmented.append(frame)  # 原始帧
            
            # 随机水平翻转
            if np.random.random() > 0.5:
                augmented.append(cv2.flip(frame, 1))
            
            # 随机亮度调整
            if np.random.random() > 0.5:
                brightness = 0.8 + np.random.random() * 0.4
                augmented.append(cv2.convertScaleAbs(frame, alpha=brightness, beta=0))
            
            # 随机对比度调整
            if np.random.random() > 0.5:
                contrast = 0.8 + np.random.random() * 0.4
                augmented.append(cv2.convertScaleAbs(frame, alpha=contrast, beta=0))
        
        return augmented
    
    def _save_frames(self, frames: List[np.ndarray], video_name: str, violation_type: str, config: PreprocessingConfig) -> List[str]:
        """保存帧到文件系统"""
        saved_paths = []
        
        # 创建违规类型目录
        violation_dir = os.path.join(self.processed_dir, violation_type)
        os.makedirs(violation_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for i, frame in enumerate(frames):
            filename = f"{video_name}_{timestamp}_{i:04d}.{config.output_format}"
            filepath = os.path.join(violation_dir, filename)
            
            cv2.imwrite(filepath, frame)
            saved_paths.append(filepath)
        
        return saved_paths
    
    def generate_train_test_split(self, train_ratio: float = 0.8) -> Dict[str, List[str]]:
        """生成训练/测试集分割"""
        all_frames = []
        
        for violation_type in os.listdir(self.processed_dir):
            violation_dir = os.path.join(self.processed_dir, violation_type)
            if os.path.isdir(violation_dir):
                for frame_file in glob.glob(os.path.join(violation_dir, f'*.{self.config.output_format if hasattr(self.config, "output_format") else "jpg"}')):
                    all_frames.append((frame_file, violation_type))
        
        np.random.shuffle(all_frames)
        
        split_idx = int(len(all_frames) * train_ratio)
        train_set = all_frames[:split_idx]
        test_set = all_frames[split_idx:]
        
        return {
            'train': train_set,
            'test': test_set
        }
    
    def create_dataset_yaml(self, output_path: str = None) -> str:
        """创建YOLO格式的数据集yaml文件"""
        if output_path is None:
            output_path = self.config.DATASET_YAML
        
        # 获取所有违规类型
        violation_types = []
        for item in os.listdir(self.processed_dir):
            item_path = os.path.join(self.processed_dir, item)
            if os.path.isdir(item_path):
                violation_types.append(item)
        
        violation_types.sort()
        
        yaml_content = f"""path: {os.path.abspath(self.processed_dir)}
train: images/train
val: images/val
test: images/test

nc: {len(violation_types)}
names: {violation_types}
"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return output_path
    
    def get_dataset_statistics(self) -> Dict[str, int]:
        """获取数据集统计信息"""
        stats = {}
        
        for violation_type in os.listdir(self.processed_dir):
            violation_dir = os.path.join(self.processed_dir, violation_type)
            if os.path.isdir(violation_dir):
                frame_count = len(glob.glob(os.path.join(violation_dir, '*.jpg')))
                stats[violation_type] = frame_count
        
        return stats

# 示例使用
if __name__ == '__main__':
    from config import Config
    
    # 初始化配置和数据集管理器
    config = Config()
    dataset_manager = VideoDatasetManager(config)
    
    # 扫描视频文件
    videos = dataset_manager.scan_videos()
    print(f"发现 {len(videos)} 个视频文件")
    
    # 打印视频信息
    for video in videos:
        print(f"视频: {video.video_name}, 时长: {video.duration:.2f}s, 分辨率: {video.width}x{video.height}, 违规类型: {video.violation_type}")
    
    # 设置预处理配置
    preprocess_config = PreprocessingConfig(
        target_width=640,
        target_height=640,
        frame_interval=2,
        augment_enabled=True,
        histogram_equalization=True,
        dehazing_enabled=True,
        max_frames_per_video=50
    )
    
    # 预处理视频
    if videos:
        processed_files = dataset_manager.preprocess_videos(videos, preprocess_config)
        print(f"成功处理 {len(processed_files)} 帧")
    
    # 获取数据集统计
    stats = dataset_manager.get_dataset_statistics()
    print("\n数据集统计:")
    for violation_type, count in stats.items():
        print(f"  {violation_type}: {count} 帧")
    
    # 创建数据集yaml文件
    yaml_path = dataset_manager.create_dataset_yaml()
    print(f"\n数据集配置文件已创建: {yaml_path}")