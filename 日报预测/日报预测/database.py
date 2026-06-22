"""
SQLite 数据库初始化与连接管理。
首次启动自动建表 + 创建默认管理员。
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "auth.db")


def get_db():
    """获取数据库连接（每请求新建，使用后关闭）"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """建表 + 种子管理员。幂等：表/用户已存在则跳过。"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    NOT NULL UNIQUE,
            password      TEXT    NOT NULL,
            display_name  TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'user',
            is_active     INTEGER NOT NULL DEFAULT 1,
            token_version INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT    NOT NULL,
            last_login    TEXT
        )
    """)

    # 种子管理员：无管理员时创建 admin / admin123
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    admin_count = cursor.fetchone()[0]
    if admin_count == 0:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pwd_hash = pwd_context.hash("admin123")
        cursor.execute(
            "INSERT INTO users (username, password, display_name, role, is_active, token_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))",
            ("admin", pwd_hash, "系统管理员", "admin", 1, 0)
        )

    conn.commit()
    conn.close()


# 启动时自动执行
init_db()
