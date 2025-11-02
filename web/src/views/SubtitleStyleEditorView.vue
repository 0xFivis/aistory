<template>
  <div class="page page-container subtitle-style-editor">
    <el-page-header class="page-header" :content="pageTitle" @back="handleBack" />

    <el-alert
      v-if="isEdit && !form.is_active"
      type="warning"
      :closable="false"
      class="alert-bar"
      title="当前样式处于禁用状态，保存后仍需在列表中启用才能被任务使用。"
    />

    <el-skeleton v-if="loading" animated :rows="6" />
    <div v-else class="editor-layout">
      <el-card class="form-card" shadow="never">
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-width="120px"
          label-position="right"
          status-icon
        >
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="样式名称" prop="name">
                <el-input v-model="form.name" maxlength="128" show-word-limit placeholder="请输入样式名称" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="是否默认" prop="is_default">
                <el-switch v-model="form.is_default" />
                <el-tooltip content="仅允许一个默认样式" placement="top">
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="启用状态" prop="is_active">
                <el-switch v-model="form.is_active" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="示例文本" prop="sample_text">
                <el-input
                  v-model="form.sample_text"
                  maxlength="200"
                  show-word-limit
                  placeholder="用于预览的示例文本"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="样式说明" prop="description">
            <el-input
              v-model="form.description"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 4 }"
              maxlength="300"
              show-word-limit
              placeholder="可选，描述该样式的用途或特点"
            />
          </el-form-item>

          <el-tabs v-model="activeTab" type="card" class="subtitle-style-tabs">
            <el-tab-pane label="基础样式" name="style">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="字体" prop="style_fields.Fontname">
                    <el-input v-model="form.style_fields.Fontname" placeholder="Microsoft YaHei" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="字号 (px)" prop="style_fields.Fontsize">
                    <el-input-number
                      v-model="displayFontSize"
                      :min="6"
                      :max="400"
                      :step="1"
                      :precision="0"
                    />
                    <template #extra>
                      <span class="extra-hint">ASS 字号：{{ actualFontSizeDisplay }}</span>
                    </template>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="主颜色" prop="style_fields.PrimaryColour">
                    <ColorPicker v-model="form.style_fields.PrimaryColour" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="描边颜色" prop="style_fields.OutlineColour">
                    <ColorPicker v-model="form.style_fields.OutlineColour" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="描边" prop="style_fields.Outline">
                    <el-input-number v-model="form.style_fields.Outline" :min="0" :max="10" :step="0.5" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="阴影" prop="style_fields.Shadow">
                    <el-input-number v-model="form.style_fields.Shadow" :min="0" :max="10" :step="0.5" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="对齐" prop="style_fields.Alignment">
                    <el-select v-model="alignmentMode" placeholder="选择字幕对齐">
                      <el-option
                        v-for="item in alignmentOptionItems"
                        :key="item.mode"
                        :value="item.mode"
                        :label="item.label"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="字符间距" prop="style_fields.Spacing">
                    <el-input-number v-model="form.style_fields.Spacing" :min="-50" :max="50" :step="0.5" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="8">
                  <el-form-item label="左边距" prop="style_fields.MarginL">
                    <el-input-number v-model="form.style_fields.MarginL" :min="0" :max="400" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="右边距" prop="style_fields.MarginR">
                    <el-input-number v-model="form.style_fields.MarginR" :min="0" :max="400" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="垂直边距" prop="style_fields.MarginV">
                    <el-input-number v-model="form.style_fields.MarginV" :min="0" :max="400" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="加粗" prop="style_fields.Bold">
                    <el-switch v-model="form.style_fields.Bold" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="斜体" prop="style_fields.Italic">
                    <el-switch v-model="form.style_fields.Italic" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-tab-pane>

            <el-tab-pane label="画布设置" name="script">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="分辨率 X" prop="script_settings.PlayResX">
                    <el-input-number v-model="form.script_settings.PlayResX" :min="640" :max="4096" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="分辨率 Y" prop="script_settings.PlayResY">
                    <el-input-number v-model="form.script_settings.PlayResY" :min="360" :max="2160" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="换行策略" prop="script_settings.WrapStyle">
                    <el-select v-model="form.script_settings.WrapStyle">
                      <el-option :value="0" label="0 - 过长换行" />
                      <el-option :value="1" label="1 - 自动换行" />
                      <el-option :value="2" label="2 - 不换行" />
                      <el-option :value="3" label="3 - 智能换行" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="边框缩放" prop="script_settings.ScaledBorderAndShadow">
                    <el-switch v-model="form.script_settings.ScaledBorderAndShadow" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="标题" prop="script_settings.Title">
                <el-input v-model="form.script_settings.Title" placeholder="可选" />
              </el-form-item>

              <el-form-item label="YCbCrMatrix" prop="script_settings.YCbCrMatrix">
                <el-input v-model="form.script_settings.YCbCrMatrix" placeholder="例如 TV.601" />
              </el-form-item>
            </el-tab-pane>

            <el-tab-pane label="特效设置" name="effect">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="模糊" prop="effect_settings.Blur">
                    <el-input-number v-model="form.effect_settings.Blur" :min="0" :max="50" :step="0.5" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Fade" prop="effect_settings.Fade">
                    <FadeEditor v-model="form.effect_settings.Fade" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="Move" prop="effect_settings.Move">
                    <MoveEditor v-model="form.effect_settings.Move" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="文本覆盖" prop="effect_settings.TextOverride">
                    <el-input v-model="form.effect_settings.TextOverride" placeholder="例如 \\1a&HFF&" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="文本大小写" prop="effect_settings.TextCase">
                    <el-select v-model="textCaseOption" placeholder="保持原样">
                      <el-option label="保持原样" value="none" />
                      <el-option label="全部大写" value="upper" />
                      <el-option label="全部小写" value="lower" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="标点处理" prop="effect_settings.StripPunctuation">
                    <el-select v-model="stripPunctuationOption" placeholder="自动">
                      <el-option label="自动（逐词默认去除）" value="auto" />
                      <el-option label="去除标点" value="remove" />
                      <el-option label="保留标点" value="keep" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item label="动画 Transform" prop="effect_settings.Animation">
                <AnimationEditor v-model="form.effect_settings.Animation" />
              </el-form-item>

              <el-form-item label="逐词序列" prop="effect_settings.SequenceMode">
                <el-select v-model="form.effect_settings.SequenceMode" placeholder="关闭">
                  <el-option label="关闭" value="" />
                  <el-option label="连续单词序列" value="word-continuous" />
                </el-select>
              </el-form-item>

              <el-row v-if="sequenceModeEnabled" :gutter="16">
                <el-col :span="12">
                  <el-form-item label="抖动 X" prop="effect_settings.SequenceJitter">
                    <el-input-number v-model="sequenceJitterDx" :min="0" :max="200" :step="0.5" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="抖动 Y" prop="effect_settings.SequenceJitter">
                    <el-input-number v-model="sequenceJitterDy" :min="0" :max="200" :step="0.5" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-tab-pane>
          </el-tabs>

          <div class="form-actions">
            <el-space>
              <el-button @click="handleBack">取消</el-button>
              <el-button type="primary" :loading="saving" @click="handleSave">
                {{ isCreate ? '创建样式' : '保存修改' }}
              </el-button>
            </el-space>
          </div>
        </el-form>
      </el-card>

      <el-card class="preview-card" shadow="never">
        <div class="preview-header">
          <div>
            <div class="preview-title">实时预览</div>
            <div class="preview-sub">使用 ass.js + video.js 前端渲染，仅供样式参考</div>
          </div>
          <el-tag size="small" type="info">前端预览</el-tag>
        </div>

        <div class="preview-controls">
          <el-radio-group v-model="previewMode" size="small">
            <el-radio-button label="default">默认视频</el-radio-button>
            <el-radio-button label="custom">视频链接</el-radio-button>
            <el-radio-button label="upload">本地上传</el-radio-button>
          </el-radio-group>

          <el-input
            v-if="previewMode === 'custom'"
            v-model="customVideoUrl"
            size="small"
            placeholder="请输入可直链访问的视频 URL"
            clearable
          />

          <div v-else-if="previewMode === 'upload'" class="upload-wrapper">
            <input class="upload-input" type="file" accept="video/*" @change="handleVideoUpload" />
            <span v-if="uploadedFileName" class="upload-name">{{ uploadedFileName }}</span>
            <el-button v-if="uploadedFileName" link type="info" @click="resetUpload">移除</el-button>
          </div>
        </div>

        <SubtitlePreviewPlayer
          :source="previewSource"
          :subtitles="assDocument"
          :resolution="previewResolution"
        />

        <el-card class="preview-meta" shadow="never">
          <div class="meta-row">
            <span class="meta-label">预览分辨率：</span>
            <span>{{ form.script_settings.PlayResX }} × {{ form.script_settings.PlayResY }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">预览文本：</span>
            <span>{{ previewSample }}</span>
          </div>
        </el-card>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

import { useSubtitleStyleStore } from '@/stores/subtitleStyle'
import { fetchSubtitleStyle } from '@/services/subtitleStyles'
import type {
  SubtitleStyle,
  SubtitleStylePayload,
  SubtitleStyleUpdatePayload,
  SubtitleStyleFieldValues,
  SubtitleScriptSettings,
  SubtitleEffectSettings
} from '@/types/subtitleStyle'
import SubtitlePreviewPlayer from '@/components/subtitle/SubtitlePreviewPlayer.vue'
import ColorPicker from '@/components/subtitle/SubtitleStyleSwatch.vue'
import MoveEditor from '@/components/subtitle/effects/MoveEditor.vue'
import FadeEditor from '@/components/subtitle/effects/FadeEditor.vue'
import AnimationEditor from '@/components/subtitle/effects/AnimationEditor.vue'
import { buildAssDocument } from '@/utils/assBuilder'

const router = useRouter()
const route = useRoute()
const subtitleStyleStore = useSubtitleStyleStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const saving = ref(false)
const activeTab = ref<'style' | 'script' | 'effect'>('style')
const originalStylePayload = ref<Record<string, any> | null>(null)

const defaultVideoUrl = 'https://vjs.zencdn.net/v/oceans.mp4'
const previewMode = ref<'default' | 'custom' | 'upload'>('default')
const customVideoUrl = ref('')
const uploadedObjectUrl = ref<string | null>(null)
const uploadedFileName = ref('')

const alignmentOptionItems = [
  { mode: 'align-1', label: '1 左下', alignment: 1 },
  { mode: 'align-2', label: '2 居中下', alignment: 2 },
  { mode: 'align-3', label: '3 右下', alignment: 3 },
  { mode: 'align-4', label: '4 左中', alignment: 4 },
  { mode: 'align-5', label: '5 居中', alignment: 5 },
  { mode: 'center-lower', label: '居中偏下', alignment: 5, variant: 'center-lower' },
  { mode: 'align-6', label: '6 右中', alignment: 6 },
  { mode: 'align-7', label: '7 左上', alignment: 7 },
  { mode: 'align-8', label: '8 居中上', alignment: 8 },
  { mode: 'align-9', label: '9 右上', alignment: 9 }
]

const normaliseSequenceMode = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const text = value.trim().toLowerCase()
  if (!text || ['none', 'off', 'false'].includes(text)) return ''
  if (['word', 'word-sequence', 'word_sequence', 'wordsequence', 'wordcontinuous', 'word-continuous'].includes(text)) {
    return 'word-continuous'
  }
  return text
}

