import type {
  AnimationConfig,
  FadeConfig,
  MoveConfig,
  SubtitleEffectSettings,
  SubtitleScriptSettings,
  SubtitleStyleFieldValues,
  TransformConfig
} from '@/types/subtitleStyle'

interface BuildAssParams {
  styleName?: string
  styleFields: SubtitleStyleFieldValues
  scriptSettings: SubtitleScriptSettings
  effectSettings: SubtitleEffectSettings
  text: string
  durationSeconds?: number
}

interface SequenceJitterConfig {
  dx: number
  dy: number
}

interface AnchorConfig {
  x: number
  y: number
}

interface AssEvent {
  start: number
  end: number
  text: string
  extraOverride?: string
}

const WORD_SEQUENCE_MODE = 'word-continuous'
const MOVE_REGEX = /\\move\(\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+)(?:\s*,\s*([-+]?\d+)\s*,\s*([-+]?\d+))?\s*\)/i

const boolToAss = (value: unknown, fallback: number): number => {
  if (typeof value === 'boolean') return value ? -1 : 0
  if (typeof value === 'number') return value !== 0 ? -1 : 0
  if (typeof value === 'string') {
     let trimmed = value.trim()
    if (!trimmed) return fallback
    return trimmed !== '0' ? -1 : 0
  }
  return fallback
}

const numberOr = (value: unknown, fallback: number): number => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return num
}

const clampInt = (value: unknown, fallback: number, min: number, max: number): number => {
  const num = Math.round(numberOr(value, fallback))
  return Math.min(max, Math.max(min, num))
}

const escapeAssText = (input: string): string =>
  input
    .replace(/\\/g, '\\\\')
    .replace(/\{/g, '\\{')
    .replace(/\}/g, '\\}')
    .replace(/\r/g, '')
    .replace(/\n/g, '\\N')

const formatAssTime = (seconds: number): string => {
  const total = Math.max(seconds, 0)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = Math.floor(total % 60)
  const centiseconds = Math.floor((total - Math.floor(total)) * 100)
  const mm = minutes.toString().padStart(2, '0')
  const ss = secs.toString().padStart(2, '0')
  const cs = centiseconds.toString().padStart(2, '0')
  return `${hours}:${mm}:${ss}.${cs}`
}

interface TextTransformOptions {
  textCase: 'upper' | 'lower' | null
  stripPunctuation: boolean
}

const normaliseTextCase = (value: unknown): 'upper' | 'lower' | null => {
  if (typeof value !== 'string') return null
  const text = value.trim().toLowerCase()
  if (!text) return null
  if (['upper', 'uppercase', 'caps', 'allupper', 'allcaps'].includes(text)) return 'upper'
  if (['lower', 'lowercase', 'alllower'].includes(text)) return 'lower'
  return null
}

const resolveStripPunctuation = (value: unknown, defaultValue: boolean): boolean => {
  if (value === null || value === undefined || value === '') return defaultValue
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const text = value.trim().toLowerCase()
    if (!text) return defaultValue
    if (['true', '1', 'yes', 'on', 'remove'].includes(text)) return true
    if (['false', '0', 'no', 'off', 'keep'].includes(text)) return false
  }
  return defaultValue
}

const transformTextContent = (input: string, options: TextTransformOptions): string => {
  let output = (input ?? '').toString()
  if (options.stripPunctuation) {
    output = output.replace(/\p{P}+/gu, '')
    output = output.replace(/\s{2,}/g, ' ')
  }
  if (options.textCase === 'upper') {
    output = output.toUpperCase()
  } else if (options.textCase === 'lower') {
    output = output.toLowerCase()
  }
  return output.trim()
}

const normaliseOverrideValue = (prefix: string, value: unknown): string | null => {
  if (value === null || value === undefined) return null
  if (typeof value === 'number' && Number.isFinite(value)) {
    return `\\${prefix}${value}`
  }
  if (typeof value === 'string') {
    let trimmed = value.trim()
    if (!trimmed) return null
    if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
      trimmed = trimmed.slice(1, -1).trim()
    }
    if (!trimmed) return null
    if (trimmed.startsWith('\\')) return trimmed
    if (trimmed.includes('(') && trimmed.includes(')')) {
      const withoutLeading = trimmed.replace(/^\\+/, '')
      return `\\${withoutLeading}`
    }
    const payload = trimmed.startsWith('(') ? trimmed : `(${trimmed})`
    return `\\${prefix}${payload}`
  }
  return null
}

