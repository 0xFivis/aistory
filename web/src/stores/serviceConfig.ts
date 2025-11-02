import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchServiceCredentials,
  createServiceCredential,
  updateServiceCredential,
  deleteServiceCredential,
  fetchServiceOptions,
  createServiceOption,
  updateServiceOption,
  deleteServiceOption
} from '@/services/serviceConfig'
import type {
  ServiceCredential,
  ServiceCredentialPayload,
  ServiceCredentialUpdatePayload,
  ServiceOption,
  ServiceOptionPayload,
  ServiceOptionUpdatePayload
} from '@/types/serviceConfig'

export const useServiceConfigStore = defineStore('serviceConfig', () => {
  const credentials = ref<ServiceCredential[]>([])
  const options = ref<ServiceOption[]>([])
  const loadingCredentials = ref(false)
  const loadingOptions = ref(false)

  async function loadCredentials(params: { serviceName?: string; isActive?: boolean } = {}) {
    loadingCredentials.value = true
    try {
      credentials.value = await fetchServiceCredentials(params)
    } finally {
      loadingCredentials.value = false
    }
  }

  async function addCredential(payload: ServiceCredentialPayload) {
    const created = await createServiceCredential(payload)
    credentials.value = [created, ...credentials.value]
    return created
  }

  async function modifyCredential(id: number, payload: ServiceCredentialUpdatePayload) {
    const updated = await updateServiceCredential(id, payload)
    credentials.value = credentials.value.map((item) => (item.id === id ? updated : item))
    return updated
  }

  async function removeCredential(id: number) {
    await deleteServiceCredential(id)
    credentials.value = credentials.value.filter((item) => item.id !== id)
  }

  async function loadOptions(params: {
    serviceName?: string
    optionType?: string
    isActive?: boolean
  } = {}) {
    loadingOptions.value = true
    try {
      options.value = await fetchServiceOptions(params)
    } finally {
      loadingOptions.value = false
    }
  }

  async function addOption(payload: ServiceOptionPayload) {
    const created = await createServiceOption(payload)
    options.value = [created, ...options.value]
    return created
  }

  async function modifyOption(id: number, payload: ServiceOptionUpdatePayload) {
    const updated = await updateServiceOption(id, payload)
    options.value = options.value.map((item) => (item.id === id ? updated : item))
    return updated
  }

  async function removeOption(id: number) {
    await deleteServiceOption(id)
    options.value = options.value.filter((item) => item.id !== id)
  }

  return {
    credentials,
    options,
    loadingCredentials,
    loadingOptions,
    loadCredentials,
    addCredential,
    modifyCredential,
    removeCredential,
    loadOptions,
    addOption,
    modifyOption,
    removeOption
  }
})
