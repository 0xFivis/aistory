<template>
  <div class="page-container home-page">
    <el-card class="section-card toolbar-card" shadow="never">
      <div class="section-header">
        <div class="section-title">任务管理</div>
        <div class="actions">
          <el-button type="primary" @click="openCreateDialog">新建任务</el-button>
          <el-button @click="openStylePresetManager">管理风格组合</el-button>
          <el-button @click="openSubtitleStyleManager">管理字幕样式</el-button>
          <el-button plain :loading="listLoading" @click="refresh">刷新</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="section-card table-card" shadow="never">
      <el-table :data="tasks" v-loading="listLoading" border stripe>
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            {{ row.params?.title ?? '未命名任务' }}
          </template>
        </el-table-column>
        <el-table-column label="模式" width="120" align="center">
          <template #default="{ row }">
            <el-tag type="info" v-if="row.mode === 'manual'">手动</el-tag>
            <el-tag type="success" v-else>自动</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="200" align="center">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="14" />
          </template>
        </el-table-column>
        <el-table-column label="更新时间" min-width="180" align="center">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="成片" width="120" align="center">
          <template #default="{ row }">
            <a
              v-if="row.final_video_url"
              :href="row.final_video_url"
              target="_blank"
              rel="noopener noreferrer"
            >查看</a>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link @click="openDetail(row.id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createVisible" title="新建任务" width="520px" destroy-on-close>
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="96px">
        <el-form-item label="任务标题" prop="title">
          <el-input v-model="createForm.title" placeholder="请输入任务标题" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="Storyboard 来源">
          <el-radio-group v-model="createForm.storyboard_mode">
            <el-radio-button label="llm">大模型生成</el-radio-button>
            <el-radio-button label="script">脚本导入</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item
          v-if="createForm.storyboard_mode === 'llm'"
          label="文案内容"
          prop="description"
        >
          <el-input
            v-model="createForm.description"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 6 }"
            placeholder="请输入视频文案"
          />
        </el-form-item>
        <el-form-item
          v-else
          label="分镜脚本"
          prop="storyboard_script_text"
        >
          <el-input
            v-model="createForm.storyboard_script_text"
            type="textarea"
            :autosize="{ minRows: 6, maxRows: 12 }"
            placeholder="粘贴分镜脚本 JSON，示例见文档"
          />
          <div class="script-helper">
            <el-button text type="primary" @click="triggerScriptFileSelect">从文件导入</el-button>
            <span class="script-hint">支持 JSON 文件，或直接粘贴。</span>
          </div>
          <input
            ref="scriptFileInput"
            type="file"
            accept=".json,application/json"
            class="hidden-file-input"
            @change="handleScriptFileSelect"
          />
        </el-form-item>
        <el-form-item label="参考视频">
          <el-input v-model="createForm.reference_video" placeholder="可填写参考视频链接" />
        </el-form-item>
        <el-form-item label="分镜数量">
          <el-input-number
            v-model="createForm.scene_count"
            :min="0"
            :max="1000"
            :step="1"
            placeholder="0 表示自动"
          />
        </el-form-item>
        <el-form-item label="旁白语言" prop="language">
          <el-select v-model="createForm.language" placeholder="选择语言">
            <el-option label="中文" value="中文" />
            <el-option label="英语" value="英语" />
          </el-select>
        </el-form-item>
        <el-form-item label="配音音色" prop="audio_voice_id">
          <el-select
            v-model="createForm.audio_voice_id"
            placeholder="请选择音色"
            filterable
            :loading="voiceLoading"
          >
            <el-option
              v-for="voice in voiceOptions"
              :key="voice.id"
              :label="voice.option_name ?? voice.option_key"
              :value="voice.option_key"
            >
              <span>{{ voice.option_name ?? voice.option_key }}</span>
              <span v-if="voice.is_default" class="option-tag">默认</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="裁剪静音">
          <el-switch
            v-model="createForm.audio_trim_silence"
            active-text="自动裁剪"
            inactive-text="保留"
          />
        </el-form-item>
        <el-form-item label="风格组合">
          <el-select
            v-model="createForm.style_preset_id"
            placeholder="可选择预设风格"
            clearable
            filterable
            :loading="styleLoading"
          >
            <el-option
              v-for="preset in activePresets"
              :key="preset.id"
              :label="preset.name"
              :value="preset.id"
            />
          </el-select>
          <div v-if="selectedPreset" class="preset-preview">
            <div class="preset-preview__name">{{ selectedPreset.name }}</div>
            <p v-if="selectedPreset.prompt_example">
              <strong>提示词示例：</strong>{{ selectedPreset.prompt_example }}
            </p>
            <p v-if="selectedPreset.trigger_words">
              <strong>触发词：</strong>{{ selectedPreset.trigger_words }}
            </p>
              <p v-if="selectedPreset.checkpoint_id || selectedPreset.lora_id">
                <strong>Liblib：</strong>
                <span v-if="selectedPreset.checkpoint_id">模型 {{ selectedPreset.checkpoint_id }}</span>
                <span v-if="selectedPreset.checkpoint_id && selectedPreset.lora_id">，</span>
                <span v-if="selectedPreset.lora_id">LoRA {{ selectedPreset.lora_id }}</span>
            </p>
          </div>
        </el-form-item>
        <el-form-item label="字幕样式">
          <el-select
            v-model="createForm.subtitle_style_id"
            placeholder="可选择字幕样式"
            clearable
            filterable
            :loading="subtitleStyleLoading"
          >
            <el-option
              v-for="style in activeSubtitleStyles"
              :key="style.id"
              :label="style.name"
              :value="style.id"
            />
          </el-select>
          <div v-if="selectedSubtitleStyle" class="subtitle-style-preview">
            <div class="subtitle-style-preview__name">{{ selectedSubtitleStyle.name }}</div>
            <p v-if="selectedSubtitleStyle.description">
              <strong>说明：</strong>{{ selectedSubtitleStyle.description }}
            </p>
            <p v-if="selectedSubtitleStyle.sample_text">
              <strong>示例：</strong>{{ selectedSubtitleStyle.sample_text }}
            </p>
          </div>
        </el-form-item>
        <el-form-item label="背景音乐">
          <el-select
            v-model="createForm.bgm_asset_id"
            placeholder="不选择则不配乐"
            clearable
            filterable
            :loading="bgmLoading"
          >
            <el-option
              v-for="asset in bgmItems"
              :key="asset.id"
              :label="asset.is_default ? `${asset.asset_name}（默认）` : asset.asset_name"
              :value="asset.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="图生视频通道">
          <el-select v-model="createForm.provider" placeholder="可选">
            <el-option label="Fal" value="fal" />
            <el-option label="RunningHub" value="runninghub" />
            <el-option label="NCA" value="nca" />
          </el-select>
        </el-form-item>
        <el-form-item label="媒体处理工具">
          <el-select v-model="createForm.media_tool" placeholder="可选">
            <el-option label="NCA" value="nca" />
            <el-option label="FFmpeg" value="ffmpeg" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行模式" prop="mode">
          <el-radio-group v-model="createForm.mode">
            <el-radio-button label="auto">自动</el-radio-button>
            <el-radio-button label="manual">手动</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeCreateDialog">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, nextTick, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import dayjs from 'dayjs'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useTaskStore } from '@/stores/task'
