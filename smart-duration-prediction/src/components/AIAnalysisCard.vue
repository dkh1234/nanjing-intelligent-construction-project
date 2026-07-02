<template>
  <div class="right-card">
    <!-- 标题栏 -->
    <div class="card-header">
      <el-icon :size="20" color="#1677FF"><Cpu /></el-icon>
      <span class="header-title">AI分析结果</span>
    </div>

    <!-- 步骤条 -->
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
              {{ idx < currentStep ? '已完成' : idx === currentStep ? (loading ? '分析中' : '等待中') : '等待中' }}
            </div>
          </div>
          <div v-if="idx < steps.length - 1" class="step-line" :class="{ 'line-done': idx < currentStep }"></div>
        </template>
      </div>
    </div>

    <!-- Markdown结果（含策划书下载） -->
    <MarkdownResult
      :content="markdownContent"
      :loading="loading"
      :download-url="downloadUrl"
      :project-name="projectName"
    />
  </div>
</template>

<script setup>
import { Cpu, Check } from '@element-plus/icons-vue'
import MarkdownResult from './MarkdownResult.vue'

defineProps({
  currentStep: { type: Number, default: 0 },
  steps: { type: Array, default: () => ['上传文件', '解析合同', '识别关键路径', 'AI工期分析', '生成策划书'] },
  loading: { type: Boolean, default: false },
  markdownContent: { type: String, default: '' },
  downloadUrl: { type: String, default: '' },
  projectName: { type: String, default: '项目策划书' }
})
</script>

<style lang="scss" scoped>
.right-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.card-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 20px;
}

.header-title { font-size: 18px; font-weight: 700; color: #1677FF; }

/* === 步骤条 === */
.steps-area { padding: 20px 0; }

.custom-steps {
  display: flex; align-items: flex-start; justify-content: center;
}

.step-node {
  display: flex; flex-direction: column; align-items: center;
  flex-shrink: 0;
}

.step-circle {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 600;
  background: #e5e6eb; color: #86909c;
  transition: all .3s;
  &.done { background: #1677FF; color: #fff; }
  &.active { background: #1677FF; color: #fff; box-shadow: 0 0 0 4px rgba(22,119,255,0.2); }
  &.pending { background: #e5e6eb; color: #86909c; }
}

.step-title {
  font-size: 12px; color: #86909c; margin-top: 8px; white-space: nowrap;
  &.text-active { color: #1677FF; font-weight: 600; }
}

.step-status { font-size: 11px; color: #c9cdd4; margin-top: 4px; }

.step-line {
  width: 40px; height: 2px; background: #e5e6eb;
  margin: 16px 4px 0; flex-shrink: 0;
  &.line-done { background: #1677FF; }
}

.loading-dot {
  width: 10px; height: 10px; border-radius: 50%; background: #fff;
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(0.5); opacity: 0.5; }
}
</style>
