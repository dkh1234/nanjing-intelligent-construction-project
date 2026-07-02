<template>
  <div class="daily-report-page">
    <!-- ==================== 标题 ==================== -->
    <div class="page-header">
      <h1 class="page-title">日报预测</h1>
      <p class="page-desc">上传日报文档，系统将自动分析并预测下一日报内容，帮助您提前规划工作。</p>
    </div>

    <!-- ==================== 左右双卡片 ==================== -->
    <div class="main-grid">

      <!-- ========== 左侧：上传日报文档 ========== -->
      <div class="card">
        <div class="card-section-title">
          <el-icon :size="16" color="#1677ff"><Document /></el-icon>
          <span>1. 上传日报文档</span>
        </div>
        <p class="card-section-desc">支持 Excel / Word / PDF 格式，文件大小不超过 20MB</p>

        <!-- 上传/解析区域 -->
        <div
          class="upload-zone"
          :class="{ 'upload-zone--parsed': parsedData }"
          @click="triggerUpload"
          @dragover.prevent="dragOver = true"
          @dragleave="dragOver = false"
          @drop.prevent="onDrop"
        >
          <!-- 状态1: 无文件，上传提示 -->
          <div v-if="!uploadReady && !parsing" class="upload-inner">
            <el-icon :size="48" color="#1677ff"><UploadFilled /></el-icon>
            <p class="upload-main">点击或拖拽文件到此处上传</p>
            <p class="upload-hint">支持 .xlsx / .xls / .docx / .doc / .pdf 格式</p>
          </div>

          <!-- 状态2: 解析中 -->
          <div v-else-if="parsing" class="upload-inner">
            <el-icon :size="48" color="#1677ff" class="is-loading"><Loading /></el-icon>
            <p class="upload-main">正在解析文件...</p>
            <p class="upload-hint">{{ fileList[0]?.name || '' }}</p>
          </div>

          <!-- 状态3: 已解析 -->
          <div v-else-if="parsedData" class="parsed-preview">
            <div class="parsed-header">
              <el-icon :size="18" color="#52c41a"><Check /></el-icon>
              <span class="parsed-title">{{ fileList[0]?.name || '文件' }}</span>
              <el-tag type="success" size="small" effect="plain">
                {{ parsedData.week_count ?? parsedData.weeks?.length ?? 0 }} 周数据
              </el-tag>
              <el-button type="danger" size="small" text :icon="Delete" @click.stop="handleFileRemove" style="margin-left: auto" />
            </div>
            <div class="parsed-weeks-list">
              <div v-for="(week, index) in (parsedData.weeks || [])" :key="index" class="parsed-week-card">
                <!-- 周头部 -->
                <div class="pwc-header">
                  <span class="pwc-label">第{{ index + 1 }}周</span>
                  <span class="pwc-date">{{ week.week_start || '-' }} ~ {{ week.week_end || '-' }}</span>
                  <span class="pwc-days">施工 {{ week.n_days ?? '-' }} 天</span>
                  <span class="pwc-temp">均温 {{ week.avg_temp ?? '-' }}°C</span>
                </div>
                <!-- 详情行 -->
                <div class="pwc-detail">
                  <div class="pwc-col">
                    <span class="pwc-col-title">人员</span>
                    <span>日均 {{ week.avg_workers ?? '-' }} / 峰值 {{ week.max_workers ?? '-' }} 人</span>
                  </div>
                  <div class="pwc-col">
                    <span class="pwc-col-title">机械</span>
                    <span>挖机 {{ week.avg_excavator ?? '-' }} · 汽车吊 {{ week.avg_mobile_crane ?? '-' }} · 装载机 {{ week.avg_loader ?? '-' }} · 总计 {{ week.total_equip ?? '-' }} 台</span>
                  </div>
                  <div class="pwc-col">
                    <span class="pwc-col-title">活动</span>
                    <span>日均 {{ week.avg_items_per_day ?? '-' }} 条 · 周计 {{ week.total_items_week ?? '-' }} 条</span>
                    <span class="pwc-tags">
                      <el-tag size="small" type="">土建 {{ week.cat_土建 ?? 0 }}</el-tag>
                      <el-tag size="small" type="success">钢结构 {{ week.cat_钢结构 ?? 0 }}</el-tag>
                      <el-tag size="small" type="warning">安装 {{ week.cat_设备安装 ?? 0 }}</el-tag>
                      <el-tag size="small" type="info">装修 {{ week.cat_装修 ?? 0 }}</el-tag>
                    </span>
                  </div>
                  <div class="pwc-col">
                    <span class="pwc-col-title">子项</span>
                    <span>活跃 {{ week.sub_count ?? '-' }} · 多样性 {{ week.sub_diversity ?? '-' }} · 降雨 {{ week.rain_days ?? 0 }}天</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 状态4: 有文件未解析 -->
          <div v-else class="upload-inner">
            <el-icon :size="48" color="#1677ff"><Document /></el-icon>
            <p class="upload-main">{{ fileList[0]?.name || '已选择文件' }}</p>
            <p class="upload-hint">点击「开始预测」解析并预测</p>
          </div>
        </div>

        <!-- 隐藏的真实上传 input -->
        <input
          ref="fileInput"
          type="file"
          :accept="'.xlsx,.xls,.docx,.doc,.pdf,.txt'"
          style="display: none"
          @change="onFileInput"
        />

        <!-- 底部操作区 -->
        <div class="card-footer">
          <!-- 预测周数设置 -->
          <div v-if="parsedData" class="predict-config">
            <span class="config-label">预测未来</span>
            <el-slider
              v-model="predictWeeks"
              :min="1"
              :max="4"
              :marks="{ 1: '1周', 2: '2周', 3: '3周', 4: '4周' }"
              show-stops
              style="flex: 1; margin: 0 16px"
            />
          </div>

          <!-- 按钮 -->
          <button
            class="btn-predict"
            :disabled="!uploadReady"
            :style="{ opacity: uploadReady ? 1 : 0.5, cursor: uploadReady ? 'pointer' : 'not-allowed' }"
            @click="handleSubmit"
          >
            <el-icon :size="16"><Promotion /></el-icon>
            {{ submitting ? '处理中...' : parsedData ? '更新预测' : '开始预测' }}
          </button>
          <p class="btn-hint">提示：请上传包含完整日报信息的文档，以获得更准确的预测结果</p>

          <!-- 错误提示 -->
          <el-alert
            v-if="errorMsg"
            :title="errorMsg"
            type="error"
            :closable="true"
            show-icon
            style="margin-top: 12px"
            @close="errorMsg = null"
          />
        </div>
      </div>

      <!-- ========== 右侧：预测结果 ========== -->
      <div class="card card-right">
        <div class="card-title-row">
          <div class="card-section-title">
            <el-icon :size="16" color="#1677ff"><DataAnalysis /></el-icon>
            <span>2. 预测结果</span>
          </div>
          <div v-if="predictionResult" class="status-tag">
            <el-icon :size="12" color="#fff"><Check /></el-icon>
            预测完成
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!predictionResult" class="empty-state">
          <div class="empty-icon">
            <el-icon :size="64" color="#d1d5db"><DataAnalysis /></el-icon>
          </div>
          <p class="empty-title">暂无预测结果</p>
          <p class="empty-desc">请先上传日报文档，然后点击「开始预测」<br/>系统将自动生成下一日报的预测内容</p>
        </div>

        <!-- 预测结果 -->
        <template v-else>
          <!-- 多周 Tab -->
          <el-tabs v-model="activeResultWeek" type="card" class="result-tabs">
            <el-tab-pane
              v-for="(pw, pwi) in predictionResult.weeks"
              :key="pwi"
              :label="'第 ' + pw.predict_week + ' 周'"
              :name="pwi"
            >
              <div class="result-header">
                <span class="result-date">预测日期：{{ pw.predict_dates }}</span>
                <button class="btn-retry" @click="handleSubmit">
                  <el-icon :size="14"><Refresh /></el-icon>
                  重新预测
                </button>
              </div>

              <!-- 指标卡片 -->
              <div class="overview-grid">
                <div class="metric-card">
                  <div class="metric-card-title">
                    <el-icon :size="14" color="#1677ff"><User /></el-icon> 施工人员
                  </div>
                  <div v-if="pw.personnel" class="metric-body">
                    <div v-for="(item, key) in pw.personnel" :key="key" class="metric-row">
                      <span class="metric-label">{{ key }}</span>
                      <span class="metric-value">{{ item.value }}<small>{{ item.unit }}</small></span>
                    </div>
                  </div>
                </div>

                <div class="metric-card">
                  <div class="metric-card-title">
                    <el-icon :size="14" color="#FF7D00"><Setting /></el-icon> 机械设备
                  </div>
                  <div v-if="pw.equipment" class="metric-body">
                    <div v-for="(item, key) in pw.equipment" :key="key" class="metric-row">
                      <span class="metric-label">{{ key }}</span>
                      <span class="metric-value">{{ item.value }}<small>{{ item.unit }}</small></span>
                    </div>
                  </div>
                </div>

                <div class="metric-card">
                  <div class="metric-card-title">
                    <el-icon :size="14" color="#00B42A"><List /></el-icon> 施工活动
                  </div>
                  <div v-if="pw.activity" class="metric-body">
                    <div v-for="(item, key) in pw.activity" :key="key" class="metric-row">
                      <span class="metric-label">{{ key }}</span>
                      <span class="metric-value">{{ item.value }}<small>{{ item.unit }}</small></span>
                    </div>
                  </div>
                </div>

                <div class="metric-card">
                  <div class="metric-card-title">
                    <el-icon :size="14" color="#1677FF"><Cloudy /></el-icon> 天气
                  </div>
                  <div v-if="pw.weather" class="weather-display">
                    <span class="weather-icon">{{ pw.weather.rain_days <= 1 ? '☀️' : pw.weather.rain_days <= 3 ? '⛅' : '🌧️' }}</span>
                    <span class="weather-value">{{ pw.weather.rain_days }} 天降雨</span>
                  </div>
                </div>
              </div>

              <!-- 活动频次分布 -->
              <div class="bar-chart-card">
                <p class="bar-chart-title">活动频次分布</p>
                <div class="bar-chart">
                  <div v-for="item in getActivityChart(pw)" :key="item.name" class="bar-row">
                    <span class="bar-label">{{ item.name }}</span>
                    <div class="bar-track">
                      <div class="bar-fill" :style="{ width: item.percent + '%', background: item.color }" />
                    </div>
                    <span class="bar-value">{{ item.value }} 次</span>
                  </div>
                </div>
              </div>

              <!-- 预测日报文本 -->
              <div v-if="pw.report_text" class="report-text-card">
                <p class="report-text-title">预测日报内容</p>
                <pre class="report-text-body">{{ pw.report_text }}</pre>
              </div>
            </el-tab-pane>
          </el-tabs>

          <!-- 下载按钮 -->
          <div class="download-row">
            <button class="btn-download" @click="downloadWord(activeResultWeek)">
              <el-icon :size="16"><Download /></el-icon>
              下载 Word 文档
            </button>
          </div>
        </template>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  UploadFilled, Document, Check, Refresh,
  Promotion, DataAnalysis, User, Setting,
  List, Cloudy, Download, Loading, Delete
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useDailyReport } from '@/composables/useDailyReport'