const normaliseTextCaseValue = (value: unknown): 'upper' | 'lower' | undefined => {
  if (typeof value !== 'string') return undefined
  const text = value.trim().toLowerCase()
  if (!text) return undefined
  if (['upper', 'uppercase', 'caps', 'allupper', 'allcaps'].includes(text)) return 'upper'
  if (['lower', 'lowercase', 'alllower'].includes(text)) return 'lower'
  return undefined
}

const parseStripPunctuationValue = (value: unknown): boolean | undefined => {
  if (value === null || value === undefined || value === '') return undefined
  if (typeof value === 'boolean') return value
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'string') {
    const text = value.trim().toLowerCase()
    if (!text) return undefined
    if (['true', '1', 'yes', 'on', 'remove'].includes(text)) return true
    if (['false', '0', 'no', 'off', 'keep'].includes(text)) return false
  }
  return undefined
}

const normaliseAlignmentVariant = (value: unknown): string => {
  if (typeof value !== 'string') return ''
  const text = value.trim().toLowerCase()
  if (!text) return ''
  if (['center-lower', 'center_lower', 'centre-lower', 'centerlower'].includes(text)) return 'center-lower'
  return ''
}

const toNonNegativeNumber = (value: unknown, fallback = 0): number => {
  const number = Number(value)
  if (!Number.isFinite(number)) return fallback
  return number < 0 ? fallback : number
}

