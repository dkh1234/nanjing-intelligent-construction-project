# 智能工期预测系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个面向中材国际的水泥厂熟料生产线 AI 工期预测前端系统，接入 Dify Workflow API。

**Architecture:** Vue3 + Element Plus + Vite + Vue Router SPA，两栏布局（可折叠侧边栏 + 上下内容区），4 个表单卡片组件 + AI 结果区域 + Dify API composable 封装。开发环境通过 Vite proxy 转发 API。

**Tech Stack:** Vue 3.5 (Composition API / script setup), Vite 5, Element Plus 2.9, Vue Router 4, Axios 1.7, markdown-it 14, SCSS, @element-plus/icons-vue

---

## File Structure

所有文件路径相对于 `d:/Users/DIfy工期预测项目/smart-duration-prediction/`：

```
smart-duration-prediction/
├── index.html                         # 入口 HTML
├── vite.config.js                     # Vite 配置（含 proxy）
├── package.json                       # 依赖清单
├── src/
│   ├── main.js                        # Vue 应用入口
│   ├── App.vue                        # 根组件（layout 骨架）
│   ├── router/
│   │   └── index.js                   # 路由配置
│   ├── views/
│   │   ├── Home.vue                   # 工作台首页
│   │   ├── DurationPrediction.vue     # ★ 工期预测核心页
│   │   └── ProjectList.vue            # 项目管理页
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppHeader.vue          # 顶部 Header
│   │   │   └── AppSidebar.vue         # 左侧可折叠导航
│   │   └── prediction/
│   │       ├── ProjectInfoCard.vue    # 卡片：项目信息+文件上传
│   │       ├── StructureParamsCard.vue# 卡片：结构参数双列
│   │       ├── CriticalPathCard.vue   # 卡片：动态关键路径
│   │       ├── AiStepProgress.vue     # AI 流程步骤条
│   │       ├── MarkdownResult.vue     # Markdown 渲染结果
│   │       └── FileDownloadCard.vue   # Word 文件下载卡片
│   ├── composables/
│   │   └── useDifyWorkflow.js         # Dify API 封装
│   ├── styles/
│   │   ├── variables.scss             # SCSS 全局变量
│   │   └── global.scss                # 全局样式
│   └── utils/
│       └── request.js                 # Axios 实例封装
```

---

### Task 1: 项目初始化

**Files:**
- Create: `package.json`
- Create: `vite.config.js`
- Create: `index.html`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "smart-duration-prediction",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.5.13",
    "vue-router": "^4.5.0",
    "element-plus": "^2.9.1",
    "axios": "^1.7.9",
    "markdown-it": "^14.1.0",
    "@element-plus/icons-vue": "^2.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "sass": "^1.83.0",
    "vite": "^5.4.14"
  }
}
```

- [ ] **Step 2: 创建 vite.config.js**

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api/dify': {
        target: 'https://api.dify.ai',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/dify/, '/v1')
      }
    }
  }
})
```

- [ ] **Step 3: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>智能工期预测系统</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.js"></script>
</body>
</html>
```

- [ ] **Step 4: 安装依赖**

Run: `cd "d:/Users/DIfy工期预测项目/smart-duration-prediction" && npm install`
Expected: 所有依赖安装成功，无报错。

- [ ] **Step 5: 验证项目能启动**

Run: `cd "d:/Users/DIfy工期预测项目/smart-duration-prediction" && npx vite --host 0.0.0.0`
Expected: Dev server 在 localhost:3000 启动。然后 Ctrl+C 停止。

- [ ] **Step 6: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/package.json smart-duration-prediction/vite.config.js smart-duration-prediction/index.html && git commit -m "feat: project scaffolding — Vite + Vue3 + Element Plus"
```

---

### Task 2: 全局样式变量

**Files:**
- Create: `src/styles/variables.scss`
- Create: `src/styles/global.scss`

- [ ] **Step 1: 创建 SCSS 变量文件**

File: `src/styles/variables.scss`

```scss
// === 颜色系统 ===
$color-primary-dark:  #0B1F3A;
$color-primary:       #1677FF;
$color-primary-hover: #4096FF;
$color-primary-light: #E6F4FF;
$color-bg:            #F5F7FA;
$color-white:         #FFFFFF;
$color-text-primary:  #1D2129;
$color-text-secondary:#86909C;
$color-text-placeholder: #C9CDD4;
$color-border:        #E5E6EB;
$color-border-light:  #F2F3F5;
$color-success:       #00B42A;
$color-warning:       #FF7D00;
$color-danger:        #F53F3F;

// === 侧边栏 ===
$sidebar-width:       220px;
$sidebar-collapsed:   54px;

// === Header ===
$header-height:       56px;

// === 阴影 ===
$shadow-card:         0 2px 12px rgba(0, 0, 0, 0.06);
$shadow-card-hover:   0 4px 16px rgba(0, 0, 0, 0.10);

// === 圆角 ===
$radius-card:         12px;
$radius-button:       6px;
$radius-input:        6px;

// === 间距 ===
$spacing-xs:          8px;
$spacing-sm:          12px;
$spacing-md:          16px;
$spacing-lg:          24px;
$spacing-xl:          32px;
$spacing-xxl:         48px;

// === 字体 ===
$font-family:         "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
$font-size-title:     24px;
$font-size-card-title:18px;
$font-size-section:   16px;
$font-size-body:      14px;
$font-size-caption:   12px;

// === 过渡 ===
$transition-normal:   0.3s ease;
$transition-fast:     0.2s ease;
```

- [ ] **Step 2: 创建全局样式文件**

File: `src/styles/global.scss`

```scss
@use './variables.scss' as *;

// === Reset ===
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: $font-family;
  font-size: $font-size-body;
  color: $color-text-primary;
  background-color: $color-bg;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}

// === 滚动条美化 ===
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #C9CDD4;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #A8ABB7;
}

// === 通用卡片样式 ===
.prediction-card {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $spacing-lg;
  margin-bottom: $spacing-md;
  transition: box-shadow $transition-normal;

  &:hover {
    box-shadow: $shadow-card-hover;
  }

  &__title {
    font-size: $font-size-card-title;
    font-weight: 600;
    color: $color-text-primary;
    margin-bottom: $spacing-md;
    padding-left: 12px;
    border-left: 3px solid $color-primary;
  }

  &__content {
    padding: 0;
  }
}

// === 蓝色渐变按钮 ===
.btn-predict {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  border-radius: $radius-button;
  background: linear-gradient(135deg, $color-primary, #4096FF);
  border: none;
  color: #fff;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background: linear-gradient(135deg, #4096FF, $color-primary);
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(22, 119, 255, 0.35);
  }

  &:active {
    transform: translateY(0);
  }

  &.is-loading {
    pointer-events: none;
    opacity: 0.8;
  }
}

// === fade 过渡 ===
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
```

