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
        :class="{ active: activeMenu === item.path }"
        @click="handleClick(item)"
      >
        <el-icon :size="20">
          <component :is="item.icon" />
        </el-icon>
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
      </div>
    </nav>

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
  </aside>
</template>

<script setup>
import {
  Timer, DataAnalysis, TrendCharts, Setting,
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
      { path: '/planning-progress', label: '策划书解析', icon: TrendCharts },
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
  height: 44px;
  padding: 0 16px;
  margin: 2px 8px 0;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: color $transition-fast, background $transition-fast;
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

  &:hover {
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
}

.nav-label {
  font-size: $font-size-body;
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
