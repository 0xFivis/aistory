<template>
  <div class="color-field">
    <el-color-picker
      v-model="pickerValue"
      color-format="hex"
      show-alpha
      :teleported="false"
      class="picker"
      @change="handlePickerChange"
    />
    <el-input
      v-model="textValue"
      class="color-input"
      size="small"
      clearable
      placeholder="支持 #RRGGBB 或 &H00BBGGRR"
      @blur="commitFromText"
      @keyup.enter.prevent="commitFromText"
      @clear="clearValue"
    />
    <span class="value-hint">{{ displayValue }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string | null | undefined
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | null): void
}>()

const pickerValue = ref<string>('#ffffff')
const textValue = ref('')

const clampAlpha = (value: number) => {
  const bounded = Math.min(Math.max(value, 0), 255)
  return bounded.toString(16).toUpperCase().padStart(2, '0')
}

const invertAlpha = (alphaHex: string) => {
  const numeric = parseInt(alphaHex, 16)
  if (Number.isNaN(numeric)) return '00'
  const inverted = 255 - numeric
  return clampAlpha(inverted)
}

const normaliseAssColour = (value: string | null | undefined) => {
  if (!value) return null
  let text = value.trim()
  if (!text) return null

  const toAssFromRgb = (hex: string): string | null => {
    const upper = hex.toUpperCase()
    if (upper.length === 3 || upper.length === 4) {
      const expand = upper
        .split('')
        .map((ch) => ch + ch)
        .join('')
      return toAssFromRgb(expand)
    }
    if (upper.length !== 6 && upper.length !== 8) {
      return null
    }
    const rgb = upper.slice(0, 6)
    const rawAlpha = upper.length === 8 ? upper.slice(6) : 'FF'
    const assAlpha = invertAlpha(rawAlpha)
    const r = rgb.slice(0, 2)
    const g = rgb.slice(2, 4)
    const b = rgb.slice(4, 6)
    return `&H${assAlpha}${b}${g}${r}`
  }

  if (text.startsWith('#')) {
    const rgbHex = text.slice(1)
    const ass = toAssFromRgb(rgbHex)
    return ass
  }

  if (!text.toUpperCase().startsWith('&H')) {
    return null
  }

  const hex = text.slice(2).toUpperCase()
  if (![6, 8].includes(hex.length)) {
    return null
  }
  return `&H${hex}`
}

const convertToHex = (value: string | null | undefined) => {
  const normalised = normaliseAssColour(value)
  if (!normalised) return '#ffffff'
  const hex = normalised.slice(2).toUpperCase()
  const assAlpha = hex.length === 8 ? hex.slice(0, 2) : '00'
  const color = hex.length === 8 ? hex.slice(2) : hex
  const b = color.slice(0, 2)
  const g = color.slice(2, 4)
  const r = color.slice(4, 6)
  const displayAlpha = invertAlpha(assAlpha)
  const base = `#${r}${g}${b}`
  return displayAlpha !== 'FF' ? `${base}${displayAlpha}` : base
}

const displayValue = computed(() => props.modelValue ?? '自动')

watch(
  () => props.modelValue,
  (value) => {
    pickerValue.value = convertToHex(value)
    textValue.value = value ?? ''
  },
  { immediate: true }
)

const emitValue = (value: string | null) => {
  const normalised = normaliseAssColour(value)
  emit('update:modelValue', normalised)
  textValue.value = normalised ?? ''
  pickerValue.value = convertToHex(normalised)
}

const handlePickerChange = (value: string | null) => {
  if (!value) {
    emitValue(null)
    return
  }
  emitValue(value)
}

const commitFromText = () => {
  const input = textValue.value.trim()
  if (!input) {
    emitValue(null)
    return
  }
  emitValue(input)
}

const clearValue = () => {
  emitValue(null)
}
</script>

<style scoped>
.color-field {
  display: flex;
  align-items: center;
  gap: 8px;
}

.picker {
  flex-shrink: 0;
}

.color-input {
  flex: 1;
}

.value-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 120px;
}
</style>
