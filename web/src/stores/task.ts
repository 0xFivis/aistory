import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchTasks,
  fetchTaskDetail,
  createTask,
  runTaskStep,
  retryTaskStep,
  resetTaskStep,
  retrySceneStep,
  updateTask,
  resetAudioPipeline as apiResetAudioPipeline,
  importStoryboardScript as apiImportStoryboardScript
} from '@/services/tasks'
import type {
  TaskSummary,
  TaskStep,
  SceneRecord,
  CreateTaskPayload,
  UpdateTaskPayload,
  StoryboardScriptPayload,
  StoryboardScriptImportResponse
} from '@/types/task'
import type { SubtitleDocument } from '@/types/subtitle'

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<TaskSummary[]>([])
  const listLoading = ref(false)
  const detailLoading = ref(false)
  const selectedTask = ref<TaskSummary | null>(null)
  const selectedSteps = ref<TaskStep[]>([])
  const selectedScenes = ref<SceneRecord[]>([])

  const hasRunningStep = computed(() =>
    selectedSteps.value.some((step) => step.status === 1)
  )
  const selectedSubtitleDocument = ref<SubtitleDocument | null>(null)

  async function loadTasks() {
    listLoading.value = true
    try {
      tasks.value = await fetchTasks()
    } finally {
      listLoading.value = false
    }
  }

  async function addTask(payload: CreateTaskPayload) {
    const task = await createTask(payload)
    tasks.value = [task, ...tasks.value]
    return task
  }

  async function editTask(taskId: number, payload: UpdateTaskPayload) {
    const detail = await updateTask(taskId, payload)
    selectedTask.value = detail.task
    selectedSteps.value = detail.steps
    selectedScenes.value = detail.scenes
    selectedSubtitleDocument.value = detail.subtitle_document ?? null

    const index = tasks.value.findIndex((item) => item.id === detail.task.id)
    if (index >= 0) {
      tasks.value.splice(index, 1, detail.task)
    } else {
      tasks.value = [detail.task, ...tasks.value]
    }

    return detail
  }

  let currentDetailRequestId = 0

  async function loadTaskDetail(taskId: number, opts: { silent?: boolean } = {}) {
    const requestId = ++currentDetailRequestId
    if (!opts.silent) {
      detailLoading.value = true
    }

    // optimistic reset to avoid flashing stale state for completed tasks
    selectedTask.value = null
    selectedSteps.value = []
    selectedScenes.value = []
    selectedSubtitleDocument.value = null

    try {
      const detail = await fetchTaskDetail(taskId)
      if (requestId !== currentDetailRequestId) {
        return
      }
      selectedTask.value = detail.task
      selectedSteps.value = detail.steps
      selectedScenes.value = detail.scenes
      selectedSubtitleDocument.value = detail.subtitle_document ?? null
    } finally {
      if (!opts.silent && requestId === currentDetailRequestId) {
        detailLoading.value = false
      }
    }
  }

  function clearSelection() {
    selectedTask.value = null
    selectedSteps.value = []
    selectedScenes.value = []
    selectedSubtitleDocument.value = null
  }

  async function triggerStep(taskId: number, stepName: string) {
    await runTaskStep(taskId, stepName)
  }

  async function retryStep(taskId: number, stepName: string) {
    await retryTaskStep(taskId, stepName)
  }

  async function resetStep(taskId: number, stepName: string) {
    await resetTaskStep(taskId, stepName)
  }

  async function retryScene(
    taskId: number,
    sceneId: number,
    stepType: 'image' | 'audio' | 'video' | 'merge'
  ) {
    await retrySceneStep(taskId, sceneId, stepType)
  }

  async function resetAudioPipeline(taskId: number) {
    await apiResetAudioPipeline(taskId)
  }

  async function importStoryboardScript(
    taskId: number,
    payload: StoryboardScriptPayload,
    options?: { autoTrigger?: boolean }
  ): Promise<StoryboardScriptImportResponse> {
    return apiImportStoryboardScript(taskId, payload, options)
  }

  async function interruptStep(taskId: number, stepName: string) {
    // call backend interrupt API
    await import('@/services/tasks').then((m) => m.interruptStep(taskId, stepName))
  }

  return {
    tasks,
    listLoading,
    detailLoading,
    selectedTask,
    selectedSteps,
    selectedScenes,
    selectedSubtitleDocument,
    hasRunningStep,
    loadTasks,
    addTask,
    editTask,
    loadTaskDetail,
    clearSelection,
    triggerStep,
    retryStep,
    resetStep,
    retryScene,
    resetAudioPipeline,
    importStoryboardScript,
    interruptStep
  }
})
