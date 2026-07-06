/**
 * 策划书解析 composable
 * 封装上传策划书文件 → 解析 → 返回结构化数据的完整流程
 */
import { ref } from 'vue'
import authRequest from '@/utils/authRequest'

export function useProjectPlan() {
  const loading = ref(false)
  const error = ref(null)
  const result = ref(null)
  const uploadFile = ref(null)

  function reset() {
    loading.value = false
    error.value = null
    result.value = null
    uploadFile.value = null
  }

  async function parse(file) {
    if (!file) {
      error.value = '请选择文件'
      return
    }

    // 文件格式校验
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['docx', 'doc'].includes(ext)) {
      error.value = '仅支持 .docx 格式文件'
      return
    }

    // 文件大小校验（20MB）
    if (file.size > 20 * 1024 * 1024) {
      error.value = '文件大小不能超过 20MB'
      return
    }

    loading.value = true
    error.value = null
    result.value = null
    uploadFile.value = file

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await authRequest.post('/planning/upload-and-parse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60000
      })

      if (response.error) {
        error.value = response.error
        return
      }

      result.value = response
    } catch (err) {
      const detail = err.response?.data?.detail
      error.value = typeof detail === 'string' ? detail : (err.message || '解析失败，请稍后重试')
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    result,
    uploadFile,
    parse,
    reset
  }
}
