import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchRunningHubWorkflows,
  createRunningHubWorkflow,
  updateRunningHubWorkflow,
  deleteRunningHubWorkflow
} from '@/services/runninghub'
import type {
  RunningHubWorkflow,
  RunningHubWorkflowPayload,
  RunningHubWorkflowUpdatePayload,
  RunningHubWorkflowType
} from '@/types/runninghub'

export const useRunningHubWorkflowStore = defineStore('runninghubWorkflows', () => {
  const workflows = ref<RunningHubWorkflow[]>([])
  const loading = ref(false)

  const imageWorkflows = computed(() =>
    workflows.value.filter((item) => item.workflow_type === 'image' && item.is_active)
  )
  const videoWorkflows = computed(() =>
    workflows.value.filter((item) => item.workflow_type === 'video' && item.is_active)
  )

  async function loadWorkflows(options: {
    workflowType?: RunningHubWorkflowType
    includeInactive?: boolean
  } = {}) {
    loading.value = true
    try {
      workflows.value = await fetchRunningHubWorkflows(options)
    } finally {
      loading.value = false
    }
  }

  async function addWorkflow(payload: RunningHubWorkflowPayload) {
    const record = await createRunningHubWorkflow(payload)
    workflows.value = [record, ...workflows.value]
    return record
  }

  async function modifyWorkflow(id: number, payload: RunningHubWorkflowUpdatePayload) {
    const record = await updateRunningHubWorkflow(id, payload)
    workflows.value = workflows.value.map((item) => (item.id === id ? record : item))
    return record
  }

  async function removeWorkflow(id: number, hardDelete = false) {
    await deleteRunningHubWorkflow(id, hardDelete)
    if (hardDelete) {
      workflows.value = workflows.value.filter((item) => item.id !== id)
    } else {
      workflows.value = workflows.value.map((item) =>
        item.id === id ? { ...item, is_active: false, is_default: false } : item
      )
    }
  }

  return {
    workflows,
    imageWorkflows,
    videoWorkflows,
    loading,
    loadWorkflows,
    addWorkflow,
    modifyWorkflow,
    removeWorkflow
  }
})
