<template>
  <div class="prediction-card">
    <h3 class="prediction-card__title">项目基础信息</h3>
    <div class="prediction-card__content">
      <el-form-item label="项目名称" required>
        <el-input
          :model-value="modelValue.projectName"
          @update:model-value="update('projectName', $event)"
          placeholder="例：5000t/d熟料生产线建设项目"
          size="large"
          clearable
        />
      </el-form-item>

      <el-form-item label="合同文件" required>
        <el-upload
          class="contract-upload"
          drag
          :limit="1"
          :auto-upload="false"
          :accept="'.pdf,.doc,.docx'"
          :file-list="fileList"
          :before-upload="beforeUpload"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <div class="upload-placeholder">
            <el-icon :size="40" color="#C9CDD4"><UploadFilled /></el-icon>
            <div class="upload-text">
              <p>将合同文件拖拽到此处，或<em>点击上传</em></p>
              <p class="upload-hint">支持 .pdf .doc .docx 格式，单个文件不超过 50MB</p>
            </div>
          </div>
        </el-upload>
      </el-form-item>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:modelValue'])

const fileList = computed(() => {
  return props.modelValue.contractFile ? [props.modelValue.contractFile] : []
})

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function handleFileChange(file) {
  update('contractFile', file)
}

function handleFileRemove() {
  update('contractFile', null)
}

function beforeUpload(file) {
  const isValidType = /\.(pdf|doc|docx)$/i.test(file.name)
  if (!isValidType) {
    ElMessage.error('仅支持 .pdf .doc .docx 格式文件')
    return false
  }
  const isLt50M = file.size / 1024 / 1024 < 50
  if (!isLt50M) {
    ElMessage.error('文件大小不能超过 50MB')
    return false
  }
  return false
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.contract-upload {
  width: 100%;

  :deep(.el-upload-dragger) {
    border: 2px dashed $color-border;
    border-radius: $radius-card;
    padding: $spacing-xl;
    transition: border-color $transition-fast;
    &:hover {
      border-color: $color-primary;
    }
  }
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
}

.upload-text {
  p {
    color: $color-text-secondary;
    font-size: $font-size-body;
    em {
      color: $color-primary;
      font-style: normal;
      cursor: pointer;
    }
  }
  .upload-hint {
    font-size: $font-size-caption;
    color: $color-text-placeholder;
    margin-top: 4px;
  }
}
</style>
