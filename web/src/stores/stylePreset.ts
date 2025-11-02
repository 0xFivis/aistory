import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchStylePresets,
  createStylePreset,
  updateStylePreset,
  deleteStylePreset
} from '@/services/stylePresets'
import type {
  StylePreset,
  StylePresetPayload,
  StylePresetUpdatePayload
} from '@/types/stylePreset'

export const useStylePresetStore = defineStore('stylePreset', () => {
  const presets = ref<StylePreset[]>([])
  const loading = ref(false)

  const activePresets = computed(() => presets.value.filter((preset) => preset.is_active))

  async function loadPresets(options: { includeInactive?: boolean } = {}) {
    loading.value = true
    try {
      presets.value = await fetchStylePresets({ includeInactive: options.includeInactive })
    } finally {
      loading.value = false
    }
  }

  async function addPreset(payload: StylePresetPayload) {
    const preset = await createStylePreset(payload)
    presets.value = [preset, ...presets.value]
    return preset
  }

  async function modifyPreset(id: number, payload: StylePresetUpdatePayload) {
    const preset = await updateStylePreset(id, payload)
    presets.value = presets.value.map((item) => (item.id === preset.id ? preset : item))
    return preset
  }

  async function removePreset(id: number, softDelete = true) {
    await deleteStylePreset(id, softDelete)
    if (softDelete) {
      presets.value = presets.value.map((item) =>
        item.id === id ? { ...item, is_active: false, updated_at: new Date().toISOString() } : item
      )
    } else {
      presets.value = presets.value.filter((item) => item.id !== id)
    }
  }

  return {
    presets,
    activePresets,
    loading,
    loadPresets,
    addPreset,
    modifyPreset,
    removePreset
  }
})