import { useStylePresetStore } from '@/stores/stylePreset'
import { useSubtitleStyleStore } from '@/stores/subtitleStyle'
import { useAssetStore } from '@/stores/asset'
import { useVoiceOptionStore } from '@/stores/voice'
import type { VoiceOption, StoryboardScriptPayload } from '@/types/task'
import { statusLabel, statusTagType } from '@/utils/task'
import { parseStoryboardScriptText } from '@/utils/storyboard'

const router = useRouter()
const taskStore = useTaskStore()
const { tasks, listLoading } = storeToRefs(taskStore)
const stylePresetStore = useStylePresetStore()
const { activePresets, loading: styleLoading } = storeToRefs(stylePresetStore)
const subtitleStyleStore = useSubtitleStyleStore()
const { activeStyles: activeSubtitleStyles, loading: subtitleStyleLoading } =
  storeToRefs(subtitleStyleStore)
const assetStore = useAssetStore()
const { bgmItems, bgmLoading } = storeToRefs(assetStore)
const voiceStore = useVoiceOptionStore()
const { options: voiceOptions, loading: voiceLoading, defaultOption: defaultVoice } = storeToRefs(voiceStore)

const detectEnglishVoice = (voice: VoiceOption) => {
  const meta = (voice.meta_data as Record<string, unknown> | null) ?? null
  const metaLanguage = meta && typeof meta['language'] === 'string' ? (meta['language'] as string) : ''
  const name = voice.option_name ?? ''
  const key = voice.option_key ?? ''
  const combined = `${metaLanguage}|${name}|${key}`.toLowerCase()
  return combined.includes('english') || combined.includes('en') || combined.includes('英')
}

const englishVoiceKey = computed(() => {
  if (!voiceOptions.value.length) {
    return defaultVoice.value?.option_key ?? ''
  }
  const english = voiceOptions.value.find((item) => detectEnglishVoice(item))
  const fallback = defaultVoice.value ?? voiceOptions.value[0]
  return (english ?? fallback).option_key
})

