<template>
  <div class="milestone-timeline">
    <div class="section-header">
      <el-icon :size="18" color="#1677FF"><Flag /></el-icon>
      <span>里程碑节点状态</span>
      <div class="legend">
        <span class="legend-item"><span class="dot green"></span>正常/提前完成</span>
        <span class="legend-item"><span class="dot yellow"></span>延期&lt;30天</span>
        <span class="legend-item"><span class="dot red"></span>延期≥30天</span>
      </div>
    </div>

    <div v-if="!milestones.length" class="empty-hint">
      <el-empty description="暂无里程碑数据" :image-size="60" />
    </div>

    <div class="timeline-track">
      <div
        v-for="(item, idx) in milestones"
        :key="idx"
        class="timeline-node"
      >
        <!-- 时间轴连线 -->
        <div class="tl-rail">
          <div class="tl-dot" :class="getDisplay(item).bg"></div>
          <div v-if="idx < milestones.length - 1" class="tl-line" :class="getDisplay(item).bg"></div>
        </div>

        <!-- 节点卡片 -->
        <div class="tl-card" :class="`card-${getDisplay(item).bg}`">
          <div class="card-top">
            <span class="node-name">{{ item.milestone_name }}</span>
            <el-tag
              :type="getTagType(getDisplay(item).bg)"
              size="small"
              effect="plain"
            >
              {{ getStatusLabel(item) }}
            </el-tag>
          </div>

          <div class="card-info">
            <div class="info-row">
              <span class="info-label">目标日期</span>
              <span class="info-value">{{ formatDate(item.target_date) }}</span>
            </div>

            <!-- 已完成且有实际日期 -->
            <div v-if="getDisplay(item).actualDate" class="info-row">
              <span class="info-label">实际完成</span>
              <span class="info-value date-red">{{ getDisplay(item).actualDate }}</span>
            </div>

            <!-- 延迟天数 -->
            <div v-if="item.delay_days !== 0" class="info-row">
              <span class="info-label">偏差</span>
              <span
                class="info-value"
                :class="item.delay_days > 0 ? 'text-red' : 'text-green'"
              >
                {{ item.delay_days > 0 ? `延迟 ${item.delay_days} 天` : `提前 ${Math.abs(item.delay_days)} 天` }}
              </span>
            </div>
          </div>

          <!-- 原因说明 -->
          <div class="card-reason">
            <el-icon :size="13"><InfoFilled /></el-icon>
            <span>{{ item.reason }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Flag, InfoFilled } from '@element-plus/icons-vue'

const props = defineProps({
  milestones: { type: Array, default: () => [] }
})

/**
 * 解析 reason 字段，返回里程碑展示状态
 *
 * 展示规则：
 * - 绿灯（绿色底纹）：提前/按期完成的里程碑
 * - 绿灯+红色字体：延迟已完成的里程碑，实际完成日期用红色字体
 * - 黄灯（黄色底纹）：延迟尚未完成的里程碑，延期<30天
 * - 红灯（红色底纹）：延迟尚未完成的里程碑，延期≥30天
 */
function getDisplay(item) {
  const { reason, delay_days } = item

  // 提取 reason 中第一个日期作为实际完成日期
  const dateMatch = reason.match(/(\d{4}-\d{2}-\d{2})/g)
  const actualDate = dateMatch ? dateMatch[0] : null

  // 判断是否已完成（含"完成"但不含"未完成"）
  const isCompleted = /完成/.test(reason) && !/未完成/.test(reason)
  // 延迟完成
  const isCompletedLate = isCompleted && /延迟/.test(reason)
  // 提前/按期完成
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
  // 默认：未逾期、开工前节点、目标日期未到等 → 绿色
  return { bg: 'green', actualDate: null }
}

function getStatusLabel(item) {
  const display = getDisplay(item)
  if (display.bg === 'green' && display.actualDate) return '延迟完成'
  if (display.bg === 'green') return '正常'
  if (display.bg === 'yellow') return '黄色预警'
  if (display.bg === 'red') return '红色预警'
  return '正常'
}

function getTagType(bg) {
  if (bg === 'green') return 'success'
  if (bg === 'yellow') return 'warning'
  if (bg === 'red') return 'danger'
  return ''
}

function formatDate(dateStr) {
  if (!dateStr) return '--'
  const d = String(dateStr).replace(/T.*/, '')
  return d
}
</script>

<style lang="scss" scoped>
.milestone-timeline {
  padding: 4px 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: #1d2129;
  margin-bottom: 4px;
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

/* === 时间轴 === */
.timeline-track {
  padding: 8px 0;
}

.timeline-node {
  display: flex;
  gap: 14px;
}

.tl-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 20px;
  flex-shrink: 0;
  padding-top: 14px;
}

.tl-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px rgba(0,0,0,0.1);

  &.green { background: #00B42A; }
  &.yellow { background: #FF7D00; }
  &.red { background: #F53F3F; }
}

.tl-line {
  width: 2px;
  flex: 1;
  min-height: 20px;
  margin: 4px 0;
  opacity: 0.3;

  &.green { background: #00B42A; }
  &.yellow { background: #FF7D00; }
  &.red { background: #e5e6eb; }
}

/* === 节点卡片 === */
.tl-card {
  flex: 1;
  padding: 12px 16px;
  border-radius: 10px;
  margin-bottom: 12px;
  border-left: 3px solid transparent;
  transition: box-shadow .2s;

  &:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }

  &.card-green {
    background: #f0fdf4;
    border-left-color: #00B42A;
  }
  &.card-yellow {
    background: #fff7ed;
    border-left-color: #FF7D00;
  }
  &.card-red {
    background: #fef2f2;
    border-left-color: #F53F3F;
  }
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.node-name {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
}

.card-info {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 20px;
  margin-bottom: 6px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.info-label {
  font-size: 12px;
  color: #86909c;
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  color: #4e5969;

  &.date-red {
    color: #F53F3F;
    font-weight: 700;
  }
  &.text-red {
    color: #F53F3F;
  }
  &.text-green {
    color: #00B42A;
  }
}

.card-reason {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  color: #86909c;
  line-height: 1.5;

  .el-icon {
    margin-top: 2px;
    flex-shrink: 0;
    color: #86909c;
  }
}
</style>
