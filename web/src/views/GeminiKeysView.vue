<template>
  <div class="gemini-keys-page">
    <el-page-header content="Gemini API Keys 管理" @back="goBack" />
    <div class="spacer" />
  <el-card>
      <template #header>
        <div class="card-header" style="justify-content:space-between; align-items:center">
          <div style="display:flex; gap:12px; align-items:center">
            <span>API Keys 列表</span>
            <el-button @click="load">刷新</el-button>
            <el-checkbox v-model="showDisabled">显示已禁用</el-checkbox>
          </div>
          <div style="display:flex; gap:8px; align-items:center">
            <el-button type="primary" @click="openCreate">添加 Key</el-button>
            <el-button type="warning" @click="openImport">批量导入</el-button>
            <el-button type="danger" @click="deleteSelected" :disabled="!selected.length">删除选中</el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredKeys" stripe @selection-change="handleSelectionChange" ref="keysTable">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="credential_key" label="Key" />
        <el-table-column prop="is_active" label="启用" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" />
        <el-table-column prop="last_used_at" label="最后使用" width="200" />
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="editKey(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="removeKey(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog title="添加/编辑 Key" v-model="dialogVisible">
      <el-form :model="form">
        <el-form-item label="Key">
          <el-input v-model="form.credential_key" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog title="批量导入 Keys" v-model="importVisible">
      <div>
        <p>每行一个 API Key（可选附加说明，用逗号分隔，例如：KEY1,说明）</p>
        <el-input type="textarea" v-model="importText" :rows="8" placeholder="粘贴多行 Key" />
      </div>
      <template #footer>
        <el-button @click="importVisible=false">取消</el-button>
        <el-button type="primary" @click="doImport">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { listCredentials, createCredential, updateCredential, deleteCredential } from '@/services/credentials'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

const router = useRouter()
const keys = ref<any[]>([])
const showDisabled = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ credential_key: '', description: '', is_active: true })
const importVisible = ref(false)
const importText = ref('')
const selected = ref<any[]>([])
const keysTable = ref()

const load = async () => {
  try {
    keys.value = await listCredentials('gemini')
  } catch (e: any) {
    ElMessage.error('加载失败')
  }
}

onMounted(() => { load() })

const handleSelectionChange = (val: any[]) => {
  selected.value = val || []
}

const filteredKeys = computed(() => {
  if (showDisabled.value) return keys.value
  return keys.value.filter((k: any) => k.is_active)
})

const goBack = () => router.back()

const openCreate = () => {
  editingId.value = null
  form.value = { credential_key: '', description: '', is_active: true }
  dialogVisible.value = true
}

const openImport = () => {
  importText.value = ''
  importVisible.value = true
}

const editKey = (row: any) => {
  editingId.value = row.id
  form.value = { credential_key: row.credential_key ?? '', description: row.description ?? '', is_active: row.is_active }
  dialogVisible.value = true
}

const submit = async () => {
  try {
    if (editingId.value) {
      await updateCredential(editingId.value, { credential_key: form.value.credential_key, description: form.value.description, is_active: form.value.is_active })
      ElMessage.success('更新成功')
    } else {
      await createCredential({ service_name: 'gemini', credential_key: form.value.credential_key, description: form.value.description, is_active: form.value.is_active })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error('保存失败')
  }
}

const removeKey = async (row: any) => {
  try {
    await deleteCredential(row.id)
    ElMessage.success('删除成功')
    load()
  } catch (e: any) {
    ElMessage.error('删除失败')
  }
}

const deleteSelected = async () => {
  if (!selected.value.length) return
  try {
    await ElMessageBox.confirm(`确认删除 ${selected.value.length} 个 Key 吗？`, '确认', { type: 'warning' })
    for (const row of selected.value) {
      await deleteCredential(row.id)
    }
    ElMessage.success('删除完成')
    selected.value = []
    load()
  } catch (e: any) {
    // cancel
  }
}

const doImport = async () => {
  const lines = importText.value.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
  try {
    for (const line of lines) {
      const parts = line.split(',')
      const key = parts[0].trim()
      const desc = parts.slice(1).join(',').trim() || ''
      if (key) {
        await createCredential({ service_name: 'gemini', credential_key: key, description: desc, is_active: true })
      }
    }
    ElMessage.success('导入完成')
    importVisible.value = false
    load()
  } catch (e: any) {
    ElMessage.error('导入失败')
  }
}

const toggleActive = async (row: any) => {
  try {
    await updateCredential(row.id, { is_active: row.is_active })
    ElMessage.success('已更新')
  } catch (e: any) {
    ElMessage.error('更新失败')
    load()
  }
}
</script>

<style scoped>
.spacer { height: 8px }
.card-header { display:flex; justify-content:space-between; align-items:center }
</style>