- [ ] **Step 3: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/styles/ && git commit -m "feat: SCSS variables and global styles"
```

---

### Task 3: Axios 实例 + Vue 入口

**Files:**
- Create: `src/utils/request.js`
- Create: `src/main.js`

- [ ] **Step 1: 创建 Axios 封装**

File: `src/utils/request.js`

```js
import axios from 'axios'

const BASE_URL = '/api/dify'

const request = axios.create({
  baseURL: BASE_URL,
  timeout: 120000, // Dify 阻塞模式最长 2 分钟
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 生产环境应通过 BFF 层注入 API Key，此处预留
    // config.headers['Authorization'] = 'Bearer ' + getApiKey()
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      return Promise.reject(new Error('请求超时，请稍后重试'))
    }
    const message = error.response?.data?.message || error.message || '网络异常，请检查网络连接'
    return Promise.reject(new Error(message))
  }
)

export default request
```

- [ ] **Step 2: 创建 main.js**

```js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import './styles/global.scss'

const app = createApp(App)

app.use(ElementPlus, { locale: zhCn })
app.use(router)

// 全局注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.mount('#app')
```

- [ ] **Step 3: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/utils/ smart-duration-prediction/src/main.js && git commit -m "feat: axios instance and Vue entry point"
```

---

### Task 4: Vue Router 配置

**Files:**
- Create: `src/router/index.js`

- [ ] **Step 1: 创建路由配置**

File: `src/router/index.js`

```js
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    meta: { title: '首页' }
  },
  {
    path: '/prediction',
    name: 'DurationPrediction',
    component: () => import('@/views/DurationPrediction.vue'),
    meta: { title: '工期预测' }
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: () => import('@/views/ProjectList.vue'),
    meta: { title: '项目管理' }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/router/ && git commit -m "feat: Vue Router setup with lazy-loaded routes"
```

---

### Task 5: App.vue 根组件 + 布局骨架

**Files:**
- Create: `src/App.vue`

- [ ] **Step 1: 创建 App.vue**

```vue
<template>
  <div class="app-layout">
    <AppHeader />
    <div class="app-body">
      <AppSidebar
        :collapsed="sidebarCollapsed"
        active-menu="prediction"
        @update:collapsed="sidebarCollapsed = $event"
        @menu-select="handleMenuSelect"
      />
      <main class="app-main" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'

const router = useRouter()
const sidebarCollapsed = ref(false)

function handleMenuSelect(path) {
  router.push(path)
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.app-main {
  flex: 1;
  margin-left: $sidebar-width;
  overflow-y: auto;
  overflow-x: hidden;
  padding: $spacing-lg;
  background: $color-bg;
  transition: margin-left $transition-normal;

  &.sidebar-collapsed {
    margin-left: $sidebar-collapsed;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/App.vue && git commit -m "feat: App.vue layout skeleton with sidebar + header"
```

---

### Task 6: AppHeader 组件

**Files:**
- Create: `src/components/layout/AppHeader.vue`

- [ ] **Step 1: 创建 AppHeader.vue**

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
      <el-tooltip content="帮助文档" placement="bottom">
        <el-button link class="header-btn">
          <el-icon :size="20"><QuestionFilled /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="消息通知" placement="bottom">
        <el-badge :value="3" :max="99" class="header-badge">
          <el-button link class="header-btn">
            <el-icon :size="20"><Bell /></el-icon>
          </el-button>
        </el-badge>
      </el-tooltip>
      <el-dropdown trigger="click">
        <div class="user-info">
          <el-avatar :size="32" icon="UserFilled" />
          <span class="user-name">张工</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>个人中心</el-dropdown-item>
            <el-dropdown-item>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<script setup>
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: $header-height;
  padding: 0 $spacing-lg;
  background: $color-primary-dark;
  flex-shrink: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.logo-icon {
  width: 36px;
  height: 36px;
  display: block;
}

.header-title {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  letter-spacing: 2px;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.header-btn {
  color: rgba(255, 255, 255, 0.75);
  padding: 6px;

  &:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.1);
  }
}

.header-badge {
  :deep(.el-badge__content) {
    background: $color-warning;
    border: 1px solid $color-primary-dark;
  }
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  margin-left: $spacing-sm;
  transition: background $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
}

.user-name {
  color: rgba(255, 255, 255, 0.85);
  font-size: $font-size-body;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/layout/AppHeader.vue && git commit -m "feat: AppHeader component with logo, notifications, and user avatar"
```

---

### Task 7: AppSidebar 组件

**Files:**
- Create: `src/components/layout/AppSidebar.vue`

- [ ] **Step 1: 创建 AppSidebar.vue**

```vue
<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-toggle" @click="toggleCollapse">
      <el-icon :size="20">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <nav class="sidebar-nav">
      <div
        v-for="item in menuItems"
        :key="item.path"
        class="nav-item"
        :class="{
          active: item.path === activeMenu,
          disabled: item.disabled
        }"
        @click="handleClick(item)"
      >
        <el-icon :size="20">
          <component :is="item.icon" />
        </el-icon>
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div class="footer-user" v-show="!collapsed">
        <el-avatar :size="36" icon="UserFilled" />
        <div class="footer-info">
          <span class="footer-name">张工</span>
          <span class="footer-role">项目经理</span>
        </div>
      </div>
      <el-avatar v-show="collapsed" :size="36" icon="UserFilled" class="footer-avatar-collapsed" />
    </div>
  </aside>
</template>

<script setup>
import {
  HomeFilled, DataAnalysis, Timer, WarningFilled,
  Box, TrendCharts, Document, Setting
} from '@element-plus/icons-vue'
import { Fold, Expand } from '@element-plus/icons-vue'

defineProps({
  collapsed: { type: Boolean, default: false },
  activeMenu: { type: String, default: 'prediction' }
})

const emit = defineEmits(['update:collapsed', 'menu-select'])

