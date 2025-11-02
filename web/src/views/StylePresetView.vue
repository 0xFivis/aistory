<template>
  <div class="page page-container">
    <el-card class="toolbar-card section-card" shadow="never">
      <div class="toolbar section-header">
        <div class="section-title">风格组合管理</div>
        <el-space size="12">
          <el-button type="primary" @click="openCreateDialog">新增风格组合</el-button>
          <el-button :loading="loading" @click="reload">刷新</el-button>
          <el-button @click="goBack">返回任务列表</el-button>
        </el-space>
        <el-space size="12">
          <span class="switch-label">显示禁用</span>
          <el-switch v-model="includeInactive" @change="handleIncludeInactiveChange" />
        </el-space>
      </div>
    </el-card>

  <el-card class="table-card section-card" shadow="never">
      <el-table
        class="style-presets-table"
        :data="presets"
        v-loading="loading"
        border
        stripe
        highlight-current-row
      >
        <el-table-column
          prop="name"
          label="名称"
          width="220"
          fixed="left"
          class-name="col-name"
          show-overflow-tooltip
        />
        <el-table-column
          label="说明"
          min-width="320"
          class-name="col-description"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span>{{ row.description || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column
          label="模型/LoRA"
          min-width="260"
          class-name="col-model"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div class="table-model">
              <span v-if="row.checkpoint_id">模型：{{ row.checkpoint_id }}</span>
              <span v-if="row.lora_id">LoRA：{{ row.lora_id }}</span>
              <span v-if="!row.checkpoint_id && !row.lora_id">-</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center" class-name="col-status">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="208" align="center" class-name="col-updated">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right" align="center" class-name="col-actions">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              size="small"
              type="warning"
              @click="toggleActive(row)"
            >{{ row.is_active ? '禁用' : '启用' }}</el-button>
            <el-button size="small" type="danger" @click="removePreset(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="640px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="120px"
        scroll-to-error
      >
        <el-form-item label="风格名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入风格名称" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="风格说明">
          <el-input
            v-model="form.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="描述该风格的整体特点"
          />
        </el-form-item>
        <el-form-item label="提示词示例">
          <el-input
            v-model="form.prompt_example"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="完整的提示词示例"
          />
        </el-form-item>
        <el-form-item label="触发词">
          <el-input
            v-model="form.trigger_words"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="换行或逗号分隔"
          />
        </el-form-item>
        <el-form-item label="字数策略">
          <el-input
            v-model="form.word_count_strategy"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="旁白字数建议，可留空"
          />
        </el-form-item>
        <el-form-item label="频道身份">
          <el-input
            v-model="form.channel_identity"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="频道口吻或人设，可留空"
          />
        </el-form-item>
        <el-form-item label="主模型">
          <el-input v-model="form.checkpoint_id" placeholder="如留空则使用默认" />
        </el-form-item>
        <el-form-item label="LoRA">
          <el-input v-model="form.lora_id" placeholder="如留空则不覆盖" />
        </el-form-item>
        <el-form-item label="图片平台">
          <el-select
            v-model="form.image_provider"
            placeholder="保持默认"
            clearable
            filterable
          >
            <el-option v-for="option in imageProviderOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.image_provider === 'runninghub'" label="图片工作流">
          <el-select
            v-model="form.runninghub_image_workflow_id"
            placeholder="选择 RunningHub 工作流"
            :loading="runninghubLoading"
            clearable
            filterable
          >
            <el-option
              v-for="workflow in imageWorkflows"
              :key="workflow.id"
              :label="workflow.name"
              :value="workflow.id"
            />
          </el-select>
          <div v-if="!runninghubLoading && form.image_provider === 'runninghub' && imageWorkflows.length === 0" class="form-hint">
            无可用的 RunningHub 图片工作流，请先在 RunningHub 管理页创建。
          </div>
        </el-form-item>
        <el-form-item label="视频平台">
          <el-select
            v-model="form.video_provider"
            placeholder="保持默认"
            clearable
            filterable
          >
            <el-option v-for="option in videoProviderOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.video_provider === 'runninghub'" label="视频工作流">
          <el-select
            v-model="form.runninghub_video_workflow_id"
            placeholder="选择 RunningHub 工作流"
            :loading="runninghubLoading"
            clearable
            filterable
          >
            <el-option
              v-for="workflow in videoWorkflows"
              :key="workflow.id"
              :label="workflow.name"
              :value="workflow.id"
            />
          </el-select>
          <div v-if="!runninghubLoading && form.video_provider === 'runninghub' && videoWorkflows.length === 0" class="form-hint">
            无可用的 RunningHub 视频工作流，请先在 RunningHub 管理页创建。
          </div>
        </el-form-item>
        <el-form-item label="附加元数据">
          <el-input
            v-model="form.metaText"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 6 }"
            placeholder="可选，JSON 格式"
          />
        </el-form-item>
        <el-form-item label="立即启用">
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
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useStylePresetStore } from '@/stores/stylePreset'
import { useRunningHubWorkflowStore } from '@/stores/runninghub'
import type { StylePreset, StylePresetPayload } from '@/types/stylePreset'

