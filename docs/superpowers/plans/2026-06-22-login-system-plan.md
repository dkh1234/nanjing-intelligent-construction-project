# 登录认证系统 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为智能工期预测系统添加基于 JWT 的登录认证、角色权限和用户管理功能。

**Architecture:** 后端新增 SQLite 用户表 + JWT 认证中间件 + 管理 API，前端新增 Pinia auth store + 路由守卫 + axios 拦截器 + 登录页 + 用户管理页，改造现有布局组件动态显示用户信息和权限菜单。

**Tech Stack:** Python FastAPI + python-jose + passlib + SQLite3 / Vue 3 + Pinia + Element Plus + axios

---

### Task 1: 后端 — SQLite 数据库层

**Files:**
- Create: `日报预测/日报预测/database.py`

```python
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
```

- [ ] **Step 1: 创建 database.py**

```bash
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/python.exe -c "from database import get_db, init_db; conn = get_db(); rows = conn.execute('SELECT * FROM users').fetchall(); print([dict(r) for r in rows]); conn.close()"
```

Expected output: 显示默认 admin 用户记录，password 字段为 bcrypt 哈希。

- [ ] **Step 2: 提交**

```bash
git add 日报预测/日报预测/database.py
git commit -m "feat: add SQLite database layer with users table and seed admin"
```

---

### Task 2: 后端 — Pydantic 数据模型

**Files:**
- Create: `日报预测/日报预测/models.py`

```python
"""用户相关的 Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import Optional


class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=64)
    role: Optional[str] = Field(None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    token_version: int
    created_at: str
    last_login: Optional[str] = None


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128)
```

- [ ] **Step 1: 创建 models.py**

```bash
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/python.exe -c "from models import UserLogin, UserCreate, UserOut; u = UserLogin(username='test', password='123456'); print(u.model_dump())"
```

Expected: `{'username': 'test', 'password': '123456'}`

- [ ] **Step 2: 提交**

```bash
git add 日报预测/日报预测/models.py
git commit -m "feat: add Pydantic user models"
```

---

### Task 3: 后端 — JWT 与密码工具

**Files:**
- Create: `日报预测/日报预测/auth.py`

```python
"""JWT 签发/验证，密码 hash/verify"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------- 密码 ----------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------- JWT ----------
SECRET_KEY = os.environ.get("JWT_SECRET", "CHANGE-ME-IN-PRODUCTION-X7k9pL2mN4vQ8wR3")
ALGORITHM = "HS256"
ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=7)


def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, token_version: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "ver": token_version,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TTL,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> Optional[dict]:
    """解码并验证 token，返回 payload 或 None"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            return None
        return payload
    except JWTError:
        return None
```

- [ ] **Step 1: 创建 auth.py**

```bash
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/python.exe -c "
from auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
h = hash_password('test')
assert verify_password('test', h)
assert not verify_password('wrong', h)
at = create_access_token(1, 'admin')
rt = create_refresh_token(1, 0)
print('access:', decode_token(at, 'access'))
print('refresh:', decode_token(rt, 'refresh'))
"
```

Expected: 打印两个 token 的 payload 字典，含 sub/role/type 等字段。

- [ ] **Step 2: 提交**

```bash
git add 日报预测/日报预测/auth.py
git commit -m "feat: add JWT and bcrypt password utilities"
```

---

### Task 4: 后端 — 认证中间件

**Files:**
- Create: `日报预测/日报预测/auth_middleware.py`

```python
"""FastAPI 认证依赖注入"""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import decode_token
from database import get_db


security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """从 Authorization Header 提取并验证 JWT，返回用户记录"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    payload = decode_token(credentials.credentials, "access")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")

    user_id = int(payload["sub"])
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号已被禁用或删除")
        return dict(row)
    finally:
        conn.close()


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """要求管理员角色"""
    if user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user
```

- [ ] **Step 1: 创建 auth_middleware.py**

```bash
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/python.exe -c "
from auth_middleware import get_current_user, require_admin
from auth import create_access_token
import sqlite3
# Smoke test: verify the functions are importable and have correct signature
print('get_current_user:', get_current_user)
print('require_admin:', require_admin)
"
```

Expected: 两个 Depends 对象打印无异常。

- [ ] **Step 2: 提交**

```bash
git add 日报预测/日报预测/auth_middleware.py
git commit -m "feat: add FastAPI auth middleware (get_current_user, require_admin)"
```

---

### Task 5: 后端 — 认证路由 (login/refresh/me/change-password)

**Files:**
- Modify: `日报预测/日报预测/api_server.py`

在 `app = FastAPI(...)` 之后、业务路由之前插入以下内容：

```python
from datetime import datetime
from fastapi import Depends, HTTPException, status
from auth import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from auth_middleware import get_current_user, require_admin
from database import get_db
from models import (
    UserLogin, UserCreate, UserUpdate, UserOut,
    TokenResponse, RefreshRequest,
    ChangePasswordRequest, ResetPasswordRequest,
)


# ========== 认证路由 ==========

@app.post("/api/auth/login", response_model=TokenResponse)
def login(body: UserLogin):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (body.username,)
        ).fetchone()
        if row is None or not verify_password(body.password, row["password"]):
            raise HTTPException(status_code=401, detail="用户名或密码错误")

        user = dict(row)
        access_token = create_access_token(user["id"], user["role"])
        refresh_token = create_refresh_token(user["id"], user["token_version"])

        conn.execute(
            "UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?",
            (user["id"],)
        )
        conn.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": UserOut(**user).model_dump(),
        }
    finally:
        conn.close()


@app.post("/api/auth/refresh")
def refresh_token(body: RefreshRequest):
    payload = decode_token(body.refresh_token, "refresh")
    if payload is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user_id = int(payload["sub"])
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE id = ? AND is_active = 1",
            (user_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="账号已被禁用或删除")
        if row["token_version"] != payload.get("ver"):
            raise HTTPException(status_code=401, detail="密码已重置，请重新登录")

        new_access = create_access_token(user_id, row["role"])
        return {"access_token": new_access}
    finally:
        conn.close()


@app.get("/api/auth/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return UserOut(**user).model_dump()


@app.post("/api/auth/change-password")
def change_password(body: ChangePasswordRequest, user: dict = Depends(get_current_user)):
    if not verify_password(body.old_password, user["password"]):
        raise HTTPException(status_code=400, detail="原密码错误")

    new_hash = hash_password(body.new_password)
    new_version = user["token_version"] + 1

    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET password = ?, token_version = ? WHERE id = ?",
            (new_hash, new_version, user["id"]),
        )
        conn.commit()
        return {"message": "密码修改成功，请重新登录"}
    finally:
        conn.close()
```

- [ ] **Step 1: 修改 api_server.py，添加认证路由**

- [ ] **Step 2: 启动后端，测试登录**

```bash
# 启动后端（后台）
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/python.exe api_server.py &
sleep 3

# 测试登录
curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Expected: 返回 `{"access_token": "...", "refresh_token": "...", "user": {...}}`

- [ ] **Step 3: 测试 refresh 和 me**

```bash
# 保存 token 变量
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

REFRESH=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")

# 测试 /me
curl -s http://127.0.0.1:8000/api/auth/me -H "Authorization: Bearer $TOKEN"
# Expected: {"id":1,"username":"admin",...}

# 测试 refresh
curl -s -X POST http://127.0.0.1:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\":\"$REFRESH\"}"
# Expected: {"access_token":"..."}
```

- [ ] **Step 4: 提交**

```bash
git add 日报预测/日报预测/api_server.py
git commit -m "feat: add auth routes (login, refresh, me, change-password)"
```

---

### Task 6: 后端 — 用户管理路由

**Files:**
- Create: `日报预测/日报预测/admin_routes.py`

```python
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
    """软删除（is_active=0）"""
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user_id == user["id"]:
            raise HTTPException(status_code=400, detail="不能删除自己")

        new_version = row["token_version"] + 1
        conn.execute(
            "UPDATE users SET is_active = 0, token_version = ? WHERE id = ?",
            (new_version, user_id),
        )
        conn.commit()
        return {"message": "用户已禁用"}
    finally:
        conn.close()