const menuItems = [
  { path: '/',            label: '首页',     icon: HomeFilled,    disabled: false },
  { path: '/projects',    label: '项目管理',  icon: DataAnalysis,  disabled: false },
  { path: '/prediction',  label: '工期预测',  icon: Timer,         disabled: false },
  { path: '/risk',        label: '风险分析',  icon: WarningFilled, disabled: true },
  { path: '/resources',   label: '资源管理',  icon: Box,           disabled: true },
  { path: '/progress',    label: '进度跟踪',  icon: TrendCharts,   disabled: true },
  { path: '/reports',     label: '报告中心',  icon: Document,      disabled: true },
  { path: '/settings',    label: '系统设置',  icon: Setting,       disabled: true }
]

function toggleCollapse() {
  emit('update:collapsed', !defineProps.collapsed)  // 实际使用 prop
}
</script>
```

Wait — there's a bug in the above. `defineProps` returns an object but I can't use it inside `toggleCollapse` directly. Let me fix by using the props via a local variable. Let me rewrite this properly.

- [ ] **Step 1 (corrected): 创建 AppSidebar.vue**

```vue
<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-toggle" @click="toggleCollapse">
      <el-icon :size="20">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <nav class="sidebar-nav">
      <div
        v-for="item in menuItems"
        :key="item.path"
        class="nav-item"
        :class="{
          active: activeMenu === item.path,
          disabled: item.disabled
        }"
        @click="handleClick(item)"
      >
        <el-icon :size="20">
          <component :is="item.icon" />
        </el-icon>
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
        <span v-if="item.disabled && !collapsed" class="nav-tag">即将上线</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div v-if="!collapsed" class="footer-user">
        <el-avatar :size="36" icon="UserFilled" />
        <div class="footer-info">
          <span class="footer-name">张工</span>
          <span class="footer-role">项目经理</span>
        </div>
      </div>
      <el-avatar v-else :size="36" icon="UserFilled" class="footer-avatar-collapsed" />
    </div>
  </aside>
</template>

<script setup>
import {
  HomeFilled, DataAnalysis, Timer, WarningFilled,
  Box, TrendCharts, Document, Setting, Fold, Expand
} from '@element-plus/icons-vue'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  activeMenu: { type: String, default: 'prediction' }
})

const emit = defineEmits(['update:collapsed', 'menu-select'])

const menuItems = [
  { path: '/',            label: '首页',     icon: markRaw(HomeFilled),    disabled: false },
  { path: '/projects',    label: '项目管理',  icon: markRaw(DataAnalysis),  disabled: false },
  { path: '/prediction',  label: '工期预测',  icon: markRaw(Timer),         disabled: false },
  { path: '/risk',        label: '风险分析',  icon: markRaw(WarningFilled), disabled: true },
  { path: '/resources',   label: '资源管理',  icon: markRaw(Box),           disabled: true },
  { path: '/progress',    label: '进度跟踪',  icon: markRaw(TrendCharts),   disabled: true },
  { path: '/reports',     label: '报告中心',  icon: markRaw(Document),      disabled: true },
  { path: '/settings',    label: '系统设置',  icon: markRaw(Setting),       disabled: true }
]

function toggleCollapse() {
  emit('update:collapsed', !props.collapsed)
}

function handleClick(item) {
  if (item.disabled) return
  emit('menu-select', item.path)
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-sidebar {
  position: fixed;
  top: $header-height;
  left: 0;
  bottom: 0;
  width: $sidebar-width;
  background: $color-primary-dark;
  display: flex;
  flex-direction: column;
  z-index: 99;
  transition: width $transition-normal;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed;
  }
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: color $transition-fast;

  &:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }
}

.sidebar-nav {
  flex: 1;
  padding: $spacing-xs 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 16px;
  margin: 2px 8px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  transition: all $transition-fast;
  white-space: nowrap;
  gap: 10px;
  position: relative;

  &:hover:not(.disabled) {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }

  &.active {
    color: #fff;
    background: $color-primary;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #fff;
      border-radius: 0 2px 2px 0;
    }
  }

  &.disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}

.nav-label {
  font-size: $font-size-body;
}

.nav-tag {
  margin-left: auto;
  font-size: 10px;
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.5);
  padding: 1px 6px;
  border-radius: 4px;
}

.sidebar-footer {
  padding: $spacing-sm;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-user {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xs;
  border-radius: 8px;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }
}

.footer-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.footer-name {
  color: #fff;
  font-size: $font-size-body;
  font-weight: 500;
}

.footer-role {
  color: rgba(255, 255, 255, 0.45);
  font-size: $font-size-caption;
}

.footer-avatar-collapsed {
  display: block;
  margin: 0 auto;
}
</style>
```

Wait, I used `markRaw` but didn't import it. Let me fix that in the import statement. Actually the icons from `@element-plus/icons-vue` are already plain objects, they don't need `markRaw`. Let me remove that to keep it simpler.

- [ ] **Step 1 (final corrected): 创建 AppSidebar.vue**

```vue
<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-toggle" @click="toggleCollapse">
      <el-icon :size="20">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <nav class="sidebar-nav">
      <div
        v-for="item in menuItems"
        :key="item.path"
        class="nav-item"
        :class="{
          active: activeMenu === item.path,
          disabled: item.disabled
        }"
        @click="handleClick(item)"
      >
        <el-icon :size="20">
          <component :is="item.icon" />
        </el-icon>
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
        <span v-if="item.disabled && !collapsed" class="nav-tag">即将上线</span>
      </div>
    </nav>

    <div class="sidebar-footer">
      <div v-if="!collapsed" class="footer-user">
        <el-avatar :size="36" icon="UserFilled" />
        <div class="footer-info">
          <span class="footer-name">张工</span>
          <span class="footer-role">项目经理</span>
        </div>
      </div>
      <el-avatar v-else :size="36" icon="UserFilled" class="footer-avatar-collapsed" />
    </div>
  </aside>
</template>

<script setup>
import {
  HomeFilled, DataAnalysis, Timer, WarningFilled,
  Box, TrendCharts, Document, Setting, Fold, Expand
} from '@element-plus/icons-vue'

const props = defineProps({
  collapsed: { type: Boolean, default: false },
  activeMenu: { type: String, default: 'prediction' }
})

const emit = defineEmits(['update:collapsed', 'menu-select'])

