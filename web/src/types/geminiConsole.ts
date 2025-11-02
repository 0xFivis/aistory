export interface GeminiTemplateSummary {
  id: number
  name: string
  slug: string
  description?: string | null
  parameters: string[]
  relative_path: string
  is_active: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface GeminiTemplateDetail extends GeminiTemplateSummary {
  content: string
}

export interface GeminiTemplatePayload {
  name: string
  slug?: string | null
  description?: string | null
  content: string
  is_active?: boolean
}

export interface GeminiTemplateUpdatePayload {
  name?: string
  slug?: string | null
  description?: string | null
  content?: string
  is_active?: boolean
}

export interface GeminiPromptRecord {
  id: number
  template_id: number
  status: string
  latency_ms?: number | null
  parameters: Record<string, any>
  prompt: string
  response_text?: string | null
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface GeminiPromptRequestPayload {
  template_id?: number
  template_slug?: string
  parameters?: Record<string, string>
  generation_config?: Record<string, unknown>
  safety_settings?: Array<Record<string, unknown>>
  timeout?: number
}
