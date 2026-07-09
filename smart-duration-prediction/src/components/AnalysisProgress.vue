<template>
  <div class="analysis-progress">
    <div class="progress-header">
      <el-icon :size="20" color="#1677FF"><Loading /></el-icon>
      <span class="header-title">分析进度</span>
    </div>

    <div class="steps-area">
      <div class="custom-steps">
        <template v-for="(step, idx) in steps" :key="idx">
          <div class="step-node">
            <div
              class="step-circle"
              :class="{
                done: idx < currentStep,
                active: idx === currentStep,
                pending: idx > currentStep
              }"
            >
              <el-icon v-if="idx < currentStep" :size="14"><Check /></el-icon>
              <span v-else-if="idx === currentStep && loading" class="loading-dot"></span>
              <span v-else>{{ idx + 1 }}</span>
            </div>
            <div class="step-title" :class="{ 'text-active': idx <= currentStep }">{{ step }}</div>
            <div class="step-status">
              {{ idx < currentStep ? '已完成' : idx === currentStep ? (loading ? '处理中' : '等待中') : '等待中' }}
            </div>
          </div>
          <div v-if="idx < steps.length - 1" class="step-line" :class="{ 'line-done': idx < currentStep }"></div>
        </template>
      </div>
    </div>

    <!-- 耗时提示 -->
    <div v-if="loading" class="time-hint">
      <el-icon :size="14"><Clock /></el-icon>
      <span>AI 分析通常需要 30-60 秒，请耐心等待...</span>
    </div>
  </div>
</template>

<script setup>
import { Loading, Check, Clock } from '@element-plus/icons-vue'

defineProps({
  currentStep: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  steps: {
    type: Array,
    default: () => [
      '上传文件',
      '提取文本',
      'AI解析策划书',
      'AI解析周报',
      '预警引擎计算',
      '生成报告'
    ]
  }
})
</script>

<style lang="scss" scoped>
.analysis-progress {
  padding: 12px 0;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: #1677FF;
}

/* === 步骤条 === */
.steps-area {
  padding: 10px 0;
}

.custom-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  flex-wrap: wrap;
}

.step-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  min-width: 70px;
}

.step-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  background: #e5e6eb;
  color: #86909c;
  transition: all .3s;

  &.done {
    background: #00B42A;
    color: #fff;
  }
  &.active {
    background: #1677FF;
    color: #fff;
    box-shadow: 0 0 0 5px rgba(22, 119, 255, 0.2);
  }
  &.pending {
    background: #e5e6eb;
    color: #86909c;
  }
}

.step-title {
  font-size: 11px;
  color: #86909c;
  margin-top: 8px;
  white-space: nowrap;
  text-align: center;

  &.text-active {
    color: #1677FF;
    font-weight: 600;
  }
}

.step-status {
  font-size: 10px;
  color: #c9cdd4;
  margin-top: 3px;
}

.step-line {
  width: 36px;
  height: 2px;
  background: #e5e6eb;
  margin: 17px 2px 0;
  flex-shrink: 0;

  &.line-done {
    background: #00B42A;
  }
}

.loading-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #fff;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(0.4); opacity: 0.4; }
}

/* === 耗时提示 === */
.time-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 20px;
  padding: 10px 16px;
  background: #f0f5ff;
  border-radius: 8px;
  font-size: 13px;
  color: #4e5969;

  .el-icon {
    color: #1677FF;
  }
}
</style>
