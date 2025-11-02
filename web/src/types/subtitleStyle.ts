export interface SubtitleStyleFieldValues {
  Fontname?: string
  Fontsize?: number
  PrimaryColour?: string
  SecondaryColour?: string
  OutlineColour?: string
  BackColour?: string
  Outline?: number
  Shadow?: number
  Alignment?: number
  MarginL?: number
  MarginR?: number
  MarginV?: number
  Bold?: number | boolean
  Italic?: number | boolean
  Spacing?: number
  [key: string]: unknown
}

export interface SubtitleScriptSettings {
  PlayResX?: number
  PlayResY?: number
  WrapStyle?: number
  ScaledBorderAndShadow?: boolean
  Title?: string
  YCbCrMatrix?: string
  [key: string]: unknown
}

export interface MovePointConfig {
  x: number
  y: number
}

export interface MoveConfig {
  from: MovePointConfig
  to: MovePointConfig
  t1?: number
  t2?: number
}

export interface FadeSimpleConfig {
  mode: 'fad'
  fadeIn: number
  fadeOut: number
}

export interface FadeAdvancedConfig {
  mode: 'fade'
  alphaFrom: number
  alphaMid: number
  alphaTo: number
  t1: number
  t2: number
  t3: number
  t4: number
}

export type FadeConfig = FadeSimpleConfig | FadeAdvancedConfig

export interface TransformConfig {
  start?: number
  end?: number
  accel?: number
  override: string
}

export interface AnimationConfig {
  transforms: TransformConfig[]
}

export interface SubtitleEffectSettings {
  Blur?: number
  Animation?: AnimationConfig | string
  Fade?: FadeConfig | string
  Move?: MoveConfig | string
  Effect?: string
  TextOverride?: string
  SequenceMode?: string
  SequenceJitter?: {
    dx?: number
    dy?: number
  }
  SequenceAnchor?: {
    x?: number
    y?: number
  }
  AlignmentVariant?: string
  TextCase?: 'upper' | 'lower' | ''
  StripPunctuation?: boolean
  [key: string]: unknown
}

export interface SubtitleStyleSections {
  style_fields: SubtitleStyleFieldValues
  script_settings: SubtitleScriptSettings
  effect_settings: SubtitleEffectSettings
}

export interface SubtitleStyle {
  id: number
  name: string
  description: string | null
  style_fields: SubtitleStyleFieldValues
  script_settings: SubtitleScriptSettings
  effect_settings: SubtitleEffectSettings
  style_payload: Record<string, unknown>
  sample_text: string | null
  is_active: boolean
  is_default: boolean
  usage_count: number
  created_at: string
  updated_at: string
}

export interface SubtitleStylePayload {
  name: string
  description?: string | null
  style_fields: SubtitleStyleFieldValues
  script_settings?: SubtitleScriptSettings
  effect_settings?: SubtitleEffectSettings
  style_payload?: Record<string, unknown>
  sample_text?: string | null
  is_active?: boolean
  is_default?: boolean
}

export interface SubtitleStyleUpdatePayload {
  name?: string
  description?: string | null
  style_fields?: SubtitleStyleFieldValues
  script_settings?: SubtitleScriptSettings
  effect_settings?: SubtitleEffectSettings
  style_payload?: Record<string, unknown>
  sample_text?: string | null
  is_active?: boolean
  is_default?: boolean
}
