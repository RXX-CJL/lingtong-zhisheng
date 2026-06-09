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

if __name__ == "__main__":
    init_db()