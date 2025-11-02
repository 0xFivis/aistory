import apiClient from './api'
import type {
  ServiceCredential,
  ServiceCredentialPayload,
  ServiceCredentialUpdatePayload,
  ServiceOption,
  ServiceOptionPayload,
  ServiceOptionUpdatePayload
} from '@/types/serviceConfig'

export async function fetchServiceCredentials(params?: {
  serviceName?: string
  isActive?: boolean
}): Promise<ServiceCredential[]> {
  const { data } = await apiClient.get<ServiceCredential[]>('/config/credentials', {
    params: {
      service_name: params?.serviceName,
      is_active: params?.isActive
    }
  })
  return data
}

export async function createServiceCredential(
  payload: ServiceCredentialPayload
): Promise<ServiceCredential> {
  const { data } = await apiClient.post<ServiceCredential>('/config/credentials', payload)
  return data
}

export async function updateServiceCredential(
  id: number,
  payload: ServiceCredentialUpdatePayload
): Promise<ServiceCredential> {
  const { data } = await apiClient.patch<ServiceCredential>(`/config/credentials/${id}`, payload)
  return data
}

export async function deleteServiceCredential(id: number): Promise<void> {
  await apiClient.delete(`/config/credentials/${id}`)
}

export async function fetchServiceOptions(params?: {
  serviceName?: string
  optionType?: string
  isActive?: boolean
}): Promise<ServiceOption[]> {
  const { data } = await apiClient.get<ServiceOption[]>('/config/options', {
    params: {
      service_name: params?.serviceName,
      option_type: params?.optionType,
      is_active: params?.isActive
    }
  })
  return data
}

export async function createServiceOption(payload: ServiceOptionPayload): Promise<ServiceOption> {
  const { data } = await apiClient.post<ServiceOption>('/config/options', payload)
  return data
}

export async function updateServiceOption(
  id: number,
  payload: ServiceOptionUpdatePayload
): Promise<ServiceOption> {
  const { data } = await apiClient.patch<ServiceOption>(`/config/options/${id}`, payload)
  return data
}

export async function deleteServiceOption(id: number): Promise<void> {
  await apiClient.delete(`/config/options/${id}`)
}
