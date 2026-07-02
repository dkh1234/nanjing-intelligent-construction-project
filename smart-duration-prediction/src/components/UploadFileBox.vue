<template>
  <div class="upload-file-box">
    <div class="upload-label">合同文件 <span class="required">*</span></div>
    <el-upload
      class="upload-area"
      drag
      :limit="1"
      :auto-upload="false"
      :accept="'.pdf,.doc,.docx'"
      :file-list="fileList"
      :before-upload="beforeUpload"
      :on-change="handleChange"
      :on-remove="handleRemove"
    >
      <div v-if="fileList.length === 0" class="upload-placeholder">
        <el-icon :size="36" color="#1677FF"><UploadFilled /></el-icon>
        <p class="upload-main-text">拖拽文件至此，或 <em>点击上传</em></p>
        <p class="upload-hint">支持格式：pdf/doc/docx，大小不超过50MB</p>
      </div>
    </el-upload>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: { type: Object, default: () => null }
})

const emit = defineEmits(['update:modelValue'])

const fileList = computed(() => {
  return props.modelValue ? [props.modelValue] : []
})

function handleChange(file) {
  emit('update:modelValue', file)
}

function handleRemove() {
  emit('update:modelValue', null)
}

function beforeUpload(file) {
  const isValid = /\.(pdf|doc|docx)$/i.test(file.name)
  if (!isValid) { ElMessage.error('仅支持 .pdf .doc .docx 格式文件'); return false }
  if (file.size / 1024 / 1024 > 50) { ElMessage.error('文件大小不能超过50MB'); return false }
  return false
}
</script>

<style lang="scss" scoped>
.upload-file-box { margin-bottom: 24px; }

.upload-label {
  font-size: 14px;
  font-weight: 600;
  color: #4e5969;
  margin-bottom: 8px;
}

.required { color: #f53f3f; margin-left: 2px; }

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
</style>