const stripOverrideBraces = (value: string): string => {
  let result = value.trim()
  if (result.startsWith('{') && result.endsWith('}')) {
    result = result.slice(1, -1).trim()
  }
  return result
}

const ensureOverrideTag = (value: string): string | null => {
  let text = stripOverrideBraces(value)
  if (!text) return null
  if (!text.startsWith('\\')) {
    text = `\\${text.replace(/^\\+/, '')}`
  }
  return text
}

const toIntValue = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') return undefined
  const num = Number(value)
  if (!Number.isFinite(num)) return undefined
  return Math.round(num)
}

const toNonNegativeInt = (value: unknown): number | undefined => {
  const num = toIntValue(value)
  if (num === undefined) return undefined
  return num < 0 ? 0 : num
}

const clampAlpha = (value: unknown): number => {
  const num = toNonNegativeInt(value)
  if (num === undefined) return 0
  if (num > 255) return 255
  return num
}

const formatFloat = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '0'
  const num = Number(value)
  if (!Number.isFinite(num)) return '0'
  if (Math.abs(num - Math.round(num)) < 1e-6) {
    return String(Math.round(num))
  }
  return Number(num.toFixed(6)).toString()
}

const buildMoveOverride = (value: MoveConfig | string | undefined): string | null => {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    return ensureOverrideTag(value)
  }
  if (!value.from || !value.to) return null
  const fromX = toIntValue((value.from as any).x)
  const fromY = toIntValue((value.from as any).y)
  const toX = toIntValue((value.to as any).x)
  const toY = toIntValue((value.to as any).y)
  if (
    fromX === undefined ||
    fromY === undefined ||
    toX === undefined ||
    toY === undefined
  ) {
    return null
  }
  let tag = `\\move(${fromX},${fromY},${toX},${toY}`
  const t1 = toNonNegativeInt((value as MoveConfig).t1)
  const t2Raw = toNonNegativeInt((value as MoveConfig).t2)
  if (t1 !== undefined || t2Raw !== undefined) {
    const start = t1 ?? 0
    const end = t2Raw !== undefined ? Math.max(t2Raw, start) : start
    tag += `,${start},${end}`
  }
  tag += ')'
  return tag
}

const normaliseMovePoint = (value: unknown): { x: number; y: number } | null => {
  if (value === null || value === undefined) return null
  if (Array.isArray(value) && value.length >= 2) {
    const x = toIntValue(value[0])
    const y = toIntValue(value[1])
    if (x === undefined || y === undefined) return null
    return { x, y }
  }
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const x = toIntValue(source.x ?? source.X)
    const y = toIntValue(source.y ?? source.Y)
    if (x === undefined || y === undefined) return null
    return { x, y }
  }
  return null
}

const normaliseMoveObject = (value: any): MoveConfig | null => {
  if (!value || typeof value !== 'object') return null
  const from = normaliseMovePoint(value.from ?? value.start)
  const to = normaliseMovePoint(value.to ?? value.end)
  if (!from || !to) return null
  const config: MoveConfig = { from, to }
  const t1 = toNonNegativeInt(value.t1 ?? value.startTime ?? value.start_time)
  const t2 = toNonNegativeInt(value.t2 ?? value.endTime ?? value.end_time)
  if (t1 !== undefined) config.t1 = t1
  if (t2 !== undefined) config.t2 = Math.max(t2, config.t1 ?? t2)
  return config
}

