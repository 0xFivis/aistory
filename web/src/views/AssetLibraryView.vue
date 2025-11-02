<template>
  <div class="asset-page page-container">
    <div class="asset-page__header section-header">
      <h2 class="section-title">素材库</h2>
      <el-button type="primary" @click="openCreateDialog">新增素材</el-button>
    </div>

    <el-card class="section-card asset-card" shadow="never">
      <el-form inline :model="filters" class="asset-filter">
        <el-form-item label="类型">
          <el-select
            v-model="filters.asset_type"
            placeholder="全部"
            clearable
            @change="handleFilter"
            @clear="handleFilter"
            style="width: 160px"
          >
            <el-option label="背景音乐" value="bgm" />
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="模板" value="template" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select
            v-model="filters.is_active"
            placeholder="全部"
            clearable
            @change="handleFilter"
            @clear="handleFilter"
            style="width: 160px"
          >
            <el-option label="启用" :value="true" />
            <el-option label="停用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="filters.keyword"
            placeholder="按名称搜索"
            clearable
            @keyup.enter="handleFilter"
            @clear="handleFilter"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="handleFilter">查询</el-button>
          <el-button text @click="resetFilter">重置</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="assets" stripe border v-loading="loading">
        <el-table-column label="#" type="index" width="60" align="center" />
        <el-table-column prop="asset_name" label="名称" min-width="160" />
        <el-table-column prop="asset_type" label="类型" width="110">
          <template #default="{ row }">
            <el-tag type="info">{{ renderTypeLabel(row.asset_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_full_url" label="资源链接" min-width="260">
          <template #default="{ row }">
            <a
              :href="row.file_full_url || row.file_url"
              target="_blank"
              rel="noopener noreferrer"
            >{{ row.file_full_url || row.file_url }}</a>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.duration">{{ formatDuration(row.duration) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_default" label="默认" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" align="center">
          <template #default="{ row }">
            <el-space wrap>
              <el-button size="small" type="primary" link @click="openEditDialog(row)">编辑</el-button>
              <el-button size="small" type="warning" link @click="toggleStatus(row)">
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" link @click="removeAsset(row)">删除</el-button>
              <el-button
                size="small"
                type="success"
                link
                :disabled="row.is_default"
                @click="setAsDefault(row)"
              >设为默认</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

  <el-dialog v-model="dialog.visible" :title="dialogTitle" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="名称" prop="asset_name">
          <el-input v-model="form.asset_name" placeholder="请输入素材名称" />
        </el-form-item>
        <el-form-item label="类型" prop="asset_type">
          <el-select v-model="form.asset_type" placeholder="请选择类型">
            <el-option label="背景音乐" value="bgm" />
            <el-option label="图片" value="image" />
            <el-option label="视频" value="video" />
            <el-option label="模板" value="template" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源来源">
          <el-radio-group v-model="form.sourceType" @change="onSourceTypeChange">
            <el-radio-button label="external">外部链接</el-radio-button>
            <el-radio-button label="upload">本地上传</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.sourceType === 'external'" label="资源链接" prop="file_url">
          <el-input v-model="form.file_url" placeholder="请输入资源链接" />
        </el-form-item>
        <el-form-item v-else label="上传文件" prop="file_url">
          <el-upload
            :show-file-list="false"
            :before-upload="beforeFileUpload"
            :http-request="handleFileUpload"
            :disabled="uploading"
          >
            <el-button type="primary" :loading="uploading">选择文件</el-button>
            <template #tip>
              <div class="upload-hint" v-if="form.file_url">
                <div>已上传路径：{{ form.file_url }}</div>
                <div v-if="uploadFullUrl">访问链接：{{ uploadFullUrl }}</div>
              </div>
              <div class="upload-hint" v-else>上传成功后将自动填写资源路径</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="form.tags"
            multiple
            placeholder="标签"
            filterable
            allow-create
            default-first-option
            collapse-tags
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :autosize="{ minRows: 3, maxRows: 5 }"
            placeholder="素材备注"
          />
        </el-form-item>
        <el-form-item label="默认">
          <el-switch v-model="form.is_default" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { storeToRefs } from 'pinia'
import type { FormInstance, FormRules, UploadRequestOptions } from 'element-plus'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useAssetStore } from '@/stores/asset'
import type {
  MediaAsset,
  MediaAssetPayload,
  MediaAssetType,
  MediaAssetUploadResponse
} from '@/types/asset'
import { uploadAssetFile } from '@/services/assets'

type SourceType = 'external' | 'upload'

type AssetForm = {
  asset_type: MediaAssetType
  asset_name: string
  file_url: string
  file_path?: string | null
  tags: string[]
  description: string
  is_default: boolean
  is_active: boolean
  sourceType: SourceType
}

const assetStore = useAssetStore()
const { items: assets, loading } = storeToRefs(assetStore)

const filters = reactive({
  asset_type: null as MediaAssetType | null,
  keyword: '',
  is_active: null as boolean | null,
  limit: 100,
  offset: 0
})

const dialog = reactive({
  visible: false,
  mode: 'create' as 'create' | 'edit',
  currentId: 0
})

const formRef = ref<FormInstance>()
const form = reactive<AssetForm>({
  asset_type: 'bgm',
  asset_name: '',
  file_url: '',
  file_path: undefined,
  tags: [],
  description: '',
  is_default: false,
  is_active: true,
  sourceType: 'upload'
})
const saving = ref(false)
const uploading = ref(false)
const uploadFullUrl = ref('')
const skipSourceTypeChange = ref(false)

const isExternalUrl = (value: string) => /^https?:\/\//i.test(value || '')

const dialogTitle = computed(() => (dialog.mode === 'create' ? '新增素材' : '编辑素材'))

const rules: FormRules = {
  asset_name: [{ required: true, message: '请输入素材名称', trigger: 'blur' }],
  asset_type: [{ required: true, message: '请选择素材类型', trigger: 'change' }],
  file_url: [
    {
      validator: (_rule, value, callback) => {
        if (form.sourceType === 'external') {
          const url = (value || '').trim()
          if (!url) {
            callback(new Error('请输入资源链接'))
            return
          }
          if (!isExternalUrl(url)) {
            callback(new Error('请输入以 http 或 https 开头的链接'))
            return
          }
        } else if (form.sourceType === 'upload') {
          if (!value) {
            callback(new Error('请先上传文件'))
            return
          }
        }
        callback()
      },
      trigger: 'change'
    }
  ]
}

const renderTypeLabel = (type: MediaAssetType) => {
  const map: Record<MediaAssetType, string> = {
    bgm: '背景音乐',
    image: '图片',
    video: '视频',
    template: '模板'
  }
  return map[type] ?? type
}

const formatDuration = (seconds?: number | null) => {
  if (!seconds || seconds <= 0) return ''
  const minutes = Math.floor(seconds / 60)
  const remain = Math.floor(seconds % 60)
  return `${String(minutes).padStart(2, '0')}:${String(remain).padStart(2, '0')}`
}

const onSourceTypeChange = () => {
  if (skipSourceTypeChange.value) {
    return
  }
  form.file_url = ''
  form.file_path = undefined
  uploadFullUrl.value = ''
  formRef.value?.clearValidate?.(['file_url'])
}

const beforeFileUpload = () => {
  if (!form.asset_type) {
    ElMessage.warning('请先选择素材类型')
    return false
  }
  return true
}

const handleFileUpload = async (options: UploadRequestOptions) => {
  if (!beforeFileUpload()) {
    return
  }

  uploading.value = true
  try {
    const result: MediaAssetUploadResponse = await uploadAssetFile(
      form.asset_type,
      options.file as File
    )
    form.file_url = result.api_path
    form.file_path = result.file_path
    uploadFullUrl.value = result.full_url ?? ''
    form.sourceType = 'upload'
    formRef.value?.validateField?.('file_url')
    options.onSuccess?.(result as any)
    ElMessage.success('文件上传成功')
  } catch (error: any) {
    const message = error?.data?.detail ?? error?.message ?? '上传失败'
    const failure = error instanceof Error ? error : new Error(message)
    options.onError?.(failure as any)
    ElMessage.error(message)
  } finally {
    uploading.value = false
  }
}

const loadData = () => {
  assetStore.loadAssets({
    asset_type: filters.asset_type ?? undefined,
    keyword: filters.keyword || undefined,
    is_active: filters.is_active === null ? undefined : filters.is_active,
    limit: filters.limit,
    offset: filters.offset
  })
}

onMounted(() => {
  loadData()
})

const handleFilter = () => {
  filters.offset = 0
  loadData()
}

const resetFilter = () => {
  filters.asset_type = null
  filters.keyword = ''
  filters.is_active = null
  filters.offset = 0
  loadData()
}

const openCreateDialog = () => {
  dialog.mode = 'create'
  dialog.currentId = 0
  skipSourceTypeChange.value = true
  form.asset_type = 'bgm'
  form.asset_name = ''
  form.file_url = ''
  form.file_path = undefined
  form.tags = []
  form.description = ''
  form.is_default = false
  form.is_active = true
  form.sourceType = 'upload'
  uploadFullUrl.value = ''
  dialog.visible = true
  nextTick(() => {
    skipSourceTypeChange.value = false
    formRef.value?.clearValidate?.()
  })
}

const openEditDialog = (asset: MediaAsset) => {
  dialog.mode = 'edit'
  dialog.currentId = asset.id
  skipSourceTypeChange.value = true
  const external = isExternalUrl(asset.file_url)
  form.asset_type = asset.asset_type
  form.asset_name = asset.asset_name
  form.file_url = asset.file_url ?? ''
  form.file_path = asset.file_path ?? undefined
  form.tags = asset.tags ? [...asset.tags] : []
  form.description = asset.description ?? ''
  form.is_default = asset.is_default
  form.is_active = asset.is_active
  form.sourceType = external ? 'external' : 'upload'
  uploadFullUrl.value = asset.file_full_url ?? (external ? asset.file_url : '')
  dialog.visible = true
  nextTick(() => {
    skipSourceTypeChange.value = false
    formRef.value?.clearValidate?.()
  })
}

const closeDialog = () => {
  dialog.visible = false
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return

    const trimmedName = form.asset_name.trim()
    const trimmedUrl = form.file_url.trim()
    const trimmedDescription = form.description?.trim() ?? ''

    const payload: MediaAssetPayload = {
      asset_type: form.asset_type,
      asset_name: trimmedName,
      file_url: trimmedUrl,
      tags: [...form.tags],
      description: trimmedDescription,
      is_default: form.is_default,
      is_active: form.is_active
    }

    if (form.sourceType === 'upload') {
      payload.file_path = form.file_path ?? undefined
    }

    saving.value = true
    try {
      if (dialog.mode === 'create') {
        await assetStore.addAsset(payload)
      } else {
        await assetStore.editAsset(dialog.currentId, payload)
      }
      dialog.visible = false
      await assetStore.reload()
    } finally {
      saving.value = false
    }
  })
}

const toggleStatus = async (asset: MediaAsset) => {
  if (asset.is_active) {
    await assetStore.removeAsset(asset.id, true)
  } else {
    await assetStore.editAsset(asset.id, { is_active: true })
    ElMessage.success('已启用素材')
  }
  await assetStore.reload()
}

const removeAsset = async (asset: MediaAsset) => {
  await ElMessageBox.confirm(`确定要删除素材 “${asset.asset_name}” 吗？`, '提示', {
    type: 'warning'
  })
  await assetStore.removeAsset(asset.id, false)
  await assetStore.reload()
}

const setAsDefault = async (asset: MediaAsset) => {
  await assetStore.markDefault(asset.id)
  await assetStore.reload()
}
</script>

<style scoped>
.asset-page {
  gap: var(--layout-section-gap);
}

.asset-page__header {
  align-items: center;
}

.asset-card :deep(.el-card__body) {
  padding: var(--space-4);
}

.asset-filter {
  margin-bottom: var(--space-3);
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.asset-filter :deep(.el-form-item) {
  margin-right: 0;
  margin-bottom: 0;
}

.upload-hint {
  margin-top: var(--space-2);
  color: var(--color-neutral-600);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

@media (max-width: 768px) {
  .asset-filter {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
