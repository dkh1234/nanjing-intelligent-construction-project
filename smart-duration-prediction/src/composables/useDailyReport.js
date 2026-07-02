/**
 * 日报预测 composable
 * 对接后端: POST /api/daily/upload-and-predict
 */
import { ref } from 'vue'
import authRequest from '@/utils/authRequest'

// ---- 状态 ----
const parsedData = ref(null)
const prediction = ref(null)
const parsing = ref(false)
const predicting = ref(false)
const errorMsg = ref(null)

// ---- 方法 ----

/** 上传文件 → 解析 + 预测（后端一次完成） */
async function uploadAndParse(file, nWeeks = 1) {
  parsing.value = true
  predicting.value = false
  parsedData.value = null
  prediction.value = null
  errorMsg.value = null

  try {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('predict_weeks', nWeeks)

    const res = await authRequest.post('/daily/upload-and-predict', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res.error) {
      errorMsg.value = res.error
      return
    }

    if (res.parsed) {
      parsedData.value = {
        ...res.parsed,
        week_count: res.parsed.week_count ?? res.parsed.weeks?.length ?? 0
      }
    }

    if (res.prediction) {
      prediction.value = res.prediction
    }
  } catch (err) {
    errorMsg.value = err.response?.data?.error || err.message || '请求失败，请检查后端服务是否启动'
  } finally {
    parsing.value = false
  }
}

/** 基于已解析数据重新预测（切换预测周数时） */
async function predictFromParsed(nWeeks = 1) {
  predicting.value = true
  prediction.value = null

  try {
    const res = await authRequest.post('/daily/predict-from-data', {
      weeks: parsedData.value.weeks,
      predict_weeks: nWeeks
    })
    prediction.value = res
  } catch {
    console.warn('后端 predict-from-data 不可用，需重新上传')
  } finally {
    predicting.value = false
  }
}

/** 重置 */
function resetAll() {
  parsedData.value = null
  prediction.value = null
  errorMsg.value = null
}

export function useDailyReport() {
  return {
    parsedData, prediction, parsing, predicting, errorMsg,
    uploadAndParse, predictFromParsed, resetAll
  }
}
