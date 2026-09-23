# -*- coding: utf-8 -*-
"""
智瞳灵声 - 单元测试文件
运行方式: pytest tests/ -v
"""
import pytest
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class TestConfig:
    """配置模块测试"""
    
    def test_config_import(self):
        """测试配置模块能否正常导入"""
        from config import Config
        assert Config is not None
    
    def test_config_dirs_created(self):
        """测试配置目录创建功能"""
        from config import Config
        Config.create_dirs()
        
        # 验证目录是否存在
        assert os.path.exists(Config.MODEL_DIR)
        assert os.path.exists(Config.OUTPUT_DIR)
        assert os.path.exists(Config.EVIDENCE_DIR)


class TestViolationDetector:
    """违规检测模块测试"""
    
    def test_violation_types(self):
        """测试违规类型定义"""
        from zhitong.violation_detector import ViolationType
        
        assert hasattr(ViolationType, 'RED_LIGHT')
        assert hasattr(ViolationType, 'NO_HELMET')
        assert hasattr(ViolationType, 'WRONG_WAY')
        assert hasattr(ViolationType, 'ILLEGAL_PARKING')
    
    def test_violation_class_creation(self):
        """测试违规对象创建"""
        import numpy as np
        from zhitong.violation_detector import Violation, ViolationType
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        violation = Violation(
            violation_type=ViolationType.RED_LIGHT,
            track_id=1,
            frame=frame,
            confidence=0.95,
            position=(100, 100, 200, 300),
            timestamp=1234567890.0
        )
        
        assert violation.violation_type == ViolationType.RED_LIGHT
        assert violation.track_id == 1
        assert violation.confidence == 0.95


class TestTracker:
    """跟踪模块测试"""
    
    def test_tracked_object_creation(self):
        """测试跟踪对象创建"""
        from zhitong.tracker import TrackedObject
        
        obj = TrackedObject(
            track_id=1,
            bbox=[100, 100, 200, 300],
            class_name='car',
            confidence=0.9
        )
        
        assert obj.track_id == 1
        assert obj.class_name == 'car'
        assert obj.confidence == 0.9


class TestDatabase:
    """数据库模块测试"""
    
    def test_database_import(self):
        """测试数据库模块能否正常导入"""
        from database import get_db, init_db
        assert get_db is not None
        assert init_db is not None
    
    def test_init_db(self):
        """测试数据库初始化"""
        from database import init_db
        # 不应抛出异常
        init_db()
    
    def test_migrate_missing_columns(self):
        """测试数据库列迁移"""
        from database import migrate_missing_columns
        # 不应抛出异常
        migrate_missing_columns()


class TestModels:
    """数据模型测试"""
    
    def test_violation_evidence_model(self):
        """测试违规证据模型"""
        from api.models import ViolationEvidence
        assert hasattr(ViolationEvidence, '__tablename__')
        assert ViolationEvidence.__tablename__ == 'violation_evidences'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