const toNumberValue = (value: unknown, fallback: number): number => {
  if (value === null || value === undefined || value === '') return fallback
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

const toAlignmentValue = (value: unknown, fallback: number): number => {
  const num = toNumberValue(value, fallback)
  return Math.min(9, Math.max(1, Math.round(num)))
}

const toWrapStyleValue = (value: unknown, fallback: number): number => {
  const num = toNumberValue(value, fallback)
  return Math.min(3, Math.max(0, Math.round(num)))
}

const parseSequenceJitterValue = (value: unknown): { dx: number; dy: number } | undefined => {
  if (value === null || value === undefined) return undefined
  if (typeof value === 'number') {
    const numeric = toNonNegativeNumber(value)
    return { dx: numeric, dy: numeric }
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return undefined
    const parts = trimmed.split(/[\s,]+/)
    if (parts.length >= 2) {
      return {
        dx: toNonNegativeNumber(parts[0]),
        dy: toNonNegativeNumber(parts[1])
      }
    }
    const numeric = toNonNegativeNumber(parts[0])
    return { dx: numeric, dy: numeric }
  }
  if (Array.isArray(value) && value.length >= 2) {
    return {
      dx: toNonNegativeNumber(value[0]),
      dy: toNonNegativeNumber(value[1])
    }
  }
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const dxSource = source.dx ?? source.x
    const dySource = source.dy ?? source.y
    if (dxSource === undefined && dySource === undefined) return undefined
    return {
      dx: toNonNegativeNumber(dxSource),
      dy: toNonNegativeNumber(dySource)
    }
  }
  return undefined
}

