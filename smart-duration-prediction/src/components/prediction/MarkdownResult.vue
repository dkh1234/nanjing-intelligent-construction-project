<template>
  <div class="prediction-card markdown-result-card">
    <h3 class="prediction-card__title">AI 分析报告</h3>

    <el-empty
      v-if="!content && !loading && !error"
      description="请填写参数后开始工期预测"
      :image-size="120"
    />

    <div v-else-if="loading" class="loading-area">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="error-area">
      <el-result icon="error" :title="error" sub-title="">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重新预测</el-button>
        </template>
      </el-result>
    </div>

    <div
      v-else-if="content"
      class="markdown-body"
      v-html="renderedMarkdown"
    ></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' }
})

defineEmits(['retry'])

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
  typographer: true
})

const renderedMarkdown = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.markdown-result-card {
  min-height: 200px;
}

.loading-area {
  padding: $spacing-md 0;
}

.error-area {
  padding: $spacing-md 0;
}

.markdown-body {
  max-height: calc(100vh - 480px);
  overflow-y: auto;
  padding: $spacing-sm 0;

  :deep(h1) {
    font-size: 22px;
    font-weight: 700;
    color: $color-primary;
    margin: $spacing-lg 0 $spacing-md;
    padding-bottom: $spacing-sm;
    border-bottom: 2px solid $color-primary-light;
  }

  :deep(h2) {
    font-size: 18px;
    font-weight: 600;
    color: $color-text-primary;
    margin: $spacing-md 0 $spacing-sm;
    padding-left: 10px;
    border-left: 3px solid $color-primary;
  }

  :deep(h3) {
    font-size: 16px;
    font-weight: 600;
    color: $color-text-primary;
    margin: $spacing-sm 0 $spacing-xs;
  }

  :deep(p) {
    line-height: 1.8;
    margin: $spacing-xs 0;
    color: $color-text-primary;
  }

  :deep(ul), :deep(ol) {
    padding-left: $spacing-lg;
    margin: $spacing-xs 0;
    line-height: 1.8;
  }

  :deep(li) {
    margin: 4px 0;
  }

  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin: $spacing-sm 0;
    font-size: $font-size-body;

    th {
      background: $color-primary-light;
      color: $color-primary;
      font-weight: 600;
      padding: 10px 12px;
      text-align: left;
      border: 1px solid $color-border;
    }

    td {
      padding: 8px 12px;
      border: 1px solid $color-border;
    }

    tr:nth-child(even) {
      background: $color-bg;
    }
  }

  :deep(code) {
    background: #F0F2F5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    color: #D63384;
  }

  :deep(pre) {
    background: #1D2129;
    padding: $spacing-md;
    border-radius: $radius-card;
    overflow-x: auto;
    margin: $spacing-sm 0;

    code {
      background: none;
      padding: 0;
      color: #E5E6EB;
      font-size: 13px;
    }
  }

  :deep(blockquote) {
    border-left: 4px solid $color-primary;
    background: $color-primary-light;
    padding: $spacing-sm $spacing-md;
    margin: $spacing-sm 0;
    border-radius: 0 $radius-button $radius-button 0;
    color: $color-text-secondary;
  }

  :deep(strong) {
    font-weight: 600;
    color: $color-text-primary;
  }
}
</style>