const {
  parsedData, prediction: predictionResult,
  parsing, predicting, errorMsg,
  uploadAndParse, resetAll
} = useDailyReport()

// ---- 状态 ----
const fileInput = ref(null)
const fileList = ref([])
const dragOver = ref(false)
const predictWeeks = ref(1)
const activeResultWeek = ref(0)
const submitting = computed(() => parsing.value || predicting.value)

const uploadReady = computed(() => fileList.value.length > 0)

// ---- 上传 ----
function triggerUpload() {
  fileInput.value?.click()
}

function validateFile(file) {
  if (!file) return false
  const ok = /\.(xlsx|xls|docx|doc|pdf|txt)$/i.test(file.name)
  if (!ok) { ElMessage.error('仅支持 Excel / Word / PDF / TXT 格式'); return false }
  if (file.size / 1024 / 1024 > 50) { ElMessage.error('文件不能超过 50MB'); return false }
  return true
}

async function onFileInput(e) {
  const file = e.target.files?.[0]
  if (!file || !validateFile(file)) return
  fileList.value = [{ name: file.name, size: file.size, raw: file }]
  // 自动解析
  await uploadAndParse(file, predictWeeks.value)
  if (errorMsg.value) {
    ElMessage.error(errorMsg.value)
  }
  // 重置 input 以便重新选择同一文件
  e.target.value = ''
}

