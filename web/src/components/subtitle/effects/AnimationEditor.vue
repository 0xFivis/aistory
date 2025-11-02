<template>
  <div class="animation-editor">
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
      <el-empty v-if="!transforms.length" description="暂无变换">
        <template #default>
          <el-button type="primary" size="small" @click="addTransform">新增变换</el-button>
        </template>
      </el-empty>
      <div v-else class="transform-list">
        <el-card
          v-for="item in transforms"
          :key="item.id"
          class="transform-card"
          shadow="never"
        >
          <div class="card-header">
            <span>变换 {{ itemIndex(item) }}</span>
            <el-button link type="danger" @click="removeTransform(item.id)">删除</el-button>
          </div>
          <div class="card-grid">
            <el-form-item label="开始(ms)">
              <el-input-number v-model="item.start" :min="0" :step="50" :controls="false" />
            </el-form-item>
            <el-form-item label="结束(ms)">
              <el-input-number v-model="item.end" :min="0" :step="50" :controls="false" />
            </el-form-item>
            <el-form-item label="加速度">
              <el-input-number v-model="item.accel" :min="0" :step="0.1" :controls="false" />
            </el-form-item>
          </div>
          <el-form-item label="覆盖标签">
            <el-input v-model="item.override" placeholder="例如 \\fscx120\\fscy120" />
          </el-form-item>
        </el-card>
      </div>
      <el-button type="primary" text size="small" @click="addTransform">新增变换</el-button>
    </div>
    <el-input
      v-else
      v-model="rawValue"
      type="textarea"
      :rows="4"
      placeholder="例如 \\t(0,200,\\fscx120)\\t(200,400,1,\\fscx100)"
      resize="vertical"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { AnimationConfig, TransformConfig } from '@/types/subtitleStyle'

interface TransformRow extends TransformConfig {
  id: number
}

const props = defineProps<{ modelValue?: AnimationConfig | string | null }>()
const emit = defineEmits<{ (event: 'update:modelValue', value: AnimationConfig | string | undefined): void }>()

const TRANSFORM_PATTERN = /\\t\(([^()]*)\)/gi

const mode = ref<'structured' | 'raw'>('structured')
const rawValue = ref('')
const syncing = ref(false)

const transforms = ref<TransformRow[]>([])
let nextId = 1

const stripOverride = (text: string): string => {
  let trimmed = text.trim()
  if (trimmed.startsWith('{') && trimmed.endsWith('}')) {
    trimmed = trimmed.slice(1, -1).trim()
  }
  return trimmed
}

const ensureOverride = (value: string): string => {
  let text = stripOverride(value)
  if (!text) return ''
  if (!text.startsWith('\\')) {
    text = `\\${text.replace(/^\\+/, '')}`
  }
  return text
}

const toTime = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') return undefined
  const num = Number(value)
  if (!Number.isFinite(num)) return undefined
  const rounded = Math.round(num)
  return rounded < 0 ? 0 : rounded
}

const toAccel = (value: unknown): number | undefined => {
  if (value === null || value === undefined || value === '') return undefined
  const num = Number(value)
  if (!Number.isFinite(num) || num < 0) return undefined
  return Number(num.toFixed(6))
}

const splitArgs = (payload: string): string[] => {
  const args: string[] = []
  let current = ''
  let depth = 0
  for (const char of payload) {
    if (char === ',' && depth === 0) {
      args.push(current.trim())
      current = ''
      continue
    }
    if (char === '(' || char === '{' || char === '[') depth += 1
    if (char === ')' || char === '}' || char === ']') depth = Math.max(0, depth - 1)
    current += char
  }
  if (current.trim()) args.push(current.trim())
  return args
}

const parseAnimationString = (text: string): TransformRow[] | null => {
  const trimmed = stripOverride(text)
  if (!trimmed) return null
  const rows: TransformRow[] = []
  const matches = Array.from(trimmed.matchAll(TRANSFORM_PATTERN))
  if (!matches.length) return null
  for (const match of matches) {
    const content = match[1]
    const parts = splitArgs(content)
    if (!parts.length) continue
    const override = ensureOverride(parts[parts.length - 1])
    if (!override) continue
    const row: TransformRow = { id: nextId++, override }
    const numeric = parts.slice(0, -1)
    if (numeric.length >= 1) row.start = toTime(numeric[0])
    if (numeric.length >= 2) row.end = toTime(numeric[1])
    if (numeric.length >= 3) row.accel = toAccel(numeric[2])
    rows.push(row)
  }
  return rows.length ? rows : null
}

