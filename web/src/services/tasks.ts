import apiClient from './api'
import type {
  TaskSummary,
  TaskDetail,
  CreateTaskPayload,
  UpdateTaskPayload,
  VoiceOption,
  StoryboardScriptPayload,
  StoryboardScriptImportResponse
} from '@/types/task'

export async function fetchTasks(): Promise<TaskSummary[]> {
  const { data } = await apiClient.get<TaskSummary[]>('/tasks')
  return data
}

export async function createTask(payload: CreateTaskPayload): Promise<TaskSummary> {
  const taskConfig: Record<string, unknown> = {
    scene_count: payload.scene_count,
    language: payload.language,
    audio_voice_id: payload.audio_voice_id,
    audio_trim_silence: payload.audio_trim_silence ?? true
  }

  if (payload.audio_voice_service) {
    taskConfig.audio_voice_service = payload.audio_voice_service
  }

  if (payload.provider !== undefined) {
    taskConfig.provider = payload.provider ?? null
  }

  if (payload.style_preset_id !== undefined) {
    taskConfig.style_preset_id = payload.style_preset_id
  }

  if (payload.subtitle_style_id !== undefined) {
    taskConfig.subtitle_style_id = payload.subtitle_style_id ?? null
  }

  if (payload.bgm_asset_id !== undefined) {
    taskConfig.bgm_asset_id = payload.bgm_asset_id
  }

  if (payload.audio_trim_silence !== undefined) {
    taskConfig.audio_trim_silence = payload.audio_trim_silence
  }

  const providers: Record<string, string> = {}
  if (payload.provider && payload.provider.trim().length > 0) {
    providers.video = payload.provider.trim()
  }
  if (payload.media_tool && payload.media_tool.trim().length > 0) {
    const tool = payload.media_tool.trim()
    providers.scene_merge = tool
    providers.finalize = tool
    providers.media_compose = tool
  }
  if (Object.keys(providers).length > 0) {
    taskConfig.providers = providers
  }

  const body = {
    title: payload.title,
    description: payload.description,
    reference_video: payload.reference_video,
    mode: payload.mode,
    task_config: taskConfig
  }
  const { data } = await apiClient.post<TaskSummary>('/tasks', body)
  return data
}

export async function fetchTaskDetail(taskId: number): Promise<TaskDetail> {
  const { data } = await apiClient.get<TaskDetail>(`/tasks/${taskId}`)
  return data
}

export async function runTaskStep(taskId: number, stepName: string): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/steps/${stepName}/run`, {})
}

export async function retryTaskStep(taskId: number, stepName: string): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/steps/${stepName}/retry`, {}, { params: { force: true } })
}

export async function resetTaskStep(taskId: number, stepName: string): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/steps/${stepName}/reset`, {})
}

export async function retrySceneStep(
  taskId: number,
  sceneId: number,
  stepType: 'image' | 'audio' | 'video' | 'merge'
): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/scenes/${sceneId}/retry`, null, {
    params: { step_type: stepType }
  })
}

export async function updateTask(taskId: number, payload: UpdateTaskPayload): Promise<TaskDetail> {
  const body: Record<string, unknown> = {}

  if (payload.title !== undefined) body.title = payload.title
  if (payload.description !== undefined) body.description = payload.description
  if (payload.reference_video !== undefined) body.reference_video = payload.reference_video
  if (payload.mode !== undefined) body.mode = payload.mode
  if (payload.scene_count !== undefined) body.scene_count = payload.scene_count
  if (payload.language !== undefined) body.language = payload.language
  if (payload.audio_voice_id !== undefined) body.audio_voice_id = payload.audio_voice_id
  if (payload.audio_voice_service !== undefined) body.audio_voice_service = payload.audio_voice_service
  if (payload.provider !== undefined) body.provider = payload.provider ?? null
  if (payload.media_tool !== undefined) body.media_tool = payload.media_tool ?? null
  if (payload.style_preset_id !== undefined) body.style_preset_id = payload.style_preset_id ?? null
  if (payload.subtitle_style_id !== undefined) body.subtitle_style_id = payload.subtitle_style_id ?? null
  if (payload.bgm_asset_id !== undefined) body.bgm_asset_id = payload.bgm_asset_id
  if (payload.audio_trim_silence !== undefined) body.audio_trim_silence = payload.audio_trim_silence

  const { data } = await apiClient.patch<TaskDetail>(`/tasks/${taskId}`, body)
  return data
}

export async function importStoryboardScript(
  taskId: number,
  payload: StoryboardScriptPayload,
  options?: { autoTrigger?: boolean }
): Promise<StoryboardScriptImportResponse> {
  const params: Record<string, unknown> = {}
  if (options?.autoTrigger !== undefined) {
    params.auto_trigger = options.autoTrigger
  }
  const { data } = await apiClient.post<StoryboardScriptImportResponse>(
    `/tasks/${taskId}/storyboard/script`,
    payload,
    { params }
  )
  return data
}

 

export async function interruptStep(taskId: number, stepName: string): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/steps/${stepName}/interrupt`, {})
}

export async function resetAudioPipeline(taskId: number): Promise<void> {
  await apiClient.post(`/tasks/${taskId}/reset/audio-pipeline`, {})
}

export async function fetchVoiceOptions(params?: {
  serviceName?: string
  optionType?: string
  includeInactive?: boolean
}): Promise<VoiceOption[]> {
  const { data } = await apiClient.get<VoiceOption[]>('/tasks/voice-options', {
    params: {
      ...(params?.serviceName ? { service_name: params.serviceName } : {}),
      ...(params?.optionType ? { option_type: params.optionType } : {}),
      ...(params?.includeInactive !== undefined
        ? { include_inactive: params.includeInactive }
        : {}),
    }
  })
  return data
}
