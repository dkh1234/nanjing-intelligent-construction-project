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
            <el-icon v-if="currentStep === 5 && index === 4" :size="16"><Check /></el-icon>
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
    default: () => ['上传文件', '解析合同', '识别关键路径', 'AI工期分析', '生成策划书']
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
