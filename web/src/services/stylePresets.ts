import apiClient from './api'
import type {
  StylePreset,
  StylePresetPayload,
  StylePresetUpdatePayload
} from '@/types/stylePreset'

export async function fetchStylePresets(params?: {
  includeInactive?: boolean
}): Promise<StylePreset[]> {
  const { data } = await apiClient.get<StylePreset[]>('/style-presets', {
    params: {
      include_inactive: params?.includeInactive ?? false
    }
  })
  return data
}

export async function fetchStylePreset(id: number): Promise<StylePreset> {
  const { data } = await apiClient.get<StylePreset>(`/style-presets/${id}`)
  return data
}

export async function createStylePreset(payload: StylePresetPayload): Promise<StylePreset> {
  const { data } = await apiClient.post<StylePreset>('/style-presets', payload)
  return data
}

export async function updateStylePreset(
  id: number,
  payload: StylePresetUpdatePayload
): Promise<StylePreset> {
  const { data } = await apiClient.put<StylePreset>(`/style-presets/${id}`, payload)
  return data
}

export async function deleteStylePreset(
  id: number,
  softDelete = true
): Promise<void> {
  await apiClient.delete(`/style-presets/${id}`, {
    params: {
      soft_delete: softDelete
    }
  })
}
