<template>
  <div class="prediction-page">
    <AiStepProgress
      :current-step="currentStep"
      :step-labels="stepLabels"
    />

    <div class="two-column">
      <div class="left-column">
        <ProjectInfoCard v-model="formState.projectInfo" />
        <StructureParamsCard v-model="formState.structureParams" />
        <CriticalPathCard v-model="formState.criticalPaths" />

        <div class="button-group">
          <el-button
            class="btn-predict"
            :loading="loading"
            :disabled="loading"
            @click="handleSubmit"
          >
            <el-icon v-if="!loading" :size="20" style="margin-right: 6px">
              <Cpu />
            </el-icon>
            {{ loading ? 'AI分析中...' : '开始工期预测' }}
          </el-button>
          <el-button
            class="btn-reset"
            :disabled="loading"
            @click="handleReset"
          >
            <el-icon :size="18" style="margin-right: 4px">
              <Refresh />
            </el-icon>
            刷新重置
          </el-button>
        </div>
      </div>

      <div class="right-column">
        <MarkdownResult
          :content="result?.markdownContent || ''"
          :loading="loading"
          :error="error"
          @retry="handleSubmit"
        />
        <FileDownloadCard
          :file-name="result?.wordFileName || '项目策划书.docx'"
          :file-size="result?.wordFileSize || ''"
          :download-url="result?.wordFileUrl || ''"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { Cpu, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import AiStepProgress from '@/components/prediction/AiStepProgress.vue'
import ProjectInfoCard from '@/components/prediction/ProjectInfoCard.vue'
import StructureParamsCard from '@/components/prediction/StructureParamsCard.vue'
import CriticalPathCard from '@/components/prediction/CriticalPathCard.vue'
import MarkdownResult from '@/components/prediction/MarkdownResult.vue'
import FileDownloadCard from '@/components/prediction/FileDownloadCard.vue'

import { useDifyWorkflow } from '@/composables/useDifyWorkflow'

const { loading, error, result, currentStep, stepLabels, submit, reset } = useDifyWorkflow()

const formState = reactive({
  projectInfo: {
    projectName: '',
    contractFile: null
  },
  structureParams: {
    heater: '',
    length: null,
    width: null,
    concreteHeight: null,
    totalHeight: null,
    foundation: '',
    concreteLayer: null,
    towerLayer: null
  },
  criticalPaths: [
    '土建施工',
    '钢结构安装',
    '设备安装',
    '电气仪表施工',
    '单机试运转与联动调试'
  ]
})

async function handleSubmit() {
  if (!formState.projectInfo.projectName.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  if (!formState.projectInfo.contractFile) {
    ElMessage.warning('请上传合同文件')
    return
  }
  if (!formState.structureParams.heater) {
    ElMessage.warning('请选择预热器类型')
    return
  }
  if (!formState.structureParams.foundation) {
    ElMessage.warning('请选择基础形式')
    return
  }
  if (!formState.structureParams.length || !formState.structureParams.width) {
    ElMessage.warning('请输入完整结构参数')
    return
  }
  if (formState.criticalPaths.some(p => !p.trim())) {
    ElMessage.warning('请填写完整的关键路径')
    return
  }

  try {
    await submit({
      projectName: formState.projectInfo.projectName,
      contractFile: formState.projectInfo.contractFile,
      heater: formState.structureParams.heater,
      length: formState.structureParams.length,
      width: formState.structureParams.width,
      concreteHeight: formState.structureParams.concreteHeight,
      totalHeight: formState.structureParams.totalHeight,
      foundation: formState.structureParams.foundation,
      concreteLayer: formState.structureParams.concreteLayer,
      towerLayer: formState.structureParams.towerLayer,
      criticalPaths: formState.criticalPaths
    })
  } catch (err) {
    // error handled in composable
  }
}

function handleReset() {
  // 清空结果和错误状态
  reset()

  // 重置表单数据到初始值
  formState.projectInfo.projectName = ''
  formState.projectInfo.contractFile = null
  formState.structureParams.heater = ''
  formState.structureParams.length = null
  formState.structureParams.width = null
  formState.structureParams.concreteHeight = null
  formState.structureParams.totalHeight = null
  formState.structureParams.foundation = ''
  formState.structureParams.concreteLayer = null
  formState.structureParams.towerLayer = null
  formState.criticalPaths = [
    '土建施工',
    '钢结构安装',
    '设备安装',
    '电气仪表施工',
    '单机试运转与联动调试'
  ]
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.prediction-page {
  max-width: 100%;
}

.button-group {
  display: flex;
  gap: $spacing-md;
  margin-top: $spacing-md;
}

.btn-predict {
  flex: 1;
}

.btn-reset {
  flex-shrink: 0;
}

.two-column {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-lg;
  align-items: start;

  @media (max-width: 1200px) {
    grid-template-columns: 1fr;
  }
}

.left-column {
  min-width: 0;
}

.right-column {
  min-width: 0;
}
</style>
