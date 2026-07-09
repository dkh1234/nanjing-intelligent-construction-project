import { ref } from 'vue'
import request from '@/utils/request'

export function useDifyWorkflow() {
  const loading = ref(false)
  const error = ref(null)
  const result = ref(null)
  const currentStep = ref(0)

  const stepLabels = ['上传文件', '解析合同', '识别关键路径', 'AI工期分析', '生成策划书']

  function reset() {
    loading.value = false
    error.value = null
    result.value = null
    currentStep.value = 0
  }

  async function submit(params) {
    loading.value = true
    error.value = null
    result.value = null

    try {
      currentStep.value = 1
      await new Promise(resolve => setTimeout(resolve, 400))

      const formData = new FormData()

      if (params.contractFile?.raw) {
        formData.append('contract_file', params.contractFile.raw)
      }
      formData.append('project_name', params.projectName || '')

      const paths = params.criticalPaths || []
      for (let i = 0; i < 5; i++) {
        formData.append(`critical_path${i + 1}`, paths[i] || '')
      }

      formData.append('heater', params.heater || '')
      formData.append('length', String(params.length || ''))
      formData.append('width', String(params.width || ''))
      formData.append('concreteHeight', String(params.concreteHeight || ''))
      formData.append('totalHeight', String(params.totalHeight || ''))
      formData.append('foundation', params.foundation || '')
      formData.append('concreteLayer', String(params.concreteLayer || ''))
      formData.append('towerLayer', String(params.towerLayer || ''))

      currentStep.value = 2
      await new Promise(resolve => setTimeout(resolve, 300))

      currentStep.value = 3
      await new Promise(resolve => setTimeout(resolve, 300))

      const response = await request.post('/workflows/run', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 180000
      })

      currentStep.value = 4
      await new Promise(resolve => setTimeout(resolve, 300))

      const outputs = response?.data?.outputs || response?.outputs || {}

      result.value = {
        markdownContent: outputs.markdown_report || outputs.text || '',
        wordFileUrl: outputs.word_file_url || '',
        wordFileName: outputs.word_file_name || '项目策划书.docx',
        wordFileSize: outputs.word_file_size || ''
      }

      currentStep.value = 5
    } catch (err) {
      error.value = err.message || '预测请求失败，请稍后重试'
      currentStep.value = 0
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    result,
    currentStep,
    stepLabels,
    submit,
    reset
  }
}
