export interface ServiceCredential {
  id: number
  service_name: string
  credential_type: string
  credential_key: string | null
  api_url: string | null
  is_active: boolean
  description: string | null
  created_at?: string | null
  updated_at?: string | null
}

export interface ServiceCredentialPayload {
  service_name: string
  credential_type?: string
  credential_key?: string | null
  credential_secret?: string | null
  api_url?: string | null
  description?: string | null
  is_active?: boolean
}

export type ServiceCredentialUpdatePayload = Partial<ServiceCredentialPayload>

export interface ServiceOption {
  id: number
  service_name: string
  option_type: string
  option_key: string
  option_value: string
  option_name: string | null
  description: string | null
  is_default: boolean
  is_active: boolean
  meta_data: Record<string, unknown> | null
  created_at?: string | null
}

export interface ServiceOptionPayload {
  service_name: string
  option_type: string
  option_key: string
  option_value: string
  option_name?: string | null
  description?: string | null
  is_default?: boolean
  is_active?: boolean
  meta_data?: Record<string, unknown> | null
}

export type ServiceOptionUpdatePayload = Partial<ServiceOptionPayload>