const router = useRouter()
const stylePresetStore = useStylePresetStore()
const runninghubStore = useRunningHubWorkflowStore()
const { presets, loading } = storeToRefs(stylePresetStore)
const {
  workflows: runninghubWorkflows,
  imageWorkflows,
  videoWorkflows,
  loading: runninghubLoading
} = storeToRefs(runninghubStore)

const includeInactive = ref(true)
const dialogVisible = ref(false)
const saving = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const editingPreset = ref<StylePreset | null>(null)
const formRef = ref<FormInstance>()

const imageProviderOptions = [
  { label: 'RunningHub', value: 'runninghub' },
  { label: 'Liblib', value: 'liblib' },
  { label: 'ComfyUI', value: 'comfyui' }
]

const videoProviderOptions = [
  { label: 'RunningHub', value: 'runninghub' },
  { label: 'Fal', value: 'fal' },
  { label: 'NCA', value: 'nca' }
]

const form = reactive({
  name: '',
  description: '',
  prompt_example: '',
  trigger_words: '',
  word_count_strategy: '',
  channel_identity: '',
  lora_id: '',
  checkpoint_id: '',
  image_provider: null as string | null,
  video_provider: null as string | null,
  runninghub_image_workflow_id: null as number | null,
  runninghub_video_workflow_id: null as number | null,
  metaText: '',
  is_active: true
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入风格名称', trigger: 'blur' }]
}

const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新增风格组合' : '编辑风格组合'))

onMounted(() => {
  loadPresets()
})

const ensureRunningHubWorkflows = async () => {
  if (runninghubLoading.value) return
  if (!runninghubWorkflows.value.length) {
    await runninghubStore.loadWorkflows({ includeInactive: false })
  }
}

const loadPresets = async () => {
  await stylePresetStore.loadPresets({ includeInactive: includeInactive.value })
}

const reload = () => {
  loadPresets()
}

const handleIncludeInactiveChange = () => {
  loadPresets()
}

const goBack = () => {
  router.push({ name: 'home' })
}

const resetForm = () => {
  form.name = ''
  form.description = ''
  form.prompt_example = ''
  form.trigger_words = ''
  form.word_count_strategy = ''
  form.channel_identity = ''
  form.lora_id = ''
  form.checkpoint_id = ''
  form.image_provider = null
  form.video_provider = null
  form.runninghub_image_workflow_id = null
  form.runninghub_video_workflow_id = null
  form.metaText = ''
  form.is_active = true
}

const openCreateDialog = () => {
  dialogMode.value = 'create'
  editingPreset.value = null
  resetForm()
  dialogVisible.value = true
  ensureRunningHubWorkflows()
  nextTick(() => formRef.value?.clearValidate())
}

const openEditDialog = (preset: StylePreset) => {
  dialogMode.value = 'edit'
  editingPreset.value = preset
  form.name = preset.name
  form.description = preset.description ?? ''
  form.prompt_example = preset.prompt_example ?? ''
  form.trigger_words = preset.trigger_words ?? ''
  form.word_count_strategy = preset.word_count_strategy ?? ''
  form.channel_identity = preset.channel_identity ?? ''
  form.lora_id = preset.lora_id ?? ''
  form.checkpoint_id = preset.checkpoint_id ?? ''
  form.image_provider = preset.image_provider ?? null
  form.video_provider = preset.video_provider ?? null
  form.runninghub_image_workflow_id = preset.runninghub_image_workflow_id ?? null
  form.runninghub_video_workflow_id = preset.runninghub_video_workflow_id ?? null
  form.metaText = preset.meta ? JSON.stringify(preset.meta, null, 2) : ''
  form.is_active = preset.is_active
  dialogVisible.value = true
  if (preset.image_provider === 'runninghub' || preset.video_provider === 'runninghub') {
    ensureRunningHubWorkflows()
  }
  nextTick(() => formRef.value?.clearValidate())
}

const closeDialog = () => {
  dialogVisible.value = false
}

const parseMeta = (value: string) => {
  if (!value.trim()) return null
  try {
    const parsed = JSON.parse(value)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
  } catch (error) {
    // handled below
  }
  throw new Error('附加元数据需要是合法的 JSON 对象')
}

const normalizeText = (value: string) => {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

const submitForm = () => {
  if (!formRef.value) return
  formRef.value.validate(async (valid) => {
    if (!valid) return
    let meta: Record<string, unknown> | null = null
    try {
      meta = parseMeta(form.metaText)
    } catch (error: any) {
      ElMessage.error(error.message || '元数据格式错误')
      return
    }

    if (form.image_provider === 'runninghub' && !form.runninghub_image_workflow_id) {
      ElMessage.error('请选择 RunningHub 图片工作流')
      return
    }

    if (form.video_provider === 'runninghub' && !form.runninghub_video_workflow_id) {
      ElMessage.error('请选择 RunningHub 视频工作流')
      return
    }

    const payload: StylePresetPayload = {
      name: form.name.trim(),
      description: normalizeText(form.description),
      prompt_example: normalizeText(form.prompt_example),
      trigger_words: normalizeText(form.trigger_words),
      word_count_strategy: normalizeText(form.word_count_strategy),
      channel_identity: normalizeText(form.channel_identity),
      lora_id: normalizeText(form.lora_id),
      checkpoint_id: normalizeText(form.checkpoint_id),
      image_provider: form.image_provider || null,
      video_provider: form.video_provider || null,
      runninghub_image_workflow_id:
        form.image_provider === 'runninghub' ? form.runninghub_image_workflow_id ?? null : null,
      runninghub_video_workflow_id:
        form.video_provider === 'runninghub' ? form.runninghub_video_workflow_id ?? null : null,
      meta,
      is_active: form.is_active
    }

    saving.value = true
    try {
      if (dialogMode.value === 'create') {
        await stylePresetStore.addPreset(payload)
        ElMessage.success('风格组合创建成功')
      } else if (editingPreset.value) {
        await stylePresetStore.modifyPreset(editingPreset.value.id, payload)
        ElMessage.success('风格组合更新成功')
      }
      await loadPresets()
      dialogVisible.value = false
      resetForm()
    } finally {
      saving.value = false
    }
  })
}

const toggleActive = async (preset: StylePreset) => {
  const targetState = !preset.is_active
  const action = targetState ? '启用' : '禁用'
  await ElMessageBox.confirm(`确定${action}风格“${preset.name}”吗？`, '提示', {
    type: 'warning'
  })
  await stylePresetStore.modifyPreset(preset.id, { is_active: targetState })
  ElMessage.success(`已${action}该风格`)
  await loadPresets()
}

const removePreset = async (preset: StylePreset) => {
  await ElMessageBox.confirm(`确定永久删除风格“${preset.name}”吗？此操作不可恢复。`, '删除确认', {
    type: 'error'
  })
  await stylePresetStore.removePreset(preset.id, false)
  ElMessage.success('风格组合已删除')
  await loadPresets()
}

const formatDate = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

watch(
  () => form.image_provider,
  (provider) => {
    if (provider === 'runninghub') {
      ensureRunningHubWorkflows()
      return
    }
    form.runninghub_image_workflow_id = null
  }
)

watch(
  () => form.video_provider,
  (provider) => {
    if (provider === 'runninghub') {
      ensureRunningHubWorkflows()
      return
    }
    form.runninghub_video_workflow_id = null
  }
)

watch(
  () => dialogVisible.value,
  (visible) => {
    if (visible) ensureRunningHubWorkflows()
  }
)
</script>

<style scoped>
.page {
  gap: var(--layout-section-gap);
}

.toolbar-card :deep(.el-card__body) {
  padding: var(--space-4);
}

.switch-label {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
}

.table-card :deep(.el-card__body) {
  padding: 0;
}

.table-card :deep(.el-table__cell) {
  padding: var(--space-3);
}

.style-presets-table :deep(.col-name .cell) {
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-900);
  white-space: nowrap;
}

.style-presets-table :deep(.col-description .cell) {
  color: var(--color-neutral-700);
  line-height: var(--line-height-base);
}

.style-presets-table :deep(.col-model .cell) {
  color: var(--color-neutral-700);
}

.style-presets-table :deep(.col-updated .cell) {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  color: var(--color-neutral-700);
}

.style-presets-table :deep(.col-actions .cell) {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
}

.table-model {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.table-liblib {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.form-hint {
  margin-top: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
}
</style>
