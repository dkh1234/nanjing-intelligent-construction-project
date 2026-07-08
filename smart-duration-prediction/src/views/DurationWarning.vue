<template>
  <div class="predict-page">
    <h1 class="page-title">工期预警</h1>

    <div class="main-grid">
      <!-- 左侧：文件上传卡片 -->
      <div class="col-left">
        <div class="left-form-card">
          <!-- 上传框 1：项目策划书 -->
          <div class="form-section">
            <div class="section-heading">
              <el-icon :size="18" color="#1677FF"><Document /></el-icon>
              <span>项目策划书</span>
            </div>
            <el-upload
              class="upload-area"
              drag
              :limit="1"
              :auto-upload="false"
              :accept="'.pdf,.doc,.docx'"
              :file-list="planFileList"
              :before-upload="(f) => beforeUpload(f, 'plan')"
              :on-change="(f) => handleFileChange(f, 'plan')"
              :on-remove="() => handleRemove('plan')"
            >
              <div v-if="planFileList.length === 0" class="upload-placeholder">
                <el-icon :size="36" color="#1677FF"><UploadFilled /></el-icon>
                <p class="upload-main-text">拖拽文件至此，或 <em>点击上传</em></p>
                <p class="upload-hint">支持格式：pdf/doc/docx，大小不超过50MB</p>
              </div>
            </el-upload>
          </div>

          <!-- 上传框 2：项目周报 -->
          <div class="form-section">
            <div class="section-heading">
              <el-icon :size="18" color="#1677FF"><DataAnalysis /></el-icon>
              <span>项目周报</span>
            </div>
            <el-upload
              class="upload-area"
              drag
              :limit="1"
              :auto-upload="false"
              :accept="'.pdf,.doc,.docx'"
              :file-list="reportFileList"
              :before-upload="(f) => beforeUpload(f, 'report')"
              :on-change="(f) => handleFileChange(f, 'report')"
              :on-remove="() => handleRemove('report')"
            >
              <div v-if="reportFileList.length === 0" class="upload-placeholder">
                <el-icon :size="36" color="#1677FF"><UploadFilled /></el-icon>
                <p class="upload-main-text">拖拽文件至此，或 <em>点击上传</em></p>
                <p class="upload-hint">支持格式：pdf/doc/docx，大小不超过50MB</p>
              </div>
            </el-upload>
          </div>

          <!-- 分析按钮 -->
          <el-button
            class="submit-btn"
            :loading="submitting"
            @click="startAnalysis"
          >
            <el-icon :size="18"><Promotion /></el-icon>
            开始工期预警分析
          </el-button>
        </div>
      </div>

      <!-- 右侧：预警结果卡片 -->
      <div class="col-right">
        <div class="right-card">
          <div class="card-header">
            <el-icon :size="20" color="#1677FF"><WarningFilled /></el-icon>
            <span class="header-title">工期预警分析结果</span>
          </div>

          <!-- 空状态 -->
          <div v-if="pageState === 'empty'" class="result-area">
            <el-empty description="上传项目策划书和项目周报后，点击分析查看工期预警结果" :image-size="140">
              <template #image>
                <el-icon :size="80" color="#c9cdd4"><Warning /></el-icon>
              </template>
            </el-empty>
          </div>

          <!-- 加载状态 -->
          <div v-else-if="pageState === 'loading'" class="result-area">
            <el-skeleton :rows="8" animated />
          </div>

          <!-- 错误状态 -->
          <div v-else-if="pageState === 'error'" class="result-area">
            <el-result
              icon="error"
              title="分析失败"
              :sub-title="errorMsg"
            >
              <template #extra>
                <el-button type="primary" @click="startAnalysis">重新分析</el-button>
              </template>
            </el-result>
          </div>

          <!-- 结果展示 -->
          <div v-else-if="pageState === 'result'" class="result-area">
            <!-- 风险等级指示灯 -->
            <div class="risk-indicator" :class="`risk-${result.risk_level}`">
              <div class="risk-light">
                <div class="light-circle"></div>
                <div class="light-ring"></div>
              </div>
              <div class="risk-text">
                <span class="risk-label">{{ riskLabel }}</span>
                <span class="risk-desc">{{ riskDesc }}</span>
              </div>
            </div>

            <!-- 分析摘要 -->
            <div v-if="result.analysis_summary" class="analysis-summary">
              <el-icon :size="16"><InfoFilled /></el-icon>
              <span>{{ result.analysis_summary }}</span>
            </div>

            <!-- 时间对比 -->
            <div class="time-compare">
              <div class="time-compare-title">
                <el-icon :size="18" color="#1677FF"><Timer /></el-icon>
                <span>工期时间对比</span>
              </div>
              <div class="time-cards">
                <div class="time-card planned">
                  <div class="time-card-label">计划完工时间</div>
                  <div class="time-card-value">{{ result.planned_completion_date }}</div>
                </div>
                <div class="time-arrow">
                  <el-icon :size="24"><Right /></el-icon>
                </div>
                <div class="time-card predicted" :class="`border-${result.risk_level}`">
                  <div class="time-card-label">预测完工时间</div>
                  <div class="time-card-value">{{ result.predicted_completion_date }}</div>
                </div>
              </div>
              <!-- 偏差 -->
              <div v-if="result.delay_days !== undefined" class="delay-info" :class="result.risk_level">
                <template v-if="result.delay_days <= 0">
                  <el-icon :size="18"><CircleCheckFilled /></el-icon>
                  <span>预计可提前 {{ Math.abs(result.delay_days) }} 天完工</span>
                </template>
                <template v-else>
                  <el-icon :size="18"><WarningFilled /></el-icon>
                  <span>预计延迟 {{ result.delay_days }} 天（约 {{ (result.delay_days / 30).toFixed(1) }} 个月）</span>
                </template>
              </div>
            </div>

            <!-- 重新分析按钮 -->
            <el-button class="reanalyze-btn" @click="resetAnalysis">
              <el-icon :size="16"><Refresh /></el-icon>
              重新分析
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Document, DataAnalysis, UploadFilled, Promotion,
  WarningFilled, Warning, InfoFilled, Timer, Right,
  CircleCheckFilled, Refresh
} from '@element-plus/icons-vue'
import authRequest from '@/utils/authRequest'

