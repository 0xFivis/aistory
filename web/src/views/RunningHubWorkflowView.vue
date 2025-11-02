<template>
  <div class="page">
    <el-card class="toolbar-card" shadow="hover">
      <div class="toolbar">
        <el-space size="12">
          <el-button type="primary" @click="openCreateDialog">新增配置</el-button>
          <el-button :loading="loading" @click="reload">刷新</el-button>
          <el-button @click="goBack">返回</el-button>
        </el-space>
        <el-space size="12">
          <el-select v-model="filters.workflowType" placeholder="类型" clearable style="width: 160px" @change="reload">
            <el-option label="全部" :value="null" />
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
          </el-select>
          <span class="switch-label">显示禁用</span>
          <el-switch v-model="filters.includeInactive" @change="reload" />
        </el-space>
      </div>
    </el-card>

    <el-card class="table-card" shadow="hover">
      <el-table :data="workflows" v-loading="loading" border stripe>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="workflow_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.workflow_type === 'image' ? '图片' : '视频' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="workflow_id" label="Workflow ID" min-width="180" />
        <el-table-column prop="instance_type" label="实例" width="120" />
        <el-table-column label="默认" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_default ? 'success' : 'info'" size="small">
              {{ row.is_default ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180" align="center">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              size="small"
              type="warning"
              @click="toggleActive(row)"
            >{{ row.is_active ? '禁用' : '启用' }}</el-button>
            <el-button size="small" type="danger" @click="removeWorkflow(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="720px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" scroll-to-error>
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入名称" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="类型" prop="workflow_type">
          <el-select v-model="form.workflow_type" placeholder="选择类型">
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item label="Slug">
          <el-input v-model="form.slug" placeholder="可选，唯一标识" maxlength="64" />
        </el-form-item>
        <el-form-item label="Workflow ID" prop="workflow_id">
          <el-input v-model="form.workflow_id" placeholder="Runninghub workflowId" maxlength="64" />
        </el-form-item>
        <el-form-item label="实例类型">
          <el-input v-model="form.instance_type" placeholder="默认 plus" maxlength="32" />
        </el-form-item>
        <el-form-item label="节点模板">
          <el-input
            v-model="form.nodeInfoText"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="JSON 数组，例如 [{&quot;nodeId&quot;:&quot;6&quot;,...}]"
          />
        </el-form-item>
        <el-form-item label="默认参数">
          <el-input
            v-model="form.defaultsText"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 8 }"
            placeholder="JSON 对象，例如 {&quot;width&quot;: 864}"
          />
        </el-form-item>
        <el-form-item label="说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="备注信息"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { storeToRefs } from 'pinia'
import { useRunningHubWorkflowStore } from '@/stores/runninghub'
import type {
  RunningHubWorkflow,
  RunningHubWorkflowPayload,
  RunningHubWorkflowType
} from '@/types/runninghub'

const router = useRouter()
const workflowStore = useRunningHubWorkflowStore()
const { workflows, loading } = storeToRefs(workflowStore)

const filters = reactive<{ workflowType: RunningHubWorkflowType | null; includeInactive: boolean }>(
  {
    workflowType: null,
    includeInactive: false
  }
)

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const saving = ref(false)
const editingWorkflow = ref<RunningHubWorkflow | null>(null)

const form = reactive({
  name: '',
  workflow_type: 'image' as RunningHubWorkflowType,
  slug: '',
  workflow_id: '',
  instance_type: 'plus',
  nodeInfoText: '',
  defaultsText: '',
  description: '',
  is_active: true,
  is_default: false
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  workflow_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  workflow_id: [{ required: true, message: '请输入 workflowId', trigger: 'blur' }]
}

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增配置' : '编辑配置'))

onMounted(() => {
  reload()
})

const reload = async () => {
  await workflowStore.loadWorkflows({
    workflowType: filters.workflowType ?? undefined,
    includeInactive: filters.includeInactive
  })
}

const goBack = () => {
  router.push({ name: 'home' })
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  editingWorkflow.value = null
  resetForm()
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

const openEditDialog = (record: RunningHubWorkflow) => {
  dialogMode.value = 'edit'
  editingWorkflow.value = record
  form.name = record.name
  form.workflow_type = record.workflow_type
  form.slug = record.slug ?? ''
  form.workflow_id = record.workflow_id
  form.instance_type = record.instance_type || 'plus'
  form.nodeInfoText = record.node_info_template ? JSON.stringify(record.node_info_template, null, 2) : ''
  form.defaultsText = record.defaults ? JSON.stringify(record.defaults, null, 2) : ''
  form.description = record.description ?? ''
  form.is_active = record.is_active
  form.is_default = record.is_default
  dialogVisible.value = true
  nextTick(() => formRef.value?.clearValidate())
}

const closeDialog = () => {
  dialogVisible.value = false
}

const resetForm = () => {
  form.name = ''
  form.workflow_type = 'image'
  form.slug = ''
  form.workflow_id = ''
  form.instance_type = 'plus'
  form.nodeInfoText = ''
  form.defaultsText = ''
  form.description = ''
  form.is_active = true
  form.is_default = false
}

const parseJson = (value: string, expectArray: boolean) => {
  if (!value.trim()) return null
  try {
    const parsed = JSON.parse(value)
    if (expectArray && Array.isArray(parsed)) return parsed
    if (!expectArray && parsed && typeof parsed === 'object' && !Array.isArray(parsed)) return parsed
  } catch (error) {
    /* noop */
  }
  throw new Error(expectArray ? '节点模板需为合法 JSON 数组' : '默认参数需为合法 JSON 对象')
}

const submitForm = () => {
  if (!formRef.value) return
  formRef.value.validate(async (valid) => {
    if (!valid) return

    let nodeTemplate: Record<string, unknown>[] | null = null
    if (form.nodeInfoText.trim()) {
      try {
        nodeTemplate = parseJson(form.nodeInfoText, true) as Record<string, unknown>[]
      } catch (error: any) {
        ElMessage.error(error.message || '节点模板格式错误')
        return
      }
    }

    let defaultsPayload: Record<string, unknown> | null = null
    if (form.defaultsText.trim()) {
      try {
        defaultsPayload = parseJson(form.defaultsText, false) as Record<string, unknown>
      } catch (error: any) {
        ElMessage.error(error.message || '默认参数格式错误')
        return
      }
    }

    const payload: RunningHubWorkflowPayload = {
      name: form.name.trim(),
      workflow_type: form.workflow_type,
      slug: form.slug.trim() ? form.slug.trim() : null,
      workflow_id: form.workflow_id.trim(),
      instance_type: form.instance_type.trim() || 'plus',
      node_info_template: nodeTemplate,
      defaults: defaultsPayload,
      description: form.description.trim() ? form.description.trim() : null,
      is_active: form.is_active,
      is_default: form.is_default
    }

    saving.value = true
    try {
      if (dialogMode.value === 'create') {
        await workflowStore.addWorkflow(payload)
        ElMessage.success('配置创建成功')
      } else if (editingWorkflow.value) {
        await workflowStore.modifyWorkflow(editingWorkflow.value.id, payload)
        ElMessage.success('配置更新成功')
      }
      dialogVisible.value = false
      await reload()
    } finally {
      saving.value = false
    }
  })
}

const toggleActive = async (record: RunningHubWorkflow) => {
  const action = record.is_active ? '禁用' : '启用'
  await ElMessageBox.confirm(`确定${action}配置“${record.name}”吗？`, '提示', { type: 'warning' })
  await workflowStore.modifyWorkflow(record.id, { is_active: !record.is_active })
  ElMessage.success(`已${action}`)
  await reload()
}

const removeWorkflow = async (record: RunningHubWorkflow) => {
  await ElMessageBox.confirm(`确定删除配置“${record.name}”吗？`, '删除确认', { type: 'error' })
  await workflowStore.removeWorkflow(record.id, true)
  ElMessage.success('配置已删除')
  await reload()
}

const formatDate = (value: string | null) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card {
  border-radius: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.switch-label {
  font-size: 14px;
  color: #4b5563;
}

.table-card {
  border-radius: 12px;
}
</style>
