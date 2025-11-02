import apiClient from './api'
import type {
  SubtitleStyle,
  SubtitleStylePayload,
  SubtitleStyleUpdatePayload
} from '@/types/subtitleStyle'

export interface SubtitleStyleClonePayload {
  name?: string
  description?: string | null
  is_active?: boolean
}

export async function fetchSubtitleStyles(params?: {
  includeInactive?: boolean
  keyword?: string
}): Promise<SubtitleStyle[]> {
  const queryParams: Record<string, unknown> = {}
  if (params?.includeInactive !== undefined) {
    queryParams.include_inactive = params.includeInactive
  }
  if (params?.keyword) {
    queryParams.keyword = params.keyword
  }
  const { data } = await apiClient.get<SubtitleStyle[]>('/subtitle-styles', {
    params: queryParams
  })
  return data
}

export async function createSubtitleStyle(payload: SubtitleStylePayload): Promise<SubtitleStyle> {
  const body = {
    ...payload,
    style_fields: payload.style_fields ?? {},
    script_settings: payload.script_settings ?? {},
    effect_settings: payload.effect_settings ?? {}
  }
  const { data } = await apiClient.post<SubtitleStyle>('/subtitle-styles', body)
  return data
}

export async function fetchSubtitleStyle(id: number): Promise<SubtitleStyle> {
  const { data } = await apiClient.get<SubtitleStyle>(`/subtitle-styles/${id}`)
  return data
}

export async function updateSubtitleStyle(
  id: number,
  payload: SubtitleStyleUpdatePayload
): Promise<SubtitleStyle> {
  const body: Record<string, unknown> = { ...payload }
  if (payload.style_fields !== undefined) {
    body.style_fields = payload.style_fields
  }
  if (payload.script_settings !== undefined) {
    body.script_settings = payload.script_settings
  }
  if (payload.effect_settings !== undefined) {
    body.effect_settings = payload.effect_settings
  }
  if (payload.style_payload !== undefined) {
    body.style_payload = payload.style_payload
  }
  const { data } = await apiClient.put<SubtitleStyle>(`/subtitle-styles/${id}`, body)
  return data
}

export async function cloneSubtitleStyle(
  id: number,
  payload?: SubtitleStyleClonePayload
): Promise<SubtitleStyle> {
  const { data } = await apiClient.post<SubtitleStyle>(`/subtitle-styles/${id}/clone`, payload ?? {})
  return data
}

export async function deleteSubtitleStyle(id: number, softDelete = true): Promise<void> {
  await apiClient.delete(`/subtitle-styles/${id}`, {
    params: { soft_delete: softDelete }
  })
}