const POS_OVERRIDE_REGEX = /\\pos\s*\(/i
const ALIGNMENT_OVERRIDE_REGEX = /\\an\d/gi
const POS_TAG_CLEANER_REGEX = /\\pos\([^{}]*?\)/gi

const removePosFromTextOverride = () => {
  const override = form.effect_settings.TextOverride
  if (typeof override !== 'string') return
  if (!POS_OVERRIDE_REGEX.test(override)) {
    POS_OVERRIDE_REGEX.lastIndex = 0
    return
  }
  POS_OVERRIDE_REGEX.lastIndex = 0
  const cleaned = override.replace(POS_TAG_CLEANER_REGEX, '').replace(/\{\s*\}/g, '').trim()
  form.effect_settings.TextOverride = cleaned
}

const form = reactive({
  name: '',
  description: '',
  sample_text: '',
  is_active: true,
  is_default: false,
  style_fields: {} as SubtitleStyleFieldValues,
  script_settings: {} as SubtitleScriptSettings,
  effect_settings: {} as SubtitleEffectSettings
})

const alignmentMode = ref('align-2')

const resolveAlignmentAnchor = (
  alignment: number,
  variant: string,
  marginL: number,
  marginR: number,
  marginV: number,
  width: number,
  height: number
) => {
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
    const blendedY = (y + bottomY) / 2
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

const computeSequenceAnchor = () => {
  const alignment = toAlignmentValue(form.style_fields.Alignment, 2)
  const variant = normaliseAlignmentVariant(form.effect_settings.AlignmentVariant)
  const marginL = toNonNegativeNumber(form.style_fields.MarginL, 60)
  const marginR = toNonNegativeNumber(form.style_fields.MarginR, 60)
  const marginV = toNonNegativeNumber(form.style_fields.MarginV, 45)
  const width = Math.max(1, Math.round(Number(form.script_settings.PlayResX) || 1920))
  const height = Math.max(1, Math.round(Number(form.script_settings.PlayResY) || 1080))

  return resolveAlignmentAnchor(alignment, variant, marginL, marginR, marginV, width, height)
}

const normaliseSequenceAnchorForSave = (value: unknown): { x: number; y: number } | undefined => {
  if (value === null || value === undefined) return undefined
  if (typeof value === 'number' && Number.isFinite(value)) {
    const numeric = Math.round(Number(value))
    return { x: numeric, y: numeric }
  }
  if (Array.isArray(value) && value.length >= 2) {
    const x = Number(value[0])
    const y = Number(value[1])
    if (Number.isFinite(x) && Number.isFinite(y)) {
      return { x: Math.round(x), y: Math.round(y) }
    }
    return undefined
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return undefined
    const parts = trimmed.split(/[\s,]+/)
    if (parts.length >= 2) {
      const x = Number(parts[0])
      const y = Number(parts[1])
      if (Number.isFinite(x) && Number.isFinite(y)) {
        return { x: Math.round(x), y: Math.round(y) }
      }
    }
    return undefined
  }
  if (typeof value === 'object') {
    const source = value as Record<string, unknown>
    const x = Number(source.x ?? source.X)
    const y = Number(source.y ?? source.Y)
    if (Number.isFinite(x) && Number.isFinite(y)) {
      return { x: Math.round(x), y: Math.round(y) }
    }
  }
  return undefined
}

const ensureSequenceAnchor = () => {
  const effectRecord = form.effect_settings as Record<string, unknown>
  const mode = normaliseSequenceMode(form.effect_settings.SequenceMode)
  if (mode !== 'word-continuous') {
    if ('SequenceAnchor' in effectRecord) {
      delete effectRecord.SequenceAnchor
    }
    return
  }
  removePosFromTextOverride()
  const target = computeSequenceAnchor()
  const current = normaliseSequenceAnchorForSave(form.effect_settings.SequenceAnchor)
  if (!current || current.x !== target.x || current.y !== target.y) {
    form.effect_settings.SequenceAnchor = { x: target.x, y: target.y }
  }
}

let syncingAlignmentMode = false

const applyAlignmentMode = (mode: string) => {
  if (!mode) return
  syncingAlignmentMode = true
  if (mode === 'center-lower') {
    form.style_fields.Alignment = 5
    form.effect_settings.AlignmentVariant = 'center-lower'
    removePosFromTextOverride()
  } else if (mode.startsWith('align-')) {
    const numeric = Number(mode.replace('align-', ''))
    if (Number.isFinite(numeric)) {
      form.style_fields.Alignment = toAlignmentValue(numeric, 2)
    }
    delete (form.effect_settings as Record<string, unknown>).AlignmentVariant
  }
  syncingAlignmentMode = false
  ensureSequenceAnchor()
  syncTextOverrideAlignment()
}

const resolveAlignmentMode = (): string => {
  const variant = normaliseAlignmentVariant(form.effect_settings.AlignmentVariant)
  if (variant === 'center-lower') {
    return 'center-lower'
  }
  const alignment = toAlignmentValue(form.style_fields.Alignment, 2)
  return `align-${alignment}`
}

watch(alignmentMode, (mode) => {
  if (syncingAlignmentMode) return
  applyAlignmentMode(mode)
})

watch(
  () => [form.style_fields.Alignment, form.effect_settings.AlignmentVariant],
  () => {
    if (syncingAlignmentMode) return
    const mode = resolveAlignmentMode()
    if (mode !== alignmentMode.value) {
      alignmentMode.value = mode
    }
  },
  { immediate: true }
)

const syncTextOverrideAlignment = () => {
  const override = form.effect_settings.TextOverride
  if (typeof override !== 'string') return
  const trimmed = override.trim()
  if (!trimmed) return
  if (!ALIGNMENT_OVERRIDE_REGEX.test(trimmed)) {
    ALIGNMENT_OVERRIDE_REGEX.lastIndex = 0
    return
  }
  ALIGNMENT_OVERRIDE_REGEX.lastIndex = 0
  const alignment = toAlignmentValue(form.style_fields.Alignment, 2)
  const updated = trimmed.replace(/\an\d/gi, `\an${alignment}`)
  if (updated !== trimmed) {
    form.effect_settings.TextOverride = updated
  }
}

const displayFontSize = ref<number>(48)
const actualFontSizeDisplay = computed(() => {
  const raw = Number(form.style_fields.Fontsize) || 0
  return raw > 0 ? raw.toFixed(1) : '0'
})
let syncingFromActual = false
let syncingFromDisplay = false

const rules: FormRules = {
  name: [{ required: true, message: '请输入样式名称', trigger: 'blur' }],
  'style_fields.Fontname': [{ required: true, message: '请输入字体名称', trigger: 'blur' }],
  'style_fields.Fontsize': [{ required: true, message: '请输入字号', trigger: 'change' }],
  'style_fields.Alignment': [{ required: true, message: '请选择对齐方式', trigger: 'change' }]
}

const mode = computed<'create' | 'edit'>(() =>
  route.name === 'subtitle-style-edit' ? 'edit' : 'create'
)

const styleId = computed(() => {
  if (mode.value === 'edit') {
    const raw = route.params.id
    const parsed = Number(raw)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
})

const isCreate = computed(() => mode.value === 'create')
const isEdit = computed(() => mode.value === 'edit')

const pageTitle = computed(() => (isCreate.value ? '新增字幕样式' : '编辑字幕样式'))

const previewSample = computed(() => form.sample_text?.trim() || '字幕预览示例 / Subtitle Preview')

const previewVideoUrl = computed(() => {
  if (previewMode.value === 'default') return defaultVideoUrl
  if (previewMode.value === 'custom') return customVideoUrl.value.trim() || null
  if (previewMode.value === 'upload') return uploadedObjectUrl.value
  return defaultVideoUrl
})

const previewSource = computed(() => {
  const src = previewVideoUrl.value
  return src ? { src, type: 'video/mp4' } : null
})

const assDocument = computed(() =>
  buildAssDocument({
    styleName: form.name || 'PreviewStyle',
    styleFields: form.style_fields,
    scriptSettings: form.script_settings,
    effectSettings: form.effect_settings,
    text: previewSample.value,
    durationSeconds: 8
  })
)

if (import.meta.env.DEV) {
  watch(assDocument, (doc) => {
    (window as any).__ASS_DOC__ = doc
  }, { immediate: true })
}

const previewResolution = computed(() => {
  const width = Math.max(1, Math.round(Number(form.script_settings.PlayResX) || 1920))
  const height = Math.max(1, Math.round(Number(form.script_settings.PlayResY) || 1080))
  return { width, height }
})

const sequenceModeEnabled = computed(() => normaliseSequenceMode(form.effect_settings.SequenceMode) === 'word-continuous')

const textCaseOption = computed<'none' | 'upper' | 'lower'>({
  get: () => {
    const value = normaliseTextCaseValue(form.effect_settings.TextCase)
    if (value === 'upper') return 'upper'
    if (value === 'lower') return 'lower'
    return 'none'
  },
  set: (selection) => {
    if (selection === 'upper' || selection === 'lower') {
      form.effect_settings.TextCase = selection
    } else {
      delete (form.effect_settings as Record<string, unknown>).TextCase
    }
  }
})

const stripPunctuationOption = computed<'auto' | 'remove' | 'keep'>({
  get: () => {
    const value = parseStripPunctuationValue(form.effect_settings.StripPunctuation)
    if (value === true) return 'remove'
    if (value === false) return 'keep'
    return 'auto'
  },
  set: (selection) => {
    if (selection === 'remove') {
      form.effect_settings.StripPunctuation = true
    } else if (selection === 'keep') {
      form.effect_settings.StripPunctuation = false
    } else {
      delete (form.effect_settings as Record<string, unknown>).StripPunctuation
    }
  }
})

const ensureSequenceJitter = () => {
  if (!sequenceModeEnabled.value) return
  const current = form.effect_settings.SequenceJitter
  if (!current || typeof current !== 'object') {
    form.effect_settings.SequenceJitter = { dx: 2, dy: 2 }
    return
  }
  const jitter = current as Record<string, unknown>
  jitter.dx = toNonNegativeNumber(jitter.dx, 2)
  jitter.dy = toNonNegativeNumber(jitter.dy, 2)
}

const sequenceJitterDx = computed({
  get: () => {
    const base = form.effect_settings.SequenceJitter
    if (!base || typeof base !== 'object') return 0
    const dx = (base as Record<string, unknown>).dx
    return toNonNegativeNumber(dx, 0)
  },
  set: (value: number) => {
    const numeric = toNonNegativeNumber(value, 0)
    if (!form.effect_settings.SequenceJitter || typeof form.effect_settings.SequenceJitter !== 'object') {
      form.effect_settings.SequenceJitter = { dx: numeric, dy: 0 }
    } else {
      (form.effect_settings.SequenceJitter as Record<string, unknown>).dx = numeric
    }
  }
})

const sequenceJitterDy = computed({
  get: () => {
    const base = form.effect_settings.SequenceJitter
    if (!base || typeof base !== 'object') return 0
    const dy = (base as Record<string, unknown>).dy
    return toNonNegativeNumber(dy, 0)
  },
  set: (value: number) => {
    const numeric = toNonNegativeNumber(value, 0)
    if (!form.effect_settings.SequenceJitter || typeof form.effect_settings.SequenceJitter !== 'object') {
      form.effect_settings.SequenceJitter = { dx: 0, dy: numeric }
    } else {
      (form.effect_settings.SequenceJitter as Record<string, unknown>).dy = numeric
    }
  }
})

const getDefaultSections = () => ({
  style_fields: {
    Fontname: 'Microsoft YaHei',
    Fontsize: 48,
    PrimaryColour: '&H00FFFFFF',
    OutlineColour: '&H00000000',
    BackColour: '&H64000000',
    Outline: 3,
    Shadow: 0,
    Alignment: 2,
    MarginL: 60,
    MarginR: 60,
    MarginV: 45,
    Spacing: 0,
    Bold: false,
    Italic: false
  } as SubtitleStyleFieldValues,
  script_settings: {
    PlayResX: 1920,
    PlayResY: 1080,
    WrapStyle: 1,
    ScaledBorderAndShadow: true,
    Title: 'Generated Subtitles',
    YCbCrMatrix: 'TV.601'
  } as SubtitleScriptSettings,
  effect_settings: {
    Blur: 0,
    TextOverride: '',
    SequenceMode: '',
    SequenceJitter: {
      dx: 2,
      dy: 2
    }
  } as SubtitleEffectSettings
})

const resetForm = () => {
  const defaults = getDefaultSections()
  form.name = ''
  form.description = ''
  form.sample_text = ''
  form.is_active = true
  form.is_default = false
  form.style_fields = { ...defaults.style_fields }
  form.script_settings = { ...defaults.script_settings }
  form.effect_settings = clonePlain(defaults.effect_settings) as SubtitleEffectSettings
  ensureSequenceAnchor()
  activeTab.value = 'style'
  originalStylePayload.value = null
  syncDisplayFontSize()
}

const toBooleanSwitch = (value: unknown): boolean => {
  if (typeof value === 'number') return value !== 0
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return value.trim() !== '0'
  return false
}

const initialiseForm = (style: SubtitleStyle | null) => {
  if (!style) {
    resetForm()
    return
  }
  const defaults = getDefaultSections()

  const sourceStyle = style.style_fields || {}
  const mergedStyle = {
    ...defaults.style_fields,
    ...sourceStyle
  } as SubtitleStyleFieldValues

  mergedStyle.Fontsize = toNumberValue(sourceStyle.Fontsize, defaults.style_fields.Fontsize ?? 48)
  mergedStyle.Outline = toNumberValue(sourceStyle.Outline, defaults.style_fields.Outline ?? 3)
  mergedStyle.Shadow = toNumberValue(sourceStyle.Shadow, defaults.style_fields.Shadow ?? 0)
  mergedStyle.Spacing = toNumberValue(sourceStyle.Spacing, defaults.style_fields.Spacing ?? 0)
  mergedStyle.MarginL = toNumberValue(sourceStyle.MarginL, defaults.style_fields.MarginL ?? 60)
  mergedStyle.MarginR = toNumberValue(sourceStyle.MarginR, defaults.style_fields.MarginR ?? 60)
  mergedStyle.MarginV = toNumberValue(sourceStyle.MarginV, defaults.style_fields.MarginV ?? 45)
  mergedStyle.Alignment = toAlignmentValue(sourceStyle.Alignment, defaults.style_fields.Alignment ?? 2)
  mergedStyle.Bold = toBooleanSwitch(sourceStyle.Bold)
  mergedStyle.Italic = toBooleanSwitch(sourceStyle.Italic)

  const sourceScript = style.script_settings || {}
  const mergedScript = {
    ...defaults.script_settings,
    ...sourceScript
  } as SubtitleScriptSettings
  mergedScript.PlayResX = Math.max(1, Math.round(toNumberValue(sourceScript.PlayResX, defaults.script_settings.PlayResX ?? 1920)))
  mergedScript.PlayResY = Math.max(1, Math.round(toNumberValue(sourceScript.PlayResY, defaults.script_settings.PlayResY ?? 1080)))
  mergedScript.WrapStyle = toWrapStyleValue(sourceScript.WrapStyle, defaults.script_settings.WrapStyle ?? 1)
  mergedScript.ScaledBorderAndShadow = toBooleanSwitch(sourceScript.ScaledBorderAndShadow)
  if (typeof mergedScript.Title === 'string') mergedScript.Title = mergedScript.Title.trim()
  if (typeof mergedScript.YCbCrMatrix === 'string') mergedScript.YCbCrMatrix = mergedScript.YCbCrMatrix.trim()

  const sourceEffect = style.effect_settings || {}
  const mergedEffect = {
    ...defaults.effect_settings,
    ...sourceEffect
  } as SubtitleEffectSettings

  if (!mergedEffect.AlignmentVariant) {
    const payload = style.style_payload as Record<string, any> | null
    const meta = payload?._meta as Record<string, any> | undefined
    const effectsMeta = meta?.effects as Record<string, any> | undefined
    const rawVariant = effectsMeta?.AlignmentVariant ?? payload?.AlignmentVariant
    const normalisedVariant = normaliseAlignmentVariant(rawVariant)
    if (normalisedVariant) {
      mergedEffect.AlignmentVariant = normalisedVariant
    }
  }
  mergedEffect.Blur = toNumberValue(sourceEffect.Blur, defaults.effect_settings.Blur ?? 0)
  const trimEffectEntry = (key: 'Fade' | 'Move' | 'Animation' | 'TextOverride') => {
    if (typeof mergedEffect[key] === 'string') {
      const trimmed = (mergedEffect[key] as string).trim()
      if (trimmed) {
        mergedEffect[key] = trimmed
      } else {
        delete (mergedEffect as Record<string, unknown>)[key]
      }
    }
  }
  trimEffectEntry('Fade')
  trimEffectEntry('Move')
  trimEffectEntry('Animation')
  trimEffectEntry('TextOverride')

  if (mergedEffect.Animation && typeof mergedEffect.Animation === 'object') {
    const maybeTransforms = (mergedEffect.Animation as { transforms?: unknown }).transforms
    if (Array.isArray(maybeTransforms) && maybeTransforms.length === 0) {
      delete (mergedEffect as Record<string, unknown>).Animation
    }
  }
  if (typeof mergedEffect.SequenceMode === 'string') {
    const normalisedMode = normaliseSequenceMode(mergedEffect.SequenceMode)
    mergedEffect.SequenceMode = normalisedMode || undefined
  }
  const parsedJitter = parseSequenceJitterValue(mergedEffect.SequenceJitter)
  if (parsedJitter) {
    mergedEffect.SequenceJitter = parsedJitter
  } else if (mergedEffect.SequenceJitter !== undefined) {
    delete mergedEffect.SequenceJitter
  }
  if (mergedEffect.SequenceMode === 'word-continuous' && !mergedEffect.SequenceJitter) {
    mergedEffect.SequenceJitter = { dx: 2, dy: 2 }
  }

  const normalisedCase = normaliseTextCaseValue(mergedEffect.TextCase)
  if (normalisedCase) {
    mergedEffect.TextCase = normalisedCase
  } else {
    delete (mergedEffect as Record<string, unknown>).TextCase
  }

  const normalisedStrip = parseStripPunctuationValue(mergedEffect.StripPunctuation)
  if (normalisedStrip === undefined) {
    delete (mergedEffect as Record<string, unknown>).StripPunctuation
  } else {
    mergedEffect.StripPunctuation = normalisedStrip
  }

  form.name = style.name
  form.description = style.description ?? ''
  form.sample_text = style.sample_text ?? ''
  form.is_active = style.is_active
  form.is_default = style.is_default
  form.style_fields = { ...mergedStyle }
  form.script_settings = { ...mergedScript }
  const plainEffectSettings = clonePlain(mergedEffect) as SubtitleEffectSettings
  form.effect_settings = plainEffectSettings
  console.log('Loaded style', style?.name, 'effect settings:', plainEffectSettings)
  ensureSequenceAnchor()
  syncTextOverrideAlignment()
  activeTab.value = 'style'
  originalStylePayload.value = style.style_payload ? JSON.parse(JSON.stringify(style.style_payload)) : null
  syncDisplayFontSize()
}

const syncDisplayFontSize = () => {
  const actual = Number(form.style_fields.Fontsize) || 0
  syncingFromActual = true
  displayFontSize.value = actual > 0 ? Math.round(actual * 10) / 10 : 0
  syncingFromActual = false
}

const clonePlain = <T>(value: T): T => {
  if (value === null || value === undefined) return value
  return JSON.parse(JSON.stringify(value))
}

const buildStylePayload = ({
  styleFields,
  scriptSettings,
  effectSettings
}: {
  styleFields: SubtitleStyleFieldValues
  scriptSettings: SubtitleScriptSettings
  effectSettings: SubtitleEffectSettings
}): Record<string, any> => {
  const base: Record<string, any> = clonePlain(originalStylePayload.value) ?? {}
  const styleMeta: Record<string, any> = {}
  const scriptMeta: Record<string, any> = {}
  const effectMeta: Record<string, any> = {}

  const applySection = (source: Record<string, any>, meta: Record<string, any>) => {
    Object.entries(source).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') {
        delete base[key]
        return
      }
      const plain = typeof value === 'object' ? clonePlain(value) : value
      base[key] = plain
      meta[key] = plain
    })
  }

  applySection(styleFields as Record<string, any>, styleMeta)
  applySection(scriptSettings as Record<string, any>, scriptMeta)
  applySection(effectSettings as Record<string, any>, effectMeta)

  base._meta = {
    style: styleMeta,
    script: scriptMeta,
    effects: effectMeta
  }

  return base
}

