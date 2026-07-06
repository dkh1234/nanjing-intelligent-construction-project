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
    path: '/planning-progress',
      name: 'PlanningProgress',
      component: () => import('@/views/PlanningProgress.vue'),
      meta: { title: '策划书解析', requiresAuth: true }
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
