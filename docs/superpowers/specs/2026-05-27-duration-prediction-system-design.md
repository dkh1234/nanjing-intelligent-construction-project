# 智能工期预测系统 — 前端设计文档

## 项目概述

为中材国际工程股份有限公司构建的水泥厂熟料生产线建设项目 AI 工期预测系统前端。接入 Dify Workflow API，输入项目参数和合同文件，输出 AI 分析报告（Markdown）和项目策划书（Word）。

## 技术栈

| 项 | 选型 | 说明 |
|---|------|------|
| 框架 | Vue 3 (Composition API) | script setup 语法 |
| 构建 | Vite 5 | 快速 HMR |
| UI 库 | Element Plus 2.9 | 企业级组件库 |
| 路由 | Vue Router 4 | SPA 路由 |
| HTTP | Axios 1.7 | API 调用 + interceptors |
| Markdown | markdown-it 14 | 渲染 AI 分析报告 |
| 样式 | SCSS | 变量 + 嵌套 + 全局样式 |
| 图标 | @element-plus/icons-vue | 统一图标库 |

## 项目结构

```
smart-duration-prediction/
├── index.html
├── vite.config.js
├── package.json
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/index.js
│   ├── views/
│   │   ├── Home.vue                   # 工作台首页
│   │   ├── DurationPrediction.vue     # ★ 工期预测（核心）
│   │   ├── ProjectList.vue            # 项目管理
│   │   ├── RiskAnalysis.vue           # 风险分析
│   │   ├── ProgressTracking.vue       # 进度跟踪
│   │   ├── ReportCenter.vue           # 报告中心
│   │   └── SystemSettings.vue         # 系统设置
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue
│   │   │   └── AppSidebar.vue         # 可折叠
│   │   └── prediction/
│   │       ├── ProjectInfoCard.vue
│   │       ├── StructureParamsCard.vue
│   │       ├── CriticalPathCard.vue
│   │       ├── AiStepProgress.vue
│   │       ├── MarkdownResult.vue
│   │       └── FileDownloadCard.vue
│   ├── composables/
│   │   └── useDifyWorkflow.js
│   ├── styles/
│   │   ├── variables.scss
│   │   └── global.scss
│   └── utils/
│       └── request.js
```

## 布局方案

两栏布局：左侧可折叠导航 + 右侧内容区（上下滚动）。

```
┌──────────────────────────────────────────┐
│  Header（深蓝 #0B1F3A，56px）              │
├────────┬─────────────────────────────────┤
│ 左侧   │  [步骤条：提交→分析→生成→完成]     │
│ 导航   │  ┌─ 参数输入区 ──────────────────┐ │
│ 220px  │  │ 卡片1: 项目基础信息            │ │
│ 可折叠  │  │ 卡片2: 结构参数（双列grid）     │ │
│        │  │ 卡片3: 结构层数               │ │
│        │  │ 卡片4: 关键路径（步骤条风格）     │ │
│        │  │ [开始工期预测] 蓝色大按钮       │ │
│        │  ├──────────────────────────────┤ │
│        │  │ AI 分析结果区                  │ │
│        │  │ Markdown 渲染 + 文件下载        │ │
│        │  └──────────────────────────────┘ │
├────────┴─────────────────────────────────┤
│  Footer                                  │
└──────────────────────────────────────────┘
```

### 侧边栏菜单

| 菜单项 | 状态 | 说明 |
|--------|------|------|
| 首页 | 可用 | 工作台统计看板 |
| 项目管理 | 可用 | 历史预测记录列表 |
| 工期预测 | 高亮 | 当前核心页面 |
| 风险分析 | 预留 | disabled 灰显 |
| 资源管理 | 预留 | disabled 灰显 |
| 进度跟踪 | 预留 | disabled 灰显 |
| 报告中心 | 预留 | disabled 灰显 |
| 系统设置 | 预留 | disabled 灰显 |

侧边栏底部：用户信息 + 退出。

## 组件设计

### 1. AppHeader.vue

