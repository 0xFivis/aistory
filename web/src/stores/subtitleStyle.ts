import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchSubtitleStyles,
  createSubtitleStyle,
  updateSubtitleStyle,
  deleteSubtitleStyle,
  cloneSubtitleStyle
} from '@/services/subtitleStyles'
import type {
  SubtitleStyle,
  SubtitleStylePayload,
  SubtitleStyleUpdatePayload
} from '@/types/subtitleStyle'
import type { SubtitleStyleClonePayload } from '@/services/subtitleStyles'

export const useSubtitleStyleStore = defineStore('subtitleStyle', () => {
  const styles = ref<SubtitleStyle[]>([])
  const loading = ref(false)

  const activeStyles = computed(() => styles.value.filter((item) => item.is_active))

  async function loadStyles(options: { includeInactive?: boolean; keyword?: string } = {}) {
    loading.value = true
    try {
      styles.value = await fetchSubtitleStyles({
        includeInactive: options.includeInactive,
        keyword: options.keyword
      })
    } finally {
      loading.value = false
    }
  }

  async function addStyle(payload: SubtitleStylePayload) {
    const style = await createSubtitleStyle(payload)
    styles.value = [
      style,
      ...styles.value.map((item) => (style.is_default ? { ...item, is_default: false } : item))
    ]
    return style
  }

  async function modifyStyle(id: number, payload: SubtitleStyleUpdatePayload) {
    const style = await updateSubtitleStyle(id, payload)
    styles.value = styles.value.map((item) => {
      if (item.id === style.id) return style
      if (style.is_default) return { ...item, is_default: false }
      return item
    })
    return style
  }

  async function duplicateStyle(id: number, payload?: SubtitleStyleClonePayload) {
    const style = await cloneSubtitleStyle(id, payload)
    styles.value = [style, ...styles.value]
    return style
  }

  async function removeStyle(id: number, softDelete = true) {
    await deleteSubtitleStyle(id, softDelete)
    if (softDelete) {
      styles.value = styles.value.map((item) =>
        item.id === id
          ? {
              ...item,
              is_active: false,
              is_default: false,
              updated_at: new Date().toISOString()
            }
          : item
      )
    } else {
      styles.value = styles.value.filter((item) => item.id !== id)
    }
  }

  function findById(id: number | undefined | null): SubtitleStyle | null {
    if (!id) return null
    return styles.value.find((item) => item.id === id) ?? null
  }

  return {
    styles,
    activeStyles,
    loading,
    loadStyles,
    addStyle,
    modifyStyle,
    duplicateStyle,
    removeStyle,
    findById
  }
})
