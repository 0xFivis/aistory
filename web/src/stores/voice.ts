import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchVoiceOptions } from '@/services/tasks'
import type { VoiceOption } from '@/types/task'

type VoiceQuery = {
  serviceName: string
  optionType: string
  includeInactive: boolean
}

const DEFAULT_QUERY: VoiceQuery = {
  serviceName: 'fishaudio',
  optionType: 'voice_id',
  includeInactive: false
}

export const useVoiceOptionStore = defineStore('voice-options', () => {
  const options = ref<VoiceOption[]>([])
  const loading = ref(false)
  const lastQuery = ref<VoiceQuery | null>(null)

  const defaultOption = computed<VoiceOption | null>(() => {
    if (!options.value.length) return null
    return options.value.find((item) => item.is_default) ?? options.value[0]
  })

  const currentServiceName = computed(() => lastQuery.value?.serviceName ?? DEFAULT_QUERY.serviceName)

  const findByKey = (key: string | undefined | null) => {
    if (!key) return null
    return options.value.find((item) => item.option_key === key) ?? null
  }

  const shouldReload = (query: VoiceQuery) => {
    if (!lastQuery.value) return true
    return (
      lastQuery.value.serviceName !== query.serviceName ||
      lastQuery.value.optionType !== query.optionType ||
      lastQuery.value.includeInactive !== query.includeInactive
    )
  }

  const loadOptions = async (query: Partial<VoiceQuery> = {}) => {
    const merged: VoiceQuery = {
      ...DEFAULT_QUERY,
      ...query
    }
    loading.value = true
    try {
      options.value = await fetchVoiceOptions({
        serviceName: merged.serviceName,
        optionType: merged.optionType,
        includeInactive: merged.includeInactive
      })
      lastQuery.value = merged
    } finally {
      loading.value = false
    }
  }

  const ensureLoaded = async (query: Partial<VoiceQuery> = {}) => {
    const merged: VoiceQuery = {
      ...DEFAULT_QUERY,
      ...query
    }

    if (!options.value.length || shouldReload(merged)) {
      await loadOptions(merged)
    }
  }

  return {
    options,
    loading,
    defaultOption,
    currentServiceName,
    findByKey,
    loadOptions,
    ensureLoaded
  }
})
