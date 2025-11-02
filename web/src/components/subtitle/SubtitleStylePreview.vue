<template>
  <el-drawer
    v-model="visible"
    size="420px"
    title="字幕样式预览"
    custom-class="subtitle-style-preview"
  >
    <div v-if="styleData" class="preview-container">
      <div class="preview-header">
        <div>
          <div class="preview-title">{{ styleData.name }}</div>
          <div class="preview-meta">
            <span>状态：{{ styleData.is_active ? '启用' : '禁用' }}</span>
            <span class="separator">|</span>
            <span>引用：{{ styleData.usage_count }}</span>
            <span v-if="styleData.is_default" class="default-tag">默认样式</span>
          </div>
        </div>
        <el-button size="small" @click="emit('update:modelValue', false)">关闭</el-button>
      </div>

      <div class="preview-section">
        <div class="preview-label">示例文本</div>
        <div class="sample-text">{{ styleData.sample_text || defaultSample }}</div>
      </div>

      <div class="preview-section">
        <div class="preview-label">基础样式</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="字体">{{ styleData.style_fields.Fontname }}</el-descriptions-item>
          <el-descriptions-item label="字号">{{ styleData.style_fields.Fontsize }}</el-descriptions-item>
          <el-descriptions-item label="主颜色">{{ styleData.style_fields.PrimaryColour }}</el-descriptions-item>
          <el-descriptions-item label="描边颜色">{{ styleData.style_fields.OutlineColour }}</el-descriptions-item>
          <el-descriptions-item label="描边 / 阴影">
            {{ styleData.style_fields.Outline ?? '-' }} / {{ styleData.style_fields.Shadow ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="对齐">{{ alignmentLabel }}</el-descriptions-item>
          <el-descriptions-item label="边距">
            {{ styleData.style_fields.MarginL ?? '-' }} /
            {{ styleData.style_fields.MarginR ?? '-' }} /
            {{ styleData.style_fields.MarginV ?? '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="preview-section">
        <div class="preview-label">画布设置</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="分辨率">
            {{ styleData.script_settings.PlayResX ?? '-' }} × {{ styleData.script_settings.PlayResY ?? '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="换行策略">
            {{ wrapStyleLabel }}
          </el-descriptions-item>
          <el-descriptions-item label="边框缩放">
            {{ styleData.script_settings.ScaledBorderAndShadow ? '开启' : '关闭' }}
          </el-descriptions-item>
          <el-descriptions-item label="标题">{{ styleData.script_settings.Title || '-' }}</el-descriptions-item>
          <el-descriptions-item label="YCbCrMatrix">{{ styleData.script_settings.YCbCrMatrix || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="preview-section">
        <div class="preview-label">特效设置</div>
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="Blur">{{ styleData.effect_settings.Blur ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="Fade">{{ styleData.effect_settings.Fade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Move">{{ styleData.effect_settings.Move || '-' }}</el-descriptions-item>
          <el-descriptions-item label="Animation">{{ styleData.effect_settings.Animation || '-' }}</el-descriptions-item>
          <el-descriptions-item label="TextOverride">{{ styleData.effect_settings.TextOverride || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </div>
    <div v-else class="empty-preview">
      <el-empty description="请选择样式" />
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SubtitleStyle } from '@/types/subtitleStyle'

const props = defineProps<{
  modelValue: boolean
  styleData: SubtitleStyle | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const defaultSample = '北京时间今晚8点，我们将正式发布最新剧集，敬请期待。'

const alignmentMap: Record<number, string> = {
  1: '左下',
  2: '居中下',
  3: '右下',
  4: '左中',
  5: '居中',
  6: '右中',
  7: '左上',
  8: '居中上',
  9: '右上'
}

const alignmentLabel = computed(() => {
  const value = props.styleData?.style_fields.Alignment
  return value ? alignmentMap[value] ?? `自定义 ${value}` : '-'
})

const wrapStyleMap: Record<number, string> = {
  0: '0 - 过长换行',
  1: '1 - 自动换行',
  2: '2 - 不换行',
  3: '3 - 智能换行'
}

const wrapStyleLabel = computed(() => {
  const value = props.styleData?.script_settings.WrapStyle
  return value !== undefined && value !== null ? wrapStyleMap[value] ?? `自定义 ${value}` : '-'
})

</script>

<style scoped>
.subtitle-style-preview :deep(.el-drawer__body) {
  padding: 0 16px 16px;
}

.preview-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-title {
  font-size: 18px;
  font-weight: 600;
}

.preview-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.separator {
  color: var(--el-text-color-disabled);
}

.default-tag {
  color: var(--el-color-success);
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.sample-text {
  border: 1px dashed var(--el-border-color);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-light);
  font-size: 16px;
}

.empty-preview {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