const buildPayload = (): SubtitleStylePayload | SubtitleStyleUpdatePayload => {
  ensureSequenceAnchor()
  syncTextOverrideAlignment()
  const style_fields = { ...form.style_fields }
  const script_settings = { ...form.script_settings }
  const effect_settings = { ...form.effect_settings }

  if (typeof style_fields.Fontname === 'string') {
    style_fields.Fontname = style_fields.Fontname.trim() || undefined
  }

  const normaliseColour = (value: unknown): string | undefined => {
    if (typeof value !== 'string') return undefined
    const trimmed = value.trim()
    return trimmed || undefined
  }

  const assignColour = (key: 'PrimaryColour' | 'SecondaryColour' | 'OutlineColour' | 'BackColour') => {
    const colour = normaliseColour(style_fields[key])
    if (colour !== undefined) {
      style_fields[key] = colour
    } else if (style_fields[key] === '') {
      delete style_fields[key]
    }
  }

  assignColour('PrimaryColour')
  assignColour('SecondaryColour')
  assignColour('OutlineColour')
  assignColour('BackColour')

  const convertBoolean = (value: unknown): number | undefined => {
    if (value === null || value === undefined) return undefined
    if (typeof value === 'boolean') return value ? -1 : 0
    if (typeof value === 'number') return value !== 0 ? -1 : 0
    if (typeof value === 'string') {
      const trimmed = value.trim()
      if (!trimmed) return undefined
      return trimmed !== '0' ? -1 : 0
    }
    return undefined
  }

  const boldValue = convertBoolean(style_fields.Bold)
  if (boldValue !== undefined) {
    style_fields.Bold = boldValue
  } else {
    delete style_fields.Bold
  }

  const italicValue = convertBoolean(style_fields.Italic)
  if (italicValue !== undefined) {
    style_fields.Italic = italicValue
  } else {
    delete style_fields.Italic
  }

  if (typeof script_settings.Title === 'string') {
    script_settings.Title = script_settings.Title.trim() || undefined
  }
  if (typeof script_settings.YCbCrMatrix === 'string') {
    script_settings.YCbCrMatrix = script_settings.YCbCrMatrix.trim() || undefined
  }

  const normaliseEffectEntry = (key: 'Fade' | 'Move' | 'Animation' | 'TextOverride') => {
    const current = effect_settings[key]
    if (current === undefined || current === null || current === '') {
      delete effect_settings[key]
      return
    }
    if (typeof current === 'object' && !Array.isArray(current)) {
      if (key === 'Animation') {
        const rows = (current as Record<string, unknown>).transforms
        if (Array.isArray(rows) && rows.length === 0) {
          delete effect_settings[key]
        }
      }
      return
    }
    if (typeof current === 'string') {
      const trimmed = current.trim()
      if (trimmed) {
        effect_settings[key] = trimmed
      } else {
        delete effect_settings[key]
      }
    }
  }

  normaliseEffectEntry('Fade')
  normaliseEffectEntry('Move')
  normaliseEffectEntry('Animation')
  normaliseEffectEntry('TextOverride')

  if (typeof effect_settings.SequenceMode === 'string') {
    const normalisedMode = normaliseSequenceMode(effect_settings.SequenceMode)
    if (!normalisedMode) {
      delete effect_settings.SequenceMode
      delete effect_settings.SequenceJitter
      delete effect_settings.SequenceAnchor
    } else {
      effect_settings.SequenceMode = normalisedMode
      if (normalisedMode === 'word-continuous') {
        const jitter = parseSequenceJitterValue(effect_settings.SequenceJitter)
        if (jitter) {
          effect_settings.SequenceJitter = jitter
        } else {
          delete effect_settings.SequenceJitter
        }
      } else {
        delete effect_settings.SequenceJitter
        delete effect_settings.SequenceAnchor
      }
    }
  } else {
    delete effect_settings.SequenceMode
    delete effect_settings.SequenceJitter
    delete effect_settings.SequenceAnchor
  }

  if (normaliseSequenceMode(effect_settings.SequenceMode) === 'word-continuous') {
    const anchor = normaliseSequenceAnchorForSave(effect_settings.SequenceAnchor)
    if (anchor) {
      effect_settings.SequenceAnchor = anchor
    } else {
      const effectRecord = effect_settings as Record<string, unknown>
      delete effectRecord.SequenceAnchor
    }
  }

  const variant = normaliseAlignmentVariant(effect_settings.AlignmentVariant)
  if (variant) {
    effect_settings.AlignmentVariant = variant
  } else {
    delete (effect_settings as Record<string, unknown>).AlignmentVariant
  }

  const payloadTextCase = normaliseTextCaseValue(effect_settings.TextCase)
  if (payloadTextCase) {
    effect_settings.TextCase = payloadTextCase
  } else {
    delete (effect_settings as Record<string, unknown>).TextCase
  }

  const payloadStrip = parseStripPunctuationValue(effect_settings.StripPunctuation)
  if (payloadStrip === undefined) {
    delete (effect_settings as Record<string, unknown>).StripPunctuation
  } else {
    effect_settings.StripPunctuation = payloadStrip
  }

  const style_payload = buildStylePayload({
    styleFields: style_fields,
    scriptSettings: script_settings,
    effectSettings: effect_settings
  })

  return {
    name: form.name.trim(),
    description: form.description.trim() || null,
    sample_text: form.sample_text.trim() || null,
    is_active: form.is_active,
    is_default: form.is_default,
    style_fields,
    script_settings,
    effect_settings,
    style_payload
  }
}