```

在 `api_server.py` 中注册路由，在文件末尾 `if __name__ == "__main__":` 之前添加：

```python
from admin_routes import router as admin_router
app.include_router(admin_router)
```

- [ ] **Step 1: 创建 admin_routes.py 并在 api_server.py 注册**

- [ ] **Step 2: 重启后端并测试用户 CRUD**

```bash
# 获取 admin token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 创建用户
curl -s -X POST http://127.0.0.1:8000/api/admin/users \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"username":"testuser","password":"test1234","display_name":"测试用户","role":"user"}'

# Expected: {"id":2,"username":"testuser",...}

# 用户列表
curl -s http://127.0.0.1:8000/api/admin/users?page=1\&page_size=10 \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"items":[...], "total":2}

# 重置密码
curl -s -X POST http://127.0.0.1:8000/api/admin/users/2/reset-password \
  -H "Authorization: Bearer $TOKEN"
# Expected: {"new_password":"..."}
```

- [ ] **Step 3: 提交**

```bash
git add 日报预测/日报预测/admin_routes.py 日报预测/日报预测/api_server.py
git commit -m "feat: add admin user management CRUD routes"
```

---

### Task 7: 后端 — 保护现有业务路由

**Files:**
- Modify: `日报预测/日报预测/api_server.py`

在 `upload_and_predict` 路由上添加 `current_user = Depends(get_current_user)`：

将：
```python
@app.post("/api/daily/upload-and-predict")
async def upload_and_predict(
    file: UploadFile = File(...),
    predict_weeks: int = Form(1)
):
```

改为：
```python
@app.post("/api/daily/upload-and-predict")
async def upload_and_predict(
    file: UploadFile = File(...),
    predict_weeks: int = Form(1),
    current_user: dict = Depends(get_current_user),
):
```

- [ ] **Step 1: 修改 upload_and_predict 签名**

- [ ] **Step 2: 验证保护生效**

```bash
# 无 token 请求应返回 401
curl -s -X POST http://127.0.0.1:8000/api/daily/upload-and-predict -F "predict_weeks=1"
# Expected: {"detail":"请先登录"}

# 带 token 请求正常运行
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "test" > /tmp/test.txt
curl -s -X POST http://127.0.0.1:8000/api/daily/upload-and-predict \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/tmp/test.txt" -F "predict_weeks=1"
# 可能返回 error（test.txt 不是合法日报），但不应返回 401
```

- [ ] **Step 3: 更新 requirements.txt**

在 `日报预测/日报预测/requirements.txt` 末尾添加：
```
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
```

然后安装：
```bash
cd "d:/Users/DIfy工期预测项目/日报预测/日报预测"
.venv/Scripts/pip.exe install python-jose[cryptography] passlib[bcrypt]
```

- [ ] **Step 4: 提交**

```bash
git add 日报预测/日报预测/api_server.py 日报预测/日报预测/requirements.txt
git commit -m "feat: protect existing business routes with JWT auth"
```

---

### Task 8: 前端 — 安装 Pinia + 创建 Auth Store

**Files:**
- Modify: `smart-duration-prediction/package.json`
- Create: `smart-duration-prediction/src/stores/auth.js`
- Modify: `smart-duration-prediction/src/main.js`

- [ ] **Step 1: 安装 Pinia**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npm install pinia
```

- [ ] **Step 2: 创建 stores/auth.js**

