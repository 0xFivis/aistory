# N8N Workflow Analysis

## Workflow Metadata
- **Name**: `历史人物-写实风格-文生图图生视频`
- **Trigger**: `需求输入-视频` form node (webhook). The preceding `设置参数-综合` node persists credential/config defaults (Liblib/FishAudio/Fal/NCA, etc.).
- **Goal**: Split the user script into storyboard scenes, generate images, synthesize narration, create image-to-video clips, merge with audio/bg-music, and return the final video.

## Stage 1 · Input & Preprocessing
- `需求输入-视频` collects script, scene count, language, target platform (Fal / ComfyUI / NCA), reference video.
- `设置参数-综合` stores static fields: Liblib prompt examples, trigger words, access keys, Liblib endpoint info, Fal/NCA/Runninghub keys.
- Auxiliary set nodes (`设置参数-视频网址`, `设置参数-提取分镜`, etc.) prepare values for requests.

## Stage 2 · Storyboard Generation
- `分镜大纲` (Google Gemini) consumes form input + Liblib prompt template → returns JSON array of scenes.
- `遍历-图片` + `循环-图片` iterate the storyboard array for downstream image/audio generation.
- Liblib prompt data informs Gemini, but no Liblib API requests occur here.

## Stage 3 · Narration / Audio
- `声音生成` (Fish Audio TTS) produces MP3 for each scene.
- `上传 mp3` stores audio on Cloudinary; `声音时长` (NCA metadata) retrieves durations.
- `设置参数 -保存内容` records per-scene first frame (filled later), audio URL, narration, duration.

## Stage 4 · Image Generation
- `ComfyUI文生图` → `等待-ComfyUI文生图` → `获取图片-ComfyUI` drive a Runninghub-hosted ComfyUI workflow to produce single-frame images.
- `判断-ComfyUI文生图` handles success/queued/failure statuses.
- Produced image URLs populate `设置参数 -保存内容`.
- **Liblib Usage**: No direct HTTP calls. Liblib credentials remain unused; workflow relies entirely on Runninghub ComfyUI for image generation.

## Stage 5 · Clip Assembly
- `处理合并` scripts consolidate scene entries (firstFrame, audioUrl, narration, duration) into `clips[]`.
- `遍历-分镜` + `循环-分镜` handle each clip sequentially.

## Stage 6 · Image-to-Video
- `路由` selects branch based on `视频平台`: Fal, ComfyUI, or NCA.
  - **Fal branch**: `Fal` request → `等待-Fal` → `获取视频-Fal` → `判断-Fal` → `设置参数-Fal`.
  - **ComfyUI branch**: `ComfyUI` → `等待-ComfyUI` → `获取视频-ComfyUI` → `判断-ComfyUI` → `视频metadata` → `设置参数-ComfyUI` (captures URL, duration, fps).
  - **NCA branch**: `设置参数-NCA` + `图片转视频` use NCA FFmpeg endpoints.
- `视频提示词-Fal` & `视频提示词-ComfyUI` call Gemini to craft English prompts for the respective services.

## Stage 7 · Merge & Background Music
- `汇聚` aggregates generated video/audio.
- `设置-filterString` computes time-stretch factor (setpts/apad filters) for FFmpeg.
- `声音视频合成` (NCA `/v1/ffmpeg/compose`) merges narration with generated video.
- `配乐合成-裁剪` mixes background music via NCA.
- Final video uploaded via `上传 Cloudinary-完整` and delivered through `返回数据-正常`; `保存视频` logs the final URL in Notion.

## Liblib Participation Summary
- Workflow stores Liblib tokens/endpoints and references prompt templates, but **no HTTP node** targets Liblib.
- Image generation paths exclusively use Runninghub/ComfyUI; image prompts are derived from Gemini’s output.
- Image-to-video branches offer Fal/ComfyUI/NCA as selectable providers; Liblib is not among the options.
- Conclusion: Liblib credentials are unused; prompts referencing Liblib serve as stylistic guidelines for Gemini rather than actual API integration.

## Result Delivery
- Final video URL returned to the user (`返回数据-正常`) and optionally saved to Notion.
- NCA handles long-running tasks (FFmpeg) via `等待` → `状态查询` loops.
- Workflow supports multiple scenes via batch loops, with waits and retries to ensure robustness.




功能总结（适用于代码逻辑设计）：
现在我们把N8N工作流这个流程步骤提取出来，先把工具放一边不管，按照我这个格式：
1、输入信息：文案、参考视频、语言、分镜数量、自动/手动、图生视频工具（基本符合目前代码的机构逻辑）
2、文案分析产出分镜信息：AI大模型服务（这里使用的Gemini，后续可能使用其他大模型服务）
3、每个分镜生成图片：文生图服务（这里可选runninghub也是ComfyUI、liblib、后续可能会有其他类似服务）
4、每个分镜生成语言：TTS服务（这里使用的是FishAudio，后续可能使用其他服务如elevenlabs或者其他开源服务）
5、每个分镜生成视频：图生视频服务（这里可选Fal、ComfyUI暂时等同于runninghub、NCA图转视频，后续可能还会支持其他工具）
6、每个分镜音视频合成：素材合成服务，包含音画同步变速处理（目前使用的NCA、后续可能直接使用本地ffmpeg服务）
7、多分镜组合成一个视频：也是素材合成服务（目前使用的NCA，后续可能使用ffmpeg服务）
8、背景音乐合成：也是素材合成服务
9、结果视频存储