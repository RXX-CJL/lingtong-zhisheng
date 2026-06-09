import os
import re
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

class VideoDownloader:
    """视频下载器类"""
    
    def __init__(self, save_dir: str):
        self.save_dir = save_dir
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.headers = {"User-Agent": self.user_agent}
        
        os.makedirs(save_dir, exist_ok=True)
    
    def download_video(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """下载单个视频"""
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件名
            if filename is None:
                filename = self._extract_filename(url, response)
            
            # 确保文件名安全
            filename = self._sanitize_filename(filename)
            
            # 添加时间戳避免重复
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{name}_{timestamp}{ext}"
            
            save_path = os.path.join(self.save_dir, filename)
            
            # 写入文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"成功下载视频: {save_path}")
            return save_path
        
        except Exception as e:
            print(f"下载视频失败 {url}: {str(e)}")
            return None
    
    def _extract_filename(self, url: str, response: requests.Response) -> str:
        """从URL或响应头提取文件名"""
        # 尝试从Content-Disposition头获取
        content_disposition = response.headers.get('Content-Disposition', '')
        match = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', content_disposition)
        if match:
            return match.group(1).strip('"\'')
        
        # 从URL路径获取
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if filename:
            return filename
        
        # 默认文件名
        return f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        illegal_chars = r'[\\/:*?"<>|]'
        return re.sub(illegal_chars, '_', filename)
    
    def search_bing_videos(self, query: str, count: int = 10) -> List[Dict[str, str]]:
        """使用Bing搜索视频"""
        search_url = "https://www.bing.com/videos/search"
        params = {
            "q": query,
            "count": count,
            "form": "HDRSC4"
        }
        
        try:
            response = requests.get(search_url, params=params, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            # 解析搜索结果页面中的视频链接
            video_urls = self._parse_bing_video_results(response.text)
            return video_urls
        
        except Exception as e:
            print(f"Bing视频搜索失败: {str(e)}")
            return []
    
    def _parse_bing_video_results(self, html_content: str) -> List[Dict[str, str]]:
        """解析Bing视频搜索结果"""
        results = []
        
        # 匹配视频信息的正则表达式
        # 匹配视频标题和URL
        pattern = r'<div class="mc_vtvc.*?<a href="([^"]+)".*?<h3 class="mc_vtvc_title">(.*?)</h3>'
        matches = re.findall(pattern, html_content, re.DOTALL)
        
        for url, title in matches:
            # 清理标题
            title = re.sub(r'<[^>]+>', '', title).strip()
            
            # 获取实际视频URL
            video_url = self._resolve_video_url(url)
            if video_url:
                results.append({
                    'title': title,
                    'url': video_url,
                    'source': 'bing'
                })
        
        return results[:10]  # 限制返回数量
    
    def _resolve_video_url(self, redirect_url: str) -> Optional[str]:
        """解析视频重定向URL"""
        try:
            response = requests.head(redirect_url, headers=self.headers, allow_redirects=True, timeout=15)
            return response.url
        except Exception:
            return redirect_url
    
    def download_videos_by_keywords(self, keywords: List[str], count_per_keyword: int = 5) -> List[str]:
        """根据关键词批量下载视频"""
        downloaded_files = []
        
        for keyword in keywords:
            print(f"\n搜索视频: {keyword}")
            videos = self.search_bing_videos(keyword, count_per_keyword)
            
            for video in videos:
                print(f"尝试下载: {video['title']}")
                filepath = self.download_video(video['url'], video['title'])
                if filepath:
                    downloaded_files.append(filepath)
        
        return downloaded_files

class TrafficViolationVideoCollector:
    """交通违规视频采集器"""
    
    def __init__(self, config):
        self.config = config
        self.raw_dir = os.path.join(config.BASE_DIR, 'data', 'raw_videos')
        self.downloader = VideoDownloader(self.raw_dir)
        
        # 违规类型关键词映射
        self.violation_keywords = {
            'red_light': ['交通违规 闯红灯 视频', 'red light violation video', '闯红灯 监控录像'],
            'no_helmet': ['电动车 未戴头盔 视频', 'motorcycle no helmet video', '未戴头盔 监控'],
            'wrong_way': ['交通逆行 视频', 'wrong way driving video', '逆行 监控录像'],
            'illegal_parking': ['违章停车 视频', 'illegal parking video', '违停 监控'],
            'lane_departure': ['压线行驶 视频', 'lane departure video', '变道违规 监控'],
            'speeding': ['超速行驶 视频', 'speeding violation video', '超速 监控录像']
        }
    
    def collect_videos(self, violation_types: Optional[List[str]] = None, count_per_type: int = 5) -> List[str]:
        """采集交通违规视频"""
        if violation_types is None:
            violation_types = list(self.violation_keywords.keys())
        
        downloaded_files = []
        
        for violation_type in violation_types:
            if violation_type not in self.violation_keywords:
                print(f"未知违规类型: {violation_type}")
                continue
            
            keywords = self.violation_keywords[violation_type]
            print(f"\n=== 采集 {violation_type} 类型视频 ===")
            
            for keyword in keywords:
                print(f"搜索关键词: {keyword}")
                videos = self.downloader.search_bing_videos(keyword, count_per_type)
                
                for video in videos:
                    # 添加违规类型前缀到文件名
                    title = f"{violation_type}_{video['title']}"
                    filepath = self.downloader.download_video(video['url'], title)
                    if filepath:
                        downloaded_files.append(filepath)
        
        return downloaded_files
    
    def collect_from_url_list(self, url_list: List[str], violation_type: str = 'unknown') -> List[str]:
        """从URL列表下载视频"""
        downloaded_files = []
        
        for url in url_list:
            filename = f"{violation_type}_{os.path.basename(urlparse(url).path)}"
            filepath = self.downloader.download_video(url, filename)
            if filepath:
                downloaded_files.append(filepath)
        
        return downloaded_files

# 示例使用
if __name__ == '__main__':
    from config import Config
    
    # 初始化配置
    config = Config()
    
    # 创建视频采集器
    collector = TrafficViolationVideoCollector(config)
    
    # 采集指定类型的视频
    print("开始采集交通违规视频...")
    
    # 采集闯红灯视频
    red_light_videos = collector.collect_videos(
        violation_types=['red_light'],
        count_per_type=3
    )
    print(f"\n采集到闯红灯视频: {len(red_light_videos)} 个")
    
    # 采集未戴头盔视频
    helmet_videos = collector.collect_videos(
        violation_types=['no_helmet'],
        count_per_type=3
    )
    print(f"采集到未戴头盔视频: {len(helmet_videos)} 个")
    
    # 也可以从URL列表下载
    # url_list = [
    #     'https://example.com/video1.mp4',
    #     'https://example.com/video2.mp4'
    # ]
    # collector.collect_from_url_list(url_list, 'speeding')
    
    print("\n视频采集完成！")