<template>
  <div class="key-path-section">
    <div class="section-title">
      <el-icon :size="18" color="#1677FF"><Link /></el-icon>
      <span>关键路径</span>
    </div>

    <div class="path-list">
      <div class="path-row" v-for="(item, idx) in modelValue" :key="idx">
        <div class="path-index">
          <span class="index-dot">{{ idx + 1 }}</span>
        </div>
        <el-select
          :model-value="item"
          @update:model-value="update(idx, $event)"
          class="path-select"
          placeholder="请选择"
          size="large"
        >
          <el-option
            v-for="opt in pathOptions[idx]"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Link } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Array, required: true }
})

const emit = defineEmits(['update:modelValue'])

const pathOptions = [
  [
    { label: '原料粉磨车间', value: '原料粉磨车间' },
    { label: '无该关键路径', value: '无该关键路径' }
  ],
  [
    { label: '窑头车间', value: '窑头车间' },
    { label: '无该关键路径', value: '无该关键路径' }
  ],
  [
    { label: '煤磨车间', value: '煤磨车间' },
    { label: '无该关键路径', value: '无该关键路径' }
  ],
  [
    { label: '窑中车间', value: '窑中车间' },
    { label: '无该关键路径', value: '无该关键路径' }
  ],
  [
    { label: '窑尾车间', value: '窑尾车间' },
    { label: '无该关键路径', value: '无该关键路径' }
  ]
]

function update(idx, val) {
  const arr = [...props.modelValue]
  arr[idx] = val
  emit('update:modelValue', arr)
}
</script>

<style lang="scss" scoped>
.key-path-section { margin-bottom: 24px; }

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #1677FF;
  margin-bottom: 14px;
}

.path-list { display: flex; flex-direction: column; }

.path-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.path-index { flex-shrink: 0; }

.index-dot {
  width: 22px; height: 22px;
  border-radius: 50%;
  background: #1677FF;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.path-select {
  flex: 1;
  :deep(.el-select__wrapper) {
    border-radius: 8px;
    box-shadow: 0 0 0 1px #dcdfe6;
    &:hover, &.is-focus { box-shadow: 0 0 0 1px #1677FF; }
  }
}
</style>
