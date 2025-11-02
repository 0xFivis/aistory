import type { SubtitleDocument } from './subtitle'

export interface TaskParams {
  title?: string
  description?: string
  reference_video?: string
}

export interface TaskConfig {
  scene_count?: number
  language?: string
  provider?: string | null
  style_preset_id?: number | null
  subtitle_style_id?: number | null
  subtitle_style_snapshot?: Record<string, unknown> | null
  bgm_asset_id?: number | null
  providers?: Record<string, string> | null
  audio_trim_silence?: boolean
  [key: string]: unknown
}

export interface TaskSummary {
  id: number
  workflow_type: string
  status: number
  progress: number
  total_scenes: number | null
  completed_scenes: number
  params: TaskParams | null
  result: Record<string, unknown> | null
  task_config: TaskConfig | null
  providers: Record<string, string> | null
  error_msg: string | null
  created_at: string
  updated_at: string
  mode: 'auto' | 'manual'
  merged_video_url: string | null
  final_video_url: string | null
  selected_voice_id?: string | null
  selected_voice_name?: string | null
  subtitle_style_id?: number | null
  subtitle_style_snapshot?: Record<string, unknown> | null
}

export interface TaskStep {
  id: number
  task_id: number
  step_name: string
  seq: number
  status: number
  progress: number
  retry_count: number
  max_retries: number
  params: Record<string, unknown> | null
  result: Record<string, unknown> | null
  error_msg: string | null
  started_at: string | null
  finished_at: string | null
}

export interface SceneRecord {
  id: number
  task_id: number
  seq: number
  status: number
  narration_text: string | null
  narration_word_count: number | null
  image_prompt: string | null
  video_prompt: string | null
  image_status: number
  audio_status: number
  audio_duration: number | null
  video_status: number
  merge_status: number
  image_url: string | null
  audio_url: string | null
  raw_video_url: string | null
  merge_video_url: string | null
  merge_video_provider: string | null
  image_meta: Record<string, unknown> | null
  audio_meta: Record<string, unknown> | null
  video_meta: Record<string, unknown> | null
  merge_meta: Record<string, unknown> | null
  image_retry_count: number
  audio_retry_count: number
  video_retry_count: number
  merge_retry_count: number
  params: Record<string, unknown> | null
  result: Record<string, unknown> | null
  error_msg: string | null
  started_at: string | null
  finished_at: string | null
}

export interface TaskDetail {
  task: TaskSummary
  steps: TaskStep[]
  scenes: SceneRecord[]
  subtitle_document?: SubtitleDocument | null
}

export interface CreateTaskPayload {
  title: string
  description: string
  reference_video?: string
  mode: 'auto' | 'manual'
  scene_count: number
  language: string
  audio_voice_id: string
  audio_voice_service?: string
  provider?: string | null
  media_tool?: string | null
  style_preset_id?: number
  subtitle_style_id?: number | null
  bgm_asset_id?: number | null
  audio_trim_silence?: boolean
}

export interface StoryboardScriptScene {
  scene_number: number
  scene_name?: string | null
  name?: string | null
  visual: string
  animation?: string | null
  narration?: string | null
  dialogue?: string | null
  [key: string]: unknown
}

export interface StoryboardScriptPayload {
  script: StoryboardScriptScene[]
}

export interface StoryboardScriptImportResponse {
  task_id: number
  scene_count: number
  provider: string
  auto_mode: 'auto' | 'manual' | null
  auto_dispatched: boolean
}

export interface UpdateTaskPayload {
  title?: string
  description?: string
  reference_video?: string
  mode?: 'auto' | 'manual'
  scene_count?: number
  language?: string
  audio_voice_id?: string
  audio_voice_service?: string
  provider?: string | null
  media_tool?: string | null
  style_preset_id?: number | null
  subtitle_style_id?: number | null
  bgm_asset_id?: number | null
  audio_trim_silence?: boolean
}

export interface VoiceOption {
  id: number
  service_name: string
  option_type: string
  option_key: string
  option_value: string
  option_name: string | null
  description: string | null
  is_default: boolean
  is_active: boolean
  meta_data: Record<string, unknown> | null
}
