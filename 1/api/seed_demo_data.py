# -*- coding: utf-8 -*-
"""
答辩演示用 - 快速生成测试数据
运行方式: python seed_demo_data.py
作用: 往 zhitong_violations.db 插入 10 条违规证据记录
"""
import sqlite3
import json
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhitong_violations.db")

# 违规类型
VIOLATION_TYPES = ["red_light", "no_helmet", "wrong_way", "illegal_parking", "lane_departure", "speeding"]

# 中文映射（供 additional_info 展示用）
TYPE_CN = {
    "red_light": "闯红灯",
    "no_helmet": "未戴头盔",
    "wrong_way": "逆行",
    "illegal_parking": "违规停车",
    "lane_departure": "压线行驶",
    "speeding": "超速"
}

# 状态分布
STATUS_POOL = ["pending", "confirmed", "confirmed", "confirmed", "rejected"]

# 模拟的云端分析结果（中文）
CLOUD_RESULTS = [
    "经豆包大模型分析，图像清晰显示车辆在红灯亮起时越过停止线，确认为闯红灯行为。",
    "云端二次确权结果：图像中摩托车驾驶员头部未佩戴头盔，确认未戴头盔违规。",
    "大模型判断：车辆逆向行驶在单向车道内，周围车辆均为正向行驶，确认为逆行。",
    "图像分析：车辆停放在禁停区域超过规定时长，确认为违规停车。",
    "大模型识别：车辆车轮越过车道分界线行驶，确认为压线行驶。"
]

def create_tables_if_not_exists(cursor):
    """确保表结构存在"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS violation_evidences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            violation_type TEXT NOT NULL,
            track_id INTEGER,
            confidence REAL,
            position TEXT,
            timestamp DATETIME,
            image_path TEXT,
            video_path TEXT,
            additional_info TEXT,
            cloud_validated INTEGER DEFAULT 0,
            cloud_result TEXT,
            status TEXT DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ 表结构检查完成")

def seed_data(cursor):
    """插入 10 条演示数据"""
    now = datetime.now()
    for i in range(1, 11):
        vtype = random.choice(VIOLATION_TYPES)
        status = random.choice(STATUS_POOL)
        confidence = round(random.uniform(0.72, 0.98), 2)
        track_id = random.randint(1, 50)

        # 随机时间：最近 7 天内
        days_ago = random.randint(0, 6)
        hours_ago = random.randint(0, 23)
        minutes_ago = random.randint(0, 59)
        ts = now - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

        # 位置信息（模拟检测框坐标）
        position = json.dumps({
            "x": random.randint(100, 500),
            "y": random.randint(80, 300),
            "w": random.randint(80, 200),
            "h": random.randint(80, 200)
        }, ensure_ascii=False)

        # 附加信息
        additional = json.dumps({
            "location": f"测试路口 {random.randint(1, 5)} 号",
            "weather": random.choice(["晴", "多云", "阴"]),
            "light_condition": random.choice(["白天", "夜间", "黄昏"]),
            "vehicle_type": random.choice(["小型轿车", "摩托车", "电动车", "货车"])
        }, ensure_ascii=False)

        # 置信度高的才走云端确认
        cloud_validated = 1 if confidence >= 0.85 else 0
        cloud_result = random.choice(CLOUD_RESULTS) if cloud_validated else None

        cursor.execute("""
            INSERT INTO violation_evidences
            (violation_type, track_id, confidence, position, timestamp,
             image_path, additional_info, cloud_validated, cloud_result, status,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vtype, track_id, confidence, position, ts.strftime("%Y-%m-%d %H:%M:%S"),
            f"uploads/violation_demo_{i:02d}.jpg",
            additional,
            cloud_validated,
            cloud_result,
            status,
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%Y-%m-%d %H:%M:%S")
        ))

    print(f"✓ 已插入 10 条演示违规记录")

def show_summary(cursor):
    """展示数据概况"""
    print("\n" + "=" * 50)
    print("数据统计:")
    print("=" * 50)

    # 总数
    cursor.execute("SELECT COUNT(*) FROM violation_evidences")
    total = cursor.fetchone()[0]
    print(f"  总记录数: {total}")

    # 按类型
    cursor.execute("SELECT violation_type, COUNT(*) FROM violation_evidences GROUP BY violation_type")
    print("\n  按类型分布:")
    for vtype, cnt in cursor.fetchall():
        print(f"    - {TYPE_CN.get(vtype, vtype)} ({vtype}): {cnt} 条")

    # 按状态
    cursor.execute("SELECT status, COUNT(*) FROM violation_evidences GROUP BY status")
    print("\n  按状态分布:")
    status_cn = {"pending": "待审核", "confirmed": "已确认", "rejected": "已驳回"}
    for status, cnt in cursor.fetchall():
        print(f"    - {status_cn.get(status, status)} ({status}): {cnt} 条")

    # 云端确权
    cursor.execute("SELECT cloud_validated, COUNT(*) FROM violation_evidences GROUP BY cloud_validated")
    print("\n  云端确权情况:")
    for cv, cnt in cursor.fetchall():
        label = "已二次确权" if cv else "本地处理"
        print(f"    - {label}: {cnt} 条")

    print("\n" + "=" * 50)
    print("下一步:")
    print("  1) 启动后端: uvicorn app:app --port 8000 --reload")
    print("  2) 启动管理端: cd web-admin && npm run dev")
    print("  3) 访问 http://localhost:5173 查看效果")
    print("=" * 50)

def main():
    print("智瞳灵声 - 演示数据生成工具")
    print("=" * 50)

    # 询问是否清空旧数据
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM violation_evidences")
            existing = cursor.fetchone()[0]
            if existing > 0:
                print(f"\n⚠️  检测到已有 {existing} 条数据，自动清空并重新生成...")
                cursor.execute("DELETE FROM violation_evidences")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='violation_evidences'")
                print("✓ 旧数据已清空")
        except:
            pass
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

    create_tables_if_not_exists(cursor)
    seed_data(cursor)
    conn.commit()
    show_summary(cursor)
    conn.close()

if __name__ == "__main__":
    main()
