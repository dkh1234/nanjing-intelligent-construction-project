<template>
  <div class="critical-path">
    <div class="section-header">
      <el-icon :size="18" color="#1677FF"><Connection /></el-icon>
      <span>关键路径工序预警</span>
      <el-tag v-if="summary.red > 0" type="danger" size="small" effect="plain">
        {{ summary.red }}项红色
      </el-tag>
      <el-tag v-if="summary.yellow > 0" type="warning" size="small" effect="plain">
        {{ summary.yellow }}项黄色
      </el-tag>
      <el-tag v-if="summary.green > 0" type="success" size="small" effect="plain">
        {{ summary.green }}项正常
      </el-tag>
    </div>

    <div v-if="!alerts.length" class="empty-hint">
      <el-empty description="暂无关键路径预警数据" :image-size="60" />
    </div>

    <div v-else>
      <!-- 按车间分组 -->
      <div v-for="(group, wsName) in groupedAlerts" :key="wsName" class="workshop-group">
        <div class="workshop-title">
          <el-icon :size="16" color="#1677FF"><Location /></el-icon>
          <span>{{ wsName }}</span>
        </div>

        <div class="process-list">
          <div
            v-for="(item, idx) in group"
            :key="idx"
            class="process-item"
            :class="`alert-${getLevelClass(item.alert_level)}`"
          >
            <div class="process-top">
              <span class="process-name">{{ item.process_name }}</span>
              <el-tag
                :type="getAlertTagType(item.alert_level)"
                size="small"
                effect="plain"
              >
                {{ item.alert_level }}
              </el-tag>
            </div>

            <div class="process-info">
              <div class="p-row">
                <span class="p-label">目标日期</span>
                <span class="p-value">{{ formatDate(item.target_date) }}</span>
              </div>
              <div v-if="item.actual_date" class="p-row">
                <span class="p-label">实际日期</span>
                <span class="p-value date-highlight">{{ formatDate(item.actual_date) }}</span>
              </div>
              <div class="p-row">
                <span class="p-label">偏差</span>
                <span
                  class="p-value"
                  :class="item.delay_days > 0 ? 'text-red' : item.delay_days < 0 ? 'text-green' : ''"
                >
                  {{ item.delay_days > 0 ? `延迟${item.delay_days}天` : item.delay_days < 0 ? `提前${Math.abs(item.delay_days)}天` : '按期' }}
                </span>
              </div>
            </div>

            <div class="process-reason">
              <el-icon :size="13"><InfoFilled /></el-icon>
              <span>{{ item.reason }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Connection, Location, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  alerts: { type: Array, default: () => [] }
})

/** 按车间分组 */
const groupedAlerts = computed(() => {
  const groups = {}
  for (const item of props.alerts) {
    const ws = item.workshop || '其他'
    if (!groups[ws]) groups[ws] = []
    groups[ws].push(item)
  }
  return groups
})

/** 汇总统计 */
const summary = computed(() => {
  let red = 0, yellow = 0, green = 0
  for (const item of props.alerts) {
    if (item.alert_level === '红色') red++
    else if (item.alert_level === '黄色') yellow++
    else green++
  }
  return { red, yellow, green }
})

function getLevelClass(level) {
  if (level === '红色') return 'red'
  if (level === '黄色') return 'yellow'
  return 'green'
}

function getAlertTagType(level) {
  if (level === '红色') return 'danger'
  if (level === '黄色') return 'warning'
  return 'success'
}

function formatDate(dateStr) {
  if (!dateStr) return '--'
  return String(dateStr).replace(/T.*/, '')
}
</script>

<style lang="scss" scoped>
.critical-path {
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

.empty-hint {
  padding: 20px 0;
}

/* === 车间分组 === */
.workshop-group {
  margin-bottom: 16px;
}

.workshop-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #1677FF;
  margin-bottom: 8px;
  padding-left: 4px;
}

.process-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.process-item {
  padding: 12px 16px;
  border-radius: 10px;
  border-left: 3px solid transparent;

  &.alert-green {
    background: #f0fdf4;
    border-left-color: #00B42A;
  }
  &.alert-yellow {
    background: #fff7ed;
    border-left-color: #FF7D00;
  }
  &.alert-red {
    background: #fef2f2;
    border-left-color: #F53F3F;
  }
}

.process-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.process-name {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.process-info {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
  margin-bottom: 4px;
}

.p-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.p-label {
  font-size: 12px;
  color: #86909c;
}

.p-value {
  font-size: 13px;
  font-weight: 500;
  color: #4e5969;

  &.date-highlight {
    color: #F53F3F;
    font-weight: 600;
  }
  &.text-red { color: #F53F3F; }
  &.text-green { color: #00B42A; }
}

.process-reason {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  color: #86909c;
  line-height: 1.5;
  margin-top: 4px;

  .el-icon {
    margin-top: 2px;
    flex-shrink: 0;
  }
}
</style>
