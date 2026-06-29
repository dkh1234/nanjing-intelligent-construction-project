<template>
  <div class="page-wrapper">
    <!-- ==================== 页面内容 ==================== -->
    <div class="page-content">
      <!-- 标题区域 -->
      <div class="page-header">
        <h1 class="page-title">日报预测</h1>
        <p class="page-desc">上传日报文档，系统将自动分析并预测下一日报内容，帮助您提前规划工作。</p>
      </div>

      <!-- 左右双卡片 -->
      <div class="main-grid">

        <!-- ========== 左侧：上传日报文档 ========== -->
        <div class="card">
          <!-- 模块标题 -->
          <div class="card-section-title">
            <el-icon :size="16" color="#1677ff"><Document /></el-icon>
            <span>1. 上传日报文档</span>
          </div>
          <p class="card-section-desc">支持 Excel / Word / PDF 格式，文件大小不超过 20MB</p>

          <!-- 拖拽上传区域 -->
          <div class="upload-zone" @click="handleUpload">
            <el-icon :size="48" color="#1677ff"><UploadFilled /></el-icon>
            <p class="upload-main">点击或拖拽文件到此处上传</p>
            <p class="upload-hint">支持 .xlsx / .xls / .docx / .doc / .pdf 格式</p>
          </div>

          <!-- 最近上传 -->
          <div class="recent-section">
            <p class="recent-title">最近上传</p>
            <div
              v-for="file in recentFiles"
              :key="file.name"
              class="file-item"
            >
              <div class="file-left">
                <div
                  class="file-icon"
                  :style="{ background: file.type === 'excel' ? '#25b864' : file.type === 'word' ? '#2c7be5' : '#f05252' }"
                >
                  {{ file.type === 'excel' ? 'X' : file.type === 'word' ? 'W' : 'P' }}
                </div>
                <div class="file-info">
                  <div class="file-name">{{ file.name }}</div>
                  <div class="file-meta">{{ file.size }} &nbsp;|&nbsp; {{ file.time }}</div>
                </div>
              </div>
              <el-icon :size="16" color="#52c41a"><Check /></el-icon>
            </div>
          </div>

          <!-- 开始预测按钮 -->
          <button class="btn-predict" @click="startPrediction">
            <el-icon :size="16"><Promotion /></el-icon>
            开始预测
          </button>
          <p class="btn-hint">提示：请上传包含完整日报信息的文档，以获得更准确的预测结果</p>
        </div>

        <!-- ========== 右侧：预测结果 ========== -->
        <div class="card card-right">
          <!-- 模块标题 -->
          <div class="card-title-row">
            <div class="card-section-title">
              <el-icon :size="16" color="#1677ff"><DataAnalysis /></el-icon>
              <span>2. 预测结果</span>
            </div>
            <div v-if="hasPrediction" class="status-tag">
              <el-icon :size="12" color="#fff"><Check /></el-icon>
              预测完成
            </div>
          </div>

          <!-- 空状态 -->
          <div v-if="!hasPrediction" class="empty-state">
            <div class="empty-icon">
              <el-icon :size="64" color="#d1d5db"><DataAnalysis /></el-icon>
            </div>
            <p class="empty-title">暂无预测结果</p>
            <p class="empty-desc">请先上传日报文档，然后点击「开始预测」<br/>系统将自动生成下一日报的预测内容</p>
          </div>

          <!-- 有结果 -->
          <template v-else>
          <div class="result-header">
            <span class="result-date">预测日期：2024-05-21（星期二）</span>
            <button class="btn-retry" @click="retryPrediction">
              <el-icon :size="14"><Refresh /></el-icon>
              重新预测
            </button>
          </div>

          <!-- 预测日报内容 -->
          <div class="result-body">
            <p class="report-heading">一、工作概述</p>
            <p class="report-text">预计今日将继续推进项目核心模块的开发与测试工作，重点完成用户管理模块的功能优化与联调测试。</p>

            <p class="report-heading">二、详细计划</p>
            <p class="report-text">1. 完成用户管理模块新增功能的编码实现</p>
            <p class="report-text">2. 进行模块单元测试与集成测试</p>
            <p class="report-text">3. 修复测试中发现的问题</p>
            <p class="report-text">4. 编写相关技术文档</p>

            <p class="report-heading">三、资源需求</p>
            <p class="report-text">1. 开发人员：3 人</p>
            <p class="report-text">2. 测试人员：1 人</p>
            <p class="report-text">3. 测试环境：1 套</p>

            <p class="report-heading">四、风险预警</p>
            <p class="report-text">1. 接口联调可能存在兼容性问题</p>
            <p class="report-text">2. 第三方服务响应时间可能影响测试进度</p>
          </div>

          <!-- 下载按钮 -->
          <div class="download-row">
            <button class="btn-download" @click="downloadWord">
              <el-icon :size="16"><Download /></el-icon>
              下载 Word 文档
            </button>
          </div>
          </template>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  UploadFilled, Document, Check, Refresh,
  Download, Promotion, DataAnalysis
} from '@element-plus/icons-vue'