- 深蓝背景 #0B1F3A，高度 56px，flex 左右布局
- 左侧：Logo（SVG图标）+ "智能工期预测系统" 标题
- 右侧：帮助文档（链接）、消息通知（badge 铃铛）、用户头像（el-avatar）
- 无 props。纯展示组件。

### 2. AppSidebar.vue

- 接收 props：`collapsed: boolean`、`activeMenu: string`
- emit：`update:collapsed`、`menu-select`
- 深蓝背景，菜单项白字 + 选中态蓝色高亮 + 左侧蓝色指示条
- 折叠时宽度 54px（仅图标），展开 220px
- 底部用户信息区，折叠时仅头像

### 3. ProjectInfoCard.vue

- Props：`modelValue: { projectName, contractFile }`
- 项目名称：el-input，placeholder="例：5000t/d熟料生产线建设项目"
- 合同文件上传：el-upload drag，accept=".pdf,.doc,.docx"，limit=1，max-size=50MB
- Word 图标 + 文件名显示
- Emit：`update:modelValue`

### 4. StructureParamsCard.vue

- Props：`modelValue: { heater, length, width, concreteHeight, totalHeight, foundation }`
- 双列 el-row / el-col (span=12)，gap=16px
- 预热器：el-select，选项 TBD（需确认业务方提供的预热器类型列表）
- 长度/宽度/砼框架/总高：el-input-number，min=0，step=0.1，后缀"m"
- 基础形式：el-select
- Emit：`update:modelValue`

### 5. CriticalPathCard.vue

- Props：`modelValue: string[]`（默认5条）
- 左侧步骤编号圆点（蓝底白字 1→2→3...），竖线连接
- 每个步骤对应一个 el-input
- 添加按钮（列表底部），删除按钮（每项右侧 × 图标）
- 限制：最少 3 条（隐藏删除按钮），最多 5 条（隐藏添加按钮）
- 动画：添加/删除时轻微的列表过渡
- Emit：`update:modelValue`

### 6. AiStepProgress.vue

- Props：`currentStep: number`（0=未开始, 1=提交表单, 2=AI分析中, 3=生成报告, 4=完成）
- 4 个步骤点 + 连接线，当前步骤蓝色高亮 + pulse 呼吸动画
- el-steps 组件定制样式

### 7. MarkdownResult.vue

- Props：`content: string`（Markdown 原始字符串）、`loading: boolean`、`error: string`
- 空状态：el-empty，描述="请填写参数后开始工期预测"
- 加载中：el-skeleton 占位
- 错误：el-result status="error" + 错误信息 + 重试按钮
- 正常：markdown-it 渲染内容，标题蓝色，表格/代码块样式定制
- 滚动区域 max-height: calc(100vh - 500px)，溢出滚动，滚动条美化

### 8. FileDownloadCard.vue

- Props：`fileName: string`、`fileSize: string`、`downloadUrl: string`
- 左侧 Word 图标（蓝色），文件名 + 大小，右侧 el-button 下载
- 文件 url 不存在时不显示
- Emit：`download`

## 数据流设计

### DurationPrediction.vue（主页面）

```
┌─ DurationPrediction.vue ─────────────────────────────┐
│                                                       │
│  表单状态 (reactive):                                  │
│  { projectName, contractFile, heater, length, width,  │
│    concreteHeight, totalHeight, foundation,           │
│    concreteLayer, towerLayer, criticalPaths[] }       │
│                                                       │
│  结果状态:                                             │
│  { markdownContent, wordFileUrl, wordFileName,         │
│    wordFileSize, currentStep, apiLoading, apiError }  │
│                                                       │
│  useDifyWorkflow() ──► Axios ──► BFF Proxy ──► Dify   │
│       ▲                                              │
│       └── submit(formState)                          │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 表单提交流程

1. 点击"开始工期预测" → 触发全部卡片 el-form validate
2. 校验通过 → `useDifyWorkflow.submit(params)`
3. `currentStep` 从 1 → 4 依次推进（模拟步骤动画，实际等待 API 返回）
4. API 返回成功 → 解析 markdown + word 链接 → 渲染结果
5. API 失败 → 错误状态展示

### Dify API 交互

使用标准 JSON 模式（文件先上传获取 file_id）：

```
POST /v1/files/upload     → 上传合同文件 → 获取 file_id
POST /v1/workflows/run    → 传入所有参数（含 file_id） + response_mode: blocking
                          → 返回 { outputs: { markdown_report, word_file_url, ... } }
