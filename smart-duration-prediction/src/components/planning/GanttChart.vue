<template>
  <div ref="chartRef" class="gantt-chart"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  milestones: { type: Array, default: () => [] },
  project: { type: Object, default: () => ({}) }
})

const chartRef = ref(null)
let chartInstance = null

// 类别颜色映射
const categoryColors = {
  '设计': '#1677FF',
  '采购': '#FF7D00',
  '施工': '#00B42A',
  '调试': '#F53F3F',
  '项目节点': '#86909C'
}

function getColor(category) {
  return categoryColors[category] || '#86909C'
}

function buildChartOption() {
  const milestones = [...(props.milestones || [])]

  if (!milestones.length) {
    return null
  }

  // 按日期排序
  const sorted = milestones
    .filter(m => m.date && /^\d{4}-\d{2}-\d{2}$/.test(m.date))
    .sort((a, b) => a.date.localeCompare(b.date))

  if (!sorted.length) return null

  // 时间范围
  const minDate = sorted[0].date
  const maxDate = sorted[sorted.length - 1].date

  // 计算相邻里程碑之间的时间跨度
  // 使用所有里程碑（不仅是有日期的），从 project start 开始
  const allDates = []
  for (const m of sorted) {
    if (m.date && /^\d{4}-\d{2}-\d{2}$/.test(m.date)) {
      allDates.push(m.date)
    }
  }

  // Y 轴数据（倒序，从上到下按时间）
  const yData = sorted.map(m => m.name)

  // 为每个里程碑创建数据：
  // 起始时间 = 前一个里程碑的日期（或项目开始日期）
  // 结束时间 = 当前里程碑日期
  const seriesData = []
  for (let i = 0; i < sorted.length; i++) {
    const startDate = i === 0 ? (props.project?.start_date || minDate) : sorted[i - 1].date
    const endDate = sorted[i].date
    seriesData.push({
      name: sorted[i].name,
      value: [startDate, endDate],
      itemStyle: {
        color: getColor(sorted[i].category),
        borderRadius: 4,
      },
      _criteria: sorted[i].criteria,
      _category: sorted[i].category,
      _date: sorted[i].date,
    })
  }

  return {
    tooltip: {
      trigger: 'item',
      formatter(params) {
        if (params.data?._name) {
          // category markLine tooltip
          return `<b>${params.data._name}</b><br/>类别: ${params.data._category}`
        }
        const d = params.data || {}
        const name = d.name || ''
        const date = d._date || ''
        const criteria = d._criteria || ''
        const category = d._category || ''
        let html = `<b>${name}</b><br/>`
        html += `完成时间: ${date}<br/>`
        html += `类别: ${category}`
        if (criteria) {
          html += `<br/>完成标准: ${criteria}`
        }
        return html
      }
    },
    grid: {
      left: 200,
      right: 60,
      top: 30,
      bottom: 60
    },
    xAxis: {
      type: 'time',
      min: minDate,
      max: maxDate,
      axisLabel: {
        formatter: '{yyyy}-{MM}-{dd}',
        rotate: 30,
        fontSize: 11,
      },
      splitLine: {
        show: true,
        lineStyle: { type: 'dashed', color: '#E5E6EB' }
      }
    },
    yAxis: {
      type: 'category',
      data: yData,
      inverse: true,
      axisLabel: {
        width: 190,
        overflow: 'truncate',
        fontSize: 12,
        color: '#1D2129'
      },
      axisTick: { show: false },
    },
    series: [
      {
        name: '里程碑',
        type: 'bar',
        data: seriesData,
        barWidth: 16,
        barGap: '0%',
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0,0,0,0.2)',
          }
        },
        encode: {
          x: [0, 1],  // [start, end]
          y: 2,       // 通过 data 的下标隐式映射到 yAxis
        },
        // 用自定义 renderItem 或者用两个坐标值编码
        coordinateSystem: 'cartesian2d',
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { type: 'dashed', color: '#C9CDD4', width: 1 },
          data: getCategoryMarkLines(sorted)
        }
      }
    ],
    dataZoom: [
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 24,
        bottom: 10,
      }
    ]
  }
}

function getCategoryMarkLines(sorted) {
  // 为每个类别组添加分隔线
  const lines = []
  const seen = new Set()
  for (const m of sorted) {
    if (!seen.has(m.category)) {
      seen.add(m.category)
      lines.push({
        yAxis: m.name,
        label: {
          show: true,
          position: 'start',
          formatter: m.category,
          color: getColor(m.category),
          fontWeight: 'bold',
          fontSize: 13,
          distance: [-190, -14]
        },
        lineStyle: { color: getColor(m.category), width: 2, type: 'solid' },
        _name: m.name,
        _category: m.category
      })
    }
  }
  return lines
}

function renderChart() {
  if (!chartRef.value) return

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }

  const option = buildChartOption()
  if (option) {
    chartInstance.setOption(option, true)
  } else {
    chartInstance.clear()
    chartInstance.setOption({
      title: {
        text: '暂无里程碑数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#C9CDD4', fontSize: 14, fontWeight: 'normal' }
      }
    })
  }
}

function handleResize() {
  chartInstance?.resize()
}

onMounted(() => {
  nextTick(renderChart)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})

watch(() => props.milestones, () => {
  nextTick(renderChart)
}, { deep: true })
</script>

<style lang="scss" scoped>
.gantt-chart {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
</style>