const handleBack = () => {
  router.push({ name: 'subtitle-styles' })
}

const handleVideoUpload = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (uploadedObjectUrl.value) {
    URL.revokeObjectURL(uploadedObjectUrl.value)
  }
  uploadedObjectUrl.value = URL.createObjectURL(file)
  uploadedFileName.value = file.name
  previewMode.value = 'upload'
  input.value = ''
}

const resetUpload = () => {
  if (uploadedObjectUrl.value) {
    URL.revokeObjectURL(uploadedObjectUrl.value)
    uploadedObjectUrl.value = null
  }
  uploadedFileName.value = ''
  if (previewMode.value === 'upload') {
    previewMode.value = 'default'
  }
}

const loadStyleDetail = async () => {
  if (isCreate.value) {
    resetForm()
    return
  }
  if (!styleId.value) {
    ElMessage.error('缺少有效的样式 ID')
    handleBack()
    return
  }
  loading.value = true
  try {
    const cached = subtitleStyleStore.findById(styleId.value)
    if (cached) {
      initialiseForm(cached)
    } else {
      const detail = await fetchSubtitleStyle(styleId.value)
      initialiseForm(detail)
    }
    await nextTick()
    formRef.value?.clearValidate()
    syncDisplayFontSize()
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '加载字幕样式失败')
    handleBack()
  } finally {
    loading.value = false
  }
}