const menuItems = [
  { path: '/',            label: '首页',     icon: HomeFilled,    disabled: false },
  { path: '/projects',    label: '项目管理',  icon: DataAnalysis,  disabled: false },
  { path: '/prediction',  label: '工期预测',  icon: Timer,         disabled: false },
  { path: '/risk',        label: '风险分析',  icon: WarningFilled, disabled: true },
  { path: '/resources',   label: '资源管理',  icon: Box,           disabled: true },
  { path: '/progress',    label: '进度跟踪',  icon: TrendCharts,   disabled: true },
  { path: '/reports',     label: '报告中心',  icon: Document,      disabled: true },
  { path: '/settings',    label: '系统设置',  icon: Setting,       disabled: true }
]

function toggleCollapse() {
  emit('update:collapsed', !props.collapsed)
}

function handleClick(item) {
  if (item.disabled) return
  emit('menu-select', item.path)
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-sidebar {
  position: fixed;
  top: $header-height;
  left: 0;
  bottom: 0;
  width: $sidebar-width;
  background: $color-primary-dark;
  display: flex;
  flex-direction: column;
  z-index: 99;
  transition: width $transition-normal;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed;
  }
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: color $transition-fast;
  flex-shrink: 0;

  &:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }
}

.sidebar-nav {
  flex: 1;
  padding: $spacing-xs 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  height: 44px;
  padding: 0 16px;
  margin: 2px 8px;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  transition: all $transition-fast;
  white-space: nowrap;
  gap: 10px;
  position: relative;

  &:hover:not(.disabled) {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }

  &.active {
    color: #fff;
    background: $color-primary;

    &::before {
      content: '';
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: #fff;
      border-radius: 0 2px 2px 0;
    }
  }

  &.disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}

.nav-label {
  font-size: $font-size-body;
}

.nav-tag {
  margin-left: auto;
  font-size: 10px;
  background: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.5);
  padding: 1px 6px;
  border-radius: 4px;
  line-height: 1.5;
}

.sidebar-footer {
  padding: $spacing-sm;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.footer-user {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xs;
  border-radius: 8px;
  cursor: pointer;
  transition: background $transition-fast;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }
}

.footer-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.footer-name {
  color: #fff;
  font-size: $font-size-body;
  font-weight: 500;
}

.footer-role {
  color: rgba(255, 255, 255, 0.45);
  font-size: $font-size-caption;
}

.footer-avatar-collapsed {
  display: block;
  margin: 0 auto;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/layout/AppSidebar.vue && git commit -m "feat: AppSidebar with collapsible navigation and 8 menu items"
```

---

### Task 8: Home.vue 首页占位

**Files:**
- Create: `src/views/Home.vue`

- [ ] **Step 1: 创建 Home.vue**

```vue
<template>
  <div class="home-page">
    <div class="page-header">
      <h2 class="page-title">工作台</h2>
      <p class="page-subtitle">水泥厂熟料生产线建设项目智能管理平台</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card" v-for="stat in stats" :key="stat.label">
        <div class="stat-value">{{ stat.value }}</div>
        <div class="stat-label">{{ stat.label }}</div>
        <div class="stat-icon" :style="{ background: stat.color }">
          <el-icon :size="24"><component :is="stat.icon" /></el-icon>
        </div>
      </div>
    </div>

    <div class="quick-actions">
      <h3 class="section-title">快捷操作</h3>
      <div class="actions-grid">
        <div class="action-card" @click="$router.push('/prediction')">
          <el-icon :size="32" color="#1677FF"><Timer /></el-icon>
          <span>新建工期预测</span>
        </div>
        <div class="action-card" @click="$router.push('/projects')">
          <el-icon :size="32" color="#1677FF"><DataAnalysis /></el-icon>
          <span>查看历史项目</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Timer, DataAnalysis, Document, TrendCharts } from '@element-plus/icons-vue'

const stats = [
  { label: '预测项目总数', value: 128, icon: Document, color: '#1677FF' },
  { label: '本月新增',     value: 23,  icon: TrendCharts, color: '#00B42A' },
  { label: '平均工期(天)', value: 365, icon: Timer, color: '#FF7D00' },
  { label: '准确率',      value: '94.2%', icon: DataAnalysis, color: '#722ED1' }
]
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.home-page { max-width: 1200px; }

.page-header { margin-bottom: $spacing-xl; }
.page-title { font-size: $font-size-title; font-weight: 600; color: $color-text-primary; margin-bottom: $spacing-xs; }
.page-subtitle { font-size: $font-size-body; color: $color-text-secondary; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-md;
  margin-bottom: $spacing-xl;
}

.stat-card {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $spacing-lg;
  position: relative;
  overflow: hidden;
  transition: box-shadow $transition-normal;
  &:hover { box-shadow: $shadow-card-hover; }
}

