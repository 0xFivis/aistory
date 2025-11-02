<template>
  <div class="page">
    <el-card class="panel-card" shadow="hover">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="服务凭证" name="credentials">
          <div class="toolbar">
            <el-space :size="12" wrap>
              <el-button type="primary" @click="openCredentialDialog('create')">新增凭证</el-button>
              <el-button type="primary" @click="() => $router.push('/service-config/gemini-keys')">管理 Gemini Keys</el-button>
              <el-button :loading="loadingCredentials" @click="reloadCredentials">刷新</el-button>
              <el-select
                v-model="credentialFilters.service"
                clearable
                placeholder="按服务筛选"
                style="width: 160px"
                @change="reloadCredentials"
              >
                <el-option
                  v-for="item in serviceNameOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
              <el-checkbox v-model="credentialFilters.includeInactive" @change="reloadCredentials">
                显示禁用
              </el-checkbox>
            </el-space>
          </div>
          <el-table
            :data="serviceCredentials"
            v-loading="loadingCredentials"
            border
            stripe
            style="width: 100%"
          >
            <el-table-column prop="service_name" label="服务" width="160" />
            <el-table-column prop="credential_type" label="凭证类型" width="140" />
            <el-table-column label="凭证" min-width="220">
              <template #default="{ row }">
                {{ row.credential_key || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="API 地址" min-width="200">
              <template #default="{ row }">
                {{ row.api_url || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="200">
              <template #default="{ row }">
                <span>{{ row.description || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="更新时间" width="180" align="center">
              <template #default="{ row }">
                {{ formatDate(row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openCredentialDialog('edit', row)">
                  编辑
                </el-button>
                <el-button
                  size="small"
                  type="warning"
                  @click="toggleCredential(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
                <el-button size="small" type="danger" @click="removeCredential(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="服务选项" name="options">
          <div class="toolbar">
            <el-space :size="12" wrap>
              <el-button type="primary" @click="openOptionDialog('create')">新增选项</el-button>
              <el-button :loading="loadingOptions" @click="reloadOptions">刷新</el-button>
              <el-select
                v-model="optionFilters.service"
                clearable
                placeholder="按服务筛选"
                style="width: 160px"
                @change="reloadOptions"
              >
                <el-option
                  v-for="item in serviceNameOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
              <el-select
                v-model="optionFilters.type"
                clearable
                placeholder="选项类型"
                style="width: 160px"
                @change="reloadOptions"
              >
                <el-option
                  v-for="item in optionTypeOptions"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>
              <el-checkbox v-model="optionFilters.includeInactive" @change="reloadOptions">
                显示禁用
              </el-checkbox>
            </el-space>
          </div>
          <el-table
            :data="serviceOptions"
            v-loading="loadingOptions"
            border
            stripe
            style="width: 100%"
          >
            <el-table-column prop="service_name" label="服务" width="140" />
            <el-table-column prop="option_type" label="类型" width="140" />
            <el-table-column prop="option_key" label="键" min-width="120" />
            <el-table-column prop="option_value" label="值" min-width="160" />
            <el-table-column label="名称" min-width="160">
              <template #default="{ row }">
                {{ row.option_name || '-' }}
              </template>
            </el-table-column>
            <el-table-column label="默认" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_default ? 'success' : 'info'">
                  {{ row.is_default ? '默认' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="说明" min-width="200">
              <template #default="{ row }">
                <span>{{ row.description || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="元数据" min-width="200">
              <template #default="{ row }">
                <code v-if="row.meta_data">{{ renderMeta(row.meta_data) }}</code>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="300" fixed="right" align="center">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="openOptionDialog('edit', row)">
                  编辑
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  :disabled="row.is_default"
                  @click="setDefaultOption(row)"
                >
                  设为默认
                </el-button>
                <el-button
                  size="small"
                  type="warning"
                  @click="toggleOption(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
                <el-button size="small" type="danger" @click="removeOption(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog
      v-model="credentialDialog.visible"
      :title="credentialDialog.mode === 'create' ? '新增服务凭证' : '编辑服务凭证'"
      width="520px"
      destroy-on-close
    >
      <el-form
        ref="credentialFormRef"
        :model="credentialForm"
        :rules="credentialRules"
        label-width="120px"
      >
        <el-form-item label="服务名称" prop="service_name">
          <el-input v-model="credentialForm.service_name" placeholder="例如 gemini" />
        </el-form-item>
        <el-form-item label="凭证类型" prop="credential_type">
          <el-input v-model="credentialForm.credential_type" placeholder="例如 api_key" />
        </el-form-item>
        <el-form-item label="凭证 Key">
          <el-input v-model="credentialForm.credential_key" placeholder="API Key 或 Access Key" />
        </el-form-item>
        <el-form-item label="凭证 Secret">
          <el-input v-model="credentialForm.credential_secret" placeholder="Secret，可留空" />
        </el-form-item>
        <el-form-item label="API URL">
          <el-input v-model="credentialForm.api_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="credentialForm.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="使用说明"
          />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="credentialForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="credentialDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="credentialDialog.saving" @click="submitCredential">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="optionDialog.visible"
      :title="optionDialog.mode === 'create' ? '新增服务选项' : '编辑服务选项'"
      width="640px"
      destroy-on-close
    >
      <el-form ref="optionFormRef" :model="optionForm" :rules="optionRules" label-width="120px">
        <el-form-item label="服务名称" prop="service_name">
          <el-input v-model="optionForm.service_name" placeholder="例如 gemini" />
        </el-form-item>
        <el-form-item label="选项类型" prop="option_type">
          <el-input v-model="optionForm.option_type" placeholder="例如 model_id" />
        </el-form-item>
        <el-form-item label="选项键" prop="option_key">
          <el-input v-model="optionForm.option_key" placeholder="唯一键" />
        </el-form-item>
        <el-form-item label="选项值" prop="option_value">
          <el-input v-model="optionForm.option_value" placeholder="具体值" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="optionForm.option_name" placeholder="可选" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="optionForm.description"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="说明"
          />
        </el-form-item>
        <el-form-item label="附加元数据">
          <el-input
            v-model="optionForm.metaText"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 6 }"
            placeholder="JSON 对象，可选"
          />
        </el-form-item>
        <el-form-item label="设为默认">
          <el-switch v-model="optionForm.is_default" />
        </el-form-item>
        <el-form-item label="立即启用">
          <el-switch v-model="optionForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="optionDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="optionDialog.saving" @click="submitOption">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useServiceConfigStore } from '@/stores/serviceConfig'
import type {
  ServiceCredential,
  ServiceCredentialPayload,
  ServiceOption,
  ServiceOptionPayload
} from '@/types/serviceConfig'

const serviceNameOptions = ['gemini', 'fishaudio', 'liblib', 'nca', 'fal', 'cloudinary', 'runninghub']
const optionTypeOptions = ['model_id', 'voice_id', 'lora_id', 'style_preset']

const serviceConfigStore = useServiceConfigStore()
const { credentials, options, loadingCredentials, loadingOptions } = storeToRefs(serviceConfigStore)

const activeTab = ref<'credentials' | 'options'>('credentials')
const credentialFilters = reactive({ service: '', includeInactive: true })
const optionFilters = reactive({ service: '', type: '', includeInactive: true })

const serviceCredentials = computed(() => credentials.value)
const serviceOptions = computed(() => options.value)

const credentialFormRef = ref<FormInstance>()
const credentialDialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', saving: false })
const editingCredential = ref<ServiceCredential | null>(null)

const credentialForm = reactive({
  service_name: '',
  credential_type: 'api_key',
  credential_key: '',
  credential_secret: '',
  api_url: '',
  description: '',
  is_active: true
})

const credentialRules: FormRules = {
  service_name: [{ required: true, message: '请输入服务名称', trigger: 'blur' }],
  credential_type: [{ required: true, message: '请输入凭证类型', trigger: 'blur' }]
}

const optionFormRef = ref<FormInstance>()
const optionDialog = reactive({ visible: false, mode: 'create' as 'create' | 'edit', saving: false })
const editingOption = ref<ServiceOption | null>(null)

const optionForm = reactive({
  service_name: '',
  option_type: '',
  option_key: '',
  option_value: '',
  option_name: '',
  description: '',
  metaText: '',
  is_default: false,
  is_active: true
})

const optionRules: FormRules = {
  service_name: [{ required: true, message: '请输入服务名称', trigger: 'blur' }],
  option_type: [{ required: true, message: '请输入选项类型', trigger: 'blur' }],
  option_key: [{ required: true, message: '请输入选项键', trigger: 'blur' }],
  option_value: [{ required: true, message: '请输入选项值', trigger: 'blur' }]
}

onMounted(async () => {
  await Promise.all([reloadCredentials(), reloadOptions()])
})

function normalizeText(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

async function reloadCredentials() {
  await serviceConfigStore.loadCredentials({
    serviceName: credentialFilters.service || undefined,
    isActive: credentialFilters.includeInactive ? undefined : true
  })
}

async function reloadOptions() {
  await serviceConfigStore.loadOptions({
    serviceName: optionFilters.service || undefined,
    optionType: optionFilters.type || undefined,
    isActive: optionFilters.includeInactive ? undefined : true
  })
}

function resetCredentialForm() {
  credentialForm.service_name = ''
  credentialForm.credential_type = 'api_key'
  credentialForm.credential_key = ''
  credentialForm.credential_secret = ''
  credentialForm.api_url = ''
  credentialForm.description = ''
  credentialForm.is_active = true
}

function openCredentialDialog(mode: 'create' | 'edit', record?: ServiceCredential) {
  credentialDialog.mode = mode
  credentialDialog.visible = true
  credentialDialog.saving = false
  editingCredential.value = record ?? null
  if (mode === 'edit' && record) {
    credentialForm.service_name = record.service_name
    credentialForm.credential_type = record.credential_type
    credentialForm.credential_key = record.credential_key ?? ''
    credentialForm.credential_secret = ''
    credentialForm.api_url = record.api_url ?? ''
    credentialForm.description = record.description ?? ''
    credentialForm.is_active = record.is_active
  } else {
    resetCredentialForm()
  }
  nextTick(() => credentialFormRef.value?.clearValidate())
}

async function submitCredential() {
  if (!credentialFormRef.value) return
  credentialFormRef.value.validate(async (valid) => {
    if (!valid) return
    credentialDialog.saving = true
    try {
      const payload: ServiceCredentialPayload = {
        service_name: credentialForm.service_name.trim(),
        credential_type: credentialForm.credential_type.trim(),
        credential_key: normalizeText(credentialForm.credential_key),
        credential_secret: normalizeText(credentialForm.credential_secret),
        api_url: normalizeText(credentialForm.api_url),
        description: normalizeText(credentialForm.description),
        is_active: credentialForm.is_active
      }

      if (credentialDialog.mode === 'create') {
        await serviceConfigStore.addCredential(payload)
        ElMessage.success('凭证创建成功')
      } else if (editingCredential.value) {
        const updatePayload = Object.fromEntries(
          Object.entries(payload).filter(([key, value]) => {
            if (value === undefined) return false
            if (!editingCredential.value) return true
            const current = (editingCredential.value as Record<string, unknown>)[key]
            return value !== current
          })
        )
        await serviceConfigStore.modifyCredential(editingCredential.value.id, updatePayload)
        ElMessage.success('凭证更新成功')
      }
      credentialDialog.visible = false
      await reloadCredentials()
    } finally {
      credentialDialog.saving = false
    }
  })
}

async function toggleCredential(record: ServiceCredential) {
  const targetState = !record.is_active
  console.debug('Opening confirm for toggleCredential', record.id, targetState)
  await ElMessageBox.confirm(`确定${targetState ? '启用' : '禁用'}该凭证?`, '提示', {
    type: 'warning',
    confirmButtonClass: 'el-button--primary',
    customClass: 'confirm-dialog'
  })
  console.debug('Confirm resolved, modifying credential', record.id, targetState)
  await serviceConfigStore.modifyCredential(record.id, { is_active: targetState })
  ElMessage.success(`已${targetState ? '启用' : '禁用'}`)
  await reloadCredentials()
}

async function removeCredential(record: ServiceCredential) {
  console.debug('Opening confirm for removeCredential', record.id)
  await ElMessageBox.confirm(`确定删除服务凭证「${record.service_name}」吗？`, '删除确认', {
    type: 'error',
    confirmButtonClass: 'el-button--danger',
    customClass: 'confirm-dialog'
  })
  console.debug('Confirm resolved, removing credential', record.id)
  await serviceConfigStore.removeCredential(record.id)
  ElMessage.success('凭证已删除')
  await reloadCredentials()
}

function resetOptionForm() {
  optionForm.service_name = ''
  optionForm.option_type = ''
  optionForm.option_key = ''
  optionForm.option_value = ''
  optionForm.option_name = ''
  optionForm.description = ''
  optionForm.metaText = ''
  optionForm.is_default = false
  optionForm.is_active = true
}

function openOptionDialog(mode: 'create' | 'edit', record?: ServiceOption) {
  optionDialog.mode = mode
  optionDialog.visible = true
  optionDialog.saving = false
  editingOption.value = record ?? null
  if (mode === 'edit' && record) {
    optionForm.service_name = record.service_name
    optionForm.option_type = record.option_type
    optionForm.option_key = record.option_key
    optionForm.option_value = record.option_value
    optionForm.option_name = record.option_name ?? ''
    optionForm.description = record.description ?? ''
    optionForm.metaText = record.meta_data ? JSON.stringify(record.meta_data, null, 2) : ''
    optionForm.is_default = record.is_default
    optionForm.is_active = record.is_active
  } else {
    resetOptionForm()
  }
  nextTick(() => optionFormRef.value?.clearValidate())
}

function parseMetaText(value: string): Record<string, unknown> | null {
  const text = value.trim()
  if (!text) return null
  try {
    const parsed = JSON.parse(text)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>
    }
  } catch (error) {
    throw new Error('元数据需要是合法的 JSON 对象')
  }
  throw new Error('元数据需要是合法的 JSON 对象')
}

async function submitOption() {
  if (!optionFormRef.value) return
  optionFormRef.value.validate(async (valid) => {
    if (!valid) return
    optionDialog.saving = true
    let meta: Record<string, unknown> | null = null
    try {
      meta = optionForm.metaText ? parseMetaText(optionForm.metaText) : null
    } catch (error: any) {
      optionDialog.saving = false
      ElMessage.error(error.message || '元数据格式错误')
      return
    }

    try {
      const payload: ServiceOptionPayload = {
        service_name: optionForm.service_name.trim(),
        option_type: optionForm.option_type.trim(),
        option_key: optionForm.option_key.trim(),
        option_value: optionForm.option_value.trim(),
        option_name: normalizeText(optionForm.option_name) ?? undefined,
        description: normalizeText(optionForm.description) ?? undefined,
        meta_data: meta ?? undefined,
        is_default: optionForm.is_default,
        is_active: optionForm.is_active
      }

      if (optionDialog.mode === 'create') {
        await serviceConfigStore.addOption(payload)
        ElMessage.success('服务选项创建成功')
      } else if (editingOption.value) {
        const updatePayload = Object.fromEntries(
          Object.entries(payload).filter(([key, value]) => {
            if (value === undefined) return false
            const current = (editingOption.value as Record<string, unknown>)[key]
            return value !== current
          })
        )
        await serviceConfigStore.modifyOption(editingOption.value.id, updatePayload)
        ElMessage.success('服务选项更新成功')
      }
      optionDialog.visible = false
      await reloadOptions()
    } finally {
      optionDialog.saving = false
    }
  })
}

async function toggleOption(record: ServiceOption) {
  const targetState = !record.is_active
  console.debug('Opening confirm for toggleOption', record.id, targetState)
  await ElMessageBox.confirm(`确定${targetState ? '启用' : '禁用'}该选项?`, '提示', {
    type: 'warning',
    confirmButtonClass: 'el-button--primary',
    customClass: 'confirm-dialog'
  })
  console.debug('Confirm resolved, modifying option', record.id, targetState)
  await serviceConfigStore.modifyOption(record.id, { is_active: targetState })
  ElMessage.success(`已${targetState ? '启用' : '禁用'}`)
  await reloadOptions()
}

async function setDefaultOption(record: ServiceOption) {
  console.debug('Opening confirm for setDefaultOption', record.id)
  await ElMessageBox.confirm(`确定将该选项设为默认吗？`, '提示', {
    type: 'warning',
    confirmButtonClass: 'el-button--primary',
    customClass: 'confirm-dialog'
  })
  console.debug('Confirm resolved, setting default option', record.id)
  await serviceConfigStore.modifyOption(record.id, { is_default: true })
  ElMessage.success('默认选项已更新')
  await reloadOptions()
}

async function removeOption(record: ServiceOption) {
  console.debug('Opening confirm for removeOption', record.id)
  await ElMessageBox.confirm(`确定删除选项「${record.option_key}」吗？`, '删除确认', {
    type: 'error',
    confirmButtonClass: 'el-button--danger',
    customClass: 'confirm-dialog'
  })
  console.debug('Confirm resolved, removing option', record.id)
  await serviceConfigStore.removeOption(record.id)
  ElMessage.success('选项已删除')
  await reloadOptions()
}

function renderMeta(meta: Record<string, unknown>): string {
  try {
    return JSON.stringify(meta)
  } catch (error) {
    return '[invalid meta]'
  }
}

function formatDate(value?: string | null): string {
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

.panel-card {
  border-radius: 12px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar :deep(.el-space) {
  flex-wrap: wrap;
}

code {
  font-size: 12px;
  white-space: nowrap;
}

/* confirm dialog styles */
.confirm-dialog {
  min-width: 320px;
  max-width: 90vw;
  text-align: center;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.12);
  background: var(--el-color-white, #fff);
}
.confirm-dialog .el-message-box__content {
  padding: 12px 16px;
}
.confirm-dialog .el-message-box__btns {
  justify-content: center;
  gap: 12px;
}
.confirm-dialog .el-button {
  min-width: 80px;
}
.el-message-box__wrapper {
  z-index: 2000; /* ensure above other elements */
}
.el-message-box__mask {
  background: rgba(0,0,0,0.35); /* darken overlay */
}
</style>