```javascript
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import router from '@/router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function saveAuth(data) {
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    user.value = data.user
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  async function login(username, password) {
    const axios = (await import('axios')).default
    const res = await axios.post('/api/auth/login', { username, password })
    saveAuth(res.data)
    return res.data
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  return { token, refreshToken, user, isLoggedIn, isAdmin, login, logout }
})
```

- [ ] **Step 3: 修改 main.js 注册 Pinia**

在 `import router from './router'` 之后添加：
```javascript
import { createPinia } from 'pinia'
```

在 `app.use(router)` 之前添加：
```javascript
app.use(createPinia())
```

完整的 main.js 变为：
```javascript
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })
app.use(createPinia())
app.use(router)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 4: 验证 Pinia 注册成功**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | head -20
```

Expected: Build 成功，无报错。（`vite build` 会检查语法和模块导入）

- [ ] **Step 5: 提交**

```bash
git add smart-duration-prediction/package.json smart-duration-prediction/package-lock.json \
        smart-duration-prediction/src/stores/auth.js smart-duration-prediction/src/main.js
git commit -m "feat: add Pinia auth store"
```

---

### Task 9: 前端 — Auth Axios 实例 + 自动续期

**Files:**
- Create: `smart-duration-prediction/src/utils/authRequest.js`

```javascript
import axios from 'axios'
import router from '@/router'

const authRequest = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ---- request 拦截：自动附加 token ----
authRequest.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- response 401 自动续期 ----
let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error)
    } else {
      resolve(token)
    }
  })
  failedQueue = []
}

authRequest.interceptors.response.use(
  (res) => res.data,   // 统一解包 data
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return authRequest(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refresh = localStorage.getItem('refresh_token')
        if (!refresh) throw new Error('no refresh token')

        const res = await axios.post('/api/auth/refresh', { refresh_token: refresh })
        const newToken = res.data.access_token
        localStorage.setItem('access_token', newToken)
        processQueue(null, newToken)
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return authRequest(originalRequest)
      } catch (e) {
        processQueue(e, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        localStorage.removeItem('user')
        router.push('/login')
        return Promise.reject(e)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default authRequest
```

- [ ] **Step 1: 创建 authRequest.js**

- [ ] **Step 2: 验证模块语法**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | tail -5
```

Expected: Build 成功。

- [ ] **Step 3: 提交**

```bash
git add smart-duration-prediction/src/utils/authRequest.js
git commit -m "feat: add authenticated axios instance with auto-refresh"
```

---

### Task 10: 前端 — 路由守卫

**Files:**
- Modify: `smart-duration-prediction/src/router/index.js`

将 router/index.js 替换为：

```javascript
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/prediction'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { title: '登录', guest: true }
  },
  {
    path: '/prediction',
    name: 'DurationPrediction',
    component: () => import('@/views/durationPredict/index.vue'),
    meta: { title: '工期预测', requiresAuth: true }
  },
  {
    path: '/daily-report',
    name: 'DailyReport',
    component: () => import('@/views/DailyReport.vue'),
    meta: { title: '日报预测', requiresAuth: true }
  },
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    meta: { title: '用户管理', requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/prediction'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// ---- 导航守卫 ----
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('user') || 'null') }
    catch { return null }
  })()

  // 已登录用户访问登录页 → 跳首页
  if (to.meta.guest && token) {
    return next('/prediction')
  }

  // 需要登录但无 token → 跳登录页（保存原目标用于回跳）
  if (to.meta.requiresAuth && !token) {
    return next({ path: '/login', query: { redirect: to.fullPath } })
  }

  // 需要管理员但角色不符 → 回首页
  if (to.meta.requiresAdmin && user?.role !== 'admin') {
    return next('/prediction')
  }

  next()
})

export default router
```

- [ ] **Step 1: 修改 router/index.js**

- [ ] **Step 2: 验证路由守卫语法**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | tail -10
```

Expected: Build 成功（Login.vue 和 UserManagement.vue 不存在时会报 warning，不影响验证）。

- [ ] **Step 3: 提交**