.stat-value { font-size: 32px; font-weight: 700; color: $color-text-primary; margin-bottom: 4px; }
.stat-label { font-size: $font-size-body; color: $color-text-secondary; }
.stat-icon {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.section-title {
  font-size: $font-size-section;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: $spacing-md;
  padding-left: 12px;
  border-left: 3px solid $color-primary;
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: $spacing-md;
}

.action-card {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $spacing-xl $spacing-lg;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  cursor: pointer;
  transition: all $transition-normal;
  span { font-size: $font-size-body; color: $color-text-primary; font-weight: 500; }
  &:hover {
    box-shadow: $shadow-card-hover;
    transform: translateY(-2px);
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/views/Home.vue && git commit -m "feat: Home page with stats dashboard and quick actions"
```

---

### Task 9: ProjectList.vue 项目管理页占位

**Files:**
- Create: `src/views/ProjectList.vue`

- [ ] **Step 1: 创建 ProjectList.vue**

```vue
<template>
  <div class="project-list-page">
    <div class="page-header">
      <h2 class="page-title">项目管理</h2>
      <p class="page-subtitle">历史预测项目记录与查询</p>
    </div>

    <el-empty description="暂无历史记录，请先进行工期预测" :image-size="160" />
  </div>
</template>

<script setup>
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.project-list-page { max-width: 1200px; }

.page-header { margin-bottom: $spacing-xl; }
.page-title { font-size: $font-size-title; font-weight: 600; color: $color-text-primary; margin-bottom: $spacing-xs; }
.page-subtitle { font-size: $font-size-body; color: $color-text-secondary; }
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/views/ProjectList.vue && git commit -m "feat: ProjectList placeholder page"
```

---

### Task 10: useDifyWorkflow Composable

**Files:**
- Create: `src/composables/useDifyWorkflow.js`

- [ ] **Step 1: 创建 useDifyWorkflow.js**

```js
import { ref } from 'vue'
import request from '@/utils/request'

export function useDifyWorkflow() {
  const loading = ref(false)
  const error = ref(null)
  const result = ref(null)
  const currentStep = ref(0)

  const stepLabels = ['提交表单', 'AI分析中', '生成报告', '完成']

  function reset() {
    loading.value = false
    error.value = null
    result.value = null
    currentStep.value = 0
  }

  async function submit(params) {
    loading.value = true
    error.value = null
    result.value = null

    try {
      // Step 1: 提交表单
      currentStep.value = 1

      // 构建 FormData（适配 Dify 自定义 multipart/form-data 模式）
      const formData = new FormData()

      if (params.contractFile?.raw) {
        formData.append('contract_file', params.contractFile.raw)
      }
      formData.append('project_name', params.projectName || '')

      // 关键路径映射为 critical_path1~5
      const paths = params.criticalPaths || []
      for (let i = 0; i < 5; i++) {
        formData.append(`critical_path${i + 1}`, paths[i] || '')
      }

      // 结构参数
      formData.append('heater', params.heater || '')
      formData.append('length', String(params.length || ''))
      formData.append('width', String(params.width || ''))
      formData.append('concreteHeight', String(params.concreteHeight || ''))
      formData.append('totalHeight', String(params.totalHeight || ''))
      formData.append('foundation', params.foundation || '')
      formData.append('concreteLayer', String(params.concreteLayer || ''))
      formData.append('towerLayer', String(params.towerLayer || ''))

      // Step 2: AI分析中
      currentStep.value = 2

      // 延迟一下展示步骤动画
      await new Promise(resolve => setTimeout(resolve, 300))

      const response = await request.post('/workflows/run', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000
      })

      // Step 3: 生成报告
      currentStep.value = 3
      await new Promise(resolve => setTimeout(resolve, 200))

      // 解析返回
      const outputs = response?.data?.outputs || response?.outputs || {}

      result.value = {
        markdownContent: outputs.markdown_report || outputs.text || '',
        wordFileUrl: outputs.word_file_url || '',
        wordFileName: outputs.word_file_name || '项目策划书.docx',
        wordFileSize: outputs.word_file_size || ''
      }

      // Step 4: 完成
      currentStep.value = 4
    } catch (err) {
      error.value = err.message || '预测请求失败，请稍后重试'
      currentStep.value = 0
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    result,
    currentStep,
    stepLabels,
    submit,
    reset
  }
}
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/composables/useDifyWorkflow.js && git commit -m "feat: useDifyWorkflow composable with FormData and step progress"
```

---

### Task 11: ProjectInfoCard 组件

**Files:**
- Create: `src/components/prediction/ProjectInfoCard.vue`

- [ ] **Step 1: 创建 ProjectInfoCard.vue**

```vue
<template>
  <div class="prediction-card">
    <h3 class="prediction-card__title">项目基础信息</h3>
    <div class="prediction-card__content">
      <el-form-item label="项目名称" required>
        <el-input
          :model-value="modelValue.projectName"
          @update:model-value="update('projectName', $event)"
          placeholder="例：5000t/d熟料生产线建设项目"
          size="large"
          clearable
        />
      </el-form-item>

      <el-form-item label="合同文件" required>
        <el-upload
          class="contract-upload"
          drag
          :limit="1"
          :auto-upload="false"
          :accept="'.pdf,.doc,.docx'"
          :file-list="fileList"
          :before-upload="beforeUpload"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <div class="upload-placeholder">
            <el-icon :size="40" color="#C9CDD4"><UploadFilled /></el-icon>
            <div class="upload-text">
              <p>将合同文件拖拽到此处，或<em>点击上传</em></p>
              <p class="upload-hint">支持 .pdf .doc .docx 格式，单个文件不超过 50MB</p>
            </div>
          </div>
        </el-upload>
      </el-form-item>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
    // { projectName: string, contractFile: File|null }
  }
})

const emit = defineEmits(['update:modelValue'])

const fileList = computed(() => {
  return props.modelValue.contractFile ? [props.modelValue.contractFile] : []
})

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function handleFileChange(file) {
  update('contractFile', file)
}

function handleFileRemove() {
  update('contractFile', null)
}

function beforeUpload(file) {
  const isValidType = /\.(pdf|doc|docx)$/i.test(file.name)
  if (!isValidType) {
    ElMessage.error('仅支持 .pdf .doc .docx 格式文件')
    return false
  }
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return false // 阻止自动上传
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.contract-upload {
  width: 100%;

  :deep(.el-upload-dragger) {
    border: 2px dashed $color-border;
    border-radius: $radius-card;
    padding: $spacing-xl;
    transition: border-color $transition-fast;
    &:hover {
      border-color: $color-primary;
    }
  }
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
}

.upload-text {
  p {
    color: $color-text-secondary;
    font-size: $font-size-body;
    em {
      color: $color-primary;
      font-style: normal;
      cursor: pointer;
    }
  }
  .upload-hint {
    font-size: $font-size-caption;
    color: $color-text-placeholder;
    margin-top: 4px;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/ProjectInfoCard.vue && git commit -m "feat: ProjectInfoCard with drag-upload and project name input"
```

---

### Task 12: StructureParamsCard 组件

**Files:**
- Create: `src/components/prediction/StructureParamsCard.vue`

- [ ] **Step 1: 创建 StructureParamsCard.vue**

```vue
<template>
  <div class="prediction-card">
    <h3 class="prediction-card__title">结构参数</h3>
    <div class="prediction-card__content">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="预热器" required>
            <el-select
              :model-value="modelValue.heater"
              @update:model-value="update('heater', $event)"
              placeholder="请选择预热器类型"
              size="large"
              style="width: 100%"
            >
              <el-option
                v-for="item in heaterOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="长度" required>
            <el-input-number
              :model-value="modelValue.length"
              @update:model-value="update('length', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="宽度" required>
            <el-input-number
              :model-value="modelValue.width"
              @update:model-value="update('width', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="砼框架" required>
            <el-input-number
              :model-value="modelValue.concreteHeight"
              @update:model-value="update('concreteHeight', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="总高" required>
            <el-input-number
              :model-value="modelValue.totalHeight"
              @update:model-value="update('totalHeight', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="基础形式" required>
            <el-select
              :model-value="modelValue.foundation"
              @update:model-value="update('foundation', $event)"
              placeholder="请选择基础形式"
              size="large"
              style="width: 100%"
            >
              <el-option
                v-for="item in foundationOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="砼层数" required>
            <el-input-number
              :model-value="modelValue.concreteLayer"
              @update:model-value="update('concreteLayer', $event)"
              :min="0"
              :step="1"
              :precision="0"
              size="large"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="塔架层数" required>
            <el-input-number
              :model-value="modelValue.towerLayer"
              @update:model-value="update('towerLayer', $event)"
              :min="0"
              :step="1"
              :precision="0"
              size="large"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Object,
    required: true
    // { heater, length, width, concreteHeight, totalHeight, foundation, concreteLayer, towerLayer }
  }
})

