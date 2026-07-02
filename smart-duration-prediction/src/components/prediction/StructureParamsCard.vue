<template>
  <div class="prediction-card">
    <h3 class="prediction-card__title">结构参数</h3>
    <div class="prediction-card__content">
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="预热器" required>
            <el-select
              :model-value="modelValue.heater"
              @update:model-value="update('heater', $event)"
              placeholder="请选择预热器类型"
              size="large"
              style="width: 100%"
            >
              <el-option
                v-for="item in heaterOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="长度" required>
            <el-input-number
              :model-value="modelValue.length"
              @update:model-value="update('length', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="宽度" required>
            <el-input-number
              :model-value="modelValue.width"
              @update:model-value="update('width', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="预热器高度" required>
            <el-input-number
              :model-value="modelValue.concreteHeight"
              @update:model-value="update('concreteHeight', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="钢框架总高" required>
            <el-input-number
              :model-value="modelValue.totalHeight"
              @update:model-value="update('totalHeight', $event)"
              :min="0"
              :precision="1"
              size="large"
              style="width: 100%"
            >
              <template #suffix><span class="unit-suffix">m</span></template>
            </el-input-number>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="基础形式" required>
            <el-select
              :model-value="modelValue.foundation"
              @update:model-value="update('foundation', $event)"
              placeholder="请选择基础形式"
              size="large"
              style="width: 100%"
            >
              <el-option
                v-for="item in foundationOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="预热器层数" required>
            <el-input-number
              :model-value="modelValue.concreteLayer"
              @update:model-value="update('concreteLayer', $event)"
              :min="0"
              :step="1"
              :precision="0"
              size="large"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="钢框架层数" required>
            <el-input-number
              :model-value="modelValue.towerLayer"
              @update:model-value="update('towerLayer', $event)"
              :min="0"
              :step="1"
              :precision="0"
              size="large"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const heaterOptions = [
  { label: '单系列五级旋风预热器', value: '单系列五级旋风预热器' },
  { label: '双系列五级旋风预热器', value: '双系列五级旋风预热器' },
  { label: '单系列六级旋风预热器', value: '单系列六级旋风预热器' },
  { label: '双系列六级旋风预热器', value: '双系列六级旋风预热器' }
]

const foundationOptions = [
  { label: '桩基础', value: '桩基础' },
  { label: '筏板基础', value: '筏板基础' },
  { label: '独立基础', value: '独立基础' },
  { label: '条形基础', value: '条形基础' }
]

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.unit-suffix {
  color: $color-text-secondary;
  font-size: $font-size-caption;
  margin-right: 4px;
}
</style>
