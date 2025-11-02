export type MediaAssetType = 'bgm' | 'image' | 'video' | 'template'

export interface MediaAsset {
  id: number
  asset_type: MediaAssetType
  asset_name: string
  file_url: string
  file_full_url?: string | null
  file_path?: string | null
  duration?: number | null
  file_size?: number | null
  tags?: string[] | null
  description?: string | null
  is_default: boolean
  is_active: boolean
  meta_info?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}

export interface MediaAssetPayload {
  asset_type: MediaAssetType
  asset_name: string
  file_url: string
  file_path?: string | null
  duration?: number | null
  file_size?: number | null
  tags?: string[] | null
  description?: string | null
  is_default?: boolean
  is_active?: boolean
  meta_info?: Record<string, unknown> | null
}

export interface MediaAssetUploadResponse {
  asset_type: MediaAssetType
  relative_path: string
  api_path: string
  full_url?: string | null
  file_path: string
  file_size: number
  content_type?: string | null
}

export interface MediaAssetQuery {
  asset_type?: MediaAssetType
  tags?: string
  keyword?: string
  is_active?: boolean | null
  limit?: number
  offset?: number
}
