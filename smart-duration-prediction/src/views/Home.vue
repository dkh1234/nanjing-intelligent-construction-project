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
