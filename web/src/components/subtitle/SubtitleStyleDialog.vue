<template>
  <el-dialog
    v-model="visible"
    :title="dialogTitle"
    width="860px"
    destroy-on-close
    class="subtitle-style-dialog"
  >
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
            <el-tooltip content="每次仅允许一个默认样式" placement="top">
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
              <el-form-item label="字号" prop="style_fields.Fontsize">
                <el-input-number v-model="form.style_fields.Fontsize" :min="1" :max="200" />
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
                <el-select v-model="form.style_fields.Alignment" placeholder="选择字幕对齐">
                  <el-option v-for="item in alignmentOptions" :key="item.value" :value="item.value" :label="item.label" />
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
                <el-input v-model="form.effect_settings.TextOverride" placeholder="例如 \1a&HFF&" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="动画 Transform" prop="effect_settings.Animation">
            <AnimationEditor v-model="form.effect_settings.Animation" />
          </el-form-item>
        </el-tab-pane>
      </el-tabs>
    </el-form>
    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch, reactive, nextTick } from 'vue'
import { type FormInstance, type FormRules } from 'element-plus'
import { InfoFilled } from '@element-plus/icons-vue'

import type {
  SubtitleStyle,
  SubtitleStylePayload,
  SubtitleStyleUpdatePayload,
  SubtitleStyleFieldValues,
  SubtitleScriptSettings,
  SubtitleEffectSettings,
  AnimationConfig
} from '@/types/subtitleStyle'
import ColorPicker from '@/components/subtitle/SubtitleStyleSwatch.vue'
import MoveEditor from '@/components/subtitle/effects/MoveEditor.vue'
import FadeEditor from '@/components/subtitle/effects/FadeEditor.vue'
import AnimationEditor from '@/components/subtitle/effects/AnimationEditor.vue'

const props = defineProps<{
  modelValue: boolean
  mode: 'create' | 'edit'
  loading: boolean
  styleData: SubtitleStyle | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'submit', payload: SubtitleStylePayload | SubtitleStyleUpdatePayload, mode: 'create' | 'edit'): void
}>()

const formRef = ref<FormInstance>()
const activeTab = ref<'style' | 'script' | 'effect'>('style')
const alignmentOptions = [
  { value: 1, label: '1 左下' },
  { value: 2, label: '2 居中下' },
  { value: 3, label: '3 右下' },
  { value: 4, label: '4 左中' },
  { value: 5, label: '5 居中' },
  { value: 6, label: '6 右中' },
  { value: 7, label: '7 左上' },
  { value: 8, label: '8 居中上' },
  { value: 9, label: '9 右上' }
]

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

const rules: FormRules = {
  name: [{ required: true, message: '请输入样式名称', trigger: 'blur' }],
  'style_fields.Fontname': [{ required: true, message: '请输入字体名称', trigger: 'blur' }],
  'style_fields.Fontsize': [{ required: true, message: '请输入字号', trigger: 'change' }],
  'style_fields.Alignment': [{ required: true, message: '请选择对齐方式', trigger: 'change' }]
}

const clonePlain = <T>(value: T): T => {
  if (value === null || value === undefined) return value
  return JSON.parse(JSON.stringify(value))
}

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const dialogTitle = computed(() => (props.mode === 'create' ? '新增字幕样式' : '编辑字幕样式'))

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
    TextOverride: ''
  } as SubtitleEffectSettings
})

const resetForm = () => {
  const defaults = getDefaultSections()
  form.name = ''
  form.description = ''
  form.sample_text = ''
  form.is_active = true
  form.is_default = false
  form.style_fields = clonePlain(defaults.style_fields) as SubtitleStyleFieldValues
  form.script_settings = clonePlain(defaults.script_settings) as SubtitleScriptSettings
  form.effect_settings = clonePlain(defaults.effect_settings) as SubtitleEffectSettings
  activeTab.value = 'style'
}

const toBooleanSwitch = (value: unknown): boolean => {
  if (typeof value === 'number') {
    return value !== 0
  }
  if (typeof value === 'boolean') {
    return value
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return false
    return trimmed !== '0'
  }
  return false
}

const toNumberValue = (value: unknown, fallback: number): number => {
  if (value === null || value === undefined || value === '') {
    return fallback
  }
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}

const toAlignmentValue = (value: unknown, fallback: number): number => {
  const number = toNumberValue(value, fallback)
  return Math.min(9, Math.max(1, Math.round(number)))
}

const toWrapStyleValue = (value: unknown, fallback: number): number => {
  const number = toNumberValue(value, fallback)
  return Math.min(3, Math.max(0, Math.round(number)))
}