const createVisible = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const scriptFileInput = ref<HTMLInputElement | null>(null)
const createForm = reactive({
  title: '',
  description: '',
  reference_video: '',
  mode: 'auto' as 'auto' | 'manual',
  storyboard_mode: 'llm' as 'llm' | 'script',
  storyboard_script_text: '',
  scene_count: 0,
  language: '英语',
  provider: '',
  media_tool: '',
  style_preset_id: undefined as number | undefined,
  subtitle_style_id: undefined as number | undefined,
  bgm_asset_id: undefined as number | undefined,
  audio_voice_id: '',
  audio_trim_silence: true
})

const validateDescription = (
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
) => {
  if (createForm.storyboard_mode === 'script') {
    callback()
    return
  }
  if (!value || !value.trim()) {
    callback(new Error('请输入文案内容'))
    return
  }
  callback()
}

const validateStoryboardScript = (
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
) => {
  if (createForm.storyboard_mode !== 'script') {
    callback()
    return
  }
  if (!value || !value.trim()) {
    callback(new Error('请粘贴分镜脚本 JSON'))
    return
  }
  try {
    parseStoryboardScriptText(value)
    callback()
  } catch (error: any) {
    callback(new Error(error?.message ?? '脚本格式不正确'))
  }
}

const createRules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  description: [{ validator: validateDescription, trigger: 'blur' }],
  language: [{ required: true, message: '请选择旁白语言', trigger: 'change' }],
  audio_voice_id: [{ required: true, message: '请选择配音音色', trigger: 'change' }],
  mode: [{ required: true, message: '请选择执行模式', trigger: 'change' }],
  storyboard_script_text: [{ validator: validateStoryboardScript, trigger: 'blur' }]
}

onMounted(() => {
  refresh()
  stylePresetStore.loadPresets()
  subtitleStyleStore.loadStyles().catch(() => {})
  assetStore.loadBgmAssets()
  voiceStore.ensureLoaded().catch(() => {})
})

watch(
  () => activePresets.value,
  () => {
    if (!createForm.style_preset_id) return
    const exists = activePresets.value.some((item) => item.id === createForm.style_preset_id)
    if (!exists) {
      createForm.style_preset_id = undefined
    }
  },
  { deep: true }
)

watch(
  () => activeSubtitleStyles.value,
  () => {
    if (!createForm.subtitle_style_id) return
    const exists = activeSubtitleStyles.value.some((item) => item.id === createForm.subtitle_style_id)
    if (!exists) {
      createForm.subtitle_style_id = undefined
    }
  },
  { deep: true }
)

watch(
  () => bgmItems.value,
  () => {
    if (!createForm.bgm_asset_id) return
    const exists = bgmItems.value.some((item) => item.id === createForm.bgm_asset_id)
    if (!exists) {
      createForm.bgm_asset_id = undefined
    }
  }
)

watch(
  () => createForm.storyboard_mode,
  (mode) => {
    if (mode === 'llm') {
      createForm.storyboard_script_text = ''
      nextTick(() => createFormRef.value?.clearValidate(['storyboard_script_text']))
    }
    if (mode === 'script') {
      createForm.description = ''
      nextTick(() => createFormRef.value?.clearValidate(['description']))
    }
  }
)

const refresh = () => {
  taskStore.loadTasks()
}

const openDetail = (taskId: number) => {
  router.push({ name: 'task-detail', params: { id: taskId } })
}

const openCreateDialog = () => {
  createVisible.value = true
  nextTick(() => createFormRef.value?.clearValidate())
}

const openStylePresetManager = () => {
  router.push({ name: 'style-presets' })
}

const openSubtitleStyleManager = () => {
  router.push({ name: 'subtitle-styles' })
}

const triggerScriptFileSelect = () => {
  scriptFileInput.value?.click()
}

const handleScriptFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string') {
      createForm.storyboard_script_text = reader.result
      nextTick(() => createFormRef.value?.validateField('storyboard_script_text'))
    }
  }
  reader.onerror = () => {
    ElMessage.error('读取脚本文件失败')
  }
  reader.readAsText(file, 'utf-8')
  if (target) {
    target.value = ''
  }
}

const resetCreateForm = () => {
  createForm.title = ''
  createForm.description = ''
  createForm.reference_video = ''
  createForm.mode = 'auto'
  createForm.storyboard_mode = 'llm'
  createForm.storyboard_script_text = ''
  createForm.scene_count = 0
  createForm.language = '英语'
  createForm.provider = ''
  createForm.media_tool = ''
  createForm.style_preset_id = undefined
  createForm.subtitle_style_id = undefined
  createForm.bgm_asset_id = undefined
  createForm.audio_voice_id = englishVoiceKey.value
  createForm.audio_trim_silence = true
}