const emit = defineEmits(['update:modelValue'])

const heaterOptions = [
  { label: '单系列五级旋风预热器', value: '单系列五级旋风预热器' },
  { label: '双系列五级旋风预热器', value: '双系列五级旋风预热器' },
  { label: '单系列六级旋风预热器', value: '单系列六级旋风预热器' },
  { label: '双系列六级旋风预热器', value: '双系列六级旋风预热器' }
]

const foundationOptions = [
  { label: '桩基础', value: '桩基础' },
  { label: '筏板基础', value: '筏板基础' },
  { label: '独立基础', value: '独立基础' },
  { label: '条形基础', value: '条形基础' }
]

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.unit-suffix {
  color: $color-text-secondary;
  font-size: $font-size-caption;
  margin-right: 4px;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/StructureParamsCard.vue && git commit -m "feat: StructureParamsCard with dual-column grid and 8 fields"
```

---

### Task 13: CriticalPathCard 组件

**Files:**
- Create: `src/components/prediction/CriticalPathCard.vue`

- [ ] **Step 1: 创建 CriticalPathCard.vue**

```vue
<template>
  <div class="prediction-card">
    <div class="card-header">
      <h3 class="prediction-card__title">关键路径</h3>
      <el-button
        v-if="modelValue.length < 5"
        type="primary"
        link
        @click="addPath"
      >
        <el-icon :size="16"><Plus /></el-icon>
        添加关键路径
      </el-button>
    </div>
    <div class="prediction-card__content">
      <TransitionGroup name="path-list" tag="div" class="path-list">
        <div class="path-item" v-for="(path, index) in modelValue" :key="index">
          <div class="path-step">
            <span class="step-number">{{ index + 1 }}</span>
            <span v-if="index < modelValue.length - 1" class="step-line"></span>
          </div>
          <div class="path-input-wrapper">
            <el-input
              :model-value="path"
              @update:model-value="updatePath(index, $event)"
              placeholder="请输入关键路径名称"
              size="large"
            />
          </div>
          <el-button
            v-if="modelValue.length > 3"
            class="path-delete"
            link
            type="danger"
            @click="removePath(index)"
          >
            <el-icon :size="18"><Close /></el-icon>
          </el-button>
          <div v-else class="path-delete-placeholder"></div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { Plus, Close } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: Array,
    required: true
    // string[]，默认长度 5
  }
})

const emit = defineEmits(['update:modelValue'])

function updatePath(index, value) {
  const newPaths = [...props.modelValue]
  newPaths[index] = value
  emit('update:modelValue', newPaths)
}

function addPath() {
  if (props.modelValue.length < 5) {
    emit('update:modelValue', [...props.modelValue, ''])
  }
}

function removePath(index) {
  if (props.modelValue.length > 3) {
    const newPaths = [...props.modelValue]
    newPaths.splice(index, 1)
    emit('update:modelValue', newPaths)
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: $spacing-md;

  .prediction-card__title {
    margin-bottom: 0;
  }
}

.path-list {
  display: flex;
  flex-direction: column;
}

.path-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-xs 0;
}

.path-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 40px;
  flex-shrink: 0;
}

