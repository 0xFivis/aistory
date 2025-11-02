export const stepNameMap: Record<string, string> = {
  storyboard: '分镜生成',
  generate_images: '生成图片',
  generate_audio: '生成音频',
  generate_videos: '生成视频',
  merge_scene_media: '分镜音视频合成',
  merge_video: '合并视频',
  finalize_video: '成片处理'
}

const statusLabelMap: Record<number, string> = {
  0: '待处理',
  1: '处理中...',
  2: '已完成',
  3: '失败',
  4: '已跳过',
  5: '已取消',
  6: '中断'
}

const statusTagTypeMap: Record<number, '' | 'info' | 'success' | 'warning' | 'danger'> = {
  0: 'info',
  1: 'warning',
  2: 'success',
  3: 'danger',
  4: '',
  5: '',
  6: 'warning'
}

export function statusLabel(status: number): string {
  return statusLabelMap[status] ?? '未知状态'
}

export function statusTagType(status: number): '' | 'info' | 'success' | 'warning' | 'danger' {
  return statusTagTypeMap[status] ?? 'info'
}
