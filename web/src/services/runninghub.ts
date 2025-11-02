import apiClient from './api'
import type {
  RunningHubWorkflow,
  RunningHubWorkflowPayload,
  RunningHubWorkflowUpdatePayload,
  RunningHubWorkflowType
} from '@/types/runninghub'

export async function fetchRunningHubWorkflows(params?: {
  workflowType?: RunningHubWorkflowType
  includeInactive?: boolean
}): Promise<RunningHubWorkflow[]> {
  const { data } = await apiClient.get<RunningHubWorkflow[]>('/runninghub/workflows', {
    params: {
      ...(params?.workflowType ? { workflow_type: params.workflowType } : {}),
      ...(params?.includeInactive ? { include_inactive: true } : {})
    }
  })
  return data
}

export async function createRunningHubWorkflow(
  payload: RunningHubWorkflowPayload
): Promise<RunningHubWorkflow> {
  const { data } = await apiClient.post<RunningHubWorkflow>('/runninghub/workflows', payload)
  return data
}

export async function updateRunningHubWorkflow(
  id: number,
  payload: RunningHubWorkflowUpdatePayload
): Promise<RunningHubWorkflow> {
  const { data } = await apiClient.put<RunningHubWorkflow>(`/runninghub/workflows/${id}`, payload)
  return data
}

export async function deleteRunningHubWorkflow(id: number, hardDelete = false): Promise<void> {
  await apiClient.delete(`/runninghub/workflows/${id}`, {
    params: { hard_delete: hardDelete }
  })
}
