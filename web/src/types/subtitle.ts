export interface SubtitleWord {
  start: number
  end: number
  text: string
}

export interface SubtitleSegment {
  index: number
  start: number
  end: number
  duration?: number
  text: string
  words?: SubtitleWord[]
}

export interface SubtitleDocument {
  id: number
  task_id: number
  language?: string | null
  model_name?: string | null
  text?: string | null
  text_preview?: string | null
  segment_count: number
  segments: SubtitleSegment[]
  info?: Record<string, unknown> | null
  options?: Record<string, unknown> | null
  srt_api_path?: string | null
  srt_relative_path?: string | null
  srt_public_url?: string | null
  ass_api_path?: string | null
  ass_relative_path?: string | null
  ass_public_url?: string | null
  created_at?: string | null
  updated_at?: string | null
}
