<template>
  <div class="move-editor">
    <div class="editor-toolbar">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button label="structured">参数</el-radio-button>
        <el-radio-button label="raw">自定义</el-radio-button>
      </el-radio-group>
      <el-button
        v-if="mode === 'raw' && structuredTag()"
        link
        type="primary"
        size="small"
        @click="applyStructuredString(rawValue)"
      >
        从字符串解析
      </el-button>
    </div>
    <div v-if="mode === 'structured'" class="grid">
      <el-row :gutter="8">
        <el-col :span="12">
          <el-form-item label="起点 X">
            <el-input-number v-model="structured.fromX" :step="1" :controls="false" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="起点 Y">
            <el-input-number v-model="structured.fromY" :step="1" :controls="false" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="8">
        <el-col :span="12">
          <el-form-item label="终点 X">
            <el-input-number v-model="structured.toX" :step="1" :controls="false" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="终点 Y">
            <el-input-number v-model="structured.toY" :step="1" :controls="false" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="8">
        <el-col :span="12">
          <el-form-item label="开始(ms)">
            <el-input-number v-model="structured.t1" :min="0" :step="10" :controls="false" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="结束(ms)">
            <el-input-number v-model="structured.t2" :min="0" :step="10" :controls="false" />
          </el-form-item>
        </el-col>
      </el-row>
    </div>
    <el-input
      v-else
      v-model="rawValue"
      type="textarea"
      :rows="3"
      placeholder="例如 \\move(100,800,100,600,0,500)"
      resize="vertical"
    />
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import type { MoveConfig } from '@/types/subtitleStyle'

const props = defineProps<{ modelValue?: MoveConfig | string | null }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: MoveConfig | string | undefined): void }>()

const MOVE_PATTERN = /\\move\(\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)\s*,\s*(-?\d+)(?:\s*,\s*(\d+)\s*,\s*(\d+)\s*)?\)/i

const mode = ref<'structured' | 'raw'>('structured')
const rawValue = ref('')
const syncing = ref(false)

const structured = reactive({
  fromX: 0,
  fromY: 0,
  toX: 0,
  toY: 0,
  t1: undefined as number | undefined,
  t2: undefined as number | undefined
})

const toInt = (value: unknown, fallback = 0): number => {
  if (value === null || value === undefined || value === '') return fallback
  const num = Number(value)
  if (!Number.isFinite(num)) return fallback
  return Math.round(num)
}

const applyStructured = (config: MoveConfig | null) => {
  syncing.value = true
  if (config) {
    structured.fromX = toInt(config.from?.x, 0)
    structured.fromY = toInt(config.from?.y, 0)
    structured.toX = toInt(config.to?.x, 0)
    structured.toY = toInt(config.to?.y, 0)
    structured.t1 = config.t1 !== undefined ? Math.max(0, toInt(config.t1)) : undefined
    structured.t2 = config.t2 !== undefined ? Math.max(0, toInt(config.t2)) : undefined
  } else {
    structured.fromX = 0
    structured.fromY = 0
    structured.toX = 0
    structured.toY = 0
    structured.t1 = undefined
    structured.t2 = undefined
  }
  syncing.value = false
}

const structuredTag = () => {
  const start = toInt(structured.fromX)
  const startY = toInt(structured.fromY)
  const endX = toInt(structured.toX)
  const endY = toInt(structured.toY)
  let tag = `\\move(${start},${startY},${endX},${endY}`
  const hasT1 = structured.t1 !== undefined && structured.t1 !== null
  const hasT2 = structured.t2 !== undefined && structured.t2 !== null
  const t1 = hasT1 ? Math.max(0, toInt(structured.t1)) : undefined
  const t2 = hasT2 ? Math.max(0, toInt(structured.t2)) : undefined
  if (t1 !== undefined || t2 !== undefined) {
    const begin = t1 ?? 0
    const end = t2 !== undefined ? Math.max(t2, begin) : begin
    tag += `,${begin},${end}`
  }
  tag += ')'
  return tag
}

const buildStructuredConfig = (): MoveConfig => {
  const from = { x: toInt(structured.fromX), y: toInt(structured.fromY) }
  const to = { x: toInt(structured.toX), y: toInt(structured.toY) }
  const config: MoveConfig = { from, to }
  const hasT1 = structured.t1 !== undefined && structured.t1 !== null
  const hasT2 = structured.t2 !== undefined && structured.t2 !== null
  const t1 = hasT1 ? Math.max(0, toInt(structured.t1)) : undefined
  const t2 = hasT2 ? Math.max(0, toInt(structured.t2)) : undefined
  if (t1 !== undefined) config.t1 = t1
  if (t2 !== undefined) config.t2 = t2
  return config
}

const stripOverride = (text: string): string => {
  let trimmed = text.trim()
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    trimmed = trimmed.slice(1, -1).trim()
  }
  return trimmed
}

const parseMoveString = (text: string): MoveConfig | null => {
  const match = MOVE_PATTERN.exec(stripOverride(text))
  if (!match) return null
  const from = { x: toInt(match[1]), y: toInt(match[2]) }
  const to = { x: toInt(match[3]), y: toInt(match[4]) }
  const config: MoveConfig = { from, to }
  if (match[5]) {
    const start = Math.max(0, toInt(match[5]))
    const end = match[6] ? Math.max(start, toInt(match[6])) : start
    config.t1 = start
    config.t2 = end
  }
  return config
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
  const parsed = parseMoveString(text)
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
      applyStructured(value as MoveConfig)
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
  () => [structured.fromX, structured.fromY, structured.toX, structured.toY, structured.t1, structured.t2],
  emitStructured
)

watch(rawValue, emitRaw)

watch(mode, (next, prev) => {
  if (syncing.value) return
  if (next === 'structured' && prev !== 'structured') {
    const parsed = parseMoveString(rawValue.value)
    if (parsed) {
      applyStructured(parsed)
    }
    emit('update:modelValue', buildStructuredConfig())
  }
  if (next === 'raw' && prev !== 'raw') {
    if (!rawValue.value.trim()) {
      rawValue.value = structuredTag()
    }
    emitRaw()
  }
})
</script>

<style scoped>
.move-editor {
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

.grid .el-form-item {
  margin-bottom: 8px;
}
</style>
