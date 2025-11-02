import type {
  MediaAsset,
  MediaAssetPayload,
  MediaAssetQuery,
  MediaAssetUploadResponse,
  MediaAssetType
} from '@/types/asset'
import apiClient from './api'

export const fetchAssets = (query: MediaAssetQuery = {}) => {
  return apiClient.get<MediaAsset[]>('/assets', { params: query }).then((res) => res.data)
}

export const fetchBgmAssets = () => {
  return apiClient.get<MediaAsset[]>('/assets/bgm').then((res) => res.data)
}

export const createAsset = (payload: MediaAssetPayload) => {
  return apiClient.post<MediaAsset>('/assets', payload).then((res) => res.data)
}

export const updateAsset = (id: number, payload: Partial<MediaAssetPayload>) => {
  return apiClient.put<MediaAsset>(`/assets/${id}`, payload).then((res) => res.data)
}

export const deleteAsset = (id: number, softDelete = true) => {
  return apiClient.delete(`/assets/${id}`, { params: { soft_delete: softDelete } })
}

export const setDefaultAsset = (id: number) => {
  return apiClient.post(`/assets/${id}/set-default`)
}

export const uploadAssetFile = (assetType: MediaAssetType, file: File) => {
  const formData = new FormData()
  formData.append('asset_type', assetType)
  formData.append('file', file)

  return apiClient
    .post<MediaAssetUploadResponse>('/assets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    .then((res) => res.data)
}
