from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

# 数据库配置
DATABASE_URL = "sqlite:///./zhitong_violations.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False  # 设置为True可以看到SQL语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """初始化数据库表"""
    from models import Base
    Base.metadata.create_all(bind=engine)
    print("数据库表创建成功")
    # 自动迁移：检查并添加缺失的列
    migrate_missing_columns()

def migrate_missing_columns():
    """检查并添加缺失的列（数据库迁移）"""
    import sqlite3
    conn = sqlite3.connect("zhitong_violations.db")
    cursor = conn.cursor()

    # 获取当前表的所有列
    cursor.execute(f"PRAGMA table_info(violation_evidences)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # 定义需要确保存在的列
    required_columns = {
        'yolo_detection_result': 'TEXT',
        'deepseek_result': 'TEXT',
        'needs_human_review': 'INTEGER DEFAULT 0',
        # M04: 车牌与违规记录绑定字段
        'plate_number': 'VARCHAR(20)',
        'plate_confidence': 'FLOAT',
        'plate_image_path': 'VARCHAR(255)',
        'plate_color': 'VARCHAR(20)',
        'confirmed_frames': 'INTEGER DEFAULT 0'
    }

    for col_name, col_type in required_columns.items():
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE violation_evidences ADD COLUMN {col_name} {col_type}")
                print(f"✓ 已添加缺失列: {col_name}")
                # 为 plate_number 建索引
                if col_name == 'plate_number':
                    try:
                        cursor.execute("CREATE INDEX IF NOT EXISTS ix_violation_evidences_plate_number ON violation_evidences (plate_number)")
                    except Exception as idx_e:
                        print(f"⚠️ 创建索引 plate_number 失败: {idx_e}")
            except Exception as e:
                print(f"⚠️ 添加列 {col_name} 失败: {e}")

    conn.commit()
    conn.close()
    print("数据库迁移检查完成")

if __name__ == "__main__":
    init_db()