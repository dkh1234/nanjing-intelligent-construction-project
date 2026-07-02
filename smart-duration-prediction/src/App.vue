<template>
  <!-- 登录页：无布局，全屏显示 -->
  <router-view v-if="isLoginPage" v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>

  <!-- 其他页面：带布局 -->
  <div v-else class="app-layout">
    <AppHeader />
    <div class="app-body">
      <AppSidebar
        :collapsed="sidebarCollapsed"
        :active-menu="activeMenu"
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
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import AppHeader from '@/components/layout/AppHeader.vue'
import AppSidebar from '@/components/layout/AppSidebar.vue'

const router = useRouter()
const route = useRoute()
const sidebarCollapsed = ref(false)

const activeMenu = computed(() => route.path)

const isLoginPage = computed(() => route.path === '/login')

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
