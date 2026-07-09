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