const handleSave = () => {
  if (!formRef.value) return
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      const payload = buildPayload()
      if (isCreate.value) {
        await subtitleStyleStore.addStyle(payload as SubtitleStylePayload)
        ElMessage.success('字幕样式已创建')
      } else if (styleId.value !== null) {
        await subtitleStyleStore.modifyStyle(styleId.value, payload as SubtitleStyleUpdatePayload)
        ElMessage.success('字幕样式已更新')
      }
      handleBack()
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? error?.message ?? '保存失败')
    } finally {
      saving.value = false
    }
  })
}

onMounted(async () => {
  resetUpload()
  await loadStyleDetail()
})

onBeforeUnmount(() => {
  resetUpload()
})

watch(
  () => form.style_fields.Fontsize,
  () => {
    if (syncingFromDisplay) return
    syncDisplayFontSize()
  },
  { immediate: true }
)

watch(
  () => form.effect_settings.SequenceMode,
  (mode) => {
    const normalised = normaliseSequenceMode(mode)
    if (mode !== undefined && normalised !== mode) {
      form.effect_settings.SequenceMode = normalised || ''
      return
    }
    if (normalised === 'word-continuous') {
      ensureSequenceJitter()
    }
    ensureSequenceAnchor()
  }
)

watch(
  () => [
    normaliseSequenceMode(form.effect_settings.SequenceMode),
    form.style_fields.Alignment,
    form.style_fields.MarginL,
    form.style_fields.MarginR,
    form.style_fields.MarginV,
    form.script_settings.PlayResX,
    form.script_settings.PlayResY,
    form.effect_settings.TextOverride
  ],
  () => {
    ensureSequenceAnchor()
  }
)

