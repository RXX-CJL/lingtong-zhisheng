"""
数据库迁移脚本 - 端云协作特性扩展

功能：
1. 自动检测现有表结构
2. 安全地添加新字段和新表（使用 ALTER TABLE）
3. 保留现有数据不丢失
4. 给 violation_evidences 表添加新字段：collaboration_session_id, ai_trace_version, final_judgment_source
5. 创建 collaboration_sessions 和 system_statistics 表（如果不存在）
6. 提供回滚能力（rollback 函数）

使用方法：
    python migrate_db.py            # 执行迁移
    python migrate_db.py --rollback # 回滚迁移
    python migrate_db.py --status   # 查看迁移状态
"""

import sqlite3
import os
import json
from datetime import datetime

# 数据库路径：sqlite:///./zhitong_violations.db
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zhitong_violations.db")

# 迁移版本标识（记录在 system_configs 表中）
MIGRATION_VERSION_KEY = "migration_version_collab"
TARGET_MIGRATION_VERSION = "1.0.0"


def get_connection():
    """获取 SQLite 数据库连接"""
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"数据库文件不存在: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(cursor, table_name):
    """检测表是否存在"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def get_table_columns(cursor, table_name):
    """获取表的全部列名"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def get_current_migration_version(cursor):
    """获取当前已应用的迁移版本"""
    if not table_exists(cursor, "system_configs"):
        return None
    try:
        cursor.execute(
            "SELECT config_value FROM system_configs WHERE config_key=?",
            (MIGRATION_VERSION_KEY,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def set_migration_version(cursor, version):
    """记录迁移版本到 system_configs 表"""
    if not table_exists(cursor, "system_configs"):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key TEXT UNIQUE,
                config_value TEXT,
                description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    cursor.execute(
        "SELECT id FROM system_configs WHERE config_key=?",
        (MIGRATION_VERSION_KEY,)
    )
    existing = cursor.fetchone()
    if existing:
        cursor.execute(
            "UPDATE system_configs SET config_value=?, updated_at=CURRENT_TIMESTAMP WHERE config_key=?",
            (version, MIGRATION_VERSION_KEY)
        )
    else:
        cursor.execute(
            "INSERT INTO system_configs (config_key, config_value, description) VALUES (?, ?, ?)",
            (MIGRATION_VERSION_KEY, version, "端云协作特性迁移版本标识")
        )


def add_column_if_missing(cursor, table_name, column_name, column_def):
    """如果列不存在则添加，返回是否添加了该列"""
    existing_columns = get_table_columns(cursor, table_name)
    if column_name not in existing_columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
        return True
    return False


def create_collaboration_sessions_table(cursor):
    """创建 collaboration_sessions 表（如果不存在）"""
    if table_exists(cursor, "collaboration_sessions"):
        return False
    cursor.execute("""
        CREATE TABLE collaboration_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id VARCHAR(64) UNIQUE,
            violation_type VARCHAR(50),
            local_confidence FLOAT,
            final_confidence FLOAT,
            judgment_result VARCHAR(20),
            disagreement BOOLEAN DEFAULT 0,
            resolved BOOLEAN DEFAULT 0,
            resolver_id INTEGER,
            ai_trace_json TEXT,
            image_path VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_collaboration_sessions_session_id ON collaboration_sessions (session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_collaboration_sessions_violation_type ON collaboration_sessions (violation_type)")
    return True


def create_system_statistics_table(cursor):
    """创建 system_statistics 表（如果不存在）"""
    if table_exists(cursor, "system_statistics"):
        return False
    cursor.execute("""
        CREATE TABLE system_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_date VARCHAR(10),
            total_detections INTEGER DEFAULT 0,
            consultations INTEGER DEFAULT 0,
            confirmations INTEGER DEFAULT 0,
            disagreements INTEGER DEFAULT 0,
            accuracy_before FLOAT DEFAULT 0.0,
            accuracy_after FLOAT DEFAULT 0.0,
            saved_cost FLOAT DEFAULT 0.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_system_statistics_stat_date ON system_statistics (stat_date)")
    return True


def create_traffic_events_table(cursor):
    """创建 traffic_events 表（如果不存在）— GPT §10 证据链持久化（M07）"""
    if table_exists(cursor, "traffic_events"):
        return False
    cursor.execute("""
        CREATE TABLE traffic_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id VARCHAR(64) UNIQUE NOT NULL,
            event_type VARCHAR(50),
            track_id INTEGER,
            state VARCHAR(20) NOT NULL DEFAULT 'detecting',
            trigger_time DATETIME,
            vehicle_info TEXT,
            scene_context TEXT,
            trajectory TEXT,
            key_frames TEXT,
            event_video_path VARCHAR(255),
            rule_judgment TEXT,
            ai_judgment TEXT,
            ai_confidence FLOAT DEFAULT 0.0,
            ai_explanation TEXT,
            evidence_chain TEXT,
            state_history TEXT,
            camera_id VARCHAR(50) DEFAULT 'default',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_events_event_id ON traffic_events (event_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_events_event_type ON traffic_events (event_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_events_state ON traffic_events (state)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_events_camera_id ON traffic_events (camera_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS ix_traffic_events_trigger_time ON traffic_events (trigger_time)")
    return True


# 记录本次迁移执行的操作，便于回滚
_last_migration_actions = []


def migrate():
    """执行数据库迁移"""
    global _last_migration_actions
    _last_migration_actions = []

    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("开始执行数据库迁移 - 端云协作特性")
    print(f"数据库路径: {DB_PATH}")
    print(f"目标迁移版本: {TARGET_MIGRATION_VERSION}")
    print("=" * 60)

    try:
        current_version = get_current_migration_version(cursor)
        print(f"当前迁移版本: {current_version or '(未迁移)'}")

        if current_version == TARGET_MIGRATION_VERSION:
            print("✓ 已是目标迁移版本，无需重复迁移")
            conn.close()
            return True

        # 步骤1：为 violation_evidences 表添加新字段
        print("\n[步骤1] 检查 violation_evidences 表新字段...")
        if table_exists(cursor, "violation_evidences"):
            new_columns = {
                "collaboration_session_id": "VARCHAR(64)",
                "ai_trace_version": "VARCHAR(20)",
                "final_judgment_source": "VARCHAR(20)"
            }
            for col_name, col_def in new_columns.items():
                added = add_column_if_missing(cursor, "violation_evidences", col_name, col_def)
                if added:
                    print(f"  ✓ 已添加字段: violation_evidences.{col_name} ({col_def})")
                    _last_migration_actions.append(("add_column", "violation_evidences", col_name))
                else:
                    print(f"  - 字段已存在，跳过: violation_evidences.{col_name}")
        else:
            print("  ⚠️ violation_evidences 表不存在，跳过字段添加步骤")

        # 步骤2：创建 collaboration_sessions 表
        print("\n[步骤2] 创建 collaboration_sessions 表...")
        created = create_collaboration_sessions_table(cursor)
        if created:
            print("  ✓ 已创建表: collaboration_sessions")
            _last_migration_actions.append(("create_table", "collaboration_sessions", None))
        else:
            print("  - 表已存在，跳过: collaboration_sessions")

        # 步骤3：创建 system_statistics 表
        print("\n[步骤3] 创建 system_statistics 表...")
        created = create_system_statistics_table(cursor)
        if created:
            print("  ✓ 已创建表: system_statistics")
            _last_migration_actions.append(("create_table", "system_statistics", None))
        else:
            print("  - 表已存在，跳过: system_statistics")

        # 步骤3.5（M07）：创建 traffic_events 表
        print("\n[步骤3.5] 创建 traffic_events 表（M07 交通事件系统）...")
        created = create_traffic_events_table(cursor)
        if created:
            print("  ✓ 已创建表: traffic_events（含 5 个索引）")
            _last_migration_actions.append(("create_table", "traffic_events", None))
        else:
            print("  - 表已存在，跳过: traffic_events")

        # 步骤4：记录迁移版本
        print("\n[步骤4] 记录迁移版本...")
        set_migration_version(cursor, TARGET_MIGRATION_VERSION)
        print(f"  ✓ 已记录迁移版本: {TARGET_MIGRATION_VERSION}")

        conn.commit()
        print("\n" + "=" * 60)
        print("✓ 数据库迁移成功完成")
        print(f"  本次操作数: {len(_last_migration_actions)}")
        print(f"  迁移版本: {TARGET_MIGRATION_VERSION}")
        print("=" * 60)
        conn.close()
        return True

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n✗ 迁移失败: {e}")
        raise


def rollback():
    """
    回滚迁移：
    - 删除本次迁移添加的新字段（SQLite 不直接支持 DROP COLUMN，通过重建表实现）
    - 删除本次迁移创建的新表
    - 清除迁移版本标识
    注意：SQLite 3.35.0+ 支持 ALTER TABLE DROP COLUMN，这里使用兼容方案
    """
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("开始回滚数据库迁移 - 端云协作特性")
    print(f"数据库路径: {DB_PATH}")
    print("=" * 60)

    try:
        # 步骤1：删除新创建的表
        print("\n[回滚步骤1] 删除新创建的表...")
        for table_name in ["traffic_events", "system_statistics", "collaboration_sessions"]:
            if table_exists(cursor, table_name):
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                print(f"  ✓ 已删除表: {table_name}")
            else:
                print(f"  - 表不存在，跳过: {table_name}")

        # 步骤2：移除 violation_evidences 表的新增字段
        # SQLite 3.35.0+ 支持 DROP COLUMN，使用 try/except 兼容旧版本
        print("\n[回滚步骤2] 移除 violation_evidences 表的新增字段...")
        if table_exists(cursor, "violation_evidences"):
            columns_to_remove = ["collaboration_session_id", "ai_trace_version", "final_judgment_source"]
            existing_columns = get_table_columns(cursor, "violation_evidences")
            for col_name in columns_to_remove:
                if col_name in existing_columns:
                    try:
                        cursor.execute(
                            f"ALTER TABLE violation_evidences DROP COLUMN {col_name}"
                        )
                        print(f"  ✓ 已移除字段: violation_evidences.{col_name}")
                    except sqlite3.OperationalError as e:
                        # 旧版本 SQLite 不支持 DROP COLUMN，采用重建表方案
                        print(f"  ⚠️ DROP COLUMN 失败 ({e})，将使用重建表方案")
                        _rebuild_table_without_columns(cursor, "violation_evidences", columns_to_remove)
                        print(f"  ✓ 已通过重建表移除字段: {columns_to_remove}")
                        break
                else:
                    print(f"  - 字段不存在，跳过: violation_evidences.{col_name}")
        else:
            print("  ⚠️ violation_evidences 表不存在，跳过")

        # 步骤3：清除迁移版本标识
        print("\n[回滚步骤3] 清除迁移版本标识...")
        if table_exists(cursor, "system_configs"):
            cursor.execute(
                "DELETE FROM system_configs WHERE config_key=?",
                (MIGRATION_VERSION_KEY,)
            )
            print(f"  ✓ 已清除迁移版本标识: {MIGRATION_VERSION_KEY}")
        else:
            print("  - system_configs 表不存在，跳过")

        conn.commit()
        print("\n" + "=" * 60)
        print("✓ 回滚成功完成")
        print("=" * 60)
        conn.close()
        return True

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n✗ 回滚失败: {e}")
        raise


def _rebuild_table_without_columns(cursor, table_name, columns_to_remove):
    """
    通过重建表的方式移除字段（兼容 SQLite < 3.35.0）
    1. 创建临时表（不含要移除的字段）
    2. 复制数据
    3. 删除原表
    4. 重命名临时表为原表名
    """
    # 获取当前所有列
    cursor.execute(f"PRAGMA table_info({table_name})")
    all_columns = cursor.fetchall()
    # 过滤掉要移除的列
    keep_columns = [row for row in all_columns if row[1] not in columns_to_remove]
    keep_col_names = [row[1] for row in keep_columns]
    keep_col_defs = []
    for row in keep_columns:
        col_name = row[1]
        col_type = row[2]
        not_null = "NOT NULL" if row[3] else ""
        default = f"DEFAULT {row[4]}" if row[4] is not None else ""
        pk = "PRIMARY KEY" if row[5] else ""
        keep_col_defs.append(f"{col_name} {col_type} {not_null} {default} {pk}".strip())

    # 创建临时表
    cursor.execute(f"DROP TABLE IF EXISTS _{table_name}_backup")
    cursor.execute(
        f"CREATE TABLE _{table_name}_backup ({', '.join(keep_col_defs)})"
    )
    # 复制数据
    cursor.execute(
        f"INSERT INTO _{table_name}_backup ({', '.join(keep_col_names)}) "
        f"SELECT {', '.join(keep_col_names)} FROM {table_name}"
    )
    # 删除原表
    cursor.execute(f"DROP TABLE {table_name}")
    # 重命名临时表
    cursor.execute(f"ALTER TABLE _{table_name}_backup RENAME TO {table_name}")


def show_status():
    """显示当前数据库迁移状态"""
    conn = get_connection()
    cursor = conn.cursor()

    print("=" * 60)
    print("数据库迁移状态")
    print(f"数据库路径: {DB_PATH}")
    print("=" * 60)

    # 当前迁移版本
    current_version = get_current_migration_version(cursor)
    print(f"\n当前迁移版本: {current_version or '(未迁移)'}")
    print(f"目标迁移版本: {TARGET_MIGRATION_VERSION}")
    print(f"迁移状态: {'✓ 已完成' if current_version == TARGET_MIGRATION_VERSION else '✗ 未完成或版本不匹配'}")

    # 表状态
    print("\n[表状态]")
    tables_to_check = ["violation_evidences", "collaboration_sessions", "system_statistics",
                       "system_configs", "traffic_events"]
    for table_name in tables_to_check:
        exists = table_exists(cursor, table_name)
        status = "✓ 存在" if exists else "✗ 不存在"
        print(f"  {table_name}: {status}")

    # violation_evidences 新字段状态
    print("\n[violation_evidences 新字段状态]")
    if table_exists(cursor, "violation_evidences"):
        existing_columns = get_table_columns(cursor, "violation_evidences")
        new_columns = ["collaboration_session_id", "ai_trace_version", "final_judgment_source"]
        for col_name in new_columns:
            status = "✓ 已添加" if col_name in existing_columns else "✗ 未添加"
            print(f"  {col_name}: {status}")
    else:
        print("  ⚠️ violation_evidences 表不存在")

    # collaboration_sessions 表结构
    print("\n[collaboration_sessions 表字段]")
    if table_exists(cursor, "collaboration_sessions"):
        columns = get_table_columns(cursor, "collaboration_sessions")
        for col in columns:
            print(f"  - {col}")
    else:
        print("  ⚠️ 表不存在")

    # system_statistics 表结构
    print("\n[system_statistics 表字段]")
    if table_exists(cursor, "system_statistics"):
        columns = get_table_columns(cursor, "system_statistics")
        for col in columns:
            print(f"  - {col}")
    else:
        print("  ⚠️ 表不存在")

    # traffic_events 表结构（M07）
    print("\n[traffic_events 表字段（M07）]")
    if table_exists(cursor, "traffic_events"):
        columns = get_table_columns(cursor, "traffic_events")
        for col in columns:
            print(f"  - {col}")
        # 统计事件数
        cursor.execute("SELECT COUNT(*) FROM traffic_events")
        count = cursor.fetchone()[0]
        print(f"  事件记录数: {count}")
    else:
        print("  ⚠️ 表不存在")

    conn.close()


def main():
    """主入口：支持命令行参数"""
    import sys
    args = sys.argv[1:]

    if "--rollback" in args:
        rollback()
    elif "--status" in args:
        show_status()
    elif "--help" in args or "-h" in args:
        print(__doc__)
    elif len(args) == 0:
        migrate()
    else:
        print(f"未知参数: {args}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
