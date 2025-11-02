<template>
  <div class="gemini-console page-container">
    <el-row :gutter="16" class="console-layout">
      <el-col :xs="24" :lg="10" class="stretch-column">
        <el-card class="templates-card section-card" shadow="never">
          <template #header>
            <div class="card-header section-header">
              <span class="section-title">提示词模板</span>
              <div class="card-actions">
                <el-switch
                  v-model="includeInactive"
                  size="small"
                  @change="handleIncludeInactiveChange"
                />
                <span class="switch-label">显示禁用</span>
                <el-button type="primary" size="small" @click="openCreateDialog">
                  新建模板
                </el-button>
              </div>
            </div>
          </template>
          <el-table
            :data="templates"
            v-loading="templatesLoading"
            height="380"
            border
            stripe
            @row-click="handleTemplateRowClick"
            class="templates-table"
          >
            <el-table-column label="名称" prop="name" min-width="160">
              <template #default="{ row }">
                <div class="template-name">
                  <el-radio
                    v-model="selectedTemplateId"
                    :label="row.id"
                    class="template-radio"
                  >
                    {{ row.name }}
                  </el-radio>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="标识" prop="slug" min-width="120" show-overflow-tooltip />
            <el-table-column label="参数" min-width="140">
              <template #default="{ row }">
                <span>{{ formatParamList(row.parameters) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="160" align="center">
              <template #default="{ row }">
                {{ formatDate(row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click.stop="openEditDialog(row.id)">
                  编辑
                </el-button>
                <el-button size="small" type="danger" @click.stop="removeTemplate(row.id)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

  <el-card class="records-card section-card" shadow="never">
          <template #header>
            <div class="card-header section-header">
              <span class="section-title">调用记录</span>
              <div class="card-actions">
                <el-button size="small" :loading="recordsLoading" @click="reloadRecords">
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          <el-table
            :data="records"
            v-loading="recordsLoading"
            height="260"
            border
            stripe
            empty-text="暂无记录"
            @row-click="openRecordDialog"
          >
            <el-table-column label="模板" min-width="140">
              <template #default="{ row }">
                {{ resolveTemplateName(row.template_id) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="耗时(ms)" width="100" align="center">
              <template #default="{ row }">
                {{ row.latency_ms ?? '-' }}
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="170" align="center">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="响应预览" min-width="220" show-overflow-tooltip>
              <template #default="{ row }">
                <span>{{ (row.response_text || row.error_message || '').slice(0, 120) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" @click.stop="openRecordDialog(row)">
                  查看详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="14" class="stretch-column">
        <el-card class="request-card section-card" shadow="never">
          <template #header>
            <div class="card-header section-header">
              <span class="section-title">Gemini 同步请求</span>
              <div class="card-actions">
                <el-button
                  type="primary"
                  :loading="executionLoading"
                  @click="submitRequest"
                >
                  发送请求
                </el-button>
              </div>
            </div>
          </template>

          <el-form
            ref="requestFormRef"
            :model="requestForm"
            :rules="requestRules"
            label-width="110px"
            class="request-form"
          >
            <el-form-item label="选择模板" prop="templateId">
              <el-select
                v-model="requestForm.templateId"
                placeholder="请选择模板"
                :loading="templatesLoading"
                clearable
                filterable
                @change="handleTemplateSelect"
              >
                <el-option
                  v-for="item in activeTemplates"
                  :key="item.id"
                  :label="item.name"
                  :value="item.id"
                />
              </el-select>
            </el-form-item>

            <template v-if="currentParameters.length">
              <el-divider content-position="left">模板参数（可选）</el-divider>
              <el-form-item
                v-for="param in currentParameters"
                :key="param"
                :label="param"
              >
                <el-input
                  v-model="parameterValues[param]"
                  placeholder="可留空"
                  clearable
                />
              </el-form-item>
            </template>

            <el-form-item label="提示词预览">
              <el-input
                :value="promptPreview"
                type="textarea"
                :autosize="{ minRows: 6, maxRows: 16 }"
                readonly
              />
            </el-form-item>
          </el-form>
        </el-card>

  <el-card class="result-card section-card" shadow="never">
          <template #header>
            <div class="card-header section-header">
              <span class="section-title">响应结果</span>
              <div class="card-actions">
                <el-button size="small" @click="resetResult">清空</el-button>
              </div>
            </div>
          </template>

          <el-alert
            v-if="executionError"
            :title="executionError"
            type="error"
            show-icon
            class="result-alert"
          />

          <template v-if="lastRecord">
            <div class="result-meta">
              <div>
                <span class="meta-label">模板：</span>{{ resolveTemplateName(lastRecord.template_id) }}
              </div>
              <div>
                <span class="meta-label">状态：</span>
                <el-tag :type="lastRecord.status === 'success' ? 'success' : 'danger'" size="small">
                  {{ lastRecord.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </div>
              <div>
                <span class="meta-label">耗时：</span>{{ lastRecord.latency_ms ?? '-' }} ms
              </div>
              <div>
                <span class="meta-label">时间：</span>{{ formatDate(lastRecord.created_at) }}
              </div>
            </div>

            <el-divider content-position="left">提示词内容</el-divider>
            <el-input
              class="result-text"
              :value="lastRecord.prompt"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 20 }"
              readonly
            />

            <el-divider content-position="left">模型返回</el-divider>
            <el-input
              class="result-text"
              :value="lastRecord.response_text || lastRecord.error_message || ''"
              type="textarea"
              :autosize="{ minRows: 6, maxRows: 20 }"
              readonly
            />
          </template>

          <el-empty v-else-if="!executionError" description="等待请求" />
        </el-card>
      </el-col>
    </el-row>

    <el-dialog
      v-model="recordDialogVisible"
      title="调用记录详情"
      width="720px"
      destroy-on-close
    >
      <div v-if="recordDialogData" class="record-dialog">
        <div class="record-meta">
          <div>
            <span class="meta-label">记录 ID：</span>{{ recordDialogData.id }}
          </div>
          <div>
            <span class="meta-label">模板：</span>{{ resolveTemplateName(recordDialogData.template_id) }}
          </div>
          <div>
            <span class="meta-label">状态：</span>
            <el-tag :type="recordDialogData.status === 'success' ? 'success' : 'danger'" size="small">
              {{ recordDialogData.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </div>
          <div>
            <span class="meta-label">耗时：</span>{{ recordDialogData.latency_ms ?? '-' }} ms
          </div>
          <div>
            <span class="meta-label">创建时间：</span>{{ formatDate(recordDialogData.created_at) }}
          </div>
          <div>
            <span class="meta-label">更新时间：</span>{{ formatDate(recordDialogData.updated_at) }}
          </div>
        </div>

        <el-divider content-position="left">请求参数</el-divider>
        <el-table v-if="recordParameters.length" :data="recordParameters" border size="small">
          <el-table-column label="参数" prop="key" width="180" />
          <el-table-column label="值" prop="value" />
        </el-table>
        <div v-else class="record-empty">无参数</div>

        <el-divider content-position="left">提示词内容</el-divider>
        <el-input
          class="record-text"
          :value="recordDialogData.prompt"
          type="textarea"
          :autosize="{ minRows: 6, maxRows: 20 }"
          readonly
        />

        <el-divider content-position="left">响应内容</el-divider>
        <el-input
          class="record-text"
          :value="recordDialogData.response_text || recordDialogData.error_message || ''"
          type="textarea"
          :autosize="{ minRows: 6, maxRows: 20 }"
          readonly
        />
      </div>
      <template #footer>
        <el-button @click="recordDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="720px"
      destroy-on-close
    >
      <el-form
        v-loading="dialogLoading"
        ref="dialogFormRef"
        :model="dialogForm"
        :rules="dialogRules"
        label-width="110px"
        class="dialog-form"
      >
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="dialogForm.name" placeholder="请输入模板名称" maxlength="128" />
        </el-form-item>
        <el-form-item label="模板标识">
          <el-input v-model="dialogForm.slug" placeholder="可留空自动生成" maxlength="128" />
        </el-form-item>
        <el-form-item label="模板说明">
          <el-input
            v-model="dialogForm.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="可选"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="dialogForm.is_active" />
        </el-form-item>
        <el-form-item label="模板内容" prop="content">
          <el-input
            v-model="dialogForm.content"
            type="textarea"
            :autosize="{ minRows: 12, maxRows: 24 }"
            placeholder="在内容中使用 {param} 声明参数占位"
          />
        </el-form-item>
        <el-form-item label="自动识别参数">
          <el-tag
            v-for="param in dialogParamsPreview"
            :key="param"
            size="small"
            class="param-tag"
          >
            {{ param }}
          </el-tag>
          <span v-if="!dialogParamsPreview.length" class="param-empty">无</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="dialogSaving" @click="submitDialog">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  fetchGeminiTemplates,
  fetchGeminiTemplate,
  createGeminiTemplate,
  updateGeminiTemplate,
  deleteGeminiTemplate,
  executeGeminiPrompt,
  fetchGeminiRecords
} from '@/services/geminiConsole'
import type {
  GeminiTemplateSummary,
  GeminiTemplateDetail,
  GeminiPromptRecord,
  GeminiTemplatePayload,
  GeminiTemplateUpdatePayload
} from '@/types/geminiConsole'

const includeInactive = ref(false)
const templates = ref<GeminiTemplateSummary[]>([])
const templatesLoading = ref(false)
const selectedTemplateId = ref<number | null>(null)
const templateDetail = ref<GeminiTemplateDetail | null>(null)

const requestFormRef = ref<FormInstance>()
const requestForm = reactive({
  templateId: null as number | null
})
const requestRules: FormRules = {
  templateId: [{ required: true, message: '请选择模板', trigger: 'change' }]
}

const parameterValues = reactive<Record<string, string>>({})
const PARAM_REGEX = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g

const records = ref<GeminiPromptRecord[]>([])
const recordsLoading = ref(false)
const recordsLimit = 50
const recordDialogVisible = ref(false)
const recordDialogData = ref<GeminiPromptRecord | null>(null)

const executionLoading = ref(false)
const executionError = ref('')
const lastRecord = ref<GeminiPromptRecord | null>(null)

type RecordParameterItem = {
  key: string
  value: string
}

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogLoading = ref(false)
const dialogSaving = ref(false)
const dialogFormRef = ref<FormInstance>()
const dialogForm = reactive({
  id: null as number | null,
  name: '',
  slug: '',
  description: '',
  content: '',
  is_active: true
})
const dialogRules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }]
}

const dialogParamsPreview = computed(() => extractParameters(dialogForm.content))
const dialogTitle = computed(() => (dialogMode.value === 'create' ? '新建模板' : '编辑模板'))

const currentParameters = computed(() => templateDetail.value?.parameters ?? [])
const activeTemplates = computed(() => templates.value.filter((item) => item.is_active))
const promptPreview = computed(() => {
  if (!templateDetail.value) return ''
  return renderPrompt(templateDetail.value.content, parameterValues)
})

const templateMap = computed<Record<number, GeminiTemplateSummary>>(() => {
  const map: Record<number, GeminiTemplateSummary> = {}
  templates.value.forEach((item) => {
    map[item.id] = item
  })
  return map
})

watch(
  () => templateDetail.value,
  (detail) => {
    const keys = detail?.parameters ?? []
    syncParameterValues(keys)
    if (detail) {
      requestForm.templateId = detail.id
    } else {
      requestForm.templateId = null
    }
  },
  { immediate: true }
)

watch(selectedTemplateId, (id) => {
  if (id === null) {
    templateDetail.value = null
    requestForm.templateId = null
    parameterValuesClear()
    records.value = []
    recordDialogVisible.value = false
    recordDialogData.value = null
    return
  }
  loadTemplateDetail(id)
  loadRecords()
})

const formatDate = (value?: string | null) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const formatParamList = (params: string[]) => {
  if (!params?.length) return '无'
  return params.join(', ')
}

function renderPrompt(template: string, values: Record<string, string>) {
  return template.replace(PARAM_REGEX, (_, key: string) => values[key] ?? '')
}

function extractParameters(content: string): string[] {
  if (!content) return []
  const keys = new Set<string>()
  let match: RegExpExecArray | null
  while ((match = PARAM_REGEX.exec(content)) !== null) {
    keys.add(match[1])
  }
  PARAM_REGEX.lastIndex = 0
  return Array.from(keys).sort()
}

function syncParameterValues(keys: string[]) {
  const existing = { ...parameterValues }
  Object.keys(parameterValues).forEach((key) => {
    if (!keys.includes(key)) {
      delete parameterValues[key]
    }
  })
  keys.forEach((key) => {
    parameterValues[key] = existing[key] ?? ''
  })
}

function parameterValuesClear() {
  Object.keys(parameterValues).forEach((key) => delete parameterValues[key])
}

function resolveErrorMessage(error: any): string {
  if (!error) return '请求失败'
  const data = error?.data ?? error?.response?.data ?? null
  if (typeof data?.detail === 'string') return data.detail
  if (data?.detail?.message) return data.detail.message
  if (error?.message) return error.message
  if (error?.statusText) return error.statusText
  return '请求失败'
}

function resolveTemplateName(id: number) {
  return templateMap.value[id]?.name ?? `#${id}`
}

async function loadTemplates() {
  templatesLoading.value = true
  try {
    const list = await fetchGeminiTemplates({ includeInactive: includeInactive.value })
    templates.value = list
    if (!list.length) {
      selectedTemplateId.value = null
      return
    }
    if (!selectedTemplateId.value || !list.some((item) => item.id === selectedTemplateId.value)) {
      const fallback = list.find((item) => item.is_active) ?? list[0]
      selectedTemplateId.value = fallback.id
    }
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error))
  } finally {
    templatesLoading.value = false
  }
}

async function loadTemplateDetail(id: number) {
  try {
    const detail = await fetchGeminiTemplate(id)
    templateDetail.value = detail
  } catch (error) {
    templateDetail.value = null
    ElMessage.error(resolveErrorMessage(error))
  }
}

async function loadRecords() {
  if (selectedTemplateId.value === null) {
    records.value = []
    if (recordDialogVisible.value) {
      recordDialogVisible.value = false
      recordDialogData.value = null
    }
    return
  }
  recordsLoading.value = true
  try {
    records.value = await fetchGeminiRecords({
      templateId: selectedTemplateId.value ?? undefined,
      limit: recordsLimit
    })
    if (recordDialogData.value) {
      const refreshed = records.value.find((item) => item.id === recordDialogData.value?.id)
      if (refreshed) {
        recordDialogData.value = refreshed
      } else {
        recordDialogVisible.value = false
        recordDialogData.value = null
      }
    }
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error))
  } finally {
    recordsLoading.value = false
  }
}

function handleTemplateRowClick(row: GeminiTemplateSummary) {
  selectedTemplateId.value = row.id
}

function handleTemplateSelect(value: number | null) {
  selectedTemplateId.value = value
}

function handleIncludeInactiveChange() {
  loadTemplates()
}

function openCreateDialog() {
  dialogMode.value = 'create'
  dialogForm.id = null
  dialogForm.name = ''
  dialogForm.slug = ''
  dialogForm.description = ''
  dialogForm.content = ''
  dialogForm.is_active = true
  dialogVisible.value = true
  nextTick(() => dialogFormRef.value?.clearValidate())
}

async function openEditDialog(id: number) {
  dialogMode.value = 'edit'
  dialogLoading.value = true
  dialogVisible.value = true
  nextTick(() => dialogFormRef.value?.clearValidate())
  try {
    const detail = await fetchGeminiTemplate(id)
    dialogForm.id = detail.id
    dialogForm.name = detail.name
  dialogForm.slug = detail.slug ?? ''
    dialogForm.description = detail.description ?? ''
    dialogForm.content = detail.content
    dialogForm.is_active = detail.is_active
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error))
    dialogVisible.value = false
  } finally {
    dialogLoading.value = false
  }
}

async function removeTemplate(id: number) {
  try {
    await ElMessageBox.confirm('删除后不可恢复，确认删除该模板吗？', '提示', {
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    await deleteGeminiTemplate(id)
    ElMessage.success('删除成功')
    templates.value = templates.value.filter((item) => item.id !== id)
    if (selectedTemplateId.value === id) {
      selectedTemplateId.value = templates.value[0]?.id ?? null
    }
    loadRecords()
  } catch (error) {
    ElMessage.error(resolveErrorMessage(error))
  }
}

function closeDialog() {
  dialogVisible.value = false
}

function buildTemplatePayload(): GeminiTemplatePayload {
  const base = {
    name: dialogForm.name.trim(),
    slug: dialogForm.slug.trim() || null,
    description: dialogForm.description.trim() || null,
    content: dialogForm.content,
    is_active: dialogForm.is_active
  }
  return base
}

async function submitDialog() {
  if (!dialogFormRef.value) return
  dialogFormRef.value.validate(async (valid) => {
    if (!valid) return
    dialogSaving.value = true
    try {
      if (dialogMode.value === 'create') {
        const payload: GeminiTemplatePayload = buildTemplatePayload()
        const detail = await createGeminiTemplate(payload)
        templates.value = [detail, ...templates.value]
        selectedTemplateId.value = detail.id
        ElMessage.success('创建成功')
      } else if (dialogForm.id !== null) {
        const payload: GeminiTemplateUpdatePayload = buildTemplatePayload()
        const detail = await updateGeminiTemplate(dialogForm.id, payload)
        templates.value = templates.value.map((item) => (item.id === detail.id ? detail : item))
        if (selectedTemplateId.value === detail.id) {
          templateDetail.value = detail
        }
        ElMessage.success('更新成功')
      }
      dialogVisible.value = false
    } catch (error) {
      ElMessage.error(resolveErrorMessage(error))
    } finally {
      dialogSaving.value = false
    }
  })
}

async function submitRequest() {
  if (!requestFormRef.value) return
  requestFormRef.value.validate(async (valid) => {
    if (!valid || !requestForm.templateId) return

    executionLoading.value = true
    executionError.value = ''
    try {
      const params: Record<string, string> = {}
      currentParameters.value.forEach((key) => {
        const value = parameterValues[key]
        if (value !== undefined && value !== null) {
          params[key] = value
        }
      })

      const record = await executeGeminiPrompt({
        template_id: requestForm.templateId,
        parameters: params
      })
      lastRecord.value = record
      records.value = [record, ...records.value].slice(0, recordsLimit)
      if (recordDialogData.value?.id === record.id) {
        recordDialogData.value = record
      }
      ElMessage.success('请求成功')
    } catch (error) {
      executionError.value = resolveErrorMessage(error)
      ElMessage.error(executionError.value)
      await loadRecords()
    } finally {
      executionLoading.value = false
    }
  })
}

function resetResult() {
  lastRecord.value = null
  executionError.value = ''
}

function reloadRecords() {
  loadRecords()
}

function openRecordDialog(record: GeminiPromptRecord) {
  recordDialogData.value = record
  recordDialogVisible.value = true
}

const recordParameters = computed<RecordParameterItem[]>(() => {
  if (!recordDialogData.value?.parameters) return []
  return Object.entries(recordDialogData.value.parameters).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value, null, 2)
  }))
})

