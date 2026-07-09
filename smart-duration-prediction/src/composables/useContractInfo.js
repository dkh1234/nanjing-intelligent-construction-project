/**
 * 合同信息提取 composable
 */
import { ref } from 'vue'
import authRequest from '@/utils/authRequest'

const extractedFields = ref(null)
const extracting = ref(false)
const errorMsg = ref(null)
const fileInfo = ref(null)
const historyList = ref([])
const loadingHistory = ref(false)
const selectedHistoryId = ref(null)
const searchKeyword = ref('')

async function uploadAndExtract(file) {
  extracting.value = true
  extractedFields.value = null
  errorMsg.value = null
  fileInfo.value = null

  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('use_ai', false)

    const res = await authRequest.post('/contract/extract', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })

    if (res.error) {
      errorMsg.value = res.error
      return
    }

    fileInfo.value = { name: res.file_name, size: res.file_size, textLength: res.text_length }

    if (res.fields) {
      extractedFields.value = res.fields
    }

    await fetchHistory()
  } catch (err) {
    errorMsg.value = err.response?.data?.error || err.message || '请求失败'
  } finally {
    extracting.value = false
  }
}

async function fetchHistory(keyword = '') {
  loadingHistory.value = true
  try {
    const params = keyword ? { keyword } : {}
    const res = await authRequest.get('/contract/history', { params })
    historyList.value = res.items || []
  } catch {
    // 静默
  } finally {
    loadingHistory.value = false
  }
}

async function loadRecord(id) {
  selectedHistoryId.value = id
  extracting.value = true
  try {
    const res = await authRequest.get(`/contract/history/${id}`)
    if (res.error) { errorMsg.value = res.error; return }
    extractedFields.value = res.fields || null
    fileInfo.value = { name: res.filename, size: res.file_size, textLength: res.text_length }
  } catch {
    errorMsg.value = '加载历史记录失败'
  } finally {
    extracting.value = false
  }
}

async function deleteRecord(id) {
  try {
    await authRequest.delete(`/contract/history/${id}`)
    if (selectedHistoryId.value === id) {
      selectedHistoryId.value = null
      extractedFields.value = null
      fileInfo.value = null
    }
    await fetchHistory(searchKeyword.value)
  } catch {
    // 静默
  }
}

function startNewUpload() {
  selectedHistoryId.value = null
  extractedFields.value = null
  errorMsg.value = null
  fileInfo.value = null
}

function resetAll() {
  extractedFields.value = null
  errorMsg.value = null
  fileInfo.value = null
  selectedHistoryId.value = null
  searchKeyword.value = ''
}

export function useContractInfo() {
  return {
    extractedFields, extracting, errorMsg, fileInfo,
    historyList, loadingHistory, selectedHistoryId, searchKeyword,
    uploadAndExtract, fetchHistory, loadRecord, deleteRecord, startNewUpload, resetAll
  }
}
