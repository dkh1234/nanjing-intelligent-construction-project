import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import authRequest from '@/utils/authRequest'

/**
 * 工期预警业务逻辑 composable
 *
 * 管理：文件上传状态、API调用、分析进度模拟、结果数据
 */
export function useDurationWarning() {
  // ========== 文件 ==========
  const planFile = ref(null)
  const reportFile = ref(null)

  // ========== 页面状态 ==========
  const pageState = ref('empty') // empty | loading | error | result
  const submitting = ref(false)
  const errorMsg = ref('')

  // ========== 分析步骤 ==========
  const analysisStep = ref(0)
  const analysisSteps = [
    '上传文件',
    '提取文本',
    'AI解析策划书',
    'AI解析周报',
    '预警引擎计算',
    '生成报告'
  ]

  // ========== 结果数据 ==========
  const result = reactive({
    risk_level: '',
    planned_completion_date: '',
    predicted_completion_date: '',
    delay_days: 0,
    analysis_summary: '',
    // 完整报告
    full_report: null
  })

  // ========== 文件操作方法 ==========
  function setPlanFile(file) { planFile.value = file }
  function setReportFile(file) { reportFile.value = file }
  function removePlanFile() { planFile.value = null }
  function removeReportFile() { reportFile.value = null }

  function beforeUpload(file) {
    const isValid = /\.(pdf|doc|docx|json)$/i.test(file.name)
    if (!isValid) { ElMessage.error('仅支持 .pdf .doc .docx .json 格式文件'); return false }
    if (file.size / 1024 / 1024 > 50) { ElMessage.error('文件大小不能超过50MB'); return false }
    return false
  }

  // ========== 模拟分析步骤推进 ==========
  let stepTimer = null

  function startStepSimulation() {
    analysisStep.value = 0
    let step = 0

    stepTimer = setInterval(() => {
      // 随机等待 3-8 秒推进一步
      if (step < analysisSteps.length - 1) {
        step++
        analysisStep.value = step
      }
    }, 3000 + Math.random() * 5000)
  }

  function stopStepSimulation() {
    if (stepTimer) {
      clearInterval(stepTimer)
      stepTimer = null
    }
    // 全部完成
    analysisStep.value = analysisSteps.length - 1
  }

  // ========== 核心 API 调用 ==========
  async function submitAnalysis() {
    if (!planFile.value) { ElMessage.warning('请上传项目策划书'); return }
    if (!reportFile.value) { ElMessage.warning('请上传项目周报'); return }

    submitting.value = true
    pageState.value = 'loading'
    errorMsg.value = ''

    // 开始模拟步骤
    startStepSimulation()

    try {
      const formData = new FormData()
      formData.append('plan_file', planFile.value.raw)
      formData.append('report_file', reportFile.value.raw)

      const res = await authRequest.post('/duration-warning', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      })

      const data = res?.data || res || {}

      result.risk_level = data.risk_level || ''
      result.planned_completion_date = data.planned_completion_date || ''
      result.predicted_completion_date = data.predicted_completion_date || ''
      result.delay_days = data.delay_days ?? 0
      result.analysis_summary = data.analysis_summary || ''
      result.full_report = data.full_report || null

      pageState.value = 'result'
      ElMessage.success('工期预警分析完成')
    } catch (err) {
      console.error('Duration Warning API Error:', err)
      errorMsg.value = err.response?.data?.detail || err.response?.data?.message || err.message || '分析失败，请稍后重试'
      pageState.value = 'error'
    } finally {
      stopStepSimulation()
      submitting.value = false
    }
  }

  // ========== 重置 ==========
  function resetAll() {
    stopStepSimulation()
    pageState.value = 'empty'
    planFile.value = null
    reportFile.value = null
    analysisStep.value = 0
  }

  // ========== 工具函数：解析里程碑展示状态 ==========
  /**
   * 解析后端返回的 reason 字段，返回前端展示所需的状态信息
   *
   * @param {Object} item - 里程碑预警项 { milestone_name, target_date, alert_level, delay_days, reason }
   * @returns {Object} { bg: 'green'|'yellow'|'red', actualDate: string|null }
   */
  function parseMilestoneDisplay(item) {
    const { reason, delay_days } = item

    // 提取 reason 中第一个日期作为实际完成日期
    const dateMatch = reason.match(/(\d{4}-\d{2}-\d{2})/g)
    const actualDate = dateMatch ? dateMatch[0] : null

    // 判断是否已完成（含"完成"但不含"未完成"）
    const isCompleted = /完成/.test(reason) && !/未完成/.test(reason)
    const isCompletedLate = isCompleted && /延迟/.test(reason)
    const isCompletedOnTime = isCompleted && !isCompletedLate

    // 判断是否尚未完成
    const isNotCompleted = /进行中|尚未开始|缺少状态/.test(reason)

    const isOverdue = delay_days > 0

    if (isCompletedOnTime) {
      return { bg: 'green', actualDate: null }
    }
    if (isCompletedLate) {
      return { bg: 'green', actualDate }
    }
    if (isNotCompleted && isOverdue && delay_days < 30) {
      return { bg: 'yellow', actualDate: null }
    }
    if (isNotCompleted && isOverdue && delay_days >= 30) {
      return { bg: 'red', actualDate: null }
    }
    // 默认：未逾期、开工前节点、目标日期未到 → 绿色
    return { bg: 'green', actualDate: null }
  }

  return {
    // 文件
    planFile,
    reportFile,
    setPlanFile,
    setReportFile,
    removePlanFile,
    removeReportFile,
    beforeUpload,
    // 状态
    pageState,
    submitting,
    errorMsg,
    // 步骤
    analysisStep,
    analysisSteps,
    // 结果
    result,
    // 方法
    submitAnalysis,
    resetAll,
    // 工具
    parseMilestoneDisplay
  }
}
