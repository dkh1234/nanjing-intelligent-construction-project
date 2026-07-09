<template>
  <div class="progress-curve">
    <div class="section-header">
      <el-icon :size="18" color="#1677FF"><TrendCharts /></el-icon>
      <span>月度进度曲线跟踪</span>
      <div class="legend">
        <span class="legend-item"><span class="dot green"></span>实际≥计划</span>
        <span class="legend-item"><span class="dot yellow"></span>偏差0~10%</span>
        <span class="legend-item"><span class="dot red"></span>偏差&gt;10%</span>
      </div>
    </div>

    <div v-if="!curveData.length" class="empty-hint">
      <el-empty description="暂无进度曲线数据" :image-size="60" />
    </div>

    <div v-else class="curve-table-wrap">
      <el-table
        :data="curveData"
        style="width: 100%"
        :header-cell-style="{ background: '#f5f7fb', color: '#4e5969', fontWeight: 600, fontSize: '13px' }"
        size="small"
        stripe
      >
        <el-table-column prop="month_label" label="月份" width="110" align="center" />
        <el-table-column label="计划进度" align="center" width="120">
          <template #default="{ row }">
            <span class="pct-value">{{ row.planned_pct.toFixed(1) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="实际进度" align="center" width="120">
          <template #default="{ row }">
            <span class="pct-value" :class="row.actual_pct >= row.planned_pct ? 'text-green' : 'text-red'">
              {{ row.actual_pct.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="偏差" align="center" width="110">
          <template #default="{ row }">
            <span
              class="deviation"
              :class="row.deviation_pct >= 0 ? 'positive' : 'negative'"
            >
              {{ row.deviation_pct >= 0 ? '+' : '' }}{{ row.deviation_pct.toFixed(1) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="状态" align="center" width="100">
          <template #default="{ row }">
            <el-tag
              :type="getAlertTagType(row.alert_level)"
              size="small"
              effect="plain"
            >
              {{ row.alert_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="说明" min-width="200">
          <template #default="{ row }">
            <span class="reason-text">{{ row.reason }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { TrendCharts } from '@element-plus/icons-vue'

defineProps({
  curveData: { type: Array, default: () => [] }
})

function getAlertTagType(level) {
  if (level === '绿色') return 'success'
  if (level === '黄色') return 'warning'
  if (level === '红色') return 'danger'
  return ''
}
</script>

<style lang="scss" scoped>
.progress-curve {
  padding: 4px 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.legend {
  display: flex;
  gap: 14px;
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: #86909c;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
  &.green { background: #00B42A; }
  &.yellow { background: #FF7D00; }
  &.red { background: #F53F3F; }
}

.empty-hint {
  padding: 20px 0;
}

.curve-table-wrap {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #e5e6eb;
}

.pct-value {
  font-weight: 600;
  font-size: 14px;
  &.text-green { color: #00B42A; }
  &.text-red { color: #F53F3F; }
}

.deviation {
  font-weight: 700;
  font-size: 14px;
  &.positive { color: #00B42A; }
  &.negative { color: #F53F3F; }
}

.reason-text {
  font-size: 12px;
  color: #86909c;
  line-height: 1.5;
}
</style>