```bash
git add smart-duration-prediction/src/router/index.js
git commit -m "feat: add auth route guards and login/admin routes"
```

---

### Task 11: 前端 — 登录页

**Files:**
- Create: `smart-duration-prediction/src/views/Login.vue`

```vue
<template>
  <div class="login-wrapper">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">智能工期预测系统</h1>
        <p class="login-subtitle">请使用管理员分配的账号登录</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        size="large"
        @keyup.enter="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            class="login-btn"
            @click="handleLogin"
          >
            登 录
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref(null)
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/prediction'
    router.push(redirect)
  } catch (err) {
    const msg = err.response?.data?.detail || '登录失败，请检查用户名和密码'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0B1F3A 0%, #1a3a6b 50%, #0B1F3A 100%);
}

.login-card {
  width: 400px;
  padding: 48px 40px 36px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.25);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: #1D2129;
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 14px;
  color: #86909C;
  margin: 0;
}

.login-btn {
  width: 100%;
}
</style>
```

- [ ] **Step 1: 创建 Login.vue**

- [ ] **Step 2: 验证构建**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | tail -10
```

Expected: Build 成功。

- [ ] **Step 3: 提交**

```bash
git add smart-duration-prediction/src/views/Login.vue
git commit -m "feat: add login page"
```

---

### Task 12: 前端 — 用户管理页

**Files:**
- Create: `smart-duration-prediction/src/views/UserManagement.vue`

```vue
<template>
  <div class="user-management">
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <el-button type="primary" @click="openCreateDialog">+ 新建用户</el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索用户名或姓名"
        clearable
        style="width: 240px"
        @change="fetchUsers"
      />
      <el-select v-model="roleFilter" placeholder="角色" clearable style="width: 120px" @change="fetchUsers">
        <el-option label="管理员" value="admin" />
        <el-option label="用户" value="user" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="fetchUsers">
        <el-option label="启用" value="1" />
        <el-option label="禁用" value="0" />
      </el-select>
    </div>

    <!-- 表格 -->
    <el-table :data="users" border stripe v-loading="tableLoading" style="width: 100%">
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="display_name" label="姓名" width="120" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
            {{ row.role === 'admin' ? '管理员' : '用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column prop="last_login" label="最后登录" width="180">
        <template #default="{ row }">
          {{ row.last_login || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="handleResetPassword(row)">重置密码</el-button>
          <el-popconfirm
            title="确定要禁用该用户吗？"
            @confirm="handleDelete(row)"
            v-if="row.is_active"
          >
            <template #reference>
              <el-button text type="danger" size="small">禁用</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchUsers"
      />
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑用户' : '新建用户'"
      width="440px"
      @closed="resetForm"
    >
      <el-form ref="dialogFormRef" :model="dialogForm" :rules="dialogRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialogForm.username" :disabled="isEditing" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="dialogForm.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item v-if="!isEditing" label="密码" prop="password">
          <el-input v-model="dialogForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="dialogForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码结果弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="密码已重置" width="400px">
      <el-alert type="success" :closable="false">
        <template #title>
          新密码：<strong style="font-size:16px;user-select:all">{{ newPassword }}</strong>
        </template>
      </el-alert>
      <p style="color:#86909C;margin-top:12px">请将此密码发送给用户。关闭后无法再次查看。</p>
      <template #footer>
        <el-button type="primary" @click="pwdDialogVisible = false">我知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import authRequest from '@/utils/authRequest'

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const tableLoading = ref(false)

async function fetchUsers() {
  tableLoading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (roleFilter.value) params.role = roleFilter.value
    if (statusFilter.value) params.is_active = statusFilter.value
    const res = await authRequest.get('/admin/users', { params })
    users.value = res.items
    total.value = res.total
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '获取用户列表失败')
  } finally {
    tableLoading.value = false
  }
}

// ---- 新建/编辑 ----
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEditing = ref(false)
const editingUserId = ref(null)
const dialogFormRef = ref(null)

const dialogForm = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'user',
})

const dialogRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

function openCreateDialog() {
  isEditing.value = false
  editingUserId.value = null
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEditing.value = true
  editingUserId.value = row.id
  dialogForm.username = row.username
  dialogForm.display_name = row.display_name
  dialogForm.role = row.role
  dialogForm.password = ''
  dialogVisible.value = true
}

function resetForm() {
  dialogForm.username = ''
  dialogForm.display_name = ''
  dialogForm.password = ''
  dialogForm.role = 'user'
  dialogFormRef.value?.resetFields()
}

async function submitDialog() {
  const valid = await dialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  dialogLoading.value = true
  try {
    if (isEditing.value) {
      await authRequest.put(`/admin/users/${editingUserId.value}`, {
        display_name: dialogForm.display_name,
        role: dialogForm.role,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await authRequest.post('/admin/users', {
        username: dialogForm.username,
        password: dialogForm.password,
        display_name: dialogForm.display_name,
        role: dialogForm.role,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (err) {
    const msg = err.response?.data?.detail || '操作失败'
    ElMessage.error(msg)
  } finally {
    dialogLoading.value = false
  }
}

// ---- 重置密码 ----
const pwdDialogVisible = ref(false)
const newPassword = ref('')

async function handleResetPassword(row) {
  try {
    const res = await authRequest.post(`/admin/users/${row.id}/reset-password`)
    newPassword.value = res.new_password
    pwdDialogVisible.value = true
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重置密码失败')
  }
}

// ---- 禁用 ----
async function handleDelete(row) {
  try {
    await authRequest.delete(`/admin/users/${row.id}`)
    ElMessage.success('用户已禁用')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(fetchUsers)
</script>

<style lang="scss" scoped>
.user-management {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin: 0;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
```

- [ ] **Step 1: 创建 UserManagement.vue**

- [ ] **Step 2: 验证构建**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | tail -10
```

Expected: Build 成功。

- [ ] **Step 3: 提交**

```bash
git add smart-duration-prediction/src/views/UserManagement.vue
git commit -m "feat: add user management page (admin-only)"
```

---

### Task 13: 前端 — 布局组件改造 (AppHeader + AppSidebar)

**Files:**
- Modify: `smart-duration-prediction/src/components/layout/AppHeader.vue`
- Modify: `smart-duration-prediction/src/components/layout/AppSidebar.vue`

- [ ] **Step 1: 修改 AppHeader.vue — 动态用户下拉**

在 `<script setup>` 中替换为：

```javascript
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function handleCommand(command) {
  if (command === 'profile') {
    // 暂无个人中心页
  } else if (command === 'users') {
    router.push('/admin/users')
  } else if (command === 'logout') {
    authStore.logout()
  }
}
```

在 `<template>` 中，将硬编码的「管理员」和下拉菜单替换为动态绑定：

```vue
<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo">
        <svg class="logo-icon" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="36" height="36" rx="8" fill="#1677FF"/>
          <path d="M10 26V12L18 18L26 12V26H22V20H14V26H10Z" fill="#fff"/>
        </svg>
      </div>
      <h1 class="header-title">智能工期预测系统</h1>
    </div>
    <div class="header-right">
      <template v-if="authStore.isLoggedIn">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <el-avatar :size="32" icon="UserFilled" />
            <span class="user-name">{{ authStore.user?.display_name || '用户' }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="users" v-if="authStore.isAdmin">
                <el-icon><Setting /></el-icon>
                用户管理
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided>
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button text style="color:#fff" @click="router.push('/login')">登录</el-button>
      </template>
    </div>
  </header>
</template>
```

注意：需要在 `<script setup>` 顶部 import `Setting` 和 `SwitchButton` 图标：
```javascript
import { Setting, SwitchButton } from '@element-plus/icons-vue'
```

- [ ] **Step 2: 修改 AppSidebar.vue — 动态菜单 + 动态用户信息**

在 `<script setup>` 中，修改 menuItems 添加用户管理项，并引入 authStore：

```javascript
import {
  Timer, DataAnalysis, Setting,
  Fold, Expand
} from '@element-plus/icons-vue'
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  activeMenu: { type: String, default: 'prediction' }
})

const emit = defineEmits(['update:collapsed', 'menu-select'])

const menuItems = computed(() => {
  const items = [
    { path: '/prediction',   label: '工期预测', icon: Timer },
    { path: '/daily-report', label: '日报预测', icon: DataAnalysis },
  ]
  if (authStore.isAdmin) {
    items.push({ path: '/admin/users', label: '用户管理', icon: Setting })
  }
  return items
})

function toggleCollapse() {
  emit('update:collapsed', !props.collapsed)
}

function handleClick(item) {
  emit('menu-select', item.path)
}
```

在 `<template>` 的 sidebar-footer 替换硬编码为动态：

```vue
<div class="sidebar-footer">
  <div v-if="!collapsed && authStore.isLoggedIn" class="footer-user">
    <el-avatar :size="36" icon="UserFilled" />
    <div class="footer-info">
      <span class="footer-name">{{ authStore.user?.display_name || '用户' }}</span>
      <span class="footer-role">{{ authStore.isAdmin ? '系统管理员' : '用户' }}</span>
    </div>
  </div>
  <el-avatar v-else-if="collapsed" :size="36" icon="UserFilled" class="footer-avatar-collapsed" />
</div>
```

- [ ] **Step 3: 验证构建**

```bash
cd "d:/Users/DIfy工期预测项目/smart-duration-prediction"
npx vite build --mode development 2>&1 | tail -10
```

Expected: Build 成功。

- [ ] **Step 4: 提交**

```bash
git add smart-duration-prediction/src/components/layout/AppHeader.vue \
        smart-duration-prediction/src/components/layout/AppSidebar.vue
git commit -m "feat: wire layout components to auth store"
```

---

### Task 14: 联调验证

- [ ] **Step 1: 确保前后端都在运行**

```bash
# 检查后端
curl -s http://127.0.0.1:8000/api/daily/health
# Expected: {"status":"ok"}

# 检查前端
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/
# Expected: 200
```

- [ ] **Step 2: 端到端登录流程**

用浏览器访问 `http://localhost:3000/#/login`，验证：
1. 使用 admin / admin123 登录
2. 登录后自动跳转到工期预测页
3. 页面顶部右侧显示「系统管理员」+ 下拉菜单
4. 侧边栏底部显示用户名和角色
5. 侧边栏出现「用户管理」菜单项
6. 下拉菜单中「退出登录」可正常退出

- [ ] **Step 3: 用户管理 CRUD 验证**

1. 点击「用户管理」，进入用户列表
2. 新建一个普通用户
3. 用新用户登录，确认侧边栏没有「用户管理」
4. 用 admin 重置新用户密码
5. 禁用该用户后，该用户无法登录（返回"账号已被禁用"）

- [ ] **Step 4: API 保护验证**

```bash
# 未登录访问预测 API
curl -s -X POST http://localhost:3000/api/daily/upload-and-predict -F "predict_weeks=1"
# Expected: {"detail":"请先登录"}
```

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "feat: end-to-end verification of login system"
```

---

## Plan Self-Review

- [x] Spec coverage: 所有设计文档中的模块均有对应任务（数据模型 Task1-2、JWT Task3、中间件 Task4、认证 API Task5、管理 API Task6、路由保护 Task7、Store Task8、Axios Task9、路由守卫 Task10、登录页 Task11、用户管理页 Task12、布局改造 Task13、联调 Task14）
- [x] 无 TBD/TODO/占位符
- [x] 类型一致性：UserOut 字段在所有任务中一致；authStore 的 login/logout 在前端各组件中用法一致；API 路径在所有任务中保持一致
- [x] 所有代码步骤包含完整实现代码
- [x] 所有命令步骤包含预期输出
