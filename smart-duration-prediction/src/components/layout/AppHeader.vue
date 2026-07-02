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

<script setup>
import { Setting, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function handleCommand(command) {
  if (command === 'users') {
    router.push('/admin/users')
  } else if (command === 'logout') {
    authStore.logout()
  }
}
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
