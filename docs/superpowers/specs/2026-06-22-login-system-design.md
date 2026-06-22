# 登录认证系统 — 架构设计

> 日期: 2026-06-22 | 状态: 待审核

## 1. 需求摘要

| 维度 | 决策 |
|------|------|
| 用户规模 | 几十到几百员工，企业内部使用 |
| 账号创建 | 管理员批量创建，无开放注册 |
| 角色 | 管理员（管账号 + 全功能）+ 普通用户（使用预测功能） |
| 认证方式 | JWT Token（access 15min + refresh 7d） |
| 前端状态 | Pinia store + localStorage |
| 密码安全 | bcrypt (work_factor=12) |
| 数据存储 | SQLite 单文件，zero-config |
| Token 吊销 | token_version 机制，重置密码时递增使旧 token 失效 |

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue 3, Port 3000)                │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │ 登录页    │  │ 用户管理  │  │  现有业务页面        │    │
│  │ LoginView│  │ AdminView│  │  (预测/日报)         │    │
│  └────┬─────┘  └────┬─────┘  └─────────┬──────────┘    │
│       │             │                  │                │
│  ┌────┴─────────────┴──────────────────┴───────────┐   │
│  │              Router 导航守卫                      │   │
│  │    beforeEach: 白名单(登录) → 直接放行             │   │
│  │    需登录 → 检查 token → 无 token → /login        │   │
│  │    /admin/* → 额外检查 role === 'admin'          │   │
│  └──────────────────────┬──────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴──────────────────────────┐   │
│  │            Axios 拦截器 (authRequest.js)          │   │
│  │    request: 自动附加 Authorization: Bearer xxx    │   │
│  │    response 401: 自动 refresh → 重试 → 失败跳登录  │   │
│  └──────────────────────┬──────────────────────────┘   │
└─────────────────────────┼───────────────────────────────┘
                          │  Vite Proxy
┌─────────────────────────┼───────────────────────────────┐
│                    后端 (FastAPI, Port 8000)             │
│                         │                               │
│  ┌──────────────────────┴──────────────────────────┐   │
│  │           AuthMiddleware (依赖注入)               │   │
│  │    解析 JWT → 查用户 → 注入 request.current_user  │   │
│  │    路由级: Depends(require_admin) 做角色检查       │   │
│  └────────┬─────────────────────────────┬──────────┘   │
│           │                             │               │
│  ┌────────┴────────┐  ┌─────────────────┴──────────┐   │
│  │  /api/auth/*    │  │  /api/admin/*              │   │
│  │  · login        │  │  · users CRUD              │   │
│  │  · refresh      │  │                            │   │
│  │  · me           │  │                            │   │
│  │  · change-pwd   │  │                            │   │
│  └────────┬────────┘  └─────────────────┬──────────┘   │
│           │                             │               │
│  ┌────────┴─────────────────────────────┴──────────┐   │
│  │              现有业务 API (受保护)                │   │
│  │    /api/daily/*  →  需要登录即可访问              │   │
│  └─────────────────────────────────────────────────┘   │
│                         │                               │
│  ┌──────────────────────┴──────────────────────────┐   │
│  │              SQLite 数据库                        │   │
│  │    users 表: id, username, password_hash,        │   │
│  │              display_name, role, is_active,      │   │
│  │              token_version, created_at, last_login│   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## 3. 登录与续期流程

### 3.1 登录

```
用户 → 输入账号密码 → POST /api/auth/login
  → 后端验证明文密码 vs bcrypt hash
  → 生成 access_token (15min, 含 user_id+role)
  → 生成 refresh_token (7d, 含 user_id+token_version)
  → 更新 last_login
  → 返回 {access_token, refresh_token, user}
  → 前端存 localStorage + Pinia store
  → 路由跳转 /prediction
```

### 3.2 自动续期

```
任意 API 请求返回 401
  → axios 拦截器捕获
  → POST /api/auth/refresh {refresh_token}
    → 成功: 拿新 access_token → 重试原请求（用户无感知）
    → 失败: 清空 token → 跳转 /login
  → 并发请求排队共享一次 refresh，避免重复调用
```

### 3.3 Token 设计

| 字段 | access_token | refresh_token |
|------|:-----------:|:------------:|
| 有效期 | 15 分钟 | 7 天 |
| 存储位置 | localStorage | localStorage |
| 包含信息 | user_id, role, exp | user_id, token_version, exp |
| 传输方式 | Authorization Header | Request Body |

## 4. 数据模型

### 4.1 users 表

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password      TEXT    NOT NULL,              -- bcrypt hash
    display_name  TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user', -- 'admin' | 'user'
    is_active     INTEGER NOT NULL DEFAULT 1,      -- 1=启用 0=禁用
    token_version INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL,
    last_login    TEXT
);
```

### 4.2 管理员种子数据

首次启动时自动检查，无管理员则创建默认账号：
- 用户名: `admin` / 密码: `admin123`（首次登录强制修改）

## 5. API 规范

| 端点 | 方法 | 权限 | 说明 |
|------|------|------|------|
| `/api/auth/login` | POST | 公开 | 登录，返回双 token + 用户信息 |
| `/api/auth/refresh` | POST | 公开 | 用 refresh_token 换新 access_token |
| `/api/auth/me` | GET | 登录 | 获取当前用户信息 |
| `/api/auth/change-password` | POST | 登录 | 修改自己的密码 |
| `/api/admin/users` | GET | 管理员 | 用户列表（分页+搜索） |
| `/api/admin/users` | POST | 管理员 | 批量/单个创建用户 |
| `/api/admin/users/{id}` | PUT | 管理员 | 编辑用户信息 |
| `/api/admin/users/{id}/reset-password` | POST | 管理员 | 重置密码（吊销旧 token） |
| `/api/admin/users/{id}` | DELETE | 管理员 | 软删除（is_active=0） |

### 请求/响应示例

**POST /api/auth/login**
```json
// Request
{"username": "zhangsan", "password": "123456"}
// Response 200
{
  "access_token": "eyJhbG...",
  "refresh_token": "dGhpcy...",
  "user": {"id": 1, "username": "zhangsan", "display_name": "张三", "role": "admin"}
}
// Response 401
{"detail": "用户名或密码错误"}
```

**POST /api/admin/users**
```json
// Request
{"username": "lisi", "password": "Abc@1234", "display_name": "李四", "role": "user"}
// Response 201
{"id": 2, "username": "lisi", "display_name": "李四", "role": "user", "is_active": true}
```

## 6. 前端设计

### 6.1 路由改造

```javascript
// router/index.js — 新增路由 + 守卫
routes: [
  { path: '/login',          meta: { guest: true }},
  { path: '/admin/users',    meta: { requiresAdmin: true }},
  { path: '/prediction',     meta: { requiresAuth: true }},   // 改
  { path: '/daily-report',   meta: { requiresAuth: true }},   // 改
]

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.guest && token) return next('/prediction')
  if (to.meta.requiresAuth && !token) return next('/login')
  if (to.meta.requiresAdmin && user?.role !== 'admin') return next('/prediction')
  next()
})
```

### 6.2 Pinia Auth Store

```javascript
// stores/auth.js
export const useAuthStore = defineStore('auth', () => {
  const token = ref(...)
  const user = ref(...)
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) { ... }
  function logout() { ... clear + router.push('/login') }

  return { token, user, isLoggedIn, isAdmin, login, logout }
})
```

### 6.3 Axios 拦截器 (authRequest.js)

- request 拦截: 自动附加 `Authorization: Bearer <access_token>`
- response 401 拦截: 自动 refresh → 重试 → 失败跳登录
- 并发安全: 同一时刻多个请求同时 401，只发一次 refresh，其余排队共享结果

### 6.4 登录页

- 居中卡片式布局（`el-card` + `el-form`）
- 深色渐变背景
- 用户名 + 密码 + 登录按钮
- 无注册入口，无忘记密码
- 已登录用户访问 `/login` 自动跳业务页

### 6.5 用户管理页

- `el-table` 展示用户列表，支持按用户名搜索、按角色/状态筛选
- `el-dialog` 弹出新建/编辑表单
- 新建用户可指定用户名、姓名、密码、角色
- 重置密码：生成随机密码，弹窗展示（一次性复制）
- 删除：`el-popconfirm` 二次确认，软删除（is_active=0）

### 6.6 布局改造

- **AppHeader**: 右侧新增用户下拉菜单（`el-dropdown`），显示用户名和角色
  - 修改密码
  - 用户管理（仅管理员可见）
  - 退出登录
- **AppSidebar**: 底部新增"用户管理"菜单项，仅管理员可见

## 7. 依赖

| 层 | 包 | 用途 |
|---|-----|------|
| 后端 | `python-jose[cryptography]` | JWT 签发与验证 |
| 后端 | `passlib[bcrypt]` | 密码哈希 |
| 后端 | SQLite3 (Python 内置) | 数据存储 |
| 前端 | `pinia` | 认证状态管理 |

## 8. 文件变更清单

```
后端 (8 文件):
  日报预测/日报预测/
  ├── api_server.py          (改) — 注册 auth + admin 路由，给业务路由加 Depends
  ├── auth.py                (新) — JWT 签发/验证，密码 hash/verify
  ├── auth_middleware.py     (新) — Depends(require_login), Depends(require_admin)
  ├── database.py            (新) — SQLite 连接 + 建表 + 种子数据
  ├── models.py              (新) — User Pydantic models
  ├── admin_routes.py        (新) — 用户管理 CRUD 路由
  └── requirements.txt       (改) — 添加 python-jose, passlib

前端 (9 文件):
  smart-duration-prediction/src/
  ├── main.js                (改) — 注册 Pinia
  ├── App.vue                (改) — 无需大改，布局由子组件处理
  ├── router/index.js        (改) — 新增路由 + 守卫
  ├── utils/request.js       (改) — 保持原样（Dify API 独立）
  ├── utils/authRequest.js   (新) — 认证 API 的 axios 实例
  ├── stores/auth.js         (新) — Pinia 认证 store
  ├── views/Login.vue        (新) — 登录页
  ├── views/UserManagement.vue(新) — 用户管理页
  ├── components/layout/
  │   ├── AppHeader.vue      (改) — 右侧添加用户下拉菜单
  │   └── AppSidebar.vue     (改) — 添加用户管理菜单项
  └── package.json           (改) — 添加 pinia
```

## 9. 实现任务

| # | 任务 | 说明 |
|---|------|------|
| 1 | 后端奠基 | database.py + models.py + 建表 + 种子 admin |
| 2 | 密码与 JWT | auth.py: hash/verify, 签发/验证 token |
| 3 | 认证 API | /auth/login, /auth/refresh, /auth/me, /auth/change-password |
| 4 | 用户管理 API | admin_routes.py CRUD + 注册到 api_server |
| 5 | 中间件挂载 | auth_middleware.py + 保护现有业务路由 |
| 6 | 前端基础设施 | Pinia store + authRequest 拦截器 + 路由守卫 |
| 7 | 登录页 | Login.vue |
| 8 | 布局改造 | AppHeader 用户下拉 + AppSidebar 菜单权限 |
| 9 | 用户管理页 | UserManagement.vue + 弹窗表单 |
| 10 | 联调验证 | 端到端流程测试 |

## 10. 自检清单

- [x] 无 TBD / TODO 占位符
- [x] 认证流程与续期逻辑一致
- [x] token_version 吊销机制与 refresh 过期策略无冲突
- [x] 路由守卫覆盖未登录、已登录跳转、管理员权限三个场景
- [x] axios 拦截器处理并发 401 场景
- [x] 所有 API 端点权限标注明确
- [x] 种子数据确保首次可用
