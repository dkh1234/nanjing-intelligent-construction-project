<template>
  <div class="contract-page">
    <!-- ==================== 上半区：上传 + 结果 ==================== -->
    <div class="top-area">
      <!-- 左：上传 -->
      <div class="upload-card">
        <div class="section-label"><el-icon :size="15" color="#1677ff"><UploadFilled /></el-icon><span>上传合同文件</span></div>
        <div class="upload-drop" @click="triggerUpload" @dragover.prevent @drop.prevent="onDrop">
          <div v-if="extracting" class="upload-state"><el-icon :size="28" color="#1677ff" class="spinner"><Loading /></el-icon><span class="upload-text">提取中...</span></div>
          <div v-else-if="fileInfo" class="upload-state done">
            <el-icon :size="22" color="#52c41a"><Check /></el-icon>
            <span class="ufile">{{ fileInfo.name }}</span>
          </div>
          <div v-else class="upload-state"><el-icon :size="28" color="#b0b7c3"><UploadFilled /></el-icon><span class="upload-text">拖拽或点击上传文件</span><span class="upload-hint">PDF / Word / Excel / TXT · 最大 100MB</span></div>
          <input ref="fileInput" type="file" accept=".pdf,.docx,.doc,.xlsx,.xls,.txt" style="display:none" @change="onFileInput" />
        </div>
        <button class="btn-go" :disabled="!fileList.length || extracting" @click="handleSubmit">
          <el-icon :size="14"><Promotion /></el-icon>{{ extracting ? '提取中...' : fileInfo ? '重新提取' : '开始提取' }}
        </button>
        <el-alert v-if="errorMsg" :title="errorMsg" type="error" :closable show-icon class="mt8" @close="errorMsg=null" />
      </div>

      <!-- 右：结果 -->
      <div class="result-card">
        <div class="result-top">
          <div class="section-label"><el-icon :size="15" color="#1677ff"><DataAnalysis /></el-icon><span>提取结果</span></div>
          <div class="result-actions">
            <span v-if="extractedFields" class="result-badge">已提取 {{ fieldCount }} 字段</span>
            <button v-if="extractedFields" class="btn-sm" @click="downloadJSON"><el-icon :size="13"><Download /></el-icon>JSON</button>
          </div>
        </div>
        <div v-if="!extractedFields" class="empty-state">
          <el-icon :size="48" color="#d1d5db"><DataAnalysis /></el-icon><p>暂无结果</p>
        </div>
        <div v-else class="fields-scroll">
          <div v-for="(g, gi) in fieldGroups" :key="gi" class="f-group">
            <div class="f-group-hd">{{ g.label }}</div>
            <div v-for="f in g.items" :key="f.key" class="f-row" :class="{ sub: g.label !== '基本信息' }">
              <span class="f-lbl">{{ f.label }}</span>
              <span class="f-val" :class="{ empty: !f.hasValue }">{{ f.displayValue }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ==================== 下半区：项目列表 ==================== -->
    <div class="bottom-area">
      <div class="bottom-header">
        <div class="section-label"><el-icon :size="15" color="#1677ff"><Folder /></el-icon><span>项目列表</span><span class="count-badge">{{ historyList.length }}</span></div>
        <el-input v-model="searchKeyword" placeholder="搜索..." :prefix-icon="Search" size="small" clearable class="search-input" @input="onSearch" @clear="onSearch" />
      </div>
      <div class="table-wrap">
        <el-table :data="historyList" v-loading="loadingHistory" size="small" stripe highlight-current-row @row-click="handleHistoryClick" :row-class-name="tableRowClass" style="flex:1">
          <el-table-column prop="filename" label="文件名称" width="160" show-overflow-tooltip />
          <el-table-column prop="project_name" label="项目名称" min-width="120" show-overflow-tooltip>
            <template #default="{ row }"><span v-if="row.project_name">{{ row.project_name }}</span><span v-else class="muted">-</span></template>
          </el-table-column>
          <el-table-column label="项目编号" width="110" show-overflow-tooltip>
            <template #default="{ row }"><span v-if="row.contract_no">{{ row.contract_no }}</span><span v-else class="muted">-</span></template>
          </el-table-column>
          <el-table-column label="开工" width="85">
            <template #default="{ row }"><span v-if="row.start_date">{{ row.start_date }}</span><span v-else class="muted">-</span></template>
          </el-table-column>
          <el-table-column label="竣工" width="85">
            <template #default="{ row }"><span v-if="row.end_date">{{ row.end_date }}</span><span v-else class="muted">-</span></template>
          </el-table-column>
          <el-table-column label="状态" width="58">
            <template #default="{ row }"><el-tag v-if="row.status==='success'" type="success" size="small" effect="plain">成功</el-tag><el-tag v-else type="danger" size="small" effect="plain">失败</el-tag></template>
          </el-table-column>
          <el-table-column label="时间" width="85">
            <template #default="{ row }">{{ row.created_at?.slice(0,10) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click.stop="handleHistoryClick(row)">查看</el-button>
              <el-button type="danger" link size="small" @click.stop="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-if="!historyList.length && !loadingHistory" class="history-empty">暂无历史记录</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { UploadFilled, Document, Check, Promotion, DataAnalysis, Download, Loading, Folder, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted } from 'vue'
import { useContractInfo } from '@/composables/useContractInfo'

const { extractedFields, extracting, errorMsg, fileInfo, historyList, loadingHistory, selectedHistoryId, searchKeyword, uploadAndExtract, fetchHistory, loadRecord, deleteRecord, resetAll } = useContractInfo()

const fileInput = ref(null)
const fileList = ref([])

const FIELD_GROUPS = [
  { label: '基本信息', fields: [
    { key:'project_name',label:'项目名称' },{ key:'contract_no',label:'合同编号' },{ key:'signing_date',label:'签订日期' },
    { key:'feed_date',label:'计划投料' },{ key:'start_date',label:'开工日期' },{ key:'end_date',label:'竣工日期' },
    { key:'duration',label:'合同工期',format:v=>v?v+' 天':'无' },{ key:'contract_amount',label:'合同金额',format:v=>v?formatAmount(v):'无' },
    { key:'construction_scale',label:'建设规模' },{ key:'project_location',label:'工程地点' },{ key:'project_scope',label:'工程范围' },
    { key:'quality_standard',label:'质量要求' },{ key:'supervisor',label:'监理人' },{ key:'defect_period',label:'缺陷责任期',format:v=>v?v+' 天':'无' },
  ]},
  { label:'发包人（甲方）',detailKey:'party_a_detail',fields:[{key:'party_a',label:'单位名称'}] },
  { label:'承包人（乙方）',detailKey:'party_b_detail',fields:[{key:'party_b',label:'单位名称'}] },
]

const fieldCount = computed(() => extractedFields.value ? Object.values(extractedFields.value).filter(f=>f?.value!=null).length : 0)

const fieldGroups = computed(() => {
  const data = extractedFields.value || {}
  return FIELD_GROUPS.map(g => {
    const items = g.fields.map(d => {
      const info = data[d.key]; const v = info?.value; const hv = v!=null && v!==''
      return {...d, hasValue:hv, displayValue:hv ? (d.format?d.format(v):v) : '无'}
    })
    let di = []
    if (g.detailKey) { const d = data[g.detailKey]?.value; if (d && typeof d === 'object') di = Object.entries(d).map(([k,v]) => ({key:'d_'+k,label:k,hasValue:true,displayValue:v,isDetail:true})) }
    return {...g, items:[...items,...di]}
  })
})

function triggerUpload() { fileInput.value?.click() }
function validateFile(f) {
  if(!f) return false
  if(!/\.(pdf|docx|doc|xlsx|xls|txt)$/i.test(f.name)) { ElMessage.error('仅支持 PDF/Word/Excel/TXT'); return false }
  if(f.size/1024/1024>100) { ElMessage.error('≤100MB'); return false }
  return true
}
async function onFileInput(e) {
  const f = e.target.files?.[0]; if(!f||!validateFile(f)) return
  fileList.value=[{name:f.name,size:f.size,raw:f}]; await uploadAndExtract(f); if(errorMsg.value) ElMessage.error(errorMsg.value); e.target.value=''
}
function onDrop(e) { const f=e.dataTransfer?.files?.[0]; if(f&&validateFile(f)){fileList.value=[{name:f.name,size:f.size,raw:f}];uploadAndExtract(f)} }
onMounted(() => fetchHistory())
let st=null
function onSearch() { clearTimeout(st); st=setTimeout(()=>fetchHistory(searchKeyword.value),300) }
function tableRowClass({row}) { return selectedHistoryId.value===row.id?'current-row':'' }
async function handleHistoryClick(item) { fileList.value=[]; await loadRecord(item.id); if(errorMsg.value) ElMessage.error(errorMsg.value) }
async function handleDelete(item) { try{await ElMessageBox.confirm(`确定删除「${item.filename}」？`,'确认删除',{confirmButtonText:'删除',cancelButtonText:'取消',type:'warning'});await deleteRecord(item.id);ElMessage.success('已删除')}catch{} }
async function handleSubmit() { if(!fileList.value.length) return; await uploadAndExtract(fileList.value[0].raw); if(errorMsg.value) ElMessage.error(errorMsg.value) }
function formatAmount(v) { if(v==null) return '-'; const n=Number(v); if(n>=1e8) return (n/1e8).toFixed(2)+' 亿元'; if(n>=1e4) return (n/1e4).toFixed(2)+' 万元'; return n.toLocaleString()+' 元' }
function downloadJSON() {
  if(!extractedFields.value) return
  const d={}; for(const[k,f] of Object.entries(extractedFields.value)) d[k]=f?.value??null
  const b=new Blob([JSON.stringify(d,null,2)],{type:'application/json;charset=utf-8'})
  const a=document.createElement('a'); a.href=URL.createObjectURL(b); a.download=`合同信息_${new Date().toISOString().slice(0,10)}.json`
  document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(a.href)
}
</script>

<style lang="scss" scoped>
.contract-page { height: 100%; display: flex; flex-direction: column; gap: 16px; }

/* ===== 上半区 ===== */
.top-area { display: grid; grid-template-columns: 340px 1fr; gap: 16px; flex-shrink: 0; max-height: 45vh; }

.upload-card, .result-card { background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:20px; }
.upload-card { display:flex; flex-direction:column; }
.result-card { display:flex; flex-direction:column; overflow:hidden; }

.section-label { display:flex; align-items:center; gap:6px; font-size:14px; font-weight:600; color:#1f2937; margin-bottom: 10px; }

.upload-drop { padding:28px 16px; border:2px dashed #d1d5db; border-radius:10px; cursor:pointer; text-align:center; transition:.2s; flex:1; display:flex; align-items:center; justify-content:center;
  &:hover { border-color:#1677ff; background:#fafcff; }
}
.upload-state { display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:8px; color:#6b7280; }
.upload-state.done { color:#1f2937; .ufile { font-weight:600; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; } }
.upload-text { font-size:14px; }
.upload-hint { font-size:11px; color:#b0b7c3; width:100%; text-align:center; }
.spinner { animation:spin 2s linear infinite; } @keyframes spin { to{transform:rotate(360deg)} }

.btn-go { margin-top:10px; height:32px; width:100%; border:none; border-radius:6px; background:#1677ff; color:#fff; font-size:13px; font-weight:500; display:flex; align-items:center; justify-content:center; gap:5px; cursor:pointer; font-family:inherit;
  &:hover:not(:disabled){background:#0d66d0} &:disabled{opacity:.5;cursor:not-allowed}
}
.mt8 { margin-top:8px; }

/* 结果区 */
.result-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; .section-label { margin-bottom:0; } }
.result-actions { display:flex; align-items:center; gap:10px; }
.result-badge { font-size:11px; color:#52c41a; }
.btn-sm { height:26px; padding:0 8px; border:1px solid #d1d5db; border-radius:4px; background:#fff; color:#1677ff; font-size:11px; cursor:pointer; display:flex; align-items:center; gap:3px; font-family:inherit; &:hover{background:#e6f0ff} }

.empty-state { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; p { font-size:13px; color:#b0b7c3; margin:0; } }

.fields-scroll { flex:1; overflow-y:auto; padding-right:4px; max-height: calc(45vh - 80px);
  &::-webkit-scrollbar { width:4px } &::-webkit-scrollbar-thumb { background:#c9cdd4; border-radius:2px }
}
.f-group { margin-bottom:10px; }
.f-group-hd { font-size:12px; font-weight:700; color:#1677ff; padding:5px 8px; background:#e6f0ff; border-radius:4px; margin-bottom:4px; }
.f-row { display:flex; align-items:baseline; padding:5px 0; border-bottom:1px solid #f5f5f5; gap:8px;
  &.sub { padding-left:8px; .f-lbl { color:#8b8f96; } }
}
.f-lbl { width:90px; flex-shrink:0; font-size:12px; font-weight:600; color:#6b7280; }
.f-val { flex:1; font-size:13px; color:#1f2937; word-break:break-all; &.empty { color:#b0b7c3; font-style:italic; } }

/* ===== 下半区 ===== */
.bottom-area { flex:1; background:#fff; border:1px solid #e5e7eb; border-radius:10px; padding:16px; display:flex; flex-direction:column; min-height:0; }
.bottom-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; .section-label { margin-bottom:0; } }
.count-badge { font-size:11px; color:#1677ff; background:#e6f0ff; padding:0 6px; border-radius:8px; font-weight:500; }
.search-input { width:180px; }

.table-wrap { flex:1; min-height:0;
  :deep(.el-table) { font-size:12px; }
  :deep(.el-table th) { background:#f8fafc; font-weight:600; color:#6b7280; }
  :deep(.el-table .current-row) { background-color:#e6f0ff!important; }
  :deep(.el-table__body tr) { cursor:pointer; }
}
.muted { color:#b0b7c3; }
.history-empty { display:flex; align-items:center; justify-content:center; font-size:13px; color:#b0b7c3; padding:40px; }
</style>
