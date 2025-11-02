<template>
  <div class="fade-editor">
    <div class="editor-toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button label="structured">参数</el-radio-button>
        <el-radio-button label="raw">自定义</el-radio-button>
      </el-radio-group>
      <el-button
        v-if="mode === 'raw' && rawValue.trim()"
        link
        type="primary"
        size="small"
        @click="applyStructuredString(rawValue)"
      >
        从字符串解析
      </el-button>
    </div>
    <div v-if="mode === 'structured'" class="structured">
      <el-radio-group v-model="structured.mode" size="small" class="mode-radio">
        <el-radio-button label="fad">淡入淡出 (\fad)</el-radio-button>
        <el-radio-button label="fade">高级 (\fade)</el-radio-button>
      </el-radio-group>
      <div v-if="structured.mode === 'fad'" class="grid">
        <el-form-item label="淡入(ms)">
          <el-input-number v-model="structured.fadeIn" :min="0" :step="50" :controls="false" />
        </el-form-item>
        <el-form-item label="淡出(ms)">
          <el-input-number v-model="structured.fadeOut" :min="0" :step="50" :controls="false" />
        </el-form-item>
      </div>
      <div v-else class="grid">
        <el-form-item label="起始 Alpha">
          <el-input-number v-model="structured.alphaFrom" :min="0" :max="255" :step="5" :controls="false" />
        </el-form-item>
        <el-form-item label="中间 Alpha">
          <el-input-number v-model="structured.alphaMid" :min="0" :max="255" :step="5" :controls="false" />
        </el-form-item>
        <el-form-item label="结束 Alpha">
          <el-input-number v-model="structured.alphaTo" :min="0" :max="255" :step="5" :controls="false" />
        </el-form-item>
        <el-form-item label="t1(ms)">
          <el-input-number v-model="structured.t1" :min="0" :step="50" :controls="false" />
        </el-form-item>
        <el-form-item label="t2(ms)">
          <el-input-number v-model="structured.t2" :min="0" :step="50" :controls="false" />
        </el-form-item>
        <el-form-item label="t3(ms)">
          <el-input-number v-model="structured.t3" :min="0" :step="50" :controls="false" />
        </el-form-item>
        <el-form-item label="t4(ms)">
          <el-input-number v-model="structured.t4" :min="0" :step="50" :controls="false" />
        </el-form-item>
      </div>
    </div>
    <el-input
      v-else
      v-model="rawValue"
      type="textarea"
      :rows="3"
      placeholder="例如 \\fad(200,200) 或 \\fade(0,255,0,0,200,200,400)"
      resize="vertical"
    />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { FadeAdvancedConfig, FadeConfig } from '@/types/subtitleStyle'

const props = defineProps<{ modelValue?: FadeConfig | string | null }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: FadeConfig | string | undefined): void }>()

const FAD_PATTERN = /\\fad\(\s*(\d+)\s*,\s*(\d+)\s*\)/i
const FADE_PATTERN = /\\fade\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/i

const mode = ref<'structured' | 'raw'>('structured')
const rawValue = ref('')
const syncing = ref(false)

const structured = reactive({
  mode: 'fad' as 'fad' | 'fade',
  fadeIn: 0,
  fadeOut: 0,
  alphaFrom: 0,
  alphaMid: 255,
  alphaTo: 0,
  t1: 0,
  t2: 0,
  t3: 0,
  t4: 0
})

const toInt = (value: unknown, fallback = 0): number => {
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return Math.round(num)
}

const clampByte = (value: unknown, fallback = 0): number => {
  const num = toInt(value, fallback)
  if (num < 0) return 0
  if (num > 255) return 255
  return num
}

const stripOverride = (text: string): string => {
  let trimmed = text.trim()
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    trimmed = trimmed.slice(1, -1).trim()
  }
  return trimmed
}

const applyStructured = (config: FadeConfig | null) => {
  syncing.value = true
  if (config && config.mode === 'fade') {
    structured.mode = 'fade'
    structured.alphaFrom = clampByte(config.alphaFrom)
    structured.alphaMid = clampByte(config.alphaMid)
    structured.alphaTo = clampByte(config.alphaTo)
    structured.t1 = Math.max(0, toInt(config.t1))
    structured.t2 = Math.max(structured.t1, toInt(config.t2))
    structured.t3 = Math.max(structured.t2, toInt(config.t3))
    structured.t4 = Math.max(structured.t3, toInt(config.t4))
  } else if (config && config.mode === 'fad') {
    structured.mode = 'fad'
    structured.fadeIn = Math.max(0, toInt(config.fadeIn))
    structured.fadeOut = Math.max(0, toInt(config.fadeOut))
  } else {
    structured.mode = 'fad'
    structured.fadeIn = 0
    structured.fadeOut = 0
  }
  syncing.value = false
}

