# GitHub 多人协作操作指南

## 项目：DIfy 工期预测系统

| 项目信息 | 详情 |
| --- | --- |
| **GitHub 仓库** | <https://github.com/dkh1234/nanjing-intelligent-construction-project> |
| **SSH 克隆地址** | `git@github.com:dkh1234/nanjing-intelligent-construction-project.git` |
| **主分支** | `master` |
| **子模块** | `smart-duration-prediction` |

---

## 目录

1. [环境准备](#1-环境准备)
2. [首次获取项目（克隆）](#2-首次获取项目克隆)
3. [日常开发流程](#3-日常开发流程)
4. [分支管理规范](#4-分支管理规范)
5. [子模块管理](#5-子模块管理)
6. [冲突处理](#6-冲突处理)
7. [常用命令速查](#7-常用命令速查)
8. [协作规则与最佳实践](#8-协作规则与最佳实践)
9. [常见问题排查](#9-常见问题排查)

---

## 1. 环境准备

### 1.1 安装 Git

**Windows：**
- 下载地址：https://git-scm.com/download/win
- 安装时选择默认选项即可，推荐勾选 "Git Bash Here"（右键菜单）
- 验证安装：打开终端输入 `git --version`，看到版本号即成功

**macOS：**
```bash
brew install git
```

**Linux (Ubuntu/Debian)：**
```bash
sudo apt update && sudo apt install git
```

### 1.2 配置 Git 用户信息

每个人首次使用 Git 必须配置自己的身份信息，这样提交记录才知道是谁做的：

```bash
git config --global user.name "你的姓名拼音或英文名"
git config --global user.email "你的邮箱@example.com"
```

> ⚠️ **重要**：user.name 请使用真实姓名拼音，方便团队成员识别。不要使用网名或昵称。

### 1.3 配置 GitHub 认证

**方式一：SSH 密钥（推荐）**

```bash
# 1. 生成 SSH 密钥（一路回车即可）
ssh-keygen -t ed25519 -C "你的邮箱@example.com"

# 2. 复制公钥内容
cat ~/.ssh/id_ed25519.pub

# 3. 打开 GitHub → Settings → SSH and GPG keys → New SSH key
#    粘贴公钥内容，保存

# 4. 测试连接
ssh -T git@github.com
```

**方式二：Personal Access Token（HTTPS 方式）**

1. 打开 GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. 点击 "Generate new token (classic)"
3. 勾选 `repo`、`workflow` 权限
4. 生成后**立即复制保存**（只显示一次）
5. 首次 git push 时输入用户名和该 Token 作为密码

### 1.4 配置换行符（Windows 用户必须）

```bash
# Windows 用户执行（防止换行符冲突）
git config --global core.autocrlf true

# macOS/Linux 用户执行
git config --global core.autocrlf input
```

---

## 2. 首次获取项目（克隆）

### 2.1 克隆主仓库

```bash
# 进入你要存放项目的目录，例如：
cd d:/projects

# 克隆仓库
git clone git@github.com:dkh1234/nanjing-intelligent-construction-project.git

# 进入项目目录
cd nanjing-intelligent-construction-project
```

### 2.2 初始化子模块

本项目包含子模块 `smart-duration-prediction`，克隆后必须初始化：

```bash
# 在项目根目录下执行
git submodule update --init --recursive
```

如果克隆时就想一步到位：

```bash
git clone --recurse-submodules git@github.com:dkh1234/nanjing-intelligent-construction-project.git
```

### 2.3 拉取所有分支

```bash
git fetch --all
```

### 2.4 验证环境

```bash
# 确认在 master 分支
git branch

# 确认子模块正常
git submodule status

# 查看项目结构
ls
```

---

## 3. 日常开发流程

### 3.1 每天开始工作前 — 拉取最新代码

```bash
# 1. 切换到 master 分支
git checkout master

# 2. 拉取远程最新代码
git pull origin master

# 3. 更新子模块（如有更新）
git submodule update --init --recursive
```

### 3.2 开始一个新功能 — 创建功能分支

```bash
# 从最新的 master 创建你的功能分支
# 命名规则: feature/功能描述-你的名字
git checkout -b feature/xxx功能-zhangsan

# 例如：
git checkout -b feature/add-login-page-zhangsan
```

### 3.3 开发过程中 — 提交代码

```bash
# 1. 查看当前修改
git status

# 2. 将修改的文件添加到暂存区
git add 文件名              # 添加单个文件
git add .                   # 添加当前目录所有修改（谨慎使用）

# 3. 提交到本地仓库（写好提交信息）
git commit -m "feat: 添加登录页面"

# 4. 推送到远程仓库
git push origin feature/add-login-page-zhangsan
```

### 3.4 提交信息规范

本项目采用以下提交信息格式：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 添加工期预测图表` |
| `fix:` | 修复 bug | `fix: 修复日期格式解析错误` |
| `docs:` | 文档修改 | `docs: 更新 API 接口文档` |
| `style:` | 代码格式（不影响功能） | `style: 统一缩进为 2 空格` |
| `refactor:` | 重构代码 | `refactor: 提取公共日期处理函数` |
| `test:` | 添加测试 | `test: 添加预测模块单元测试` |
| `chore:` | 构建/工具变更 | `chore: 更新依赖版本` |

> ⚠️ **重要**：提交信息必须使用中文，方便团队理解。不要写 "update"、"fix bug" 这种模糊信息。

### 3.5 合并到 master — Pull Request 流程

```bash
# 1. 确保功能分支已推送到 GitHub
git push origin feature/xxx功能-zhangsan

# 2. 在 GitHub 网页上创建 Pull Request
#    打开仓库页面 → Pull requests → New pull request
#    base: master  ←  compare: feature/xxx功能-zhangsan

# 3. 填写 PR 描述：做了什么、为什么这么做、测试了没有

# 4. 通知团队成员进行 Code Review

# 5. Review 通过后，由项目负责人合并到 master

# 6. 合并后删除远程功能分支（在 GitHub PR 页面勾选即可）

# 7. 本地也清理一下
git checkout master
git pull origin master
git branch -d feature/xxx功能-zhangsan  # 删除本地分支
```

---

## 4. 分支管理规范

### 4.1 分支类型

```
master              ← 主分支，始终可部署，禁止直接提交
  ├── develop       ← 开发分支（可选，大项目使用）
  ├── feature/xxx   ← 功能分支，从 master 分出，合并回 master
  ├── fix/xxx       ← 修复分支，从 master 分出，合并回 master
  └── hotfix/xxx    ← 紧急修复，从 master 分出，合并回 master
```

### 4.2 分支命名规则

| 分支类型 | 命名格式 | 示例 |
|----------|----------|------|
| 功能开发 | `feature/功能简述-姓名` | `feature/duration-chart-wangwu` |
| Bug 修复 | `fix/问题简述-姓名` | `fix/date-parse-error-zhangsan` |
| 紧急修复 | `hotfix/问题简述-姓名` | `hotfix/login-crash-lisi` |

### 4.3 黄金规则

| 规则 | 说明 |
|------|------|
| ❌ **禁止**直接推送到 master | master 只能通过 Pull Request 合并 |
| ❌ **禁止** `git push --force` | 强制推送会覆盖别人的代码 |
| ❌ **禁止**提交大文件（>10MB） | 大文件用 Git LFS 或云盘共享 |
| ✅ 每天开始先 pull | 避免基于旧代码开发 |
| ✅ 功能分支存活不超过 3 天 | 小步快跑，避免合并冲突积累 |
| ✅ 提交前先本地测试 | 确保代码能正常运行 |

---

## 5. 子模块管理

本项目包含 `smart-duration-prediction` 子模块，它是一个独立的 Git 仓库。

### 5.1 初始化子模块（首次使用）

```bash
git submodule update --init --recursive
```

### 5.2 拉取子模块最新代码

```bash
# 方式一：进入子模块目录拉取
cd smart-duration-prediction
git checkout main   # 或 master，看子模块的默认分支
git pull
cd ..

# 方式二：在项目根目录一键更新
git submodule update --remote
```

### 5.3 修改子模块内容

如果你需要修改子模块中的代码：

```bash
# 1. 进入子模块
cd smart-duration-prediction

# 2. 确保在正确的分支上
git checkout main

# 3. 正常修改、提交
git add .
git commit -m "feat: 某某修改"

# 4. 推送子模块
git push origin main

# 5. 回到主项目，记录子模块的版本变更
cd ..
git add smart-duration-prediction
git commit -m "chore: 更新 smart-duration-prediction 子模块"
git push origin 你的分支名
```

> ⚠️ **重要**：修改子模块前，务必和团队沟通，确认没有人同时在改。

### 5.4 检查子模块状态

```bash
# 查看子模块当前指向的提交
git submodule status

# 输出示例：
#  a1b2c3d smart-duration-prediction (v1.0)
# 如果前面有 + 号，说明子模块有未提交的变更
# 如果前面有 - 号，说明子模块未初始化
```

---

## 6. 冲突处理

### 6.1 冲突是怎样产生的

当两个人修改了同一个文件的同一行时，Git 无法自动合并，需要手动解决。

### 6.2 解决冲突步骤

```bash
# 情况一：在合并 master 到你的功能分支时冲突
git checkout feature/xxx
git merge master

# 如果出现冲突提示：
# Auto-merging 某文件
# CONFLICT (content): Merge conflict in 某文件

# 情况二：在 GitHub PR 页面提示有冲突
# 同样在本地操作解决
```

**解决流程：**

```bash
# 1. 打开冲突文件，你会看到类似这样的标记：
#    <<<<<<< HEAD
#    你的修改
#    =======
#    别人的修改
#    >>>>>>> master

# 2. 手动编辑文件，删除 <<<<<<<, =======, >>>>>>> 标记
#    保留正确的代码（可能两边都要，也可能只保留一边）

# 3. 标记冲突已解决
git add 冲突文件名

# 4. 完成合并
git commit -m "merge: 解决与 master 的冲突"

# 5. 推送到远程
git push origin feature/xxx
```

### 6.3 减少冲突的技巧

- **每天拉取 master**：`git pull origin master`
- **小步提交**：不要把大量修改攒在一起提交
- **沟通先行**：修改公共文件前，先在群里说一声
- **按模块分工**：尽量避免两个人同时改同一个文件

---

## 7. 常用命令速查

### 7.1 日常高频命令

```bash
# ── 查看类 ──
git status                          # 查看当前修改状态
git log --oneline -10               # 查看最近 10 条提交记录
git log --oneline --graph --all     # 查看分支图
git diff                            # 查看未暂存的修改内容
git diff --staged                   # 查看已暂存的修改内容

# ── 撤销类 ──
git checkout -- 文件名              # 撤销单个文件的修改（未 add 时）
git reset HEAD 文件名               # 取消暂存（已 add 但未 commit）
git reset --soft HEAD~1             # 撤销最近一次 commit（保留修改）
git reset --hard HEAD~1             # 彻底撤销最近一次 commit（丢弃修改）

# ── 暂存工作现场（切换分支但不想提交时）──
git stash                           # 暂存当前修改
git stash pop                       # 恢复暂存的修改
git stash list                      # 查看暂存列表

# ── 分支操作 ──
git branch                          # 查看本地分支
git branch -a                       # 查看所有分支（含远程）
git branch -d 分支名                # 删除本地分支
git checkout -b 新分支名            # 创建并切换到新分支
git merge 分支名                    # 将指定分支合并到当前分支

# ── 远程操作 ──
git remote -v                       # 查看远程仓库地址
git fetch origin                    # 拉取远程信息（不合并）
git pull origin master              # 拉取并合并 master
git push origin 分支名              # 推送到远程
git push origin --delete 分支名     # 删除远程分支
```

### 7.2 紧急情况处理

```bash
# "我提交到了错误的分支"
git log --oneline -1                # 记下最新的 commit hash
git checkout 正确的分支
git cherry-pick <commit-hash>       # 把那次提交"摘"过来
git checkout 错误的分支
git reset --hard HEAD~1             # 在错误分支上撤销

# "我的代码乱了，想回到和远程 master 一样"
git fetch origin
git checkout master
git reset --hard origin/master

# "我不小心 add 了一个不该提交的文件"
git reset HEAD 文件名               # 取消暂存该文件
# 然后可以将文件加入 .gitignore
```

---

## 8. 协作规则与最佳实践

### 8.1 开发铁律

| 序号 | 规则 |
|------|------|
| 1 | **每天开始工作前，先 `git pull` 拉取最新代码** |
| 2 | **永远在功能分支上开发，不直接在 master 上改代码** |
| 3 | **子模块修改前必须团队沟通，避免冲突** |
| 4 | **提交前检查是否包含敏感信息（密码、密钥、Token）** |
| 5 | **大文件（>10MB）不要提交到 Git，用网盘共享** |
| 6 | **不提交编译产物、依赖包、临时文件** |

### 8.2 需要加入 .gitignore 的内容

以下内容**不应该**提交到仓库：

```
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# IDE
.idea/
.vscode/
*.swp
*.swo

# 数据库
*.db
*.sqlite

# 临时文件
*.tmp
*.log
*.bak

# 环境配置（如果包含敏感信息）
.env
.env.local

# 系统文件
.DS_Store
Thumbs.db
```

### 8.3 团队沟通约定

| 场景 | 沟通方式 |
|------|----------|
| 开始新功能 | 团队群里说一声，确认没人同时在改 |
| 修改子模块 | 必须提前沟通，约定时间段 |
| 创建 PR | @相关同事请求 Review |
| 遇到冲突 | 和冲突的提交者一起看，不要自己拍脑袋解决 |
| 需要回滚 | 在群里通知，说明原因和影响 |

### 8.4 推荐的 Git 工作流（简化版 Git Flow）

```
1. git pull origin master          ← 拉取最新
2. git checkout -b feature/xxx     ← 创建功能分支
3. [开发中... 小步提交]
4. git push origin feature/xxx     ← 推送功能分支
5. [在 GitHub 创建 PR]
6. [Code Review → 修改 → 通过]
7. [合并到 master，删除功能分支]
8. git checkout master && git pull ← 切回 master 并更新
```

---

## 9. 常见问题排查

### Q1: `git push` 时提示 "Permission denied"

**原因**：SSH 密钥未配置或已过期。

**解决**：
```bash
# 检查 SSH 连接
ssh -T git@github.com

# 如果失败，重新配置 SSH 密钥（见 1.3 节）
```

### Q2: `git pull` 时提示 "You have unstaged changes"

**原因**：本地有未提交的修改。

**解决**：
```bash
# 方案 A：先提交本地修改
git add .
git commit -m "临时保存"
git pull origin master

# 方案 B：暂存修改
git stash
git pull origin master
git stash pop
```

### Q3: 子模块显示为空文件夹

**原因**：克隆时没有初始化子模块。

**解决**：
```bash
git submodule update --init --recursive
```

### Q4: git push 后子模块在同事电脑上显示老版本

**原因**：同事没有更新子模块。

**解决（同事执行）**：
```bash
git pull origin master
git submodule update --init --recursive
```

### Q5: 不小心 `git add .` 添加了不该提交的文件

**解决**：
```bash
# 取消暂存但保留文件修改
git reset HEAD 文件路径

# 将该文件加入 .gitignore 防止下次再误加
echo "文件路径" >> .gitignore
git add .gitignore
git commit -m "chore: 更新 .gitignore"
```

### Q6: 提交后发现漏了文件

**解决**：
```bash
# 添加遗漏的文件
git add 遗漏的文件

# 合并到上一次提交（不产生新的 commit）
git commit --amend --no-edit

# 如果已经 push 了，需要强制推送（⚠️ 仅在你的个人功能分支上使用！）
git push --force-with-lease origin 你的分支名
```

---

## 附录：快速启动清单

### 新人入职第一天

- [ ] 安装 Git
- [ ] 配置 user.name 和 user.email
- [ ] 配置 SSH 密钥并添加到 GitHub
- [ ] 克隆项目到本地
- [ ] 初始化子模块
- [ ] 创建自己的第一个功能分支试一下
- [ ] 阅读 [启动与关闭步骤.txt](../启动与关闭步骤.txt)
- [ ] 将本文件的 Git 别名配置添加到 ~/.bashrc 或 ~/.gitconfig

### 每日工作清单

- [ ] `git pull origin master` — 拉取最新代码
- [ ] `git submodule update` — 同步子模块
- [ ] 创建/切换到功能分支
- [ ] 开发，小步提交
- [ ] 推送并创建 PR
- [ ] 下班前确认代码已推送到远程

---

> 📅 文档版本：v1.0
> 📝 最后更新：2026-06-29
> 👤 维护者：项目组
>
> **如有疑问，先在团队群沟通，不要猜！**
