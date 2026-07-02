<template>
  <div v-if="downloadUrl" class="prediction-card file-download-card">
    <div class="download-content">
      <div class="file-icon">
        <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect width="48" height="48" rx="10" fill="#E6F4FF"/>
          <path d="M14 8H30L36 14V40C36 41.1 35.1 42 34 42H14C12.9 42 12 41.1 12 40V10C12 8.9 12.9 8 14 8Z" fill="#1677FF"/>
          <path d="M30 8V14H36" fill="#4096FF"/>
          <text x="24" y="32" text-anchor="middle" fill="white" font-size="10" font-weight="bold">W</text>
        </svg>
      </div>
      <div class="file-info">
        <span class="file-name">{{ fileName }}</span>
        <span v-if="fileSize" class="file-size">{{ fileSize }}</span>
      </div>
      <el-button type="primary" :icon="Download" @click="handleDownload">
        下载文件
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { Download } from '@element-plus/icons-vue'

const props = defineProps({
  fileName: { type: String, default: '项目策划书.docx' },
  fileSize: { type: String, default: '' },
  downloadUrl: { type: String, default: '' }
})

const emit = defineEmits(['download'])

function handleDownload() {
  if (props.downloadUrl) {
    window.open(props.downloadUrl, '_blank')
  }
  emit('download')
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.file-download-card {
  margin-bottom: 0;
}

.download-content {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.file-icon {
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.file-name {
  font-size: $font-size-section;
  font-weight: 500;
  color: $color-text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-size {
  font-size: $font-size-caption;
  color: $color-text-secondary;
}
</style>
