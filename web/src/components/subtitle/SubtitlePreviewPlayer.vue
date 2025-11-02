<template>
  <div class="preview-player">
    <div class="player-shell" :style="frameStyle" ref="containerRef">
      <video
        ref="videoRef"
        class="video-js vjs-default-skin vjs-big-play-centered preview-video"
        preload="auto"
        playsinline
      ></video>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'
import ASS from 'assjs'

interface PreviewSource {
  src: string
  type?: string
}

interface PreviewResolution {
  width: number
  height: number
}

const props = defineProps<{
  source: PreviewSource | null
  subtitles: string
  resolution?: PreviewResolution
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const containerRef = ref<HTMLElement | null>(null)

type VideoJsPlayer = ReturnType<typeof videojs>
type VideoJsPlayerOptions = NonNullable<Parameters<typeof videojs>[1]>

let player: VideoJsPlayer | null = null
let assInstance: { destroy: () => void; resize?: () => void } | null = null

const resolution = computed<PreviewResolution>(() => {
  const width = Math.max(1, Number(props.resolution?.width) || 1920)
  const height = Math.max(1, Number(props.resolution?.height) || 1080)
  return { width, height }
})

const frameStyle = computed(() => {
  const { width, height } = resolution.value
  const ratio = height / width
  return {
    paddingBottom: `${ratio * 100}%`
  }
})

const disposeAss = () => {
  if (assInstance) {
    try {
      assInstance.destroy()
    } catch (err) {
      console.warn('ASS destroy failed', err)
    }
    assInstance = null
  }
}

const renderAss = () => {
  disposeAss()
  const subtitles = props.subtitles
  if (!subtitles || !player) return
  const container = (player.el() as HTMLElement | null) ?? containerRef.value
  const videoElement = player.el()?.getElementsByTagName('video')[0] as HTMLVideoElement | undefined
  if (!videoElement || !container) return
  try {
    assInstance = new ASS(subtitles, videoElement, {
      container,
      offscreenRender: false,
      resampling: 'script_height'
    })
  } catch (error) {
    console.error('ASS 渲染失败', error)
  }
}

const updateSource = () => {
  if (!player) return
  if (!props.source) {
    player.pause()
    player.src({ src: '', type: '' })
    return
  }
  player.src({
    src: props.source.src,
    type: props.source.type ?? 'video/mp4'
  })
  player.load()
}

const applyAspectRatio = () => {
  if (!player) return
  const { width, height } = resolution.value
  if (width > 0 && height > 0) {
    player.aspectRatio(`${width}:${height}`)
  }
}

watch(
  () => props.source,
  () => {
    updateSource()
  },
  { deep: true }
)

watch(
  () => props.subtitles,
  () => {
    renderAss()
  }
)

watch(
  resolution,
  () => {
    applyAspectRatio()
    renderAss()
  },
  { deep: true }
)

onMounted(() => {
  const element = videoRef.value
  if (!element) return
  const options: VideoJsPlayerOptions = {
    controls: true,
    autoplay: false,
    preload: 'auto',
    loop: true,
    fluid: true
  }
  player = videojs(element, options)
  player.fill(true)
  player.on('loadedmetadata', () => {
    applyAspectRatio()
    renderAss()
  })
  player.on('resize', () => {
    if (assInstance && typeof assInstance.resize === 'function') {
      assInstance.resize()
    }
  })
  updateSource()
  applyAspectRatio()
})

onBeforeUnmount(() => {
  disposeAss()
  if (player) {
    player.dispose()
    player = null
  }
})
</script>

<style scoped>
.preview-player {
  position: relative;
  width: 100%;
}

.player-shell {
  position: relative;
  width: 100%;
}

.preview-player :deep(.video-js) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.preview-player :deep(.vjs-poster) {
  background-size: cover;
}

.preview-player :deep(.vjs-tech) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-player :deep(canvas),
.preview-player :deep(.ASS-container) {
  pointer-events: none;
}
</style>