watch(
  () => form.style_fields.Alignment,
  () => {
    syncTextOverrideAlignment()
  }
)

watch(displayFontSize, (value) => {
  if (syncingFromActual) return
  syncingFromDisplay = true
  const numeric = Math.max(0, Number(value) || 0)
  form.style_fields.Fontsize = Math.max(1, Math.round(numeric * 10) / 10)
  syncingFromDisplay = false
})

watch(
  previewMode,
  (mode, previous) => {
    if (previous === 'upload' && mode !== 'upload' && uploadedObjectUrl.value) {
      URL.revokeObjectURL(uploadedObjectUrl.value)
      uploadedObjectUrl.value = null
      uploadedFileName.value = ''
    }
  }
)
</script>

<style scoped>
.subtitle-style-editor {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  padding: 0;
}

.alert-bar {
  margin-bottom: 8px;
}

.editor-layout {
  display: grid;
  grid-template-columns: minmax(420px, 1fr) minmax(340px, 440px);
  gap: 16px;
  align-items: stretch;
}

.form-card,
.preview-card {
  height: fit-content;
}

.extra-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}


.subtitle-style-tabs {
  margin-top: 12px;
}

.info-icon {
  margin-left: 8px;
  color: var(--el-color-info);
  cursor: pointer;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.preview-title {
  font-size: 18px;
  font-weight: 600;
}

.preview-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.upload-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.upload-input {
  font-size: 12px;
}

.upload-name {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.preview-meta {
  margin-top: 12px;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.meta-label {
  color: var(--el-text-color-regular);
}

@media (max-width: 1180px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
}
</style>