onMounted(async () => {
  await loadTemplates()
  if (selectedTemplateId.value !== null) {
    await loadTemplateDetail(selectedTemplateId.value)
    await loadRecords()
  }
})
</script>

<style scoped>
.gemini-console {
  gap: var(--layout-section-gap);
}

.console-layout {
  width: 100%;
}

.stretch-column {
  display: flex;
  flex-direction: column;
  gap: var(--layout-section-gap);
}

.templates-card,
.records-card,
.request-card,
.result-card {
  flex: none;
}

.templates-card :deep(.el-card__body),
.records-card :deep(.el-card__body) {
  padding: 0;
}

.request-card :deep(.el-card__body),
.result-card :deep(.el-card__body) {
  padding: var(--space-4);
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
}

.switch-label {
  font-size: var(--font-size-xs);
  color: var(--color-neutral-600);
}

.templates-table {
  cursor: pointer;
}

.template-radio {
  --el-radio-font-size: var(--font-size-sm);
}

.template-name {
  display: flex;
  align-items: center;
}

.records-card,
.templates-card {
  flex: 1;
}

.request-form {
  max-width: 640px;
}

.result-card {
  flex: 1;
}

.result-alert {
  margin-bottom: var(--space-3);
}

.result-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--space-2) var(--space-4);
  margin-bottom: var(--space-3);
  color: var(--color-neutral-700);
}

.meta-label {
  color: var(--color-neutral-600);
}

.result-text {
  margin-bottom: var(--space-4);
}

.record-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.record-meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-2) var(--space-4);
}

.record-empty {
  color: var(--color-neutral-500);
  padding: var(--space-3) 0;
}

.record-text {
  margin-bottom: 0;
}

.dialog-form {
  padding-top: var(--space-2);
}

.param-tag {
  margin-right: var(--space-2);
  margin-bottom: var(--space-2);
}

.param-empty {
  color: var(--color-neutral-500);
}

@media (max-width: 1024px) {
  .templates-card,
  .records-card,
  .request-card,
  .result-card {
    flex: none;
  }

  .templates-table {
    min-height: 320px;
  }
}
</style>
