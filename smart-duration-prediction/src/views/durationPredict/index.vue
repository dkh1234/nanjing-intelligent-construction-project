<template>
  <div class="predict-page">
    <h1 class="page-title">工期预测</h1>

    <div class="main-grid">
      <!-- 左侧：表单卡片 -->
      <div class="col-left">
        <ProjectInfoCard ref="formRef" :submitting="submitting" @submit="startAnalysis" />
      </div>

      <!-- 右侧：AI分析卡片 -->
      <div class="col-right">
        <AIAnalysisCard
          :current-step="currentStep"
          :loading="submitting"
          :markdown-content="markdownContent"
          :download-url="downloadUrl"
          :project-name="projectName"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import ProjectInfoCard from '@/components/ProjectInfoCard.vue'
import AIAnalysisCard from '@/components/AIAnalysisCard.vue'
import request from '@/utils/request'

const formRef = ref(null)
const submitting = ref(false)
const currentStep = ref(-1)
const markdownContent = ref('')
const downloadUrl = ref('')
const projectName = ref('项目策划书')

const steps = ['上传文件', '解析合同', '识别关键路径', 'AI工期分析', '生成策划书']

async function startAnalysis() {
  const form = formRef.value?.form
  if (!form) return

  // 校验
  if (!form.projectName.trim()) { ElMessage.warning('请输入项目名称'); return }
  if (!form.contractFile) { ElMessage.warning('请上传合同文件'); return }
  if (!form.heater) { ElMessage.warning('请选择预热器'); return }
  if (!form.foundation) { ElMessage.warning('请选择基础形式'); return }
  if (form.criticalPaths.some(p => !p.trim())) { ElMessage.warning('请填写完整关键路径'); return }

  submitting.value = true
  currentStep.value = -1

  try {
    // step 0: 上传文件
    await advance(0, 600)
    // step 1: 解析合同
    await advance(1, 500)
    // step 2: 识别关键路径
    await advance(2, 500)

    // step 3: AI工期分析 — 调用API
    currentStep.value = 3

    // 1. 上传文件获取 file_id
    let fileId = ''
    if (form.contractFile?.raw) {
      const fileForm = new FormData()
      fileForm.append('file', form.contractFile.raw)
      fileForm.append('user', 'admin')
      const uploadRes = await request.post('/files/upload', fileForm, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      })
      fileId = uploadRes?.id || uploadRes?.data?.id || ''
    }

    // 2. 构建请求体 (Chat API)
    const inputs = {
      project_name: form.projectName,
      heater: form.heater || '',
      length: String(form.length ?? ''),
      width: String(form.width ?? ''),
      concreteHeight: String(form.concreteHeight ?? ''),
      totalHeight: String(form.totalHeight ?? ''),
      foundation: form.foundation || '',
      concreteLayer: String(form.concreteLayer ?? ''),
      towerLayer: String(form.towerLayer ?? '')
    }

    form.criticalPaths.forEach((p, i) => {
      inputs[`critical_path${i + 1}`] = p || ''
    })

    // 文件放入 inputs 中
    if (fileId) {
      inputs.contract_file = {
        transfer_method: 'local_file',
        upload_file_id: fileId,
        type: 'document'
      }
    }

    const body = {
      inputs,
      query: '请根据以上参数进行工期预测分析，生成项目策划书',
      response_mode: 'blocking',
      user: 'admin'
    }

    const res = await request.post('/chat-messages', body, { timeout: 600000 })

    console.log('Dify 完整响应:', JSON.stringify(res, null, 2))

    const data = res?.data || res || {}
    const answer = data.answer || ''
    markdownContent.value = answer
    projectName.value = form.projectName || '项目策划书'

    // 尝试从多个可能的字段获取文件URL
    const fileUrl = data.download_url
      || data.file_url
      || data.word_file_url
      || data.metadata?.file_url
      || (data.files && data.files[0]?.url)
      || ''
    downloadUrl.value = fileUrl
    console.log('文件下载URL:', fileUrl || '未找到')

    // step 4: 生成策划书
    await advance(4, 400)
    ElMessage.success('AI分析完成，策划书已生成')
  } catch (err) {
    console.error('Dify API Error:', err)
    console.error('Status:', err.response?.status, 'Data:', err.response?.data)
    const data = err.data || err.response?.data
    const msg = data && Object.keys(data).length > 0
      ? JSON.stringify(data)
      : (err.message || '未知错误')
    ElMessage.error(msg.slice(0, 300))
    currentStep.value = -1
  } finally {
    submitting.value = false
  }
}

function advance(step, delay) {
  currentStep.value = step
  return new Promise(resolve => setTimeout(resolve, delay))
}
</script>

<style lang="scss" scoped>
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

@media (max-width: 1100px) {
  .main-grid { grid-template-columns: 1fr; }
}
</style>