const initialiseForm = (style: SubtitleStyle | null) => {
  if (!style) {
    resetForm()
    return
  }
  const defaults = getDefaultSections()
  const sourceStyle = clonePlain(style.style_fields) || {}
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

  const sourceScript = clonePlain(style.script_settings) || {}
  const mergedScript = {
    ...defaults.script_settings,
    ...sourceScript
  } as SubtitleScriptSettings
  mergedScript.PlayResX = Math.max(1, Math.round(toNumberValue(sourceScript.PlayResX, defaults.script_settings.PlayResX ?? 1920)))
  mergedScript.PlayResY = Math.max(1, Math.round(toNumberValue(sourceScript.PlayResY, defaults.script_settings.PlayResY ?? 1080)))
  mergedScript.WrapStyle = toWrapStyleValue(sourceScript.WrapStyle, defaults.script_settings.WrapStyle ?? 1)
  mergedScript.ScaledBorderAndShadow = toBooleanSwitch(sourceScript.ScaledBorderAndShadow)
  if (typeof mergedScript.Title === 'string') {
    mergedScript.Title = mergedScript.Title.trim()
  }
  if (typeof mergedScript.YCbCrMatrix === 'string') {
    mergedScript.YCbCrMatrix = mergedScript.YCbCrMatrix.trim()
  }

  const sourceEffect = clonePlain(style.effect_settings) || {}
  const mergedEffect = {
    ...defaults.effect_settings,
    ...sourceEffect
  } as SubtitleEffectSettings
  mergedEffect.Blur = toNumberValue(sourceEffect.Blur, defaults.effect_settings.Blur ?? 0)

  const trimEffectEntry = (key: 'Fade' | 'Move' | 'Animation' | 'TextOverride') => {
    if (typeof mergedEffect[key] === 'string') {
      const trimmed = (mergedEffect[key] as string).trim()
      if (trimmed) {
        mergedEffect[key] = trimmed
      } else {
        delete mergedEffect[key]
      }
    }
  }

  trimEffectEntry('Fade')
  trimEffectEntry('Move')
  trimEffectEntry('Animation')
  trimEffectEntry('TextOverride')

  if (mergedEffect.Animation && typeof mergedEffect.Animation === 'object') {
    const animation = mergedEffect.Animation as AnimationConfig
    const rows = Array.isArray(animation.transforms) ? animation.transforms : []
    if (rows.length === 0) {
      delete mergedEffect.Animation
    }
  }

  form.name = style.name
  form.description = style.description ?? ''
  form.sample_text = style.sample_text ?? ''
  form.is_active = style.is_active
  form.is_default = style.is_default
  form.style_fields = clonePlain(mergedStyle) as SubtitleStyleFieldValues
  form.script_settings = clonePlain(mergedScript) as SubtitleScriptSettings
  form.effect_settings = clonePlain(mergedEffect) as SubtitleEffectSettings
  activeTab.value = 'style'
}

watch(
  () => props.styleData,
  (value) => {
    initialiseForm(value ?? null)
    nextTick(() => formRef.value?.clearValidate())
  },
  { immediate: true }
)

watch(
  () => props.modelValue,
  (value) => {
    if (!value) {
      return
    }
    if (props.mode === 'create') {
      resetForm()
      nextTick(() => formRef.value?.clearValidate())
    }
  }
)

const buildPayload = (): SubtitleStylePayload | SubtitleStyleUpdatePayload => {
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
    if (typeof value === 'boolean') {
      return value ? -1 : 0
    }
    if (typeof value === 'number') {
      return value !== 0 ? -1 : 0
    }
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

  const trimEffectString = (value: unknown): string | undefined => {
    if (typeof value !== 'string') return undefined
    const trimmed = value.trim()
    return trimmed || undefined
  }

  const assignEffectString = (key: 'Fade' | 'Move' | 'Animation' | 'TextOverride') => {
    const value = trimEffectString(effect_settings[key])
    if (value !== undefined) {
      effect_settings[key] = value
    } else if (effect_settings[key] === '') {
      delete effect_settings[key]
    }
  }

  assignEffectString('Fade')
  assignEffectString('Move')
  assignEffectString('Animation')
  assignEffectString('TextOverride')

  const payload = {
    name: form.name.trim(),
    description: form.description.trim() || null,
    sample_text: form.sample_text.trim() || null,
    is_active: form.is_active,
    is_default: form.is_default,
    style_fields,
    script_settings,
    effect_settings
  }

  if (props.mode === 'edit') {
    return payload as SubtitleStyleUpdatePayload
  }
  return payload as SubtitleStylePayload
}

const handleSubmit = () => {
  if (!formRef.value) return
  formRef.value.validate((valid) => {
    if (!valid) return
    const payload = buildPayload()
    emit('submit', payload, props.mode)
  })
}

const handleCancel = () => {
  emit('update:modelValue', false)
}
</script>

<style scoped>
.subtitle-style-dialog :deep(.el-dialog__body) {
  padding-top: 8px;
}

.subtitle-style-tabs {
  margin-top: 12px;
}

.info-icon {
  margin-left: 8px;
  color: var(--el-color-info);
  cursor: pointer;
}
</style>
