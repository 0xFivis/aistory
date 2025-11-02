declare module 'assjs' {
  interface ASSOptions {
    container?: HTMLElement
    blend?: string
    offscreenRender?: boolean
    workerUrl?: string
    fonts?: Array<{ name: string; url: string }>
    resampling?: 'video_width' | 'video_height' | 'script_width' | 'script_height'
  }

  interface ASSInstance {
    resize(): void
    seek(time: number): void
    destroy(): void
  }

  interface ASSConstructor {
    new (subtitleText: string, video: HTMLVideoElement, options?: ASSOptions): ASSInstance
  }

  const ASS: ASSConstructor
  export default ASS
}
