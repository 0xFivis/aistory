<template>
  <div class="page page-container subtitle-style-page">
    <el-card class="section-card toolbar-card" shadow="never">
      <div class="section-header">
        <div class="section-title">字幕样式管理</div>
        <div class="toolbar-actions">
          <el-space size="12">
            <el-button type="primary" @click="goCreate">新增样式</el-button>
            <el-button :loading="loading" @click="reload">刷新</el-button>
            <el-button @click="goBack">返回任务列表</el-button>
          </el-space>
          <el-space size="12">
            <el-input
              v-model="keyword"
              class="keyword-input"
              size="small"
              placeholder="搜索名称或描述"
              clearable
              @clear="handleKeywordChange"
              @keyup.enter="handleKeywordChange"
            />
            <el-space size="8" class="switch-wrapper">
              <span class="switch-label">显示禁用</span>
              <el-switch v-model="includeInactive" @change="handleIncludeInactiveChange" />
            </el-space>
          </el-space>
        </div>
      </div>
    </el-card>

    <el-card class="section-card table-card" shadow="never">
      <el-table
        class="subtitle-style-table"
        :data="styles"
        v-loading="loading"
        border
        stripe
        highlight-current-row
      >
        <el-table-column prop="name" label="名称" width="220" fixed="left" show-overflow-tooltip />
        <el-table-column label="描述" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.description || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="默认" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="引用次数" width="110" align="center">
          <template #default="{ row }">
            {{ row.usage_count }}
          </template>
        </el-table-column>
        <el-table-column label="示例文本" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.sample_text || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="420" fixed="right" align="center">
          <template #default="{ row }">
            <el-space>
              <el-button size="small" type="primary" @click="goEdit(row.id)">编辑</el-button>
              <el-button size="small" @click="openPreview(row)">预览</el-button>
              <el-button size="small" type="success" plain @click="duplicate(row)">复制</el-button>
              <el-button size="small" type="warning" @click="toggleActive(row)">
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                :disabled="row.usage_count > 0 || row.is_default"
                @click="remove(row)"
              >删除</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <SubtitleStylePreview
      v-model="previewVisible"
      :style-data="activePreviewStyle"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { useSubtitleStyleStore } from '@/stores/subtitleStyle'
import type { SubtitleStyle } from '@/types/subtitleStyle'
import SubtitleStylePreview from '@/components/subtitle/SubtitleStylePreview.vue'

const router = useRouter()
const subtitleStyleStore = useSubtitleStyleStore()
const { styles, loading } = storeToRefs(subtitleStyleStore)

const includeInactive = ref(false)
const keyword = ref('')
const previewVisible = ref(false)
const activeStyle = ref<SubtitleStyle | null>(null)

const activePreviewStyle = computed(() => activeStyle.value)

const formatDate = (value: string | null | undefined) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const loadStyles = async () => {
  try {
    await subtitleStyleStore.loadStyles({
      includeInactive: includeInactive.value,
      keyword: keyword.value.trim() || undefined
    })
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '加载字幕样式失败')
  }
}

const reload = async () => {
  await loadStyles()
}

const handleIncludeInactiveChange = async () => {
  await loadStyles()
}

const handleKeywordChange = async () => {
  await loadStyles()
}

const goBack = () => {
  router.push({ name: 'home' })
}

const goCreate = () => {
  router.push({ name: 'subtitle-style-create' })
}

const goEdit = (id: number) => {
  router.push({ name: 'subtitle-style-edit', params: { id } })
}

const openPreview = (style: SubtitleStyle) => {
  activeStyle.value = style
  previewVisible.value = true
}

const toggleActive = async (style: SubtitleStyle) => {
  try {
    await subtitleStyleStore.modifyStyle(style.id, {
      is_active: !style.is_active,
      is_default: style.is_active ? false : style.is_default
    })
    ElMessage.success(style.is_active ? '已禁用' : '已启用')
    await loadStyles()
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '更新状态失败')
  }
}

const duplicate = async (style: SubtitleStyle) => {
  try {
    const result = await subtitleStyleStore.duplicateStyle(style.id, {
      name: `${style.name} 副本`,
      is_active: true
    })
    ElMessage.success(`已复制为 ${result.name}`)
    await loadStyles()
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '复制失败')
  }
}

const remove = async (style: SubtitleStyle) => {
  if (style.usage_count > 0) {
    ElMessage.warning('仍有任务引用该样式，无法删除')
    return
  }
  if (style.is_default) {
    ElMessage.warning('默认样式无法删除，请先取消默认')
    return
  }
  try {
    await ElMessageBox.confirm('确认删除该字幕样式？此操作不可恢复。', '提示', {
      type: 'warning'
    })
    await subtitleStyleStore.removeStyle(style.id, false)
    ElMessage.success('字幕样式已删除')
    await loadStyles()
  } catch (error: any) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error(error?.data?.detail ?? error?.message ?? '删除失败')
  }
}

onMounted(() => {
  void loadStyles()
})
</script>

<style scoped>
.subtitle-style-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.toolbar-card {
  padding-bottom: 8px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.switch-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.switch-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.keyword-input {
  width: 220px;
}

.subtitle-style-table {
  width: 100%;
}
</style>
