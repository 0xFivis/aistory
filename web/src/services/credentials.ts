import apiClient from './api'

export async function listCredentials(serviceName?: string) {
  const params: Record<string, any> = {}
  if (serviceName) params.service_name = serviceName
  const { data } = await apiClient.get('/config/credentials', { params })
  return data
}

export async function getCredential(id: number, includeSecret = false) {
  const { data } = await apiClient.get(`/config/credentials/${id}`, { params: { include_secret: includeSecret } })
  return data
}

export async function createCredential(payload: any) {
  const { data } = await apiClient.post('/config/credentials', payload)
  return data
}

export async function updateCredential(id: number, payload: any) {
  const { data } = await apiClient.patch(`/config/credentials/${id}`, payload)
  return data
}

export async function deleteCredential(id: number) {
  const { data } = await apiClient.delete(`/config/credentials/${id}`)
  return data
}