```

`useDifyWorkflow.js` composable 封装完整流程，对外暴露：

```js
{ submit, loading, result, error, currentStep, reset }
```

## 安全架构

- 开发环境：vite.config.js proxy 代理转发到 Dify，API Key 仅存于 server 端
- 生产环境：必须部署 BFF 层（Node/Go/Java），API Key 存储于环境变量，前端不感知
- 不做前端硬编码 API Key

## 路由设计

| 路径 | 组件 | 标题 |
|------|------|------|
| `/` | Home.vue | 工作台首页 |
| `/prediction` | DurationPrediction.vue | 工期预测 |
| `/projects` | ProjectList.vue | 项目管理 |

其他预留页面统一 redirect 到 `/`。

## UI 设计规范

### 颜色

| Token | 值 | 用途 |
|-------|-----|------|
| --color-primary-dark | #0B1F3A | Header/侧边栏背景 |
| --color-primary | #1677FF | 按钮/链接/高亮 |
| --color-primary-light | #E6F4FF | 浅蓝背景 |
| --color-bg | #F5F7FA | 页面底色 |
| --color-white | #FFFFFF | 卡片背景 |
| --color-text-primary | #1D2129 | 主文字 |
| --color-text-secondary | #86909C | 辅助文字 |
| --color-border | #E5E6EB | 边框 |
| --color-success | #00B42A | 步骤完成 |
| --color-warning | #FF7D00 | 警告 |

### 阴影

```
--shadow-card: 0 2px 12px rgba(0, 0, 0, 0.06);
--shadow-card-hover: 0 4px 16px rgba(0, 0, 0, 0.1);
```

### 圆角

- 卡片：12px
- 按钮：6px
- 输入框：6px

### 间距

| Token | 值 | 场景 |
|-------|-----|------|
| xs | 8px | 标签间距 |
| sm | 12px | 卡片内间距 |
| md | 16px | 卡片 padding |
| lg | 24px | 卡片间距 |
| xl | 32px | 大区块间距 |

### 字体

字体栈：`"PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif`

| 层级 | 大小 | 字重 |
|------|------|------|
| 页面标题 | 24px | 600 |
| 卡片标题 | 18px | 600 |
| 区块标题 | 16px | 500 |
| 正文 | 14px | 400 |
| 辅助文字 | 12px | 400 |

## 关键路径默认值

| 序号 | 默认值 |
|------|--------|
| 1 | 土建施工 |
| 2 | 钢结构安装 |
| 3 | 设备安装 |
| 4 | 电气仪表施工 |
| 5 | 单机试运转与联动调试 |

## 边界情况处理

| 场景 | 处理方式 |
|------|----------|
| 首次进入页面 | 结果区显示空状态引导 |
| 表单未填完点击提交 | el-form validate 拦截，滚动到第一个错误字段 |
| 文件超过 50MB | el-upload before-upload 钩子拦截 + 提示 |
| API 调用失败 | 显示错误卡片，展示错误信息 + 重试按钮 |
| API 超时 | Axios timeout 120s，超时后显示超时提示 |
| 下载链接过期 | 提示"文件链接已过期，请重新生成" |
| 侧边栏折叠 | 导航区 54px，内容区自动伸展 |
| 小屏幕 < 1024px | 自适应堆叠布局，输入区和结果区上下排列 |

## 未实现项（后续迭代）

- 表单暂存（localStorage）
- 项目管理页完整功能（历史记录列表/搜索/筛选/详情）
- 项目数据对比分析图表
- 用户登录/鉴权
- 多语言
- 深色模式

---

## 变更记录

| 日期 | 变更 |
|------|------|
| 2026-05-27 | 初始版本，完成设计文档 |