const parseMoveString = (value: string): MoveConfig | null => {
  const text = stripOverrideBraces(value)
  const match = text.match(MOVE_REGEX)
  if (!match) return null
  const x1 = Number(match[1])
  const y1 = Number(match[2])
  const x2 = Number(match[3])
  const y2 = Number(match[4])
  if (!Number.isFinite(x1) || !Number.isFinite(y1) || !Number.isFinite(x2) || !Number.isFinite(y2)) {
    return null
  }
  const config: MoveConfig = {
    from: { x: Math.round(x1), y: Math.round(y1) },
    to: { x: Math.round(x2), y: Math.round(y2) }
  }
  if (match[5] !== undefined) {
    const t1 = toNonNegativeInt(Number(match[5]))
    if (t1 !== undefined) config.t1 = t1
  }
  if (match[6] !== undefined) {
    const t2 = toNonNegativeInt(Number(match[6]))
    if (t2 !== undefined) config.t2 = t2
  }
  return config
}

const resolveMoveData = (value: MoveConfig | string | undefined): { override: string | null; config: MoveConfig | null } => {
  if (value === null || value === undefined) {
    return { override: null, config: null }
  }
  if (typeof value === 'string') {
    const override = ensureOverrideTag(value)
    return {
      override,
      config: parseMoveString(value)
    }
  }
  const config = normaliseMoveObject(value)
  const override = buildMoveOverride(value)
  if (config && !override) {
    return { override: buildMoveOverride(config), config }
  }
  return { override, config }
}

const buildFadeOverride = (value: FadeConfig | string | undefined): string | null => {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    return ensureOverrideTag(value)
  }
  if (value.mode === 'fade') {
    const alphaFrom = clampAlpha(value.alphaFrom)
    const alphaMid = clampAlpha(value.alphaMid)
    const alphaTo = clampAlpha(value.alphaTo)
    const t1 = toNonNegativeInt(value.t1) ?? 0
    const t2 = toNonNegativeInt(value.t2) ?? t1
    const t3 = toNonNegativeInt(value.t3) ?? t2
    const t4 = toNonNegativeInt(value.t4) ?? t3
    return `\\fade(${alphaFrom},${alphaMid},${alphaTo},${t1},${t2},${t3},${t4})`
  }
  const fadeIn = toNonNegativeInt(value.fadeIn) ?? 0
  const fadeOut = toNonNegativeInt(value.fadeOut) ?? 0
  return `\\fad(${fadeIn},${fadeOut})`
}

const buildTransformOverride = (transform: TransformConfig): string | null => {
  if (!transform || typeof transform !== 'object') return null
  const override = ensureOverrideTag(transform.override)
  if (!override) return null
  const args: string[] = []
  const start = toNonNegativeInt(transform.start)
  const end = toNonNegativeInt(transform.end)
  const accel = transform.accel !== undefined ? Number(transform.accel) : undefined
  if (start !== undefined && end !== undefined) {
    args.push(String(start))
    args.push(String(Math.max(end, start)))
    if (accel !== undefined && Number.isFinite(accel) && accel >= 0) {
      args.push(formatFloat(accel))
    }
  } else if (accel !== undefined && Number.isFinite(accel) && accel >= 0) {
    args.push('0', '0', formatFloat(accel))
  }
  args.push(override)
  return `\\t(${args.join(',')})`
}

const buildAnimationOverride = (value: AnimationConfig | string | undefined): string | null => {
  if (value === null || value === undefined) return null
  if (typeof value === 'string') {
    return ensureOverrideTag(value)
  }
  if (!Array.isArray(value.transforms)) return null
  const tags = value.transforms
    .map((item) => buildTransformOverride(item))
    .filter((tag): tag is string => Boolean(tag))
  if (!tags.length) return null
  return tags.join('')
}

const mergeOverrides = (
  effectSettings: SubtitleEffectSettings,
  options?: { omitMove?: boolean; moveOverride?: string | null }
): string => {
  const overrides: string[] = []
  const blur = normaliseOverrideValue('blur', effectSettings.Blur)
  if (blur) overrides.push(blur)

  const fade = buildFadeOverride(effectSettings.Fade as FadeConfig | string | undefined)
  if (fade) overrides.push(fade)

  if (!(options?.omitMove ?? false)) {
    const move = options?.moveOverride ?? buildMoveOverride(effectSettings.Move as MoveConfig | string | undefined)
    if (move) overrides.push(move)
  }

  const animation = buildAnimationOverride(effectSettings.Animation as AnimationConfig | string | undefined)
  if (animation) overrides.push(animation)

  if (typeof effectSettings.TextOverride === 'string') {
    const trimmed = effectSettings.TextOverride.trim()
    if (trimmed) {
      if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
        overrides.push(trimmed.slice(1, -1))
      } else if (trimmed.startsWith('\\')) {
        overrides.push(trimmed)
      } else {
        overrides.push(`\\${trimmed}`)
      }
    }
  }

  if (!overrides.length) return ''
  return `{${overrides.join('')}}`
}