const buildStructuredConfig = (): FadeConfig => {
  if (structured.mode === 'fade') {
    const advanced: FadeAdvancedConfig = {
      mode: 'fade',
      alphaFrom: clampByte(structured.alphaFrom),
      alphaMid: clampByte(structured.alphaMid, 255),
      alphaTo: clampByte(structured.alphaTo),
      t1: Math.max(0, toInt(structured.t1)),
      t2: Math.max(0, toInt(structured.t2)),
      t3: Math.max(0, toInt(structured.t3)),
      t4: Math.max(0, toInt(structured.t4))
    }
    advanced.t2 = Math.max(advanced.t2, advanced.t1)
    advanced.t3 = Math.max(advanced.t3, advanced.t2)
    advanced.t4 = Math.max(advanced.t4, advanced.t3)
    return advanced
  }
  return {
    mode: 'fad',
    fadeIn: Math.max(0, toInt(structured.fadeIn)),
    fadeOut: Math.max(0, toInt(structured.fadeOut))
  }
}

const parseFadeString = (text: string): FadeConfig | null => {
  const trimmed = stripOverride(text)
  const fadMatch = FAD_PATTERN.exec(trimmed)
  if (fadMatch) {
    return {
      mode: 'fad',
      fadeIn: Math.max(0, toInt(fadMatch[1])),
      fadeOut: Math.max(0, toInt(fadMatch[2]))
    }
  }
  const fadeMatch = FADE_PATTERN.exec(trimmed)
  if (fadeMatch) {
    return {
      mode: 'fade',
      alphaFrom: clampByte(fadeMatch[1]),
      alphaMid: clampByte(fadeMatch[2], 255),
      alphaTo: clampByte(fadeMatch[3]),
      t1: Math.max(0, toInt(fadeMatch[4])),
      t2: Math.max(0, toInt(fadeMatch[5])),
      t3: Math.max(0, toInt(fadeMatch[6])),
      t4: Math.max(0, toInt(fadeMatch[7]))
    }
  }
  return null
}

const emitStructured = () => {
  if (syncing.value || mode.value !== 'structured') return
  emit('update:modelValue', buildStructuredConfig())
}

const emitRaw = () => {
  if (syncing.value || mode.value !== 'raw') return
  const text = rawValue.value.trim()
  emit('update:modelValue', text ? text : undefined)
}

const applyStructuredString = (text: string) => {
  const parsed = parseFadeString(text)
  if (parsed) {
    applyStructured(parsed)
    mode.value = 'structured'
    emit('update:modelValue', parsed)
  }
}

watch(
  () => props.modelValue,
  (value) => {
    syncing.value = true
    if (typeof value === 'string' && value.trim()) {
      mode.value = 'raw'
      rawValue.value = value
    } else if (value && typeof value === 'object') {
      mode.value = 'structured'
      applyStructured(value as FadeConfig)
      rawValue.value = ''
    } else {
      mode.value = 'structured'
      applyStructured(null)
      rawValue.value = ''
    }
    syncing.value = false
  },
  { immediate: true, deep: true }
)

watch(
  () => [
    structured.mode,
    structured.fadeIn,
    structured.fadeOut,
    structured.alphaFrom,
    structured.alphaMid,
    structured.alphaTo,
    structured.t1,
    structured.t2,
    structured.t3,
    structured.t4
  ],
  emitStructured
)

watch(rawValue, emitRaw)

watch(mode, (next, prev) => {
  if (syncing.value) return
  if (next === 'structured' && prev !== 'structured') {
    const parsed = parseFadeString(rawValue.value)
    if (parsed) {
      applyStructured(parsed)
    }
    emit('update:modelValue', buildStructuredConfig())
  }
  if (next === 'raw' && prev !== 'raw') {
    if (!rawValue.value.trim()) {
      const config = buildStructuredConfig()
      rawValue.value = config.mode === 'fade'
        ? `\\fade(${config.alphaFrom},${config.alphaMid},${config.alphaTo},${config.t1},${config.t2},${config.t3},${config.t4})`
        : `\\fad(${config.fadeIn},${config.fadeOut})`
    }
    emitRaw()
  }
})
</script>

<style scoped>
.fade-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.mode-radio {
  margin-bottom: 8px;
}

.structured .grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
}

.structured .grid .el-form-item {
  margin-bottom: 0;
}
</style>
