export interface StylePreset {
  id: number
  name: string
  description: string | null
  prompt_example: string | null
  trigger_words: string | null
  word_count_strategy: string | null
  channel_identity: string | null
  lora_id: string | null
  checkpoint_id: string | null
  image_provider: string | null
  video_provider: string | null
  runninghub_image_workflow_id: number | null
  runninghub_video_workflow_id: number | null
  meta: Record<string, unknown> | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface StylePresetPayload {
  name: string
  description?: string | null
  prompt_example?: string | null
  trigger_words?: string | null
  word_count_strategy?: string | null
  channel_identity?: string | null
  lora_id?: string | null
  checkpoint_id?: string | null
  image_provider?: string | null
  video_provider?: string | null
  runninghub_image_workflow_id?: number | null
  runninghub_video_workflow_id?: number | null
  meta?: Record<string, unknown> | null
  is_active?: boolean
}

export type StylePresetUpdatePayload = Partial<StylePresetPayload>