const mergeOverrideBlocks = (base: string, extra?: string): string => {
  const blocks: string[] = []
  const push = (value?: string) => {
    if (!value) return
    let text = value
    if (text.startsWith('{') && text.endsWith('}')) {
      text = text.slice(1, -1)
    }
    if (text) blocks.push(text)
  }
  push(base)
  push(extra)
  return blocks.length ? `{${blocks.join('')}}` : ''
}

const normaliseSequenceMode = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const text = value.trim().toLowerCase()
  if (!text || ['none', 'off', 'false'].includes(text)) return ''
  if (['word', 'wordsequence', 'word_sequence', 'wordcontinuous', WORD_SEQUENCE_MODE].includes(text)) {
    return WORD_SEQUENCE_MODE
  }
  return text
}

const normaliseAlignmentVariant = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const text = value.trim().toLowerCase()
  if (!text) return ''
  if (['center-lower', 'center_lower', 'centre-lower', 'centerlower'].includes(text)) {
    return 'center-lower'
  }
  return ''
}

const toNonNegativeNumber = (value: unknown, fallback = 0): number => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return num < 0 ? fallback : num
}

const parseSequenceJitter = (value: unknown): SequenceJitterConfig => {
  if (value === null || value === undefined) {
    return { dx: 2, dy: 2 }
  }
  if (typeof value === 'number') {
    const numeric = toNonNegativeNumber(value, 2)
    return { dx: numeric, dy: numeric }
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return { dx: 2, dy: 2 }
    const parts = trimmed.split(/[\s,]+/)
    if (parts.length >= 2) {
      return {
        dx: toNonNegativeNumber(parts[0], 2),
        dy: toNonNegativeNumber(parts[1], 2)
      }
    }
    const numeric = toNonNegativeNumber(parts[0], 2)
    return { dx: numeric, dy: numeric }
  }
  if (Array.isArray(value) && value.length >= 2) {
    return {
      dx: toNonNegativeNumber(value[0], 2),
      dy: toNonNegativeNumber(value[1], 2)
    }
  }
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const dxSource = source.dx ?? source.x
    const dySource = source.dy ?? source.y
    if (dxSource === undefined && dySource === undefined) {
      return { dx: 2, dy: 2 }
    }
    return {
      dx: toNonNegativeNumber(dxSource, 2),
      dy: toNonNegativeNumber(dySource, 2)
    }
  }
  return { dx: 2, dy: 2 }
}

const parseSequenceAnchor = (
  value: unknown,
  fallback: AnchorConfig,
  options?: { overrideVariant?: string; margins?: { marginL: number; marginR: number; marginV: number }; width?: number; height?: number }
): AnchorConfig => {
  if (value === null || value === undefined) return fallback
  if (typeof value === 'number') return { x: value, y: fallback.y }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return fallback
    const parts = trimmed.split(/[\s,]+/)
    if (parts.length >= 2) {
      return {
        x: Number(parts[0]) || fallback.x,
        y: Number(parts[1]) || fallback.y
      }
    }
    const numeric = Number(parts[0])
    return { x: Number.isFinite(numeric) ? numeric : fallback.x, y: fallback.y }
  }
  if (Array.isArray(value) && value.length >= 2) {
    return {
      x: Number(value[0]) || fallback.x,
      y: Number(value[1]) || fallback.y
    }
  }
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const x = Number(source.x ?? source.dx)
    const y = Number(source.y ?? source.dy)
    const baseX = Number.isFinite(x) ? x : fallback.x
    let resultY = Number.isFinite(y) ? y : fallback.y
    if (options?.overrideVariant === 'center-lower') {
      resultY = fallback.y
    }
    return { x: baseX, y: resultY }
  }
  return fallback
}

