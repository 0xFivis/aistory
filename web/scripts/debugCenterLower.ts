import { buildAssDocument } from '../src/utils/assBuilder.ts'
import type { SubtitleEffectSettings, SubtitleScriptSettings, SubtitleStyleFieldValues } from '../src/types/subtitleStyle'

const styleFields: SubtitleStyleFieldValues = {
  Fontname: 'Arial',
  Fontsize: 80,
  PrimaryColour: '&H00FFFFFF',
  SecondaryColour: '&H000000FF',
  OutlineColour: '&H00000000',
  BackColour: '&H80000000',
  Bold: true,
  Italic: false,
  ScaleX: 60,
  ScaleY: 60,
  Spacing: 0,
  Outline: 4,
  Shadow: 2,
  Alignment: 5,
  MarginL: 10,
  MarginR: 10,
  MarginV: 300
}

const scriptSettings: SubtitleScriptSettings = {
  Title: 'Spring Pop Words (1080x1920)',
  PlayResX: 1080,
  PlayResY: 1920,
  WrapStyle: 1,
  ScaledBorderAndShadow: true
}

const effectSettings: SubtitleEffectSettings = {
  SequenceMode: 'word-continuous',
  SequenceJitter: { dx: 3, dy: 3 },
  AlignmentVariant: 'center-lower',
  Move: {
    from: { x: 540, y: 1640 },
    to: { x: 540, y: 1550 },
    t1: 0,
    t2: 240
  },
  Animation: {
    transforms: [
      { start: 0, end: 220, accel: 0.45, override: '\\fscx120\\fscy120' },
      { start: 220, end: 420, override: '\\fscx102\\fscy102\\bord6' },
      { start: 420, end: 680, override: '\\bord4' }
    ]
  },
  Fade: { mode: 'fad', fadeIn: 80, fadeOut: 120 },
  TextOverride: '\\alpha&H20&'
}

const variantDoc = buildAssDocument({
  styleName: 'Variant',
  styleFields,
  scriptSettings,
  effectSettings,
  text: 'Love is never gone away',
  durationSeconds: 8
})

const baseDoc = buildAssDocument({
  styleName: 'BaseCenter',
  styleFields: { ...styleFields, Alignment: 5 },
  scriptSettings,
  effectSettings: { ...effectSettings, AlignmentVariant: undefined },
  text: 'Love is never gone away',
  durationSeconds: 8
})

const variantLines = variantDoc.split('\n').filter((line) => line.startsWith('Dialogue:'))
const baseLines = baseDoc.split('\n').filter((line) => line.startsWith('Dialogue:'))

console.log('--- center-lower ---')
console.log(variantLines.join('\n'))
console.log('\n--- pure center ---')
console.log(baseLines.join('\n'))
