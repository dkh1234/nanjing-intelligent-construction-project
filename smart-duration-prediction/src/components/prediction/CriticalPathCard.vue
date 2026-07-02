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
