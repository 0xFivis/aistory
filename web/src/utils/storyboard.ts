import type { StoryboardScriptPayload, StoryboardScriptScene } from '@/types/task'

export function parseStoryboardScriptText(raw: string): StoryboardScriptPayload {
  if (!raw || !raw.trim()) {
    throw new Error('请提供分镜脚本 JSON 内容')
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(raw)
  } catch (error: any) {
    const message = error?.message ? `JSON 解析失败：${error.message}` : 'JSON 解析失败'
    throw new Error(message)
  }

  let script: unknown
  if (Array.isArray(parsed)) {
    script = parsed
  } else if (parsed && typeof parsed === 'object' && Array.isArray((parsed as any).script)) {
    script = (parsed as any).script
  } else {
    throw new Error('脚本格式无效：缺少 script 数组')
  }

  if (!Array.isArray(script) || script.length === 0) {
    throw new Error('脚本内容为空')
  }

  const normalized: StoryboardScriptScene[] = script.map((item, index) => {
    if (!item || typeof item !== 'object') {
      throw new Error(`脚本第 ${index + 1} 条不是对象`)
    }
    return item as StoryboardScriptScene
  })

  return { script: normalized }
}
