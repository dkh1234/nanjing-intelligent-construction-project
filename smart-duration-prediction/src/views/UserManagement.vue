<template>
  <div class="user-management">
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <el-button type="primary" @click="openCreateDialog">+ 新建用户</el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索用户名或姓名"
        clearable
        style="width: 240px"
        @change="fetchUsers"
      />
      <el-select v-model="roleFilter" placeholder="角色" clearable style="width: 120px" @change="fetchUsers">
        <el-option label="管理员" value="admin" />
        <el-option label="用户" value="user" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px" @change="fetchUsers">
        <el-option label="启用" value="1" />
        <el-option label="禁用" value="0" />
      </el-select>
    </div>

    <!-- 表格 -->
    <el-table :data="users" border stripe v-loading="tableLoading" style="width: 100%">
      <el-table-column prop="username" label="用户名" width="140" align="center" />
      <el-table-column prop="display_name" label="姓名" width="120" align="center" />
      <el-table-column prop="role" label="角色" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'" size="small">
            {{ row.role === 'admin' ? '管理员' : '用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" align="center" />
      <el-table-column prop="last_login" label="最后登录" width="180" align="center">
        <template #default="{ row }">
          {{ row.last_login || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="320" fixed="right" align="center">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="handleResetPassword(row)">重置密码</el-button>
          <el-popconfirm
            title="确定要启用该用户吗？"
            @confirm="handleEnable(row)"
            v-if="!row.is_active"
          >
            <template #reference>
              <el-button text type="success" size="small">启用</el-button>
            </template>
          </el-popconfirm>
          <el-popconfirm
            title="确定要禁用该用户吗？"
            @confirm="handleDisable(row)"
            v-if="row.is_active"
          >
            <template #reference>
              <el-button text type="danger" size="small">禁用</el-button>
            </template>
          </el-popconfirm>
          <el-popconfirm
            title="确定要删除该用户吗？此操作不可恢复"
            @confirm="handleDelete(row)"
          >
            <template #reference>
              <el-button text type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="fetchUsers"
      />
    </div>

    <!-- 新建/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑用户' : '新建用户'"
      width="440px"
      @closed="resetForm"
    >
      <el-form ref="dialogFormRef" :model="dialogForm" :rules="dialogRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialogForm.username" :disabled="isEditing" placeholder="登录账号" />
        </el-form-item>
        <el-form-item label="姓名" prop="display_name">
          <el-input v-model="dialogForm.display_name" placeholder="显示名称" />
        </el-form-item>
        <el-form-item v-if="!isEditing" label="密码" prop="password">
          <el-input v-model="dialogForm.password" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="dialogForm.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="dialogLoading" @click="submitDialog">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码结果弹窗 -->
    <el-dialog v-model="pwdDialogVisible" title="密码已重置" width="400px">
      <el-alert type="success" :closable="false">
        <template #title>
          新密码：<strong style="font-size:16px;user-select:all">{{ newPassword }}</strong>
        </template>
      </el-alert>
      <p style="color:#86909C;margin-top:12px">请将此密码发送给用户。关闭后无法再次查看。</p>
      <template #footer>
        <el-button type="primary" @click="pwdDialogVisible = false">我知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import authRequest from '@/utils/authRequest'

const users = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const tableLoading = ref(false)

async function fetchUsers() {
  tableLoading.value = true
  try {
    const params = { page: page.value, page_size: pageSize.value }
    if (keyword.value) params.keyword = keyword.value
    if (roleFilter.value) params.role = roleFilter.value
    if (statusFilter.value) params.is_active = statusFilter.value
    const res = await authRequest.get('/admin/users', { params })
    users.value = res.items
    total.value = res.total
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '获取用户列表失败')
  } finally {
    tableLoading.value = false
  }
}

// ---- 新建/编辑 ----
const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEditing = ref(false)
const editingUserId = ref(null)
const dialogFormRef = ref(null)

const dialogForm = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'user',
})

const dialogRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

function openCreateDialog() {
  isEditing.value = false
  editingUserId.value = null
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEditing.value = true
  editingUserId.value = row.id
  dialogForm.username = row.username
  dialogForm.display_name = row.display_name
  dialogForm.role = row.role
  dialogForm.password = ''
  dialogVisible.value = true
}

function resetForm() {
  dialogForm.username = ''
  dialogForm.display_name = ''
  dialogForm.password = ''
  dialogForm.role = 'user'
  dialogFormRef.value?.resetFields()
}

async function submitDialog() {
  const valid = await dialogFormRef.value.validate().catch(() => false)
  if (!valid) return

  dialogLoading.value = true
  try {
    if (isEditing.value) {
      await authRequest.put(`/admin/users/${editingUserId.value}`, {
        display_name: dialogForm.display_name,
        role: dialogForm.role,
      })
      ElMessage.success('用户信息已更新')
    } else {
      await authRequest.post('/admin/users', {
        username: dialogForm.username,
        password: dialogForm.password,
        display_name: dialogForm.display_name,
        role: dialogForm.role,
      })
      ElMessage.success('用户创建成功')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (err) {
    const msg = err.response?.data?.detail || '操作失败'
    ElMessage.error(msg)
  } finally {
    dialogLoading.value = false
  }
}

// ---- 重置密码 ----
const pwdDialogVisible = ref(false)
const newPassword = ref('')

async function handleResetPassword(row) {
  try {
    const res = await authRequest.post(`/admin/users/${row.id}/reset-password`)
    newPassword.value = res.new_password
    pwdDialogVisible.value = true
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '重置密码失败')
  }
}

// ---- 启用 ----
async function handleEnable(row) {
  try {
    await authRequest.put(`/admin/users/${row.id}`, { is_active: true })
    ElMessage.success('用户已启用')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

// ---- 禁用 ----
async function handleDisable(row) {
  try {
    await authRequest.put(`/admin/users/${row.id}`, { is_active: false })
    ElMessage.success('用户已禁用')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

// ---- 删除 ----
async function handleDelete(row) {
  try {
    await authRequest.delete(`/admin/users/${row.id}`)
    ElMessage.success('用户已删除')
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '操作失败')
  }
}

onMounted(fetchUsers)
</script>

<style lang="scss" scoped>
.user-management {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #1d2129;
  margin: 0;
}

.search-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
