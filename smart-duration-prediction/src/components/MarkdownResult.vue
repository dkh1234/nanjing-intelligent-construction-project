<template>
  <div class="markdown-block">
    <div class="markdown-header">
      <span class="markdown-title">
        <el-icon :size="16" color="#1677FF"><Document /></el-icon>
        Markdown分析结果
      </span>
      <el-button size="small" text @click="copyContent">
        <el-icon :size="14"><CopyDocument /></el-icon>
        复制
      </el-button>
    </div>

    <div class="markdown-body" ref="bodyRef">
      <el-empty v-if="!content && !loading" description="等待AI分析完成..." :image-size="80" />
      <div v-else-if="loading" class="loading-skel">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else class="rendered" v-html="rendered" />
    </div>

    <!-- 策划书下载 -->
    <div v-if="content && !loading" class="download-section">
      <span class="download-label">策划书文件下载</span>
      <el-button type="primary" plain size="default" @click="handleDownload">
        <el-icon :size="14"><Download /></el-icon>
        下载Word文件
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Document, CopyDocument, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'

const props = defineProps({
  content: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  downloadUrl: { type: String, default: '' },
  projectName: { type: String, default: '项目策划书' }
})

const bodyRef = ref(null)

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const rendered = computed(() => props.content ? md.render(props.content) : '')

function handleDownload() {
  if (!props.content) return

  // 将 markdown 第一个 h1 标题替换为项目名称
  let content = props.content
  const firstH1 = content.match(/^# .+/m)
  if (firstH1) {
    content = content.replace(firstH1[0], `# ${props.projectName}`)
  }

  const htmlBody = md.render(content)

  const wordHtml = `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
      xmlns:w="urn:schemas-microsoft-com:office:word"
      xmlns="http://www.w3.org/TR/REC-html40">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <!--[if gte mso 9]><xml><w:WordDocument><w:View>Print</w:View></w:WordDocument></xml><![endif]-->
  <style>
    body { font-family: "PingFang SC", "Microsoft YaHei", sans-serif; font-size: 14px; line-height: 1.8; color: #333; padding: 40px; }
    h1 { font-size: 22px; color: #1677FF; border-bottom: 2px solid #e6f4ff; padding-bottom: 8px; }
    h2 { font-size: 16px; border-left: 3px solid #1677FF; padding-left: 10px; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin: 10px 0; }
    th { background: #e6f4ff; padding: 6px 10px; border: 1px solid #ccc; }
    td { padding: 6px 10px; border: 1px solid #ccc; }
  </style>
</head>
<body>${htmlBody}</body>
</html>`

  const blob = new Blob(['﻿' + wordHtml], { type: 'application/msword;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `${props.projectName}.doc`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
  ElMessage.success('Word文件下载成功')
}

async function copyContent() {
  if (!props.content) return
  try {
    await navigator.clipboard.writeText(props.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style lang="scss" scoped>
.markdown-block { margin-bottom: 20px; }

.markdown-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.markdown-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.markdown-body {
  background: #f7f8fa;
  border-radius: 12px;
  padding: 18px;
  height: 480px;
  overflow-y: auto;

  &::-webkit-scrollbar { width: 5px; }
  &::-webkit-scrollbar-thumb { background: #c9cdd4; border-radius: 3px; }

  :deep(h1) { font-size: 20px; font-weight: 700; color: #1677FF; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 2px solid #e6f4ff; }
  :deep(h2) { font-size: 16px; font-weight: 600; color: #1d2129; margin: 20px 0 10px; padding-left: 8px; border-left: 3px solid #1677FF; }
  :deep(h3) { font-size: 15px; font-weight: 600; color: #1d2129; margin: 14px 0 8px; }
  :deep(p) { line-height: 1.7; color: #4e5969; margin: 6px 0; }
  :deep(ul), :deep(ol) { padding-left: 20px; color: #4e5969; line-height: 1.8; }
  :deep(table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px;
    th { background: #e6f4ff; color: #1677FF; font-weight: 600; padding: 8px 10px; text-align: left; border: 1px solid #e5e6eb; }
    td { padding: 7px 10px; border: 1px solid #e5e6eb; color: #4e5969; }
  }
  :deep(code) { background: #e8eaed; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
  :deep(pre) { background: #1d2129; padding: 14px; border-radius: 8px; overflow-x: auto;
    code { background: none; color: #e5e6eb; padding: 0; }
  }
  :deep(strong) { font-weight: 600; color: #1d2129; }
  :deep(blockquote) { border-left: 3px solid #1677FF; background: #e6f4ff; padding: 8px 14px; margin: 8px 0; border-radius: 0 6px 6px 0; color: #4e5969; }
}

.loading-skel { padding: 8px 0; }

.rendered { font-size: 14px; line-height: 1.6; }

.download-section {
  margin-top: 14px;
  background: #f7f8fa;
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.download-label {
  font-size: 13px;
  font-weight: 600;
  color: #4e5969;
}
</style>