// ========== 文件上传 ==========
const planFile = ref(null)
const reportFile = ref(null)

const planFileList = computed(() => planFile.value ? [planFile.value] : [])
const reportFileList = computed(() => reportFile.value ? [reportFile.value] : [])

function beforeUpload(file, type) {
  const isValid = /\.(pdf|doc|docx)$/i.test(file.name)
  if (!isValid) { ElMessage.error('仅支持 .pdf .doc .docx 格式文件'); return false }
  if (file.size / 1024 / 1024 > 50) { ElMessage.error('文件大小不能超过50MB'); return false }
  return false
}

function handleFileChange(file, type) {
  if (type === 'plan') planFile.value = file
  else reportFile.value = file
}

function handleRemove(type) {
  if (type === 'plan') planFile.value = null
  else reportFile.value = null
}

// ========== 页面状态 ==========
const pageState = ref('empty') // empty | loading | error | result
const submitting = ref(false)
const errorMsg = ref('')

const result = reactive({
  risk_level: '',        // green | yellow | red
  planned_completion_date: '',
  predicted_completion_date: '',
  delay_days: 0,
  analysis_summary: ''
})

// ========== Mock 模式（开发调试用，联调时改为 false）==========
const USE_MOCK = false

const mockResults = {
  green: {
    risk_level: 'green',
    planned_completion_date: '2026-12-31',
    predicted_completion_date: '2026-12-20',
    delay_days: -11,
    analysis_summary: '根据当前施工进度和资源配置情况分析，项目进度良好，预计可提前11天完成施工任务。各关键路径均在可控范围内，建议继续保持当前施工节奏。'
  },
  yellow: {
    risk_level: 'yellow',
    planned_completion_date: '2026-12-31',
    predicted_completion_date: '2027-01-18',
    delay_days: 18,
    analysis_summary: '根据周报数据，近期因原材料供应延迟和部分工序衔接不畅，导致工期有所滞后。预计延迟18天完工，仍在可控范围内，建议加强工序协调和资源调配。'
  },
  red: {
    risk_level: 'red',
    planned_completion_date: '2026-12-31',
    predicted_completion_date: '2027-03-15',
    delay_days: 74,
    analysis_summary: '根据周报分析，项目存在严重延期风险。多项关键路径节点滞后，累计延迟达74天。建议立即启动应急预案，增加施工班组和延长作业时间，并与业主沟通调整工期计划。'
  }
}

// ========== 风险等级文案 ==========
const riskLabel = computed(() => ({
  green: '工期正常',
  yellow: '工期预警',
  red: '工期严重滞后'
}[result.risk_level] || ''))

const riskDesc = computed(() => ({
  green: '项目可按计划时间完工，各项指标正常',
  yellow: '预计延迟在一个月以内，需关注施工进度',
  red: '预计延迟超过一个月，建议立即采取措施'
}[result.risk_level] || ''))

// ========== 核心逻辑 ==========
async function startAnalysis() {
  // 校验
  if (!planFile.value) { ElMessage.warning('请上传项目策划书'); return }
  if (!reportFile.value) { ElMessage.warning('请上传项目周报'); return }

  submitting.value = true
  pageState.value = 'loading'

  try {
    if (USE_MOCK) {
      // Mock 模式：随机返回绿/黄/红便于测试（实际使用时按需切换）
      await sleep(1500)
      const levels = ['green', 'yellow', 'red']
      const level = levels[Math.floor(Math.random() * levels.length)]
      Object.assign(result, mockResults[level])
    } else {
      // 真实 API 调用
      const formData = new FormData()
      formData.append('plan_file', planFile.value.raw)
      formData.append('report_file', reportFile.value.raw)

      const res = await authRequest.post('/duration-warning', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })

      const data = res?.data || res || {}
      Object.assign(result, {
        risk_level: data.risk_level || '',
        planned_completion_date: data.planned_completion_date || '',
        predicted_completion_date: data.predicted_completion_date || '',
        delay_days: data.delay_days ?? 0,
        analysis_summary: data.analysis_summary || ''
      })
    }

    pageState.value = 'result'
    ElMessage.success('工期预警分析完成')
  } catch (err) {
    console.error('Duration Warning API Error:', err)
    errorMsg.value = err.response?.data?.detail || err.response?.data?.message || err.message || '分析失败，请稍后重试'
    pageState.value = 'error'
  } finally {
    submitting.value = false
  }
}

function resetAnalysis() {
  pageState.value = 'empty'
  planFile.value = null
  reportFile.value = null
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.predict-page {
  padding: 0;
  height: calc(100vh - 56px - 48px);
  overflow: hidden;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.main-grid {
  display: grid;
  grid-template-columns: 43% 57%;
  gap: 20px;
  height: calc(100% - 56px);
  overflow: hidden;
}

.col-left {
  overflow-y: auto;
  padding-right: 4px;
  &::-webkit-scrollbar { width: 5px; }
  &::-webkit-scrollbar-thumb { background: #c9cdd4; border-radius: 3px; }
}

.col-right {
  overflow-y: auto;
  &::-webkit-scrollbar { width: 5px; }
  &::-webkit-scrollbar-thumb { background: #c9cdd4; border-radius: 3px; }
}

// ====== 左侧卡片 ======
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

.upload-area {
  width: 100%;
  :deep(.el-upload-dragger) {
    background: #fff;
    border: 1px dashed #dcdfe6;
    border-radius: 12px;
    padding: 20px;
    transition: border-color .2s;
    &:hover { border-color: #1677FF; }
  }
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-main-text {
  font-size: 14px; color: #4e5969;
  em { color: #1677FF; font-style: normal; cursor: pointer; }
}

.upload-hint { font-size: 12px; color: #8c8c8c; }

.submit-btn {
  width: 100%; height: 48px;
  background: #1677FF; border: none; border-radius: 10px;
  font-size: 16px; font-weight: 600; color: #fff;
  margin-top: 4px;
  transition: background .2s;
  &:hover { background: #4096FF; }
}

// ====== 右侧卡片 ======
.right-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.card-header {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.header-title { font-size: 18px; font-weight: 700; color: #1677FF; }

.result-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

// ====== 风险指示灯 ======
.risk-indicator {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 28px;
  border-radius: 16px;
  background: #f5f7fb;
  margin-bottom: 20px;
}

.risk-light {
  position: relative;
  width: 72px;
  height: 72px;
  flex-shrink: 0;
}

.light-circle {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 48px;
  height: 48px;
  border-radius: 50%;
  z-index: 2;
}

.light-ring {
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 68px;
  height: 68px;
  border-radius: 50%;
  opacity: 0.2;
  z-index: 1;
}

// 绿色
.risk-green {
  .light-circle {
    background: radial-gradient(circle at 40% 40%, #52c41a, #00B42A);
    box-shadow: 0 0 20px rgba(0, 180, 42, 0.5);
  }
  .light-ring {
    background: #00B42A;
    animation: pulse-green 2s ease-in-out infinite;
  }
}

// 黄色
.risk-yellow {
  .light-circle {
    background: radial-gradient(circle at 40% 40%, #ffb84d, #FF7D00);
    box-shadow: 0 0 20px rgba(255, 125, 0, 0.5);
  }
  .light-ring {
    background: #FF7D00;
    animation: pulse-yellow 1.5s ease-in-out infinite;
  }
}

// 红色
.risk-red {
  .light-circle {
    background: radial-gradient(circle at 40% 40%, #ff6b6b, #F53F3F);
    box-shadow: 0 0 20px rgba(245, 63, 63, 0.5);
  }
  .light-ring {
    background: #F53F3F;
    animation: pulse-red 1s ease-in-out infinite;
  }
}

@keyframes pulse-green {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.15; }
  50% { transform: translate(-50%, -50%) scale(1.15); opacity: 0.35; }
}

@keyframes pulse-yellow {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.2; }
  50% { transform: translate(-50%, -50%) scale(1.12); opacity: 0.4; }
}

@keyframes pulse-red {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.25; }
  50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.5; }
}

.risk-text {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.risk-label {
  font-size: 22px;
  font-weight: 700;
  color: #1d2129;
}

.risk-desc {
  font-size: 14px;
  color: #86909c;
  line-height: 1.5;
}

// ====== 分析摘要 ======
.analysis-summary {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 16px;
  background: #f0f5ff;
  border-radius: 10px;
  border-left: 3px solid #1677FF;
  font-size: 14px;
  color: #4e5969;
  line-height: 1.7;
  margin-bottom: 20px;

  .el-icon {
    margin-top: 2px;
    flex-shrink: 0;
    color: #1677FF;
  }
}

// ====== 时间对比 ======
.time-compare {
  margin-bottom: 20px;
}

.time-compare-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
  margin-bottom: 16px;
}

.time-cards {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.time-card {
  flex: 1;
  padding: 16px;
  border-radius: 12px;
  text-align: center;
  border: 1px solid #e5e6eb;
  background: #fff;

  &.planned {
    background: #f5f7fb;
  }

  &.predicted {
    &.border-green { border-color: #00B42A; border-width: 2px; }
    &.border-yellow { border-color: #FF7D00; border-width: 2px; }
    &.border-red { border-color: #F53F3F; border-width: 2px; }
  }
}

.time-card-label {
  font-size: 12px;
  color: #86909c;
  margin-bottom: 6px;
}

.time-card-value {
  font-size: 20px;
  font-weight: 700;
  color: #1d2129;
}

.time-arrow {
  flex-shrink: 0;
  color: #c9cdd4;
}

// 延迟信息
.delay-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;

  &.green {
    background: #f0fdf4;
    color: #00B42A;
  }

  &.yellow {
    background: #fff7ed;
    color: #FF7D00;
  }

  &.red {
    background: #fef2f2;
    color: #F53F3F;
  }
}

// ====== 重新分析按钮 ======
.reanalyze-btn {
  width: 100%;
  height: 44px;
  border: 1px solid #dcdfe6;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: #4e5969;
  background: #fff;
  transition: all .2s;

  &:hover {
    border-color: #1677FF;
    color: #1677FF;
    background: #f0f5ff;
  }
}

// ====== 响应式 ======
@media (max-width: 1100px) {
  .main-grid { grid-template-columns: 1fr; }
}
</style>