.step-number {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: $color-primary;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-line {
  width: 2px;
  flex: 1;
  min-height: 16px;
  background: $color-border;
  margin: 4px 0;
}

.path-input-wrapper {
  flex: 1;
}

.path-delete {
  flex-shrink: 0;
  opacity: 0.4;
  transition: opacity $transition-fast;

  &:hover {
    opacity: 1;
  }
}

.path-delete-placeholder {
  width: 32px;
  flex-shrink: 0;
}

// 列表过渡动画
.path-list-enter-active,
.path-list-leave-active {
  transition: all 0.3s ease;
}

.path-list-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.path-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.path-list-move {
  transition: transform 0.3s ease;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/CriticalPathCard.vue && git commit -m "feat: CriticalPathCard with dynamic step-style list (3-5 items)"
```

---

### Task 14: AiStepProgress 组件

**Files:**
- Create: `src/components/prediction/AiStepProgress.vue`

- [ ] **Step 1: 创建 AiStepProgress.vue**

```vue
<template>
  <div class="ai-step-progress">
    <el-steps :active="currentStep" align-center finish-status="success">
      <el-step
        v-for="(label, index) in stepLabels"
        :key="index"
        :title="label"
      >
        <template #icon v-if="currentStep === index + 1">
          <span class="step-icon active">
            <el-icon v-if="currentStep === 4 && index === 3" :size="16"><Check /></el-icon>
            <span v-else class="pulse-dot"></span>
          </span>
        </template>
      </el-step>
    </el-steps>
  </div>
</template>

<script setup>
import { Check } from '@element-plus/icons-vue'

defineProps({
  currentStep: { type: Number, default: 0 },
  stepLabels: {
    type: Array,
    default: () => ['提交表单', 'AI分析中', '生成报告', '完成']
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ai-step-progress {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $spacing-lg $spacing-xl;
  margin-bottom: $spacing-md;

  :deep(.el-step__title) {
    font-size: $font-size-body;
    font-weight: 500;
  }

  :deep(.el-step__head.is-process) {
    color: $color-primary;
    border-color: $color-primary;
  }

  :deep(.el-step__head.is-finish) {
    color: $color-success;
    border-color: $color-success;

    .el-step__icon {
      background: $color-success;
      border-color: $color-success;
    }
  }
}

.step-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: $color-primary;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;

  &.active {
    animation: pulse-glow 1.5s ease-in-out infinite;
  }
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(22, 119, 255, 0.5);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(22, 119, 255, 0);
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/AiStepProgress.vue && git commit -m "feat: AiStepProgress with 4-step animated progress bar"
```

---

### Task 15: MarkdownResult 组件

**Files:**
- Create: `src/components/prediction/MarkdownResult.vue`

- [ ] **Step 1: 创建 MarkdownResult.vue**

```vue
<template>
  <div class="prediction-card markdown-result-card">
    <h3 class="prediction-card__title">AI 分析报告</h3>

    <!-- 空状态 -->
    <el-empty
      v-if="!content && !loading && !error"
      description="请填写参数后开始工期预测"
      :image-size="120"
    />

    <!-- 加载中 -->
    <div v-else-if="loading" class="loading-area">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="error-area">
      <el-result icon="error" :title="error" sub-title="">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重新预测</el-button>
        </template>
      </el-result>
    </div>

    <!-- Markdown 渲染 -->
    <div
      v-else-if="content"
      class="markdown-body"
      v-html="renderedMarkdown"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

defineEmits(['retry'])

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true
})

const renderedMarkdown = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.markdown-result-card {
  min-height: 200px;
}

.loading-area {
  padding: $spacing-md 0;
}

.error-area {
  padding: $spacing-md 0;
}

.markdown-body {
  max-height: calc(100vh - 480px);
  overflow-y: auto;
  padding: $spacing-sm 0;

  :deep(h1) {
    font-size: 22px;
    font-weight: 700;
    color: $color-primary;
    margin: $spacing-lg 0 $spacing-md;
    padding-bottom: $spacing-sm;
    border-bottom: 2px solid $color-primary-light;
  }

  :deep(h2) {
    font-size: 18px;
    font-weight: 600;
    color: $color-text-primary;
    margin: $spacing-md 0 $spacing-sm;
    padding-left: 10px;
    border-left: 3px solid $color-primary;
  }

  :deep(h3) {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    margin: $spacing-sm 0 $spacing-xs;
  }

  :deep(p) {
    line-height: 1.8;
    margin: $spacing-xs 0;
    color: $color-text-primary;
  }

  :deep(ul), :deep(ol) {
    padding-left: $spacing-lg;
    margin: $spacing-xs 0;
    line-height: 1.8;
  }

  :deep(li) {
    margin: 4px 0;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: $spacing-sm 0;
    font-size: $font-size-body;

    th {
      background: $color-primary-light;
      color: $color-primary;
      font-weight: 600;
      padding: 10px 12px;
      text-align: left;
      border: 1px solid $color-border;
    }

    td {
      padding: 8px 12px;
      border: 1px solid $color-border;
    }

    tr:nth-child(even) {
      background: $color-bg;
    }
  }

  :deep(code) {
    background: #F0F2F5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    color: #D63384;
  }

  :deep(pre) {
    background: #1D2129;
    padding: $spacing-md;
    border-radius: $radius-card;
    overflow-x: auto;
    margin: $spacing-sm 0;

    code {
      background: none;
      padding: 0;
      color: #E5E6EB;
      font-size: 13px;
    }
  }

  :deep(blockquote) {
    border-left: 4px solid $color-primary;
    background: $color-primary-light;
    padding: $spacing-sm $spacing-md;
    margin: $spacing-sm 0;
    border-radius: 0 $radius-button $radius-button 0;
    color: $color-text-secondary;
  }

  :deep(strong) {
    font-weight: 600;
    color: $color-text-primary;
  }
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/MarkdownResult.vue && git commit -m "feat: MarkdownResult with empty/loading/error states and styled markdown rendering"
```

---

### Task 16: FileDownloadCard 组件

**Files:**
- Create: `src/components/prediction/FileDownloadCard.vue`

- [ ] **Step 1: 创建 FileDownloadCard.vue**

```vue
<template>
  <div v-if="downloadUrl" class="prediction-card file-download-card">
    <div class="download-content">
      <div class="file-icon">
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="48" height="48" rx="10" fill="#E6F4FF"/>
          <path d="M14 8H30L36 14V40C36 41.1 35.1 42 34 42H14C12.9 42 12 41.1 12 40V10C12 8.9 12.9 8 14 8Z" fill="#1677FF"/>
          <path d="M30 8V14H36" fill="#4096FF"/>
          <text x="24" y="32" text-anchor="middle" fill="white" font-size="10" font-weight="bold">W</text>
        </svg>
      </div>
      <div class="file-info">
        <span class="file-name">{{ fileName }}</span>
        <span v-if="fileSize" class="file-size">{{ fileSize }}</span>
      </div>
      <el-button type="primary" :icon="Download" @click="handleDownload">
        下载文件
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { Download } from '@element-plus/icons-vue'

const props = defineProps({
  fileName: { type: String, default: '项目策划书.docx' },
  fileSize: { type: String, default: '' },
  downloadUrl: { type: String, default: '' }
})

const emit = defineEmits(['download'])

function handleDownload() {
  if (props.downloadUrl) {
    window.open(props.downloadUrl, '_blank')
  }
  emit('download')
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.file-download-card {
  margin-bottom: 0;
}

.download-content {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.file-icon {
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.file-name {
  font-size: $font-size-section;
  font-weight: 500;
  color: $color-text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: $font-size-caption;
  color: $color-text-secondary;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/components/prediction/FileDownloadCard.vue && git commit -m "feat: FileDownloadCard with Word icon and blue download button"
```

---

### Task 17: DurationPrediction.vue 核心页面

**Files:**
- Create: `src/views/DurationPrediction.vue`

- [ ] **Step 1: 创建 DurationPrediction.vue**

```vue
<template>
  <div class="prediction-page">
    <!-- AI 流程步骤条 -->
    <AiStepProgress
      :current-step="currentStep"
      :step-labels="stepLabels"
    />

    <!-- 表单输入区 -->
    <div class="input-area">
      <ProjectInfoCard v-model="formState.projectInfo" />
      <StructureParamsCard v-model="formState.structureParams" />
      <CriticalPathCard v-model="formState.criticalPaths" />

      <el-button
        class="btn-predict"
        :loading="loading"
        :disabled="loading"
        @click="handleSubmit"
      >
        <el-icon v-if="!loading" :size="20" style="margin-right: 6px">
          <Cpu />
        </el-icon>
        {{ loading ? 'AI分析中...' : '开始工期预测' }}
      </el-button>
    </div>

    <!-- AI 结果区 -->
    <div class="result-area">
      <MarkdownResult
        :content="result?.markdownContent || ''"
        :loading="loading"
        :error="error"
        @retry="handleSubmit"
      />
      <FileDownloadCard
        :file-name="result?.wordFileName || '项目策划书.docx'"
        :file-size="result?.wordFileSize || ''"
        :download-url="result?.wordFileUrl || ''"
      />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { Cpu } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import AiStepProgress from '@/components/prediction/AiStepProgress.vue'
import ProjectInfoCard from '@/components/prediction/ProjectInfoCard.vue'
import StructureParamsCard from '@/components/prediction/StructureParamsCard.vue'
import CriticalPathCard from '@/components/prediction/CriticalPathCard.vue'
import MarkdownResult from '@/components/prediction/MarkdownResult.vue'
import FileDownloadCard from '@/components/prediction/FileDownloadCard.vue'

import { useDifyWorkflow } from '@/composables/useDifyWorkflow'

const { loading, error, result, currentStep, stepLabels, submit } = useDifyWorkflow()

const formState = reactive({
  projectInfo: {
    projectName: '',
    contractFile: null
  },
  structureParams: {
    heater: '',
    length: null,
    width: null,
    concreteHeight: null,
    totalHeight: null,
    foundation: '',
    concreteLayer: null,
    towerLayer: null
  },
  criticalPaths: [
    '土建施工',
    '钢结构安装',
    '设备安装',
    '电气仪表施工',
    '单机试运转与联动调试'
  ]
})

async function handleSubmit() {
  // 基础校验
  if (!formState.projectInfo.projectName.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!formState.projectInfo.contractFile) {
    ElMessage.warning('请上传合同文件')
    return
  }
  if (!formState.structureParams.heater) {
    ElMessage.warning('请选择预热器类型')
    return
  }
  if (!formState.structureParams.foundation) {
    ElMessage.warning('请选择基础形式')
    return
  }
  if (!formState.structureParams.length || !formState.structureParams.width) {
    ElMessage.warning('请输入完整结构参数')
    return
  }
  if (formState.criticalPaths.some(p => !p.trim())) {
    ElMessage.warning('请填写完整的关键路径')
    return
  }

  try {
    await submit({
      projectName: formState.projectInfo.projectName,
      contractFile: formState.projectInfo.contractFile,
      heater: formState.structureParams.heater,
      length: formState.structureParams.length,
      width: formState.structureParams.width,
      concreteHeight: formState.structureParams.concreteHeight,
      totalHeight: formState.structureParams.totalHeight,
      foundation: formState.structureParams.foundation,
      concreteLayer: formState.structureParams.concreteLayer,
      towerLayer: formState.structureParams.towerLayer,
      criticalPaths: formState.criticalPaths
    })
  } catch (err) {
    // 错误已在 composable 中处理
  }
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.prediction-page {
  max-width: 1100px;
}

.input-area {
  margin-bottom: $spacing-lg;
}

.result-area {
  // 结果区紧随输入区
}
</style>
```

- [ ] **Step 2: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add smart-duration-prediction/src/views/DurationPrediction.vue && git commit -m "feat: DurationPrediction core page — form + AI result integration"
```

---

### Task 18: 集成验证 + 首次启动

**Files:**
- Verify: 所有文件完整

- [ ] **Step 1: 启动开发服务器验证编译**

Run: `cd "d:/Users/DIfy工期预测项目/smart-duration-prediction" && npx vite build`
Expected: 构建成功，无 TypeScript/Vue 编译错误。

- [ ] **Step 2: 修复所有编译问题**

如有编译错误，逐一修复后重新构建。

- [ ] **Step 3: 启动开发服务器**

Run: `cd "d:/Users/DIfy工期预测项目/smart-duration-prediction" && npx vite --host 0.0.0.0`
Expected: Dev server 在 localhost:3000 启动，打开浏览器验证：
- Header 显示正确
- 侧边栏可折叠、菜单切换正常
- 首页统计卡片正常显示
- 工期预测页表单完整渲染
- 文件拖拽上传区域正常
- 关键路径步骤条样式正确
- 空状态显示正确

- [ ] **Step 4: 提交最终验证**

```bash
cd "d:/Users/DIfy工期预测项目" && git add -A && git status
```

- [ ] **Step 5: Commit**

```bash
cd "d:/Users/DIfy工期预测项目" && git add -A && git commit -m "feat: full integration — intelligent duration prediction system complete"
```

---

## 文件创建顺序总结

```
01. package.json              → 依赖清单
02. vite.config.js             → Vite + proxy
03. index.html                 → 入口 HTML
04. src/styles/variables.scss  → SCSS 变量
05. src/styles/global.scss     → 全局样式
06. src/utils/request.js       → Axios 封装
07. src/main.js                → Vue 入口
08. src/router/index.js        → 路由
09. src/App.vue                → 布局骨架
10. src/components/layout/AppHeader.vue     → Header
11. src/components/layout/AppSidebar.vue    → 侧边栏
12. src/views/Home.vue                      → 首页
13. src/views/ProjectList.vue               → 项目管理
14. src/composables/useDifyWorkflow.js       → Dify API
15. src/components/prediction/ProjectInfoCard.vue      → 卡片1
16. src/components/prediction/StructureParamsCard.vue  → 卡片2
17. src/components/prediction/CriticalPathCard.vue     → 卡片3
18. src/components/prediction/AiStepProgress.vue       → 步骤条
19. src/components/prediction/MarkdownResult.vue       → Markdown渲染
20. src/components/prediction/FileDownloadCard.vue     → 下载卡片
21. src/views/DurationPrediction.vue        → ★ 核心页面集成
```

---

## 待确认项

1. **预热器类型选项** — 当前使用了 4 个默认选项（单/双系列 + 五级/六级旋风预热器），需业务方确认
2. **基础形式选项** — 当前：桩基础/筏板基础/独立基础/条形基础
3. **Dify API Key** — 需配置在 vite proxy 或生产 BFF 的环境变量中
4. **Dify 返回格式** — `outputs.markdown_report`、`outputs.word_file_url` 等字段名需与实际工作流输出对齐