const applyStructured = (config: AnimationConfig | null) => {
  syncing.value = true
  if (config && Array.isArray(config.transforms)) {
    transforms.value = config.transforms.map((item) => ({
      id: nextId++,
      start: item.start,
      end: item.end,
      accel: item.accel,
      override: item.override || ''
    }))
  } else {
    transforms.value = []
  }
  syncing.value = false
}

const buildStructuredConfig = (): AnimationConfig => {
  const payload = transforms.value
    .map((item) => {
      const override = ensureOverride(item.override || '')
      if (!override) return null
      const entry: TransformConfig = { override }
      const start = toTime(item.start)
      const end = toTime(item.end)
      if (start !== undefined && end !== undefined) {
        entry.start = start
        entry.end = Math.max(end, start)
      }
      const accel = toAccel(item.accel)
      if (accel !== undefined) entry.accel = accel
      return entry
    })
    .filter((entry): entry is TransformConfig => Boolean(entry))
  return { transforms: payload }
}

const toRawString = (config: AnimationConfig): string => {
  return config.transforms
    .map((item) => {
      const args: Array<string> = []
      if (item.start !== undefined && item.end !== undefined) {
        args.push(String(item.start))
        args.push(String(Math.max(item.end, item.start)))
        if (item.accel !== undefined) args.push(String(item.accel))
      } else if (item.accel !== undefined) {
        args.push('0', '0', String(item.accel))
      }
      args.push(ensureOverride(item.override || ''))
      return `\\t(${args.join(',')})`
    })
    .join('')
}

const emitStructured = () => {
  if (syncing.value || mode.value !== 'structured') return
  const config = buildStructuredConfig()
  emit('update:modelValue', config.transforms.length ? config : undefined)
}

const emitRaw = () => {
  if (syncing.value || mode.value !== 'raw') return
  const text = rawValue.value.trim()
  emit('update:modelValue', text ? text : undefined)
}

const applyStructuredString = (value: string) => {
  const rows = parseAnimationString(value)
  if (rows) {
    transforms.value = rows
    mode.value = 'structured'
    const config = buildStructuredConfig()
    emit('update:modelValue', config.transforms.length ? config : undefined)
  }
}

const addTransform = () => {
  transforms.value.push({
    id: nextId++,
    start: 0,
    end: 0,
    accel: undefined,
    override: '\\fscx120'
  })
}

const removeTransform = (id: number) => {
  transforms.value = transforms.value.filter((item) => item.id !== id)
}

const itemIndex = (item: TransformRow) => {
  const index = transforms.value.findIndex((row) => row.id === item.id)
  return index >= 0 ? index + 1 : 0
}

watch(
  () => props.modelValue,
  (value) => {
    syncing.value = true
    if (typeof value === 'string' && value.trim()) {
      mode.value = 'raw'
      rawValue.value = value
      transforms.value = []
    } else if (value && typeof value === 'object') {
      mode.value = 'structured'
      applyStructured(value as AnimationConfig)
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

watch(transforms, emitStructured, { deep: true })
watch(rawValue, emitRaw)

watch(mode, (next, prev) => {
  if (syncing.value) return
  if (next === 'structured' && prev !== 'structured') {
    const parsed = parseAnimationString(rawValue.value)
    if (parsed) {
      transforms.value = parsed
    }
    const config = buildStructuredConfig()
    emit('update:modelValue', config.transforms.length ? config : undefined)
  }
  if (next === 'raw' && prev !== 'raw') {
    if (!rawValue.value.trim()) {
      rawValue.value = toRawString(buildStructuredConfig())
    }
    emitRaw()
  }
})
</script>

<style scoped>
.animation-editor {
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

.transform-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 8px;
}

.transform-card {
  border: 1px solid var(--el-border-color-lighter);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  font-weight: 500;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
  margin-bottom: 8px;
}
</style>
