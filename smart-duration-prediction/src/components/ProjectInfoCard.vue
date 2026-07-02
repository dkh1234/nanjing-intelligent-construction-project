<template>
  <div class="left-form-card">
    <!-- 1. 项目基本信息 -->
    <div class="form-section">
      <div class="section-heading">
        <el-icon :size="18" color="#1677FF"><InfoFilled /></el-icon>
        <span>项目基本信息</span>
      </div>
      <div class="form-field">
        <label class="field-label">项目名称 <span class="req">*</span></label>
        <el-input
          v-model="form.projectName"
          placeholder="5000t/d 熟料生产线项目"
          size="large"
          class="styled-input"
        />
      </div>
      <UploadFileBox v-model="form.contractFile" />
    </div>

    <!-- 2. 结构参数 -->
    <div class="form-section">
      <div class="section-heading">
        <el-icon :size="18" color="#1677FF"><Grid /></el-icon>
        <span>结构参数</span>
      </div>
      <div class="grid-2col">
        <div class="form-field">
          <label class="field-label">预热器</label>
          <el-select v-model="form.heater" placeholder="请选择" size="large" class="styled-select">
            <el-option v-for="o in heaterOpts" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
        <div class="form-field">
          <label class="field-label">长度 (m)</label>
          <el-input-number v-model="form.length" :min="0" :precision="1" size="large" class="styled-num" controls-position="right" />
        </div>
        <div class="form-field">
          <label class="field-label">宽度 (m)</label>
          <el-input-number v-model="form.width" :min="0" :precision="1" size="large" class="styled-num" controls-position="right" />
        </div>
        <div class="form-field">
          <label class="field-label">砼框架 (m)</label>
          <el-input-number v-model="form.concreteHeight" :min="0" :precision="1" size="large" class="styled-num" controls-position="right" />
        </div>
        <div class="form-field">
          <label class="field-label">总高 (m)</label>
          <el-input-number v-model="form.totalHeight" :min="0" :precision="1" size="large" class="styled-num" controls-position="right" />
        </div>
        <div class="form-field">
          <label class="field-label">基础形式</label>
          <el-select v-model="form.foundation" placeholder="请选择" size="large" class="styled-select">
            <el-option v-for="o in foundationOpts" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
      </div>
    </div>

    <!-- 3. 结构层数 -->
    <div class="form-section">
      <div class="section-heading">
        <el-icon :size="18" color="#1677FF"><OfficeBuilding /></el-icon>
        <span>结构层数</span>
      </div>
      <div class="grid-2col">
        <div class="form-field">
          <label class="field-label">砼层数</label>
          <el-input-number v-model="form.concreteLayer" :min="0" :step="1" size="large" class="styled-num" controls-position="right" />
        </div>
        <div class="form-field">
          <label class="field-label">塔架层数</label>
          <el-input-number v-model="form.towerLayer" :min="0" :step="1" size="large" class="styled-num" controls-position="right" />
        </div>
      </div>
    </div>

    <!-- 4. 关键路径 -->
    <KeyPathList v-model="form.criticalPaths" />

    <!-- 主按钮 -->
    <el-button class="submit-btn" :loading="submitting" @click="$emit('submit')">
      <el-icon :size="18"><Promotion /></el-icon>
      开始工期预测
    </el-button>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { InfoFilled, Grid, OfficeBuilding, Promotion } from '@element-plus/icons-vue'
import UploadFileBox from './UploadFileBox.vue'
import KeyPathList from './KeyPathList.vue'

defineProps({ submitting: { type: Boolean, default: false } })
defineEmits(['submit'])

const form = reactive({
  projectName: '',
  contractFile: null,
  heater: '',
  length: null,
  width: null,
  concreteHeight: null,
  totalHeight: null,
  concreteLayer: null,
  towerLayer: null,
  foundation: '',
  criticalPaths: ['原料粉磨车间', '窑头车间', '煤磨车间', '窑中车间', '窑尾车间']
})

const heaterOpts = ['四级预热器', '五级预热器', '六级预热器', '七级预热器']
const foundationOpts = ['桩基础', '天然基础']

defineExpose({ form })
</script>

<style lang="scss" scoped>
.left-form-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.form-section { margin-bottom: 24px; }

.section-heading {
  display: flex; align-items: center; gap: 8px;
  font-size: 18px; font-weight: 700; color: #1677FF;
  margin-bottom: 16px;
}

.form-field { margin-bottom: 12px; }

.field-label {
  display: block;
  font-size: 14px; font-weight: 600; color: #4e5969;
  margin-bottom: 6px;
  .req { color: #f53f3f; }
}

.grid-2col {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

:deep(.styled-input .el-input__wrapper),
:deep(.styled-num .el-input__wrapper),
:deep(.styled-select .el-select__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #dcdfe6;
  transition: box-shadow .2s;
  &:hover, &.is-focus { box-shadow: 0 0 0 1px #1677FF; }
}

:deep(.styled-num) { width: 100%; }
:deep(.styled-select) { width: 100%; }

.submit-btn {
  width: 100%; height: 48px;
  background: #1677FF; border: none; border-radius: 10px;
  font-size: 16px; font-weight: 600; color: #fff;
  margin-top: 4px;
  transition: background .2s;
  &:hover { background: #4096FF; }
}
</style>
