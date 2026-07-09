"""管理员用户管理 CRUD"""
import secrets
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import hash_password
from auth_middleware import get_current_user, require_admin
from database import get_db
from models import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


def generate_password(length=10) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("/users")
def list_users(
    keyword: str = Query(default="", description="搜索用户名或姓名"),
    role: str = Query(default="", description="筛选角色"),
    is_active: str = Query(default="", description="筛选状态: 1/0"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: dict = Depends(require_admin),
):
    conn = get_db()
    try:
        where = ["1=1"]
        params = []

        if keyword:
            where.append("(username LIKE ? OR display_name LIKE ?)")
            kw = f"%{keyword}%"
            params.extend([kw, kw])

        if role:
            where.append("role = ?")
            params.append(role)

        if is_active:
            where.append("is_active = ?")
            params.append(int(is_active))

        where_clause = " AND ".join(where)

        total = conn.execute(
            f"SELECT COUNT(*) FROM users WHERE {where_clause}", params
        ).fetchone()[0]

        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM users WHERE {where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

        return {
            "items": [UserOut(**dict(r)).model_dump() for r in rows],
            "total": total,
        }
    finally:
        conn.close()


@router.post("/users", status_code=201)
def create_user(body: UserCreate, user: dict = Depends(require_admin)):
    conn = get_db()
    try:
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (body.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")

        pwd_hash = hash_password(body.password)
        cur = conn.execute(
            "INSERT INTO users (username, password, display_name, role, is_active, token_version, created_at) "
            "VALUES (?, ?, ?, ?, 1, 0, datetime('now', 'localtime'))",
            (body.username, pwd_hash, body.display_name, body.role),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
        return UserOut(**dict(row)).model_dump()
    finally:
        conn.close()


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate, user: dict = Depends(require_admin)):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        updates = {}
        if body.display_name is not None:
            updates["display_name"] = body.display_name
        if body.role is not None:
            updates["role"] = body.role
        if body.is_active is not None:
            updates["is_active"] = 1 if body.is_active else 0

        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            vals = list(updates.values()) + [user_id]
            conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", vals)
            conn.commit()

        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return UserOut(**dict(row)).model_dump()
    finally:
        conn.close()


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    user: dict = Depends(require_admin),
):
    """重置密码：生成随机密码，递增 token_version 使旧 refresh_token 失效"""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")

        new_pwd = generate_password()
        new_hash = hash_password(new_pwd)
        new_version = row["token_version"] + 1

        conn.execute(
            "UPDATE users SET password = ?, token_version = ? WHERE id = ?",
            (new_hash, new_version, user_id),
        )
        conn.commit()

        return {
            "new_password": new_pwd,
        }
    finally:
        conn.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_admin)):
    """硬删除：从数据库中永久移除"""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user_id == user["id"]:
            raise HTTPException(status_code=400, detail="不能删除自己")

        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"message": "用户已删除"}
    finally:
        conn.close()