function onDrop(e) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && validateFile(file)) {
    fileList.value = [{ name: file.name, size: file.size, raw: file }]
    uploadAndParse(file, predictWeeks.value)
  }
}

function handleFileRemove() {
  fileList.value = []
  resetAll()
}

// ---- 提交 ----
async function handleSubmit() {
  if (!uploadReady.value) return
  await uploadAndParse(fileList.value[0].raw, predictWeeks.value)
  activeResultWeek.value = 0
  if (errorMsg.value) {
    ElMessage.error(errorMsg.value)
  }
}

// ---- 活动图表 ----
function getActivityChart(pw) {
  if (!pw?.activity) return []
  const cats = ['土建活动频次', '钢结构活动频次', '设备安装活动频次', '装修活动频次']
  const colors = ['#1677FF', '#FF7D00', '#00B42A', '#F53F3F']
  const maxVal = Math.max(...cats.map(c => pw.activity[c]?.value ?? 0), 1)
  return cats
    .filter(c => pw.activity[c] != null)
    .map((c, i) => ({
      name: c,
      value: pw.activity[c].value,
      percent: (pw.activity[c].value / maxVal) * 100,
      color: colors[i]
    }))
}

// ---- 下载 Word ----
function downloadWord(weekIndex = 0) {
  const pw = predictionResult.value?.weeks?.[weekIndex]
  if (!pw?.report_text) {
    ElMessage.warning('暂无预测日报内容可下载')
    return
  }

  // 构建 HTML 格式的 Word 文档
  const html = `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body>
<h2>预测日报</h2>
<p><strong>预测日期：</strong>${pw.predict_dates}</p>
<hr/>
<pre style="font-family: 'PingFang SC','Microsoft YaHei',sans-serif; font-size: 14px; line-height: 1.8; white-space: pre-wrap;">${pw.report_text}</pre>
<hr/>
<p style="color: #999; font-size: 12px;">由智能工期预测系统生成，仅供参考</p>
</body>
</html>`

  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `预测日报_${pw.predict_dates?.split(' ~ ')[0] || 'report'}.doc`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.daily-report-page {
  height: 100%;
}

/* ==================== 标题 ==================== */
.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1;
  margin: 0 0 8px;
}

