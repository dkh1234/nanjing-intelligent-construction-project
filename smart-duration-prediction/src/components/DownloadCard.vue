<template>
  <div v-if="downloadUrl" class="download-card">
    <div class="download-title">
      <el-icon :size="16" color="#1677FF"><FolderOpened /></el-icon>
      <span>策划书文件下载</span>
    </div>
    <div class="download-body">
      <svg class="word-icon" viewBox="0 0 44 44" fill="none">
        <rect width="44" height="44" rx="10" fill="#E6F4FF"/>
        <path d="M12 6h16l8 8v26a2 2 0 01-2 2H12a2 2 0 01-2-2V8a2 2 0 012-2z" fill="#1677FF"/>
        <path d="M28 6v8h8" fill="#69B1FF"/>
        <text x="22" y="30" text-anchor="middle" fill="#fff" font-size="10" font-weight="700">W</text>
      </svg>
      <div class="file-meta">
        <span class="file-name">{{ fileName }}</span>
        <span class="file-size">{{ fileSize }}</span>
      </div>
      <el-button class="download-btn" @click="handleDownload">
        <el-icon :size="16"><Download /></el-icon>
        下载Word文件
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { FolderOpened, Download } from '@element-plus/icons-vue'

const props = defineProps({
  fileName: { type: String, default: '项目策划书.docx' },
  fileSize: { type: String, default: '2.45MB' },
  downloadUrl: { type: String, default: '' }
})

function handleDownload() {
  if (props.downloadUrl) window.open(props.downloadUrl, '_blank')
}
</script>

<style lang="scss" scoped>
.download-card { margin-top: 20px; }

.download-title {
  display: flex; align-items: center; gap: 6px;
  font-size: 14px; font-weight: 600; color: #1d2129;
  margin-bottom: 12px;
}

.download-body {
  display: flex; align-items: center; gap: 14px;
  background: #f7f8fa; border-radius: 12px; padding: 16px 18px;
}

.word-icon { flex-shrink: 0; }

.file-meta {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 4px;
}

.file-name {
  font-size: 14px; color: #1d2129; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.file-size { font-size: 12px; color: #86909c; }

.download-btn {
  flex-shrink: 0;
  border: 1px solid #1677FF; color: #1677FF; border-radius: 8px;
  font-size: 13px; font-weight: 500;
  &:hover { background: #e6f4ff; border-color: #4096FF; color: #4096FF; }
}
</style>
