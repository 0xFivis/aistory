import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { MediaAsset, MediaAssetPayload, MediaAssetQuery } from '@/types/asset'
import {
  fetchAssets,
  createAsset,
  updateAsset,
  deleteAsset,
  setDefaultAsset,
  fetchBgmAssets
} from '@/services/assets'
import { ElMessage } from 'element-plus'

export const useAssetStore = defineStore('asset', () => {
  const loading = ref(false)
  const items = ref<MediaAsset[]>([])
  const total = ref(0)
  const lastQuery = ref<MediaAssetQuery>({})
  const bgmItems = ref<MediaAsset[]>([])
  const bgmLoading = ref(false)
  const bgmLoaded = ref(false)

  const loadBgmAssets = async (options: { force?: boolean } = {}) => {
    const { force = false } = options
    if (bgmLoading.value) {
      return bgmItems.value
    }
    if (!force && bgmLoaded.value) {
      return bgmItems.value
    }

    bgmLoading.value = true
    try {
      const data = await fetchBgmAssets()
      bgmItems.value = data
      bgmLoaded.value = true
    } catch (error: any) {
      bgmLoaded.value = false
      ElMessage.error(error?.data?.detail ?? '加载背景音乐失败')
    } finally {
      bgmLoading.value = false
    }
    return bgmItems.value
  }

  const loadAssets = async (query: MediaAssetQuery = {}) => {
    loading.value = true
    try {
      lastQuery.value = { ...query }
      const data = await fetchAssets(query)
      items.value = data
      total.value = data.length
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '加载素材失败')
    } finally {
      loading.value = false
    }
  }

  const reload = async () => {
    await loadAssets(lastQuery.value)
  }

  const addAsset = async (payload: MediaAssetPayload) => {
    loading.value = true
    try {
      const data = await createAsset(payload)
      items.value = [data, ...items.value]
      total.value += 1
      ElMessage.success('素材已添加')
      if (data.asset_type === 'bgm') {
        await loadBgmAssets({ force: true })
      }
      return data
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '添加素材失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  const editAsset = async (id: number, payload: Partial<MediaAssetPayload>) => {
    loading.value = true
    try {
      const previous = items.value.find((item) => item.id === id)
      const data = await updateAsset(id, payload)
      const index = items.value.findIndex((item) => item.id === id)
      if (index >= 0) {
        items.value[index] = data
      }
      ElMessage.success('素材已更新')
      if (previous?.asset_type === 'bgm' || data.asset_type === 'bgm') {
        await loadBgmAssets({ force: true })
      }
      return data
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '更新素材失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  const removeAsset = async (id: number, softDelete = true) => {
    loading.value = true
    try {
      const target = items.value.find((item) => item.id === id)
      await deleteAsset(id, softDelete)
      items.value = items.value.filter((item) => item.id !== id)
      total.value = Math.max(total.value - 1, 0)
      ElMessage.success(softDelete ? '素材已禁用' : '素材已删除')
      if (target?.asset_type === 'bgm') {
        await loadBgmAssets({ force: true })
      }
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '删除素材失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  const markDefault = async (id: number) => {
    loading.value = true
    try {
      const target = items.value.find((item) => item.id === id)
      await setDefaultAsset(id)
      items.value = items.value.map((item) => ({
        ...item,
        is_default: item.id === id,
        is_active: item.id === id ? true : item.is_active
      }))
      ElMessage.success('已设为默认素材')
      if (target?.asset_type === 'bgm') {
        await loadBgmAssets({ force: true })
      }
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '设置默认失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    items,
    total,
    bgmItems,
    bgmLoading,
    loadAssets,
    loadBgmAssets,
    reload,
    addAsset,
    editAsset,
    removeAsset,
    markDefault
  }
})