.page-desc {
  font-size: 14px;
  color: #6b7280;
  line-height: 1.5;
  margin: 0;
}

/* ==================== 布局 ==================== */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;

  @media (max-width: 1100px) {
    grid-template-columns: 1fr;
  }
}

/* ==================== 卡片 ==================== */
.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  padding: 24px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.card-right {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* ==================== 卡片标题 ==================== */
.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.card-section-desc {
  font-size: 12px;
  color: #6b7280;
  margin: 8px 0 0;
}

/* ==================== 状态标签 ==================== */
.status-tag {
  height: 26px;
  padding: 0 12px;
  background: #52c41a;
  border-radius: 6px;
  color: #ffffff;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ==================== 上传区 ==================== */
.upload-zone {
  margin-top: 16px;
  width: 100%;
  min-height: 200px;
  flex: 1 1 auto;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, min-height 0.3s;
  cursor: pointer;
  box-sizing: border-box;

  &:hover { border-color: #1677ff; }

  &--parsed {
    min-height: auto;
    flex: 0 0 auto;
    cursor: default;
    border-style: solid;
    border-color: #e5e7eb;
    background: #fafcff;
    display: block;
    padding: 0;
  }
}

.upload-inner {
  text-align: center;
  padding: 20px;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.upload-main {
  font-size: 14px;
  color: #1f2937;
  margin: 16px 0 0;
}

.upload-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 8px 0 0;
}

/* ==================== 解析预览（上传框内） ==================== */
.parsed-preview {
  padding: 12px 16px;
}

.parsed-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 8px;
}

.parsed-title {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
}

.parsed-weeks-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.parsed-week-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px 14px;
  transition: border-color 0.15s, box-shadow 0.15s;

  &:hover {
    border-color: #b0c8e8;
    box-shadow: 0 2px 8px rgba(22, 119, 255, 0.06);
  }
}

.pwc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
}

.pwc-label {
  font-size: 13px;
  font-weight: 700;
  color: #1677ff;
}

.pwc-date {
  font-size: 12px;
  color: #374151;
  font-weight: 500;
}

.pwc-days {
  font-size: 11px;
  color: #6b7280;
  margin-left: auto;
}

.pwc-temp {
  font-size: 11px;
  color: #6b7280;
}

.pwc-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pwc-col {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 11px;
  color: #374151;
  padding: 2px 0;

  .pwc-col-title {
    font-weight: 600;
    color: #6b7280;
    width: 32px;
    flex-shrink: 0;
    font-size: 10px;
  }
}

.pwc-tags {
  display: flex;
  gap: 4px;
  margin-left: 8px;

  .el-tag {
    font-size: 10px;
    height: 18px;
    padding: 0 5px;
  }
}

/* ==================== 预测设置 ==================== */
.predict-config {
  display: flex;
  align-items: center;
  margin-top: 16px;
  padding: 0 4px;
}

.config-label {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
}

/* ==================== 按钮 ==================== */
/* ==================== 卡片底部操作区 ==================== */
.card-footer {
  margin-top: auto;
  padding-top: 8px;
}

/* ==================== 预测按钮 ==================== */
.btn-predict {
  height: 40px;
  width: 100%;
  border: none;
  border-radius: 6px;
  background: #1677ff;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
  margin-top: 20px;
  padding: 0;
  transition: background 0.2s;
  font-family: inherit;

  &:hover:not(:disabled) { background: #0d66d0; }
}

.btn-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 12px 0 0;
}

/* ==================== 空状态 ==================== */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  min-height: 300px;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-title {
  font-size: 15px;
  font-weight: 500;
  color: #9ca3af;
  margin: 0 0 8px;
}

.empty-desc {
  font-size: 13px;
  color: #b0b7c3;
  line-height: 1.7;
  margin: 0;
}

/* ==================== 预测结果 ==================== */
.result-tabs {
  :deep(.el-tabs__header) { margin: 0 0 16px; }
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.result-date {
  font-size: 14px;
  color: #1f2937;
  font-weight: 500;
}

.btn-retry {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #1677ff;
  font-size: 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;

  &:hover { background: #e6f0ff; }
}

/* ==================== 指标卡片 ==================== */
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.metric-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.metric-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;

  .metric-label {
    font-size: 12px;
    color: #6b7280;
    flex: 1;
  }

  .metric-value {
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
    white-space: nowrap;

    small { font-size: 11px; font-weight: 400; color: #9ca3af; margin-left: 2px; }
  }
}

.weather-display {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
}

.weather-icon { font-size: 28px; }

.weather-value {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
}

/* ==================== 活动频次图 ==================== */
.bar-chart-card {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.bar-chart-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 12px;
}

.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  width: 70px;
  font-size: 12px;
  color: #6b7280;
  text-align: right;
  flex-shrink: 0;
}

.bar-track {
  flex: 1;
  height: 16px;
  background: #e5e7eb;
  border-radius: 3px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}

.bar-value {
  width: 44px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  flex-shrink: 0;
}

/* ==================== 预测日报文本 ==================== */
.report-text-card {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-top: 16px;
}

.report-text-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.report-text-body {
  font-family: 'PingFang SC', 'Microsoft YaHei', monospace;
  font-size: 13px;
  color: #1f2937;
  line-height: 1.8;
  white-space: pre-wrap;
  margin: 0;
  padding: 0;
  background: transparent;
  border: none;
}

/* ==================== 下载按钮 ==================== */
.download-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.btn-download {
  height: 36px;
  padding: 0 16px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #ffffff;
  color: #1677ff;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;

  &:hover { background: #e6f0ff; }
}
</style>