const anchorFromAlignment = (
  alignment: number,
  marginL: number,
  marginR: number,
  marginV: number,
  width: number,
  height: number,
  variant?: string
): AnchorConfig => {
  const horizontal = ((alignment - 1) % 3 + 3) % 3
  const vertical = Math.floor((alignment - 1) / 3)

  let x = width / 2
  if (horizontal === 0) {
    x = Math.max(marginL, 0)
  } else if (horizontal === 2) {
    x = Math.max(width - marginR, 0)
  }

  let y = height * 0.85
  if (vertical <= 0) {
    y = Math.max(height - marginV, 0)
  } else if (vertical === 1) {
    y = height / 2
  } else {
    y = Math.max(marginV, 0)
  }

  if (variant === 'center-lower') {
    const bottomY = Math.max(height - marginV, 0)
    const centerY = height / 2
    const blendedY = (centerY + bottomY) / 2
    return {
      x: Math.round(x),
      y: Math.round(blendedY)
    }
  }

  return {
    x: Math.round(x),
    y: Math.round(y)
  }
}

const extractAnchorFromOverride = (overrideBlock: string | undefined, fallback: AnchorConfig): AnchorConfig => {
  if (!overrideBlock) return fallback
  let source = overrideBlock
  if (source.startsWith('{') && source.endsWith('}')) {
    source = source.slice(1, -1)
  }
  const match = source.match(/\\pos\(\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*\)/i)
  if (!match) return fallback
  const x = Number(match[1])
  const y = Number(match[2])
  if (!Number.isFinite(x) || !Number.isFinite(y)) return fallback
  return { x, y }
}

const makeSeededRandom = (seed: number) => {
  let state = seed >>> 0
  return () => {
    state = (state + 0x6d2b79f5) | 0
    let t = Math.imul(state ^ (state >>> 15), 1 | state)
    t ^= t + Math.imul(t ^ (t >>> 7), 61 | t)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const POS_REGEX = /\\pos\(/i

const buildSequenceMove = (
  anchor: AnchorConfig,
  jitter: SequenceJitterConfig,
  start: number,
  end: number,
  index: number,
  includePos: boolean,
  baseMove?: MoveConfig | null
): string => {
  const needsMove = Boolean(baseMove) || jitter.dx > 0 || jitter.dy > 0
  const rng = makeSeededRandom(index + 1)
  const jitterValue = (amplitude: number) => {
    if (amplitude <= 0) return 0
    return (rng() * 2 - 1) * amplitude
  }
  const anchorX = Math.round(anchor.x)
  const anchorY = Math.round(anchor.y)
  let startX = Math.round(anchor.x + jitterValue(jitter.dx))
  let startY = Math.round(anchor.y + jitterValue(jitter.dy))
  const endX = Math.round(anchor.x + jitterValue(jitter.dx))
  const endY = Math.round(anchor.y + jitterValue(jitter.dy))
  const durationMs = Math.max(Math.round((end - start) * 1000), 1)
  let moveStartTime = 0
  let moveEndTime = durationMs

  if (baseMove) {
    const fromX = toIntValue((baseMove.from as any)?.x)
    const fromY = toIntValue((baseMove.from as any)?.y)
    const toX = toIntValue((baseMove.to as any)?.x)
    const toY = toIntValue((baseMove.to as any)?.y)
    if (fromX !== undefined && fromY !== undefined && toX !== undefined && toY !== undefined) {
      startX += fromX - toX
      startY += fromY - toY
    }
    const t1 = toNonNegativeInt((baseMove as any).t1)
    const t2 = toNonNegativeInt((baseMove as any).t2)
    if (t1 !== undefined || t2 !== undefined) {
      moveStartTime = t1 ?? 0
      moveEndTime = Math.max(t2 ?? moveStartTime, moveStartTime)
    }
  }

  const posTag = includePos ? `\\pos(${anchorX},${anchorY})` : ''
  let moveTag = ''
  if (needsMove) {
    moveTag = `\\move(${startX},${startY},${endX},${endY},${moveStartTime},${moveEndTime})`
  }
  if (!posTag && !moveTag) return ''
  const tags = [posTag, moveTag].filter(Boolean).join('')
  return `{${tags}}`
}

const buildWordSequenceEvents = (
  text: string,
  durationSeconds: number,
  anchor: AnchorConfig,
  jitter: SequenceJitterConfig,
  includePos: boolean,
  baseMove: MoveConfig | null,
  transformOptions: TextTransformOptions
): AssEvent[] => {
  const words = (text.match(/\S+/g) || [])
    .map((word) => transformTextContent(word, transformOptions))
    .filter(Boolean)
  if (!words.length) return []
  let perWord = durationSeconds / Math.max(words.length, 1)
  perWord = Math.min(Math.max(perWord, 0.35), 0.8)
  const targetDuration = durationSeconds > 0 ? durationSeconds : perWord * words.length
  let cursor = 0
  return words.map((word, index) => {
    const start = cursor
    let end = cursor + perWord
    if (index === words.length - 1) {
      end = Math.max(end, targetDuration)
    }
    if (end <= start) {
      end = start + 0.35
    }
    cursor = end
    return {
      start,
      end,
      text: escapeAssText(word),
      extraOverride: buildSequenceMove(anchor, jitter, start, end, index, includePos, baseMove)
    }
  })
}

export const buildAssDocument = ({
  styleName = 'PreviewStyle',
  styleFields,
  scriptSettings,
  effectSettings,
  text,
  durationSeconds = 8
}: BuildAssParams): string => {
  const playResX = clampInt(scriptSettings.PlayResX, 1920, 1, 8192)
  const playResY = clampInt(scriptSettings.PlayResY, 1080, 1, 8192)
  const wrapStyle = clampInt(scriptSettings.WrapStyle, 1, 0, 3)
  const scaled = boolToAss(scriptSettings.ScaledBorderAndShadow, 1) === -1 ? 'yes' : 'no'

  const styleFont = (styleFields.Fontname as string) || 'Microsoft YaHei'
  const fontSize = numberOr(styleFields.Fontsize, 48)
  const primaryColour = (styleFields.PrimaryColour as string) || '&H00FFFFFF'
  const secondaryColour = (styleFields.SecondaryColour as string) || '&H00000000'
  const outlineColour = (styleFields.OutlineColour as string) || '&H00000000'
  const backColour = (styleFields.BackColour as string) || '&H64000000'
  const bold = boolToAss(styleFields.Bold, 0)
  const italic = boolToAss(styleFields.Italic, 0)
  const spacing = numberOr(styleFields.Spacing, 0)
  const outline = numberOr(styleFields.Outline, 3)
  const shadow = numberOr(styleFields.Shadow, 0)
  const alignment = clampInt(styleFields.Alignment, 2, 1, 9)
  const marginL = clampInt(styleFields.MarginL, 60, 0, 1000)
  const marginR = clampInt(styleFields.MarginR, 60, 0, 1000)
  const marginV = clampInt(styleFields.MarginV, 45, 0, 1000)

  const sequenceMode = normaliseSequenceMode(effectSettings.SequenceMode)
  const moveData = resolveMoveData(effectSettings.Move as MoveConfig | string | undefined)
  const overrideBlock = mergeOverrides(effectSettings, {
    omitMove: sequenceMode === WORD_SEQUENCE_MODE && Boolean(moveData.config),
    moveOverride: moveData.override
  })
  const alignmentVariant = normaliseAlignmentVariant(effectSettings.AlignmentVariant)
  const textCase = normaliseTextCase(effectSettings.TextCase)
  const stripPunctuation = resolveStripPunctuation(effectSettings.StripPunctuation, sequenceMode === WORD_SEQUENCE_MODE)
  const textOptions: TextTransformOptions = {
    textCase,
    stripPunctuation
  }

  const parts: string[] = []
  parts.push('[Script Info]')
  parts.push(`Title: ${scriptSettings.Title ?? 'Subtitle Preview'}`)
  parts.push('ScriptType: v4.00+')
  parts.push(`PlayResX: ${playResX}`)
  parts.push(`PlayResY: ${playResY}`)
  parts.push(`LayoutResX: ${playResX}`)
  parts.push(`LayoutResY: ${playResY}`)
  parts.push(`WrapStyle: ${wrapStyle}`)
  parts.push(`ScaledBorderAndShadow: ${scaled}`)
  if (scriptSettings.YCbCrMatrix) {
    parts.push(`YCbCr Matrix: ${scriptSettings.YCbCrMatrix}`)
  }

  parts.push('')
  parts.push('[V4+ Styles]')
  parts.push(
    'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding'
  )
  parts.push(
    `Style: ${styleName},${styleFont},${fontSize},${primaryColour},${secondaryColour},${outlineColour},${backColour},${bold},${italic},0,0,100,100,${spacing},0,1,${outline},${shadow},${alignment},${marginL},${marginR},${marginV},1`
  )

  parts.push('')
  parts.push('[Events]')
  parts.push('Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text')

  const rawLines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const baseLines = rawLines.length ? rawLines : ['字幕预览示例 / Subtitle Preview']
  const processedLines = baseLines
    .map((line) => transformTextContent(line, textOptions))
    .filter(Boolean)
  const fallbackLine = transformTextContent('字幕预览示例 / Subtitle Preview', textOptions) || '字幕预览示例 / Subtitle Preview'
  const safeLines = (processedLines.length ? processedLines : [fallbackLine]).map((line) => escapeAssText(line))

  const alignmentAnchor = anchorFromAlignment(
    alignment,
    marginL,
    marginR,
    marginV,
    playResX,
    playResY,
    alignmentVariant
  )
  const overrideAnchor = extractAnchorFromOverride(overrideBlock, alignmentAnchor)
  const sequenceAnchor = sequenceMode === WORD_SEQUENCE_MODE
    ? parseSequenceAnchor(effectSettings.SequenceAnchor, alignmentAnchor, {
        overrideVariant: alignmentVariant,
        margins: { marginL, marginR, marginV },
        width: playResX,
        height: playResY
      })
    : parseSequenceAnchor(effectSettings.SequenceAnchor, overrideAnchor, {
        overrideVariant: alignmentVariant,
        margins: { marginL, marginR, marginV },
        width: playResX,
        height: playResY
      })
  const jitter = sequenceMode === WORD_SEQUENCE_MODE
    ? parseSequenceJitter(effectSettings.SequenceJitter)
    : { dx: 0, dy: 0 }
  const baseHasPos = !!(overrideBlock && POS_REGEX.test(overrideBlock))
  const variantOverride = !baseHasPos && alignmentVariant === 'center-lower'
    ? `\\pos(${alignmentAnchor.x},${alignmentAnchor.y})`
    : ''

  let events: AssEvent[] = []
  if (sequenceMode === WORD_SEQUENCE_MODE) {
    events = buildWordSequenceEvents(
      text,
      durationSeconds,
      sequenceAnchor,
      jitter,
      !baseHasPos,
      moveData.config ?? null,
      textOptions
    )
  }

  if (!events.length) {
    const dialogueText = safeLines.join('\\N')
    events = [
      {
        start: 0,
        end: durationSeconds,
        text: dialogueText
      }
    ]
    if (variantOverride) {
      events = events.map((event) => ({ ...event, extraOverride: variantOverride }))
    }
  }

  if (variantOverride && sequenceMode !== WORD_SEQUENCE_MODE) {
    events = events.map((event) => {
      if (event.extraOverride) return event
      return { ...event, extraOverride: variantOverride }
    })
  }

  events.forEach((event) => {
    const startTime = formatAssTime(event.start)
    const endTime = formatAssTime(event.end)
    const overridePayload = mergeOverrideBlocks(overrideBlock, event.extraOverride)
    const finalText = `${overridePayload}${event.text}`
    parts.push(`Dialogue: 0,${startTime},${endTime},${styleName},,${marginL},${marginR},${marginV},,${finalText}`)
  })

  return parts.join('\n')
}