// ---- 状态 ----
const hasPrediction = ref(false)

// ---- mock 数据 ----
const recentFiles = [
  { name: '2024-05-20_项目日报.xlsx', size: '12.5 KB',  time: '2024-05-20 10:30', type: 'excel' },
  { name: '2024-05-19_项目日报.docx', size: '18.3 KB',  time: '2024-05-19 18:45', type: 'word'  },
  { name: '2024-05-18_项目日报.pdf',  size: '256.7 KB', time: '2024-05-18 17:20', type: 'pdf'   }
]

// ---- 交互方法 ----
const handleUpload = () => { console.log('上传文件') }
const startPrediction = () => { hasPrediction.value = true; console.log('开始预测') }
const retryPrediction = () => { console.log('重新预测') }
const downloadWord = () => { console.log('下载 Word 文档') }
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.page-wrapper {
  min-height: 100vh;
  background: #f8fafc;
  padding: 32px;
  box-sizing: border-box;
}

.page-content {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

/* ==================== 标题区域 ==================== */
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

/* ==================== 左右布局 ==================== */
.main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 900px) {
  .main-grid {
    grid-template-columns: 1fr;
  }
  .page-wrapper {
    padding: 16px;
  }
}

/* ==================== 卡片通用 ==================== */
.card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
  padding: 24px;
  box-sizing: border-box;
}

/* ==================== 卡片标题行 ==================== */
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

/* ==================== 上传区域 ==================== */
.upload-zone {
  height: 200px;
  width: 100%;
  margin-top: 16px;
  border: 1.5px dashed #d1d5db;
  border-radius: 8px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-zone:hover {
  border-color: #1677ff;
  background: #fafcff;
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

/* ==================== 最近上传 ==================== */
.recent-section {
  margin-top: 24px;
}

.recent-title {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  margin: 0 0 12px;
}

.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 6px;
  background: #ffffff;
  cursor: default;
  transition: background 0.2s;
  margin-bottom: 8px;
}

.file-item:hover {
  background: #f3f4f6;
}

.file-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-icon {
  width: 16px;
  height: 16px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.file-name {
  font-size: 14px;
  color: #1f2937;
}

.file-meta {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
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
}

.btn-predict:hover {
  background: #0d66d0;
}

.btn-hint {
  font-size: 12px;
  color: #6b7280;
  margin: 12px 0 0;
}

/* ==================== 右侧卡片 flex ==================== */
.card-right {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* ==================== 右侧空状态 ==================== */
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

/* ==================== 右侧：预测日期与操作 ==================== */
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 24px;
  margin-bottom: 16px;
}

.result-date {
  font-size: 14px;
  color: #1f2937;
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
}

.btn-retry:hover {
  background: #e6f0ff;
}

/* ==================== 预测正文 ==================== */
.result-body {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  box-sizing: border-box;
}

.report-heading {
  font-size: 14px;
  font-weight: 500;
  color: #1f2937;
  margin: 16px 0 8px;
}

.report-heading:first-child {
  margin-top: 0;
}

.report-text {
  font-size: 14px;
  color: #1f2937;
  line-height: 1.6;
  margin: 0 0 4px;
  padding-left: 20px;
}

.report-text:last-child {
  margin-bottom: 0;
}

/* ==================== 下载按钮 ==================== */
.download-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
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
}

.btn-download:hover {
  background: #e6f0ff;
}
</style>
