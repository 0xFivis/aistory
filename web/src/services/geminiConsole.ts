import apiClient from './api'
import type {
  GeminiTemplateSummary,
  GeminiTemplateDetail,
  GeminiTemplatePayload,
  GeminiTemplateUpdatePayload,
  GeminiPromptRecord,
  GeminiPromptRequestPayload
} from '@/types/geminiConsole'

export async function fetchGeminiTemplates(params?: {
  includeInactive?: boolean
}): Promise<GeminiTemplateSummary[]> {
  const { data } = await apiClient.get<GeminiTemplateSummary[]>('/gemini-console/templates', {
    params: {
      include_inactive: params?.includeInactive ?? false
    }
  })
  return data
}

export async function fetchGeminiTemplate(id: number): Promise<GeminiTemplateDetail> {
  const { data } = await apiClient.get<GeminiTemplateDetail>(`/gemini-console/templates/${id}`)
  return data
}

export async function createGeminiTemplate(
  payload: GeminiTemplatePayload
): Promise<GeminiTemplateDetail> {
  const { data } = await apiClient.post<GeminiTemplateDetail>('/gemini-console/templates', payload)
  return data
}

export async function updateGeminiTemplate(
  id: number,
  payload: GeminiTemplateUpdatePayload
): Promise<GeminiTemplateDetail> {
  const { data } = await apiClient.put<GeminiTemplateDetail>(`/gemini-console/templates/${id}`, payload)
  return data
}

export async function deleteGeminiTemplate(id: number): Promise<void> {
  await apiClient.delete(`/gemini-console/templates/${id}`)
}

export async function executeGeminiPrompt(
  payload: GeminiPromptRequestPayload
): Promise<GeminiPromptRecord> {
  const { data } = await apiClient.post<GeminiPromptRecord>('/gemini-console/requests', payload)
  return data
}

export async function fetchGeminiRecords(params?: {
  templateId?: number
  limit?: number
}): Promise<GeminiPromptRecord[]> {
  const { data } = await apiClient.get<GeminiPromptRecord[]>('/gemini-console/records', {
    params: {
      template_id: params?.templateId,
      limit: params?.limit ?? 50
    }
  })
  return data
}

export async function fetchGeminiRecord(id: number): Promise<GeminiPromptRecord> {
  const { data } = await apiClient.get<GeminiPromptRecord>(`/gemini-console/records/${id}`)
  return data
}
