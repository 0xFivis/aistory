export type RunningHubWorkflowType = 'image' | 'video'

export interface RunningHubWorkflow {
  id: number
  name: string
  slug: string | null
  workflow_type: RunningHubWorkflowType
  workflow_id: string
  instance_type: string
  node_info_template: Record<string, unknown>[] | null
  defaults: Record<string, unknown> | null
  description: string | null
  is_active: boolean
  is_default: boolean
  created_at: string | null
  updated_at: string | null
}

export interface RunningHubWorkflowPayload {
  name: string
  slug?: string | null
  workflow_type: RunningHubWorkflowType
  workflow_id: string
  instance_type?: string
  node_info_template?: Record<string, unknown>[] | null
  defaults?: Record<string, unknown> | null
  description?: string | null
  is_active?: boolean
  is_default?: boolean
}

export type RunningHubWorkflowUpdatePayload = Partial<RunningHubWorkflowPayload>