const closeCreateDialog = () => {
  createVisible.value = false
  resetCreateForm()
}

const submitCreate = () => {
  if (!createFormRef.value) return
  createFormRef.value.validate(async (valid) => {
    if (!valid) return
    creating.value = true
    try {
      const storyboardMode = createForm.storyboard_mode
      const wantAutoAfterScript = createForm.mode === 'auto'
      let scriptPayload: StoryboardScriptPayload | null = null
      if (storyboardMode === 'script') {
        try {
          scriptPayload = parseStoryboardScriptText(createForm.storyboard_script_text)
        } catch (error: any) {
          ElMessage.error(error?.message ?? '脚本格式不正确')
          creating.value = false
          return
        }
      }
      const sceneCount = typeof createForm.scene_count === 'number' ? createForm.scene_count : 0
      const descriptionValue =
        storyboardMode === 'script'
          ? createForm.description?.trim() || '脚本导入任务'
          : createForm.description
      const task = await taskStore.addTask({
        title: createForm.title,
        description: descriptionValue,
        reference_video: createForm.reference_video || undefined,
        mode: storyboardMode === 'script' ? 'manual' : createForm.mode,
        scene_count: sceneCount,
        language: createForm.language,
        audio_voice_id: createForm.audio_voice_id,
        audio_trim_silence: createForm.audio_trim_silence,
        provider: createForm.provider || undefined,
        media_tool: createForm.media_tool || undefined,
        style_preset_id: createForm.style_preset_id,
        subtitle_style_id: createForm.subtitle_style_id,
        bgm_asset_id: createForm.bgm_asset_id
      })
      if (storyboardMode === 'script' && scriptPayload) {
        if (wantAutoAfterScript) {
          await taskStore.editTask(task.id, { mode: 'auto' })
        }
        await taskStore.importStoryboardScript(task.id, scriptPayload, {
          autoTrigger: wantAutoAfterScript
        })
        ElMessage.success(
          wantAutoAfterScript ? '脚本导入成功，Storyboard 已完成并继续执行' : '脚本导入成功'
        )
      } else {
        ElMessage.success('任务创建成功，Storyboard 步骤已排队')
      }
      closeCreateDialog()
      router.push({ name: 'task-detail', params: { id: task.id } })
    } catch (error: any) {
      const message = error?.data?.detail || '任务创建失败'
      ElMessage.error(message)
    } finally {
      creating.value = false
    }
  })
}

const formatDate = (value: string) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const selectedPreset = computed(() => {
  if (!createForm.style_preset_id) return null
  return activePresets.value.find((item) => item.id === createForm.style_preset_id) ?? null
})

const selectedSubtitleStyle = computed(() => {
  return subtitleStyleStore.findById(createForm.subtitle_style_id) ?? null
})

watch(
  () => voiceOptions.value,
  () => {
    if (!voiceOptions.value.length) {
      createForm.audio_voice_id = ''
      return
    }
    const exists = voiceOptions.value.some(
      (item: VoiceOption) => item.option_key === createForm.audio_voice_id
    )
    if (!exists || !createForm.audio_voice_id) {
      createForm.audio_voice_id = englishVoiceKey.value
    }
  }
)
</script>

<style scoped>
.home-page {
  gap: var(--layout-section-gap);
}

.toolbar-card :deep(.el-card__body) {
  padding: var(--space-4);
}

.actions {
  display: inline-flex;
  gap: var(--space-3);
}

.actions :deep(.el-button + .el-button) {
  margin-left: 0;
}

.table-card :deep(.el-card__body) {
  padding: 0;
}

.table-card :deep(.el-table__cell) {
  padding: var(--space-3);
}

.preset-preview {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

.subtitle-style-preview {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

.preset-preview__name {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-1);
  color: var(--color-neutral-900);
}

.subtitle-style-preview__name {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-1);
  color: var(--color-neutral-900);
}

.preset-preview p {
  margin: 2px 0;
}

.subtitle-style-preview p {
  margin: 2px 0;
}

.option-tag {
  margin-left: var(--space-2);
  font-size: var(--font-size-xs);
  color: var(--color-neutral-500);
}

.script-helper {
  margin-top: var(--space-2);
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-neutral-600);
}

.script-helper .script-hint {
  font-size: var(--font-size-xs);
}

.hidden-file-input {
  display: none;
}

@media (max-width: 768px) {
  .actions {
    flex-wrap: wrap;
    width: 100%;
    gap: var(--space-2);
  }
}
</style>