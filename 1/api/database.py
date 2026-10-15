from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

# 数据库配置
# 必须锚定到本文件所在目录：SQLAlchemy 的 sqlite:///./x.db 是相对进程 cwd 解析的，
# 若从项目根启动就会静默连到 E:\output\1\zhitong_violations.db（0 字节空壳），
# 表现为"总违规数 0"却不报错。此处改为绝对路径，与启动目录无关。
# （2026-09-27 由 DSH 修复，原行：DATABASE_URL = "sqlite:///./zhitong_violations.db"）
_DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhitong_violations.db")
DATABASE_URL = "sqlite:///" + _DB_FILE.replace("\\", "/")

# 只读提示：同名的 0 字节空壳文件存在时给出明确警告（不自动删除任何文件）
_SHELL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "zhitong_violations.db")
if os.path.exists(_SHELL) and os.path.getsize(_SHELL) == 0:
    print(f"[database] 注意：检测到 0 字节同名的空壳数据库 {_SHELL}；"
          f"当前实际使用的是 {_DB_FILE}，请勿误删或误用。")

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
    # ★2026-10-06 由 DSH 修复（G2/T29：本文件 L11 早已锚定绝对路径，此处却漏了）。
    # 原实现 sqlite3.connect("zhitong_violations.db") 是**相对进程 cwd** 解析的：
    #   start-all.bat 从项目根 E:\output\1 启动 → 迁移检查作用在
    #   E:\output\1\zhitong_violations.db（**0 字节空壳**）上 →
    #   ALTER TABLE 报 "no such table"，被下面的 except 吞掉 → **静默失效**，
    #   缺列永远补不上，且不报错、不提示。
    conn = sqlite3.connect(_DB_FILE)
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