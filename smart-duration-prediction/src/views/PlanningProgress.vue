<template>
  <div class="planning-page">
    <!-- ==================== 标题 ==================== -->
    <div class="page-header">
      <h1 class="page-title">策划书解析</h1>
      <p class="page-desc">上传项目策划书（.docx），自动提取关键节点信息并生成项目进度图。</p>
    </div>

    <!-- ==================== 上传区 ==================== -->
    <div class="card upload-card">
      <div class="card-section-title">
        <el-icon :size="16" color="#1677ff"><Upload /></el-icon>
        <span>1. 上传策划书文档</span>
      </div>
      <p class="card-section-desc">支持 .docx 格式，文件大小不超过 20MB</p>

      <div
        class="upload-zone"
        :class="{ 'upload-zone--has-file': uploadFile }"
        @click="triggerUpload"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="onDrop"
      >
        <!-- 无文件 -->
        <div v-if="!uploadFile && !loading" class="upload-inner">
          <el-icon :size="48" color="#1677ff"><UploadFilled /></el-icon>
          <p class="upload-main">点击或拖拽文件到此处上传</p>
          <p class="upload-hint">支持 .docx 格式</p>
        </div>

        <!-- 解析中 -->
        <div v-else-if="loading" class="upload-inner">
          <el-icon :size="48" color="#1677ff" class="is-loading"><Loading /></el-icon>
          <p class="upload-main">正在解析文档...</p>
          <p class="upload-hint">{{ uploadFile?.name || '' }}</p>
        </div>

        <!-- 已选择文件 -->
        <div v-else-if="uploadFile && !result && !error" class="upload-inner">
          <el-icon :size="48" color="#1677ff"><Document /></el-icon>
          <p class="upload-main">{{ uploadFile.name }}</p>
          <p class="upload-hint">点击「开始解析」提取关键节点信息</p>
        </div>

        <!-- 解析完成 -->
        <div v-else-if="result" class="parsed-preview">
          <div class="parsed-header">
            <el-icon :size="18" color="#52c41a"><Check /></el-icon>
            <span class="parsed-title">{{ uploadFile?.name || '文件' }}</span>
            <el-tag type="success" size="small" effect="plain">
              {{ result.milestones?.length || 0 }} 个里程碑
            </el-tag>
            <el-button type="danger" size="small" text :icon="Delete" @click.stop="handleReset" style="margin-left: auto" />
          </div>
        </div>
      </div>

      <!-- 隐藏上传 input -->
      <input
        ref="fileInput"
        type="file"
        accept=".docx,.doc"
        style="display: none"
        @change="onFileChange"
      />

      <!-- 操作按钮 -->
      <div class="upload-actions">
        <el-button
          v-if="!result"
          type="primary"
          size="large"
          :loading="loading"
          :disabled="!uploadFile"
          @click="handleParse"
        >
          <el-icon :size="18" style="margin-right: 6px"><Cpu /></el-icon>
          {{ loading ? '解析中...' : '开始解析' }}
        </el-button>
        <el-button
          v-else
          size="large"
          @click="handleReset"
        >
          重新上传
        </el-button>
      </div>
    </div>

    <!-- ==================== 错误提示 ==================== -->
    <div v-if="error" class="card error-card">
      <el-result icon="error" :title="error" sub-title="">
        <template #extra>
          <el-button type="primary" @click="handleReset">重新上传</el-button>
        </template>
      </el-result>
    </div>

    <!-- ==================== 结果区 ==================== -->
    <template v-if="result">
      <!-- 项目概况 -->
      <div class="card">
        <div class="card-section-title">
          <el-icon :size="16" color="#1677ff"><InfoFilled /></el-icon>
          <span>项目概况</span>
        </div>
        <div class="project-info-grid">
          <div class="info-item" v-if="result.project.name">
            <span class="info-label">项目名称</span>
            <span class="info-value">{{ result.project.name }}</span>
          </div>
          <div class="info-item" v-if="result.project.scale">
            <span class="info-label">建设规模</span>
            <span class="info-value">{{ result.project.scale }}</span>
          </div>
          <div class="info-item" v-if="result.project.owner">
            <span class="info-label">项目业主</span>
            <span class="info-value">{{ result.project.owner }}</span>
          </div>
          <div class="info-item" v-if="result.project.location">
            <span class="info-label">工程地点</span>
            <span class="info-value">{{ result.project.location }}</span>
          </div>
          <div class="info-item" v-if="result.project.contract_period">
            <span class="info-label">合同工期</span>
            <span class="info-value">{{ result.project.contract_period }}</span>
          </div>
          <div class="info-item" v-if="result.project.planning_version">
            <span class="info-label">策划版本</span>
            <span class="info-value">{{ result.project.planning_version }}</span>
          </div>
        </div>
      </div>

      <!-- 里程碑进度图 -->
      <div class="card">
        <div class="card-section-title">
          <el-icon :size="16" color="#1677ff"><TrendCharts /></el-icon>
          <span>2. 项目进度图</span>
          <el-radio-group v-model="chartMode" size="small" style="margin-left: auto">
            <el-radio-button value="gantt">甘特图</el-radio-button>
            <el-radio-button value="table">数据表格</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 甘特图 -->
        <div v-show="chartMode === 'gantt'" class="gantt-container">
          <GanttChart :milestones="result.milestones || []" :project="result.project" />
        </div>

        <!-- 数据表格 -->
        <div v-show="chartMode === 'table'" class="table-container">
          <el-table :data="result.milestones" stripe border style="width: 100%" max-height="600">
            <el-table-column type="index" label="序号" width="60" align="center" />
            <el-table-column prop="name" label="节点名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="date" label="完成时间" width="130" align="center" sortable />
            <el-table-column prop="criteria" label="完成标准/条件" min-width="250" show-overflow-tooltip />
            <el-table-column prop="category" label="类别" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="categoryTagType(row.category)" size="small" effect="plain">
                  {{ row.category }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 关键路径 -->
      <div v-if="result.critical_paths?.length" class="card">
        <div class="card-section-title">
          <el-icon :size="16" color="#1677ff"><Connection /></el-icon>
          <span>3. 关键路径（{{ result.critical_paths.length }} 条）</span>
        </div>
        <el-collapse>
          <el-collapse-item
            v-for="(cp, idx) in result.critical_paths"
            :key="idx"
            :title="cp.name"
          >
            <div v-if="cp.steps?.length" class="path-steps">
              <div v-for="(step, si) in cp.steps" :key="si" class="path-step-row">
                <el-tag :type="phaseTagType(step.phase)" size="small" effect="dark">
                  {{ step.phase }}
                </el-tag>
                <span class="step-date" v-if="step.date">{{ step.date }}</span>
                <span class="step-desc">{{ step.description }}</span>
              </div>
            </div>
            <div v-else class="path-empty">
              <el-empty description="暂无详细步骤数据" :image-size="60" />
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  Upload, UploadFilled, Loading, Document, Delete,
  Cpu, Check, InfoFilled, TrendCharts, Connection
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useProjectPlan } from '@/composables/useProjectPlan'
import GanttChart from '@/components/planning/GanttChart.vue'

const { loading, error, result, uploadFile, parse, reset } = useProjectPlan()

const fileInput = ref(null)
const dragOver = ref(false)
const chartMode = ref('gantt')

function triggerUpload() {
  if (!result.value) {
    fileInput.value?.click()
  }
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  if (file) {
    uploadFile.value = file
    error.value = null
  }
}

function onDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    uploadFile.value = file
    error.value = null
  }
}

function handleParse() {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  parse(uploadFile.value)
}

function handleReset() {
  reset()
  if (fileInput.value) fileInput.value.value = ''
}

function categoryTagType(cat) {
  const map = {
    '设计': '',
    '采购': 'warning',
    '施工': 'success',
    '调试': 'danger',
    '项目节点': 'info'
  }
  return map[cat] || 'info'
}

function phaseTagType(phase) {
  const map = {
    '设计': '',
    '采购': 'warning',
    '施工': 'success'
  }
  return map[phase] || 'info'
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.planning-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: $spacing-lg;
}

.page-title {
  font-size: $font-size-title;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: $spacing-xs;
}

.page-desc {
  font-size: $font-size-body;
  color: $color-text-secondary;
}

.card {
  background: $color-white;
  border-radius: $radius-card;
  box-shadow: $shadow-card;
  padding: $spacing-lg;
  margin-bottom: $spacing-md;
}

.card-section-title {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  font-size: $font-size-section;
  font-weight: 600;
  color: $color-text-primary;
  margin-bottom: $spacing-sm;
  padding-left: 10px;
  border-left: 3px solid $color-primary;
}

.card-section-desc {
  font-size: $font-size-caption;
  color: $color-text-secondary;
  margin-bottom: $spacing-md;
  padding-left: 23px;
}

// 上传区
.upload-zone {
  border: 2px dashed $color-border;
  border-radius: $radius-card;
  padding: $spacing-xl;
  cursor: pointer;
  transition: border-color $transition-fast, background $transition-fast;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    border-color: $color-primary;
    background: $color-primary-light;
  }

  &--has-file {
    border-color: $color-primary;
  }
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-xs;
}

.upload-main {
  font-size: $font-size-body;
  font-weight: 500;
  color: $color-text-primary;
  margin: $spacing-xs 0 0;
}

.upload-hint {
  font-size: $font-size-caption;
  color: $color-text-placeholder;
}

.parsed-preview {
  width: 100%;
}

.parsed-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.parsed-title {
  font-size: $font-size-body;
  font-weight: 500;
  color: $color-text-primary;
}

.upload-actions {
  margin-top: $spacing-md;
  display: flex;
  justify-content: center;
}

// 错误卡片
.error-card {
  :deep(.el-result__title) {
    font-size: $font-size-body;
  }
}

// 项目信息
.project-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-md $spacing-xl;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: $font-size-caption;
  color: $color-text-secondary;
}

.info-value {
  font-size: $font-size-body;
  color: $color-text-primary;
  font-weight: 500;
}

// 图表容器
.gantt-container {
  width: 100%;
  height: 500px;
}

.table-container {
  margin-top: $spacing-sm;
}

// 关键路径步骤
.path-steps {
  padding: $spacing-sm 0;
}

.path-step-row {
  display: flex;
  align-items: flex-start;
  gap: $spacing-sm;
  padding: $spacing-xs 0;
  font-size: $font-size-caption;
}

.step-date {
  color: $color-primary;
  font-weight: 500;
  white-space: nowrap;
  min-width: 90px;
}

.step-desc {
  color: $color-text-secondary;
  flex: 1;
}

.path-empty {
  padding: $spacing-md 0;
}

// 响应式
@media (max-width: 900px) {
  .project-info-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .project-info-grid {
    grid-template-columns: 1fr;
  }
  .gantt-container {
    height: 350px;
  }
}
</style>
