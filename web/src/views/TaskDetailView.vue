<template>
  <div class="detail-page page-container">
    <el-page-header content="任务详情" @back="goBack" />

    <div class="spacer" />

  <el-card v-loading="detailLoading" shadow="never" class="info-card section-card">
      <template #header>
        <div class="card-header section-header">
          <span class="section-title">任务概览</span>
          <div class="card-actions">
            <el-button type="primary" link @click="openEditDialog" :disabled="!task">编辑配置</el-button>
            <el-button type="primary" link @click="reload">刷新</el-button>
          </div>
        </div>
      </template>
      <el-descriptions :column="3" border label-class-name="desc-label">
        <el-descriptions-item label="任务 ID">{{ task?.id ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="标题">{{ task?.params?.title ?? '未命名任务' }}</el-descriptions-item>
        <el-descriptions-item label="执行模式">
          <el-tag v-if="task?.mode === 'manual'" type="info">手动</el-tag>
          <el-tag v-else type="success">自动</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="任务状态">
          <el-tag :type="statusTagType(task?.status ?? 0)">{{ statusLabel(task?.status ?? 0) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进度">
          <el-progress :percentage="task?.progress ?? 0" :stroke-width="14" />
        </el-descriptions-item>
        <el-descriptions-item label="媒体处理工具">
          {{ mediaToolLabel || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="配音音色">
          <span v-if="task?.selected_voice_name">
            {{ task?.selected_voice_name }}
            <span
              v-if="task?.selected_voice_id && task?.selected_voice_name !== task?.selected_voice_id"
              class="desc-sub"
            >
              ({{ task?.selected_voice_id }})
            </span>
          </span>
          <span v-else-if="task?.selected_voice_id">ID {{ task?.selected_voice_id }}</span>
          <span v-else>未选择</span>
        </el-descriptions-item>
        <el-descriptions-item label="静音裁剪">
          <el-tag :type="audioTrimEnabled ? 'success' : 'info'">
            {{ audioTrimEnabled ? '已启用' : '未启用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="背景音乐">
          <span v-if="currentBgmAsset">
            {{ currentBgmAsset.is_default ? `${currentBgmAsset.asset_name}（默认）` : currentBgmAsset.asset_name }}
          </span>
          <span v-else-if="currentBgmId">ID {{ currentBgmId }}（已停用或不存在）</span>
          <span v-else>未选择</span>
        </el-descriptions-item>
        <el-descriptions-item label="字幕样式">
          <span v-if="currentSubtitleStyleLabel">{{ currentSubtitleStyleLabel }}</span>
          <span v-else>未选择</span>
        </el-descriptions-item>
        <el-descriptions-item label="分镜完成">
          {{ task?.completed_scenes ?? 0 }}/{{ task?.total_scenes ?? '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="合并后视频">
          <a
            v-if="task?.merged_video_url"
            :href="task?.merged_video_url"
            target="_blank"
            rel="noopener noreferrer"
          >查看</a>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="最终成片">
          <a
            v-if="task?.final_video_url"
            :href="task?.final_video_url"
            target="_blank"
            rel="noopener noreferrer"
          >查看</a>
          <span v-else>-</span>
        </el-descriptions-item>

          watch(
            () => task.value?.mode,
            (mode) => {
              if (!mode) return
              if (!scriptDialogVisible.value) {
                scriptForm.autoTrigger = mode === 'auto'
              }
            },
            { immediate: true }
          )

          watch(
            () => scriptDialogVisible.value,
            (visible) => {
              if (!visible) {
                scriptForm.text = ''
                if (detailScriptFileInput.value) {
                  detailScriptFileInput.value.value = ''
                }
              }
            }
          )
        <el-descriptions-item label="创建时间">{{ formatTime(task?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatTime(task?.updated_at) }}</el-descriptions-item>
        <el-descriptions-item label="错误信息">{{ task?.error_msg ?? '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

  <el-card v-loading="detailLoading" shadow="never" class="subtitles-card section-card">
    <template #header>
      <div class="card-header section-header">
        <span class="section-title">字幕信息</span>
        <div class="card-actions" v-if="subtitleDocument">
          <el-link
            v-if="subtitleSrtLink"
            type="primary"
            :href="subtitleSrtLink"
            target="_blank"
            rel="noopener noreferrer"
          >下载 SRT</el-link>
          <el-link
            v-if="subtitleAssLink"
            type="primary"
            :href="subtitleAssLink"
            target="_blank"
            rel="noopener noreferrer"
          >下载 ASS</el-link>
        </div>
      </div>
    </template>
    <div v-if="subtitleDocument" class="subtitle-meta">
      <el-descriptions :column="3" border label-class-name="desc-label">
        <el-descriptions-item label="语言">{{ subtitleDocument.language || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ subtitleDocument.model_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="样式">{{ subtitleStyleLabel || '-' }}</el-descriptions-item>
  <el-descriptions-item label="片段数量">{{ subtitleDocument.segment_count }}</el-descriptions-item>
  <el-descriptions-item label="词数统计">{{ subtitleWordCount }}</el-descriptions-item>
        <el-descriptions-item label="SRT 文件">
          <template v-if="subtitleSrtLink">
            <a :href="subtitleSrtLink" target="_blank" rel="noopener noreferrer">下载</a>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="ASS 文件">
          <template v-if="subtitleAssLink">
            <a :href="subtitleAssLink" target="_blank" rel="noopener noreferrer">下载</a>
          </template>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ subtitleDocument.created_at ? formatTime(subtitleDocument.created_at) : '-' }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ subtitleDocument.updated_at ? formatTime(subtitleDocument.updated_at) : '-' }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="subtitlePreviewText" class="subtitle-preview">
        <div class="subtitle-preview__label">文本概览</div>
        <div class="subtitle-preview__content">{{ subtitlePreviewText }}</div>
      </div>

      <el-table
        v-if="subtitleSegments.length"
        :data="subtitleSegments"
  :row-key="subtitleRowKey"
        border
        stripe
        size="small"
        class="subtitle-table"
        empty-text="暂无字幕片段"
      >
        <el-table-column label="#" width="70" align="center">
          <template #default="{ row }">{{ row.index }}</template>
        </el-table-column>
        <el-table-column label="字幕文本" min-width="260">
          <template #default="{ row }">{{ row.text }}</template>
        </el-table-column>
        <el-table-column label="开始时间" width="140" align="center">
          <template #default="{ row }">{{ formatSubtitleTimestamp(row.start) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" width="140" align="center">
          <template #default="{ row }">{{ formatSubtitleTimestamp(row.end) }}</template>
        </el-table-column>
        <el-table-column label="时长" width="110" align="center">
          <template #default="{ row }">{{ formatSubtitleDuration(row) }}</template>
        </el-table-column>
        <el-table-column label="词数" width="100" align="center">
          <template #default="{ row }">{{ row.words?.length ?? 0 }}</template>
        </el-table-column>
      </el-table>

      <div v-else class="subtitle-empty">暂无字幕片段</div>
    </div>
    <div v-else class="subtitle-empty">暂无字幕数据</div>
  </el-card>

  <el-card shadow="never" class="steps-card section-card">
      <template #header>
        <div class="card-header section-header">
          <span class="section-title">步骤进展</span>
          <div class="card-actions">
            <el-button
              v-if="storyboardStep"
              size="small"
              type="primary"
              plain
              :disabled="!canImportScript"
              @click="openScriptDialog"
            >导入分镜脚本</el-button>
            <el-button
              v-if="audioStartStep"
              size="small"
              type="primary"
              plain
              :loading="startingAudio"
              :disabled="!canStartAudioPipeline || startingAudio"
              @click="handleStartAudioPipeline"
            >执行音频相关步骤</el-button>
            <el-button
              v-if="nextAutoRunnableStep"
              size="small"
              type="primary"
              plain
              :loading="continuingPipeline"
              :disabled="!canContinuePipeline || continuingPipeline"
              @click="handleContinuePipeline"
            >继续执行后续步骤</el-button>
            <el-button
              size="small"
              type="warning"
              plain
              :loading="resettingAudio"
              :disabled="!task || hasRunningStep || resettingAudio"
              @click="handleResetAudioPipeline"
            >重置音频相关步骤</el-button>
          </div>
        </div>
      </template>
      <el-table :data="steps" border stripe>
        <el-table-column label="顺序" width="90" align="center">
          <template #default="{ row }">{{ row.seq }}</template>
        </el-table-column>
        <el-table-column label="步骤" min-width="160">
          <template #default="{ row }">{{ stepNameMap[row.step_name] ?? row.step_name }}</template>
        </el-table-column>
        <el-table-column label="状态" width="140" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="160" align="center">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="12" />
          </template>
        </el-table-column>
        <el-table-column label="重试次数" width="120" align="center">
          <template #default="{ row }">{{ row.retry_count }}/{{ row.max_retries }}</template>
        </el-table-column>
        <el-table-column label="输出链接" min-width="220">
          <template #default="{ row }">
            <div class="link-list" v-if="getStepOutputs(row).length">
              <div v-for="item in getStepOutputs(row)" :key="item.label">
                <a :href="item.url" target="_blank" rel="noopener noreferrer">{{ item.label }}</a>
              </div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="最近更新" min-width="180" align="center">
          <template #default="{ row }">{{ formatTime(row.finished_at || row.started_at) }}</template>
        </el-table-column>
        <el-table-column label="错误信息" min-width="220">
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right" align="center">
          <template #default="{ row }">
            <el-space wrap>
              <el-button
                v-if="canRunStep(row)"
                size="small"
                type="primary"
                @click="handleRunStep(row.step_name)"
              >执行步骤</el-button>
              <el-button
                v-if="canRetryStep(row)"
                size="small"
                type="warning"
                @click="handleRetryStep(row.step_name)"
              >重试执行</el-button>
              <el-button
                v-if="(row.step_name === 'generate_images' || row.step_name === 'generate_videos') && row.status === 1"
                size="small"
                type="danger"
                :loading="interrupting"
                @click="handleInterruptStep(row)"
              >中断</el-button>
              <el-button
                v-if="row.step_name === 'finalize_video'"
                size="small"
                type="info"
                plain
                :disabled="!canResetFinalizeStep"
                :loading="resettingFinalize"
                @click="handleResetFinalizeStep"
              >重置该步</el-button>
              <el-button
                v-if="row.step_name === 'finalize_video'"
                size="small"
                type="primary"
                plain
                :disabled="!canRerunFinalizeStep"
                :loading="rerunningFinalize"
                @click="handleRerunFinalizeStep"
              >重新执行</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

  <el-card shadow="never" class="scenes-card section-card">
      <template #header>
        <div class="card-header section-header">
          <span class="section-title">分镜列表</span>
        </div>
      </template>
      <el-table :data="scenes" border stripe>
        <el-table-column label="序号" width="80" align="center">
          <template #default="{ row }">{{ row.seq }}</template>
        </el-table-column>
        <el-table-column label="旁白内容" min-width="240">
          <template #default="{ row }">{{ row.narration_text || '-' }}</template>
        </el-table-column>
        <el-table-column label="文生图提示词" min-width="260">
          <template #default="{ row }">
            <span v-if="row.image_prompt" class="prompt-text">{{ row.image_prompt }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="图片" min-width="220" align="center">
          <template #default="{ row }">
            <div v-if="row.image_status === 2 && row.image_url" class="scene-media-thumb">
              <el-image
                :src="row.image_url"
                :preview-src-list="[row.image_url]"
                :preview-teleported="true"
                fit="contain"
                class="scene-media-image"
              />
            </div>
            <el-tag v-else :type="statusTagType(row.image_status)">{{ statusLabel(row.image_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="音频" min-width="220" align="center">
          <template #default="{ row }">
            <div v-if="row.audio_status === 2 && row.audio_url" class="scene-media-completed scene-media-audio">
              <span v-if="getAudioDuration(row)" class="media-duration">{{ getAudioDuration(row) }}</span>
              <audio :src="row.audio_url" controls preload="none" class="scene-audio-player">
                <source :src="row.audio_url" />
                您的浏览器不支持音频播放。
              </audio>
            </div>
            <el-tag v-else :type="statusTagType(row.audio_status)">{{ statusLabel(row.audio_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="图生视频提示词" min-width="260">
          <template #default="{ row }">
            <span v-if="row.video_prompt" class="prompt-text">{{ row.video_prompt }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="图生视频" min-width="240" align="center">
          <template #default="{ row }">
            <div
              v-if="row.video_status === 2 && getSceneVideoUrl(row, 'raw')"
              class="scene-media-completed scene-media-video"
            >
              <div class="scene-video-thumb">
                <video
                  :src="getSceneVideoUrl(row, 'raw') || undefined"
                  controls
                  preload="metadata"
                  crossorigin="anonymous"
                  class="scene-video-player"
                  @loadeddata="handleVideoLoaded"
                />
              </div>
              <div class="scene-media-actions">
                <span v-if="getSceneVideoDuration(row, 'raw')" class="media-duration">
                  {{ getSceneVideoDuration(row, 'raw') }}
                </span>
                <el-tag v-if="row.video_provider" size="small" effect="plain">{{ row.video_provider }}</el-tag>
              </div>
            </div>
            <el-tag v-else :type="statusTagType(row.video_status)">{{ statusLabel(row.video_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="音视频合成" min-width="240" align="center">
          <template #default="{ row }">
            <div
              v-if="row.merge_status === 2 && getSceneVideoUrl(row, 'merge')"
              class="scene-media-completed scene-media-video"
            >
              <div class="scene-video-thumb">
                <video
                  :src="getSceneVideoUrl(row, 'merge') || undefined"
                  controls
                  preload="metadata"
                  crossorigin="anonymous"
                  class="scene-video-player"
                  @loadeddata="handleVideoLoaded"
                />
              </div>
              <div class="scene-media-actions">
                <span v-if="getSceneVideoDuration(row, 'merge')" class="media-duration">
                  {{ getSceneVideoDuration(row, 'merge') }}
                </span>
                <el-tag v-if="row.merge_video_provider" size="small" effect="plain">
                  {{ row.merge_video_provider }}
                </el-tag>
              </div>
            </div>
            <el-tag v-else :type="statusTagType(row.merge_status)">{{ statusLabel(row.merge_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="产出链接" min-width="260">
          <template #default="{ row }">
            <div
              class="link-list"
              v-if="row.image_url || row.audio_url || row.raw_video_url || row.merge_video_url"
            >
              <div v-if="row.image_url"><a :href="row.image_url" target="_blank" rel="noopener noreferrer">图片链接</a></div>
              <div v-if="row.audio_url"><a :href="row.audio_url" target="_blank" rel="noopener noreferrer">音频链接</a></div>
              <div v-if="row.raw_video_url"><a :href="row.raw_video_url" target="_blank" rel="noopener noreferrer">原始视频</a></div>
              <div v-if="row.merge_video_url"><a :href="row.merge_video_url" target="_blank" rel="noopener noreferrer">合成视频</a></div>
            </div>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" width="160">
          <template #default="{ row }">
            <el-tooltip v-if="row.error_msg" :content="row.error_msg" placement="top">
              <span class="text-ellipsis">{{ row.error_msg }}</span>
            </el-tooltip>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" align="center">
          <template #default="{ row }">
            <el-space wrap>
              <el-button
                v-if="row.image_status === 3"
                size="small"
                type="warning"
                :disabled="hasRunningStep"
                @click="handleRetryScene(row.id, 'image')"
              >重试图生图</el-button>
              <el-button
                v-if="row.audio_status === 3"
                size="small"
                type="warning"
                :disabled="hasRunningStep"
                @click="handleRetryScene(row.id, 'audio')"
              >重试配音</el-button>
              <el-button
                v-if="row.video_status === 3"
                size="small"
                type="warning"
                :disabled="hasRunningStep"
                @click="handleRetryScene(row.id, 'video')"
              >重试图生视频</el-button>
              <el-button
                v-if="row.merge_status === 3"
                size="small"
                type="warning"
                :disabled="hasRunningStep"
                @click="handleRetryScene(row.id, 'merge')"
              >重试音视频合成</el-button>
            </el-space>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="scriptDialogVisible"
      title="导入分镜脚本"
      width="560px"
      destroy-on-close
      @close="closeScriptDialog"
    >
      <el-form ref="scriptFormRef" :model="scriptForm" :rules="scriptRules" label-width="104px">
        <el-form-item label="脚本内容" prop="text">
          <el-input
            v-model="scriptForm.text"
            type="textarea"
            :autosize="{ minRows: 8, maxRows: 12 }"
            placeholder="粘贴分镜脚本 JSON"
          />
          <div class="script-helper">
            <el-button text type="primary" @click="triggerScriptFileSelect">从文件导入</el-button>
            <span class="script-hint">导入将覆盖现有分镜，请确认任务尚未生成分镜。</span>
          </div>
          <input
            ref="detailScriptFileInput"
            class="hidden-file-input"
            type="file"
            accept=".json,application/json"
            @change="handleScriptFileSelect"
          />
        </el-form-item>
        <el-form-item label="导入后自动执行">
          <el-switch
            v-model="scriptForm.autoTrigger"
            active-text="自动继续"
            inactive-text="手动继续"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeScriptDialog">取消</el-button>
        <el-button type="primary" :loading="scriptSubmitting" @click="submitScriptImport">
          确认导入
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="editVisible"
      title="编辑任务"
      width="540px"
      destroy-on-close
      @close="closeEditDialog"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editRules"
        label-width="96px"
      >
        <el-form-item label="任务标题" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入任务标题" maxlength="64" show-word-limit />
        </el-form-item>
        <el-form-item label="文案内容" prop="description">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :autosize="{ minRows: 4, maxRows: 6 }"
            placeholder="请输入视频文案"
          />
        </el-form-item>
        <el-form-item label="参考视频">
          <el-input v-model="editForm.reference_video" placeholder="可填写参考视频链接" />
        </el-form-item>
        <el-form-item label="分镜数量">
          <el-input-number
            v-model="editForm.scene_count"
            :min="0"
            :max="1000"
            :step="1"
            placeholder="0 表示自动"
          />
        </el-form-item>
        <el-form-item label="旁白语言" prop="language">
          <el-select v-model="editForm.language" placeholder="选择语言">
            <el-option label="中文" value="中文" />
            <el-option label="英语" value="英语" />
          </el-select>
        </el-form-item>
        <el-form-item label="风格组合">
          <el-select
            v-model="editForm.style_preset_id"
            placeholder="可选择预设风格"
            clearable
            filterable
            :loading="styleLoading"
          >
            <el-option
              v-for="preset in activePresets"
              :key="preset.id"
              :label="preset.name"
              :value="preset.id"
            />
          </el-select>
          <div v-if="editSelectedPreset" class="preset-preview">
            <div class="preset-preview__name">{{ editSelectedPreset.name }}</div>
            <p v-if="editSelectedPreset.prompt_example">
              <strong>提示词示例：</strong>{{ editSelectedPreset.prompt_example }}
            </p>
            <p v-if="editSelectedPreset.trigger_words">
              <strong>触发词：</strong>{{ editSelectedPreset.trigger_words }}
            </p>
            <p v-if="editSelectedPreset.checkpoint_id || editSelectedPreset.lora_id">
              <strong>Liblib：</strong>
              <span v-if="editSelectedPreset.checkpoint_id">模型 {{ editSelectedPreset.checkpoint_id }}</span>
              <span v-if="editSelectedPreset.checkpoint_id && editSelectedPreset.lora_id">，</span>
              <span v-if="editSelectedPreset.lora_id">LoRA {{ editSelectedPreset.lora_id }}</span>
            </p>
          </div>
        </el-form-item>
        <el-form-item label="字幕样式">
          <el-select
            v-model="editForm.subtitle_style_id"
            placeholder="可选择字幕样式"
            clearable
            filterable
            :loading="subtitleStyleLoading"
          >
            <el-option
              v-for="style in activeSubtitleStyles"
              :key="style.id"
              :label="style.name"
              :value="style.id"
            />
            <el-option
              v-if="editSelectedSubtitleStyle && !editSelectedSubtitleStyle.is_active"
              :key="`inactive-${editSelectedSubtitleStyle.id}`"
              :label="`${editSelectedSubtitleStyle.name}（已停用）`"
              :value="editSelectedSubtitleStyle.id"
              disabled
            />
          </el-select>
          <div v-if="editSelectedSubtitleStyle" class="subtitle-style-preview">
            <div class="subtitle-style-preview__name">{{ editSelectedSubtitleStyle.name }}</div>
            <p v-if="editSelectedSubtitleStyle.description">
              <strong>说明：</strong>{{ editSelectedSubtitleStyle.description }}
            </p>
            <p v-if="editSelectedSubtitleStyle.sample_text">
              <strong>示例：</strong>{{ editSelectedSubtitleStyle.sample_text }}
            </p>
          </div>
        </el-form-item>
        <el-form-item label="配音音色" prop="audio_voice_id">
          <el-select
            v-model="editForm.audio_voice_id"
            placeholder="请选择音色"
            filterable
            :loading="voiceLoading"
          >
            <el-option
              v-for="voice in voiceOptions"
              :key="voice.id"
              :label="voice.option_name ?? voice.option_key"
              :value="voice.option_key"
            >
              <span>{{ voice.option_name ?? voice.option_key }}</span>
              <span v-if="voice.is_default" class="option-tag">默认</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="裁剪静音">
          <el-switch
            v-model="editForm.audio_trim_silence"
            active-text="自动裁剪"
            inactive-text="保留"
          />
        </el-form-item>
        <el-form-item label="背景音乐">
          <el-select
            v-model="editForm.bgm_asset_id"
            placeholder="不选择则不配乐"
            clearable
            filterable
            :loading="bgmLoading"
          >
            <el-option
              v-for="asset in bgmItems"
              :key="asset.id"
              :label="asset.is_default ? `${asset.asset_name}（默认）` : asset.asset_name"
              :value="asset.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="图生视频通道">
          <el-select v-model="editForm.provider" placeholder="可选" clearable>
            <el-option label="Fal" value="fal" />
            <el-option label="RunningHub" value="runninghub" />
            <el-option label="NCA" value="nca" />
          </el-select>
        </el-form-item>
        <el-form-item label="媒体处理工具">
          <el-select v-model="editForm.media_tool" placeholder="可选" clearable>
            <el-option label="NCA" value="nca" />
            <el-option label="FFmpeg" value="ffmpeg" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行模式" prop="mode">
          <el-radio-group v-model="editForm.mode">
            <el-radio-button label="auto">自动</el-radio-button>
            <el-radio-button label="manual">手动</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" :loading="editing" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useIntervalFn } from '@vueuse/core'

import { useTaskStore } from '@/stores/task'
import { useStylePresetStore } from '@/stores/stylePreset'
import { useSubtitleStyleStore } from '@/stores/subtitleStyle'
import { useAssetStore } from '@/stores/asset'
import { useVoiceOptionStore } from '@/stores/voice'
import { statusLabel, statusTagType, stepNameMap } from '@/utils/task'
import type { SceneRecord, VoiceOption, StoryboardScriptPayload } from '@/types/task'
import type { SubtitleDocument as SubtitleDocumentInfo, SubtitleSegment } from '@/types/subtitle'
import type { MediaAsset } from '@/types/asset'
import { parseStoryboardScriptText } from '@/utils/storyboard'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const {
  selectedTask,
  selectedSteps,
  selectedScenes,
  selectedSubtitleDocument,
  detailLoading,
  hasRunningStep
} = storeToRefs(taskStore)
const stylePresetStore = useStylePresetStore()
const { activePresets, loading: styleLoading } = storeToRefs(stylePresetStore)
const subtitleStyleStore = useSubtitleStyleStore()
const {
  styles: subtitleStyles,
  activeStyles: activeSubtitleStyles,
  loading: subtitleStyleLoading
} = storeToRefs(subtitleStyleStore)
const assetStore = useAssetStore()
const { bgmItems, bgmLoading } = storeToRefs(assetStore)
const voiceStore = useVoiceOptionStore()
const { options: voiceOptions, loading: voiceLoading, defaultOption: defaultVoice } = storeToRefs(voiceStore)

const detectEnglishVoice = (voice: VoiceOption) => {
  const meta = (voice.meta_data as Record<string, unknown> | null) ?? null
  const metaLanguage = meta && typeof meta['language'] === 'string' ? (meta['language'] as string) : ''
  const label = voice.option_name ?? ''
  const identifier = voice.option_key ?? ''
  const combined = `${metaLanguage}|${label}|${identifier}`.toLowerCase()
  return combined.includes('english') || combined.includes('en') || combined.includes('英')
}

const englishVoiceKey = computed(() => {
  if (!voiceOptions.value.length) {
    return defaultVoice.value?.option_key ?? ''
  }
  const english = voiceOptions.value.find((item) => detectEnglishVoice(item))
  const fallback = defaultVoice.value ?? voiceOptions.value[0]
  return (english ?? fallback).option_key
})

const taskId = computed(() => Number(route.params.id))

const task = computed(() => selectedTask.value)
const steps = computed(() => selectedSteps.value)
const scenes = computed(() => selectedScenes.value)

const subtitleDocument = computed<SubtitleDocumentInfo | null>(() => {
  return selectedSubtitleDocument.value
})

const subtitleSegments = computed<SubtitleSegment[]>(() => {
  const doc = subtitleDocument.value
  if (!doc?.segments?.length) {
    return []
  }
  return [...doc.segments].sort((a, b) => {
    const left = typeof a.index === 'number' ? a.index : 0
    const right = typeof b.index === 'number' ? b.index : 0
    return left - right
  })
})

const subtitleWordCount = computed(() => {
  return subtitleSegments.value.reduce((total, segment) => {
    if (Array.isArray(segment.words)) {
      return total + segment.words.length
    }
    const text = (segment.text ?? '').trim()
    if (!text) {
      return total
    }
    const tokens = text.split(/\s+/u).filter((item) => item.length > 0)
    if (tokens.length > 0) {
      return total + tokens.length
    }
    return total + text.length
  }, 0)
})

const subtitlePreviewText = computed(() => {
  const doc = subtitleDocument.value
  if (!doc) {
    return ''
  }
  const preview = (doc.text_preview ?? '').trim()
  if (preview) {
    return preview
  }
  const snippets = subtitleSegments.value
    .slice(0, 5)
    .map((segment) => (segment.text ?? '').trim())
    .filter((text) => text.length > 0)
  return snippets.join(' / ')
})

const buildSubtitleLink = (publicUrl?: string | null, apiPath?: string | null) => {
  const normalizedPublicUrl = typeof publicUrl === 'string' ? publicUrl.trim() : ''
  if (normalizedPublicUrl) {
    return normalizedPublicUrl
  }
  const normalizedApiPath = typeof apiPath === 'string' ? apiPath.trim() : ''
  return normalizedApiPath
}

const subtitleSrtLink = computed(() => {
  const doc = subtitleDocument.value
  if (!doc) return ''
  return buildSubtitleLink(doc.srt_public_url, doc.srt_api_path)
})

const subtitleAssLink = computed(() => {
  const doc = subtitleDocument.value
  if (!doc) return ''
  return buildSubtitleLink(doc.ass_public_url, doc.ass_api_path)
})

const subtitleStyleLabel = computed(() => {
  const doc = subtitleDocument.value
  if (!doc?.options) {
    return ''
  }
  const options = doc.options as Record<string, unknown>
  const snapshotRaw = options['style_snapshot']
  if (snapshotRaw && typeof snapshotRaw === 'object') {
    const snapshot = snapshotRaw as Record<string, unknown>
    const name = typeof snapshot['name'] === 'string' ? (snapshot['name'] as string) : ''
    const isActiveRaw = snapshot['is_active']
    let isActive: boolean | null = null
    if (typeof isActiveRaw === 'boolean') {
      isActive = isActiveRaw
    } else if (typeof isActiveRaw === 'string') {
      isActive = isActiveRaw.toLowerCase() !== 'false'
    }
    if (name) {
      if (isActive === false) {
        return `${name}（已停用）`
      }
      return name
    }
  }

  const styleNameRaw = options['style_name']
  if (typeof styleNameRaw === 'string' && styleNameRaw.trim().length > 0) {
    return styleNameRaw.trim()
  }

  const payloadRaw = options['style_payload']
  if (payloadRaw && typeof payloadRaw === 'object') {
    const payload = payloadRaw as Record<string, unknown>
    const name = typeof payload['Name'] === 'string' ? (payload['Name'] as string) : ''
    if (name) {
      return name
    }
  }

  return ''
})

const formatSubtitleTimestamp = (value: number | null | undefined) => {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--'
  }
  const totalMs = Math.max(0, Math.round(value * 1000))
  const hours = Math.floor(totalMs / 3_600_000)
  const minutes = Math.floor((totalMs % 3_600_000) / 60_000)
  const seconds = Math.floor((totalMs % 60_000) / 1000)
  const milliseconds = totalMs % 1000
  const hh = hours.toString().padStart(2, '0')
  const mm = minutes.toString().padStart(2, '0')
  const ss = seconds.toString().padStart(2, '0')
  const ms = milliseconds.toString().padStart(3, '0')
  return `${hh}:${mm}:${ss}.${ms}`
}

const formatSubtitleDuration = (segment: SubtitleSegment) => {
  const durationSource = typeof segment.duration === 'number' ? segment.duration : segment.end - segment.start
  if (typeof durationSource !== 'number' || Number.isNaN(durationSource) || !Number.isFinite(durationSource)) {
    return '--'
  }
  if (durationSource <= 0) {
    return '0.00s'
  }
  return `${durationSource.toFixed(2)}s`
}

const subtitleRowKey = (segment: SubtitleSegment) => segment.index

const storyboardStep = computed(() => {
  return steps.value.find((step) => step.step_name === 'storyboard') ?? null
})

const canImportScript = computed(() => {
  const step = storyboardStep.value
  if (!task.value || !step) return false
  if (hasRunningStep.value) return false
  if (scenes.value.length > 0) return false
  return step.status === 0 || step.status === 3
})

const taskProviders = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  const configProviders = (task.value?.task_config?.providers ?? null) as
    | Record<string, unknown>
    | null
  if (configProviders) {
    Object.entries(configProviders).forEach(([key, value]) => {
      if (typeof value === 'string' && value.trim().length > 0) {
        map[key] = value.trim()
      }
    })
  }
  const persisted = (task.value?.providers ?? null) as Record<string, unknown> | null
  if (persisted) {
    Object.entries(persisted).forEach(([key, value]) => {
      if (typeof value === 'string' && value.trim().length > 0) {
        map[key] = value.trim()
      }
    })
  }
  return map
})

const taskMediaTool = computed(() => {
  const providers = taskProviders.value
  return providers.scene_merge || providers.media_compose || providers.finalize || ''
})

const mediaToolLabel = computed(() => {
  const mapper: Record<string, string> = { nca: 'NCA', ffmpeg: 'FFmpeg' }
  const value = taskMediaTool.value?.toLowerCase()
  if (!value) return ''
  return mapper[value] ?? value
})

const audioTrimEnabled = computed(() => {
  const raw = task.value?.task_config?.audio_trim_silence
  if (typeof raw === 'boolean') return raw
  return true
})

const currentBgmId = computed(() => {
  const value = task.value?.task_config?.bgm_asset_id
  return toNumberOrNull(value)
})

const currentBgmAsset = computed<MediaAsset | null>(() => {
  const id = currentBgmId.value
  if (!id) return null
  if (!bgmItems.value.length && !bgmLoading.value) {
    assetStore.loadBgmAssets().catch(() => {})
  }
  return bgmItems.value.find((item) => item.id === id) ?? null
})

const currentSubtitleStyleLabel = computed(() => {
  const snapshotRaw = task.value?.subtitle_style_snapshot
  if (snapshotRaw && typeof snapshotRaw === 'object') {
    const snapshot = snapshotRaw as Record<string, unknown>
    const name = typeof snapshot.name === 'string' ? snapshot.name : ''
    let isActiveFlag: boolean | null = null
    if (typeof snapshot.is_active === 'boolean') {
      isActiveFlag = snapshot.is_active
    } else if (typeof snapshot.is_active === 'string') {
      isActiveFlag = snapshot.is_active.toLowerCase() !== 'false'
    }
    if (name) {
      if (isActiveFlag === false) {
        return `${name}（已停用）`
      }
      return name
    }
  }

  const styleId = task.value?.subtitle_style_id
  if (typeof styleId === 'number') {
    const style = subtitleStyleStore.findById(styleId)
    if (style) {
      return style.is_active ? style.name : `${style.name}（已停用）`
    }
    return `ID ${styleId}（已删除或不可用）`
  }

  const configId = toNumberOrNull(task.value?.task_config?.subtitle_style_id)
  if (configId !== null) {
    return `ID ${configId}`
  }

  return ''
})

const lockedSteps = ref<string[]>([])
const resettingAudio = ref(false)
const startingAudio = ref(false)
const continuingPipeline = ref(false)
const resettingFinalize = ref(false)
const rerunningFinalize = ref(false)

const audioStartStep = computed(() => {
  return steps.value.find((step) => step.step_name === 'generate_audio') ?? null
})

const finalizeStep = computed(() => {
  return steps.value.find((step) => step.step_name === 'finalize_video') ?? null
})

const canResetFinalizeStep = computed(() => {
  const step = finalizeStep.value
  if (!task.value || !step) return false
  if (resettingFinalize.value || rerunningFinalize.value) return false
  if (hasRunningStep.value && step.status !== 1) return false
  return step.status !== 1
})

const canRerunFinalizeStep = computed(() => {
  const step = finalizeStep.value
  if (!task.value || !step) return false
  if (rerunningFinalize.value || resettingFinalize.value) return false
  if (hasRunningStep.value && step.status !== 1) return false
  return step.status !== 1
})

const canStartAudioPipeline = computed(() => {
  const startStep = audioStartStep.value
  if (!task.value || !startStep) return false
  if (hasRunningStep.value) return false
  if (lockedSteps.value.includes(startStep.step_name)) return false
  return startStep.status === 0
})

const editVisible = ref(false)
const editing = ref(false)
const editFormRef = ref<FormInstance>()
const editForm = reactive({
  title: '',
  description: '',
  reference_video: '',
  mode: 'auto' as 'auto' | 'manual',
  scene_count: 0,
  language: '英语',
  provider: '',
  media_tool: '',
  style_preset_id: undefined as number | undefined,
  subtitle_style_id: undefined as number | undefined,
  bgm_asset_id: undefined as number | undefined,
  audio_voice_id: '',
  audio_trim_silence: true
})

const detailScriptFileInput = ref<HTMLInputElement | null>(null)
const scriptDialogVisible = ref(false)
const scriptSubmitting = ref(false)
const scriptFormRef = ref<FormInstance>()
const scriptForm = reactive({
  text: '',
  autoTrigger: true
})

const validateScriptText = (
  _rule: unknown,
  value: string,
  callback: (error?: Error) => void
) => {
  if (!scriptDialogVisible.value) {
    callback()
    return
  }
  if (!value || !value.trim()) {
    callback(new Error('请粘贴分镜脚本 JSON'))
    return
  }
  try {
    parseStoryboardScriptText(value)
    callback()
  } catch (error: any) {
    callback(new Error(error?.message ?? '脚本格式不正确'))
  }
}

const scriptRules: FormRules = {
  text: [{ validator: validateScriptText, trigger: 'blur' }]
}

const editRules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  description: [{ required: true, message: '请输入文案内容', trigger: 'blur' }],
  language: [{ required: true, message: '请选择旁白语言', trigger: 'change' }],
  audio_voice_id: [{ required: true, message: '请选择配音音色', trigger: 'change' }],
  mode: [{ required: true, message: '请选择执行模式', trigger: 'change' }]
}

const initEditForm = () => {
  const current = task.value
  if (!current) return
  editForm.title = current.params?.title ?? ''
  editForm.description = current.params?.description ?? ''
  editForm.reference_video = current.params?.reference_video ?? ''
  editForm.mode = current.mode ?? 'auto'
  let sceneCountValue = 0
  if (typeof current.task_config?.scene_count === 'number') {
    sceneCountValue = current.task_config.scene_count
  } else if (typeof current.total_scenes === 'number') {
    sceneCountValue = current.total_scenes
  }
  if (!Number.isFinite(sceneCountValue)) {
    sceneCountValue = 0
  }
  editForm.scene_count = Math.max(0, Number(sceneCountValue))
  editForm.language = (current.task_config?.language as string) || '英语'
  const videoProvider =
    (current.task_config?.provider as string | null) || taskProviders.value.video || ''
  editForm.provider = videoProvider || ''
  editForm.media_tool = taskMediaTool.value || ''
  const presetId = current.task_config?.style_preset_id
  editForm.style_preset_id = typeof presetId === 'number' ? presetId : undefined
  const snapshotId = toNumberOrNull(
    current.subtitle_style_snapshot && typeof current.subtitle_style_snapshot === 'object'
      ? (current.subtitle_style_snapshot as Record<string, unknown>).id
      : null
  )
  const subtitleId =
    typeof current.subtitle_style_id === 'number'
      ? current.subtitle_style_id
      : toNumberOrNull(current.task_config?.subtitle_style_id) ?? snapshotId
  editForm.subtitle_style_id = subtitleId !== null ? subtitleId : undefined
  const bgmId = toNumberOrNull(current.task_config?.bgm_asset_id)
  editForm.bgm_asset_id = bgmId !== null ? bgmId : undefined
  const voiceKey = current.task_config?.audio_voice_id
  editForm.audio_voice_id = typeof voiceKey === 'string' ? voiceKey : ''
  const trimFlag = current.task_config?.audio_trim_silence
  editForm.audio_trim_silence = typeof trimFlag === 'boolean' ? trimFlag : true
  if (!editForm.audio_voice_id) {
    editForm.audio_voice_id = englishVoiceKey.value
  }
}

const openEditDialog = () => {
  if (!task.value) return
  stylePresetStore.loadPresets()
  subtitleStyleStore.loadStyles({ includeInactive: true }).catch(() => {})
  assetStore.loadBgmAssets()
  voiceStore.ensureLoaded().catch(() => {})
  initEditForm()
  editVisible.value = true
  nextTick(() => editFormRef.value?.clearValidate())
}

const closeEditDialog = () => {
  editVisible.value = false
  nextTick(() => editFormRef.value?.clearValidate())
}

const openScriptDialog = () => {
  if (!task.value || scenes.value.length > 0) return
  scriptForm.text = ''
  scriptForm.autoTrigger = task.value.mode === 'auto'
  scriptDialogVisible.value = true
  nextTick(() => scriptFormRef.value?.clearValidate())
}

const closeScriptDialog = () => {
  scriptDialogVisible.value = false
  nextTick(() => scriptFormRef.value?.clearValidate())
}

const triggerScriptFileSelect = () => {
  detailScriptFileInput.value?.click()
}

const handleScriptFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement | null
  const file = target?.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string') {
      scriptForm.text = reader.result
      nextTick(() => scriptFormRef.value?.validateField('text'))
    }
  }
  reader.onerror = () => {
    ElMessage.error('读取脚本文件失败')
  }
  reader.readAsText(file, 'utf-8')
  if (target) {
    target.value = ''
  }
}

const submitScriptImport = () => {
  if (!scriptFormRef.value || !task.value) return
  scriptFormRef.value.validate(async (valid) => {
    if (!valid) return
    scriptSubmitting.value = true
    try {
      const payload: StoryboardScriptPayload = parseStoryboardScriptText(scriptForm.text)
      await taskStore.importStoryboardScript(task.value!.id, payload, {
        autoTrigger: scriptForm.autoTrigger
      })
      ElMessage.success(
        scriptForm.autoTrigger ? '脚本导入成功，后续步骤已排队' : '脚本导入成功'
      )
      closeScriptDialog()
      loadDetail({ silent: true })
    } catch (error: any) {
      const message = error?.data?.detail ?? error?.message ?? '脚本导入失败'
      ElMessage.error(message)
    } finally {
      scriptSubmitting.value = false
    }
  })
}

const submitEdit = () => {
  if (!task.value || !editFormRef.value) return
  const currentTask = task.value
  editFormRef.value.validate(async (valid) => {
    if (!valid) return
    editing.value = true
    try {
      const providerValue = editForm.provider ? editForm.provider.trim() : ''
      const mediaToolValue = editForm.media_tool ? editForm.media_tool.trim() : ''
      const referenceVideo = editForm.reference_video ? editForm.reference_video.trim() : ''
      const sceneCount = typeof editForm.scene_count === 'number' ? editForm.scene_count : 0
      await taskStore.editTask(currentTask.id, {
        title: editForm.title,
        description: editForm.description,
        reference_video: referenceVideo,
        mode: editForm.mode,
        scene_count: sceneCount,
        language: editForm.language,
        audio_voice_id: editForm.audio_voice_id,
        audio_trim_silence: editForm.audio_trim_silence,
        provider: providerValue || null,
        media_tool: mediaToolValue || null,
        style_preset_id: editForm.style_preset_id ?? null,
        subtitle_style_id: editForm.subtitle_style_id ?? null,
        bgm_asset_id: editForm.bgm_asset_id ?? null
      })
      ElMessage.success('任务配置已更新')
      closeEditDialog()
      loadDetail({ silent: true })
    } catch (error: any) {
      ElMessage.error(error?.data?.detail ?? '更新任务配置失败')
    } finally {
      editing.value = false
    }
  })
}

const editSelectedPreset = computed(() => {
  if (!editForm.style_preset_id) return null
  return activePresets.value.find((item) => item.id === editForm.style_preset_id) ?? null
})

const editSelectedSubtitleStyle = computed(() => {
  if (!editForm.subtitle_style_id) return null
  return subtitleStyleStore.findById(editForm.subtitle_style_id) ?? null
})

watch(
  () => activePresets.value,
  () => {
    if (!editForm.style_preset_id) return
    const exists = activePresets.value.some((item) => item.id === editForm.style_preset_id)
    if (!exists) {
      editForm.style_preset_id = undefined
    }
  },
  { deep: true }
)

watch(
  () => subtitleStyles.value,
  () => {
    if (!editForm.subtitle_style_id) return
    const exists = subtitleStyleStore.findById(editForm.subtitle_style_id)
    if (!exists) {
      editForm.subtitle_style_id = undefined
    }
  },
  { deep: true }
)

watch(
  () => bgmItems.value,
  () => {
    if (!editForm.bgm_asset_id) return
    const exists = bgmItems.value.some((item) => item.id === editForm.bgm_asset_id)
    if (!exists) {
      editForm.bgm_asset_id = undefined
    }
  }
)

watch(
  () => voiceOptions.value,
  () => {
    if (!voiceOptions.value.length) {
      if (editVisible.value) {
        editForm.audio_voice_id = ''
      }
      return
    }

    const exists = voiceOptions.value.some(
      (item: VoiceOption) => item.option_key === editForm.audio_voice_id
    )

    if (!exists || !editForm.audio_voice_id) {
      const persistedKey = task.value?.task_config?.audio_voice_id
      const persisted =
        typeof persistedKey === 'string' ? voiceStore.findByKey(persistedKey) : null
      const fallbackKey = persisted?.option_key ?? englishVoiceKey.value
      editForm.audio_voice_id = fallbackKey
    }
  }
)

watch(
  () => task.value,
  (value) => {
    if (value && editVisible.value) {
      initEditForm()
    }
  }
)


type StepRow = (typeof steps.value)[number]

interface StepOutputLink {
  label: string
  url: string
}

type SceneVideoSource = 'raw' | 'merge'

const getStepOutputs = (step: StepRow): StepOutputLink[] => {
  const outputs: StepOutputLink[] = []
  const result = step.result as Record<string, unknown> | null
  if (!result) {
    return outputs
  }

  const data = result as Record<string, unknown>

  const append = (label: string, value: unknown) => {
    if (typeof value === 'string' && value.trim().length > 0) {
      outputs.push({ label, url: value })
    }
  }

  append('资源链接', data.resource_url)
  append('图片链接', data.image_url)
  append('音频链接', data.audio_url)

  if (step.step_name === 'merge_scene_media') {
    append('合成视频', data.merge_video_url ?? data.video_url)
    return outputs
  }

  if (step.step_name === 'merge_video') {
    append('合并视频', data.merge_video_url ?? data.merged_video_url ?? data.video_url)
    return outputs
  }

  if (step.step_name === 'finalize_video') {
    append('最终成片', data.final_video_url ?? data.video_url)
    return outputs
  }

  append('原始视频', data.raw_video_url ?? data.video_url)
  append('合成视频', data.merge_video_url ?? data.merged_video_url)
  append('最终成片', data.final_video_url)

  return outputs
}

const loadDetail = (opts: { silent?: boolean } = {}) => {
  const id = taskId.value
  if (!Number.isFinite(id)) return
  taskStore.loadTaskDetail(id, opts)
}

onMounted(() => {
  loadDetail()
  stylePresetStore.loadPresets()
  subtitleStyleStore.loadStyles({ includeInactive: true }).catch(() => {})
  assetStore.loadBgmAssets()
  voiceStore.ensureLoaded().catch(() => {})
})

watch(
  () => taskId.value,
  () => {
    taskStore.clearSelection()
    editVisible.value = false
    subtitleStyleStore.loadStyles({ includeInactive: true }).catch(() => {})
    loadDetail()
  }
)

const shouldPoll = computed(() => {
  if (!task.value) return false
  if (task.value.status === 1) return true
  return steps.value.some((step) => step.status === 1)
})

const { pause, resume: resumePolling } = useIntervalFn(() => loadDetail({ silent: true }), 4000, {
  immediate: false
})

watch(
  () => shouldPoll.value,
  (flag) => {
    if (flag) {
    resumePolling()
    } else {
      pause()
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  pause()
})

const nextPendingStep = computed(() => steps.value.find((step) => ![2, 4, 5].includes(step.status)))

const nextAutoRunnableStep = computed(() => {
  if (!task.value) return null
  if (task.value.mode === 'manual') return null
  if (hasRunningStep.value) return null
  const candidate = nextPendingStep.value
  if (!candidate) return null
  if (lockedSteps.value.includes(candidate.step_name)) return null
  if (![0, 3, 6].includes(candidate.status)) return null
  return candidate
})

const canContinuePipeline = computed(() => !!nextAutoRunnableStep.value)

const canRunStep = (step: StepRow) => {
  if (!task.value) return false
  if (task.value.mode !== 'manual') return false
  if (lockedSteps.value.includes(step.step_name)) return false
  // If the step is interrupted (6), allow manual execution directly
  if (step.status === 6) return true
  // Otherwise allow execution only for the next pending step when it's pending(0) or failed(3)
  return nextPendingStep.value?.id === step.id && [0, 3].includes(step.status)
}

// Allow retry for failed(3) and interrupted(6) steps
const canRetryStep = (step: StepRow) => [3, 6].includes(step.status)

const lockStep = (stepName: string) => {
  if (!lockedSteps.value.includes(stepName)) {
    lockedSteps.value = [...lockedSteps.value, stepName]
  }
}

const unlockStep = (stepName: string) => {
  lockedSteps.value = lockedSteps.value.filter((name) => name !== stepName)
}

const handleRunStep = async (stepName: string) => {
  if (!task.value) return
  lockStep(stepName)
  try {
    await taskStore.triggerStep(task.value.id, stepName)
    ElMessage.success('步骤已进入队列')
    if (stepName === 'finalize_video') {
      assetStore.loadBgmAssets({ force: true }).catch(() => {})
    }
    loadDetail({ silent: true })
  } catch (error: any) {
    unlockStep(stepName)
    ElMessage.error(error?.data?.detail ?? '执行步骤失败')
  }
}

const handleRetryStep = async (stepName: string) => {
  if (!task.value) return
  try {
    await taskStore.retryStep(task.value.id, stepName)
    await taskStore.triggerStep(task.value.id, stepName)
    ElMessage.success('已重新排队执行该步骤')
    if (stepName === 'finalize_video') {
      assetStore.loadBgmAssets({ force: true }).catch(() => {})
    }
    loadDetail({ silent: true })
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '重试失败')
  }
}

const handleResetFinalizeStep = async () => {
  if (!task.value || !finalizeStep.value) return
  if (!canResetFinalizeStep.value) {
    ElMessage.warning('当前无法重置该步骤')
    return
  }

  try {
    await ElMessageBox.confirm('确认将最终成片步骤重置为待处理吗？此操作不会自动重新执行。', '确认重置', {
      type: 'warning',
      confirmButtonText: '重置',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  resettingFinalize.value = true
  lockStep('finalize_video')
  try {
    await taskStore.resetStep(task.value.id, 'finalize_video')
    ElMessage.success('最终成片步骤已重置')
    loadDetail({ silent: true })
  } catch (error: any) {
    unlockStep('finalize_video')
    ElMessage.error(error?.data?.detail ?? '重置失败')
  } finally {
    resettingFinalize.value = false
    unlockStep('finalize_video')
  }
}

const handleRerunFinalizeStep = async () => {
  if (!task.value || !finalizeStep.value) return
  if (!canRerunFinalizeStep.value) {
    ElMessage.warning('当前无法重新执行该步骤')
    return
  }

  rerunningFinalize.value = true
  lockStep('finalize_video')
  try {
    await taskStore.triggerStep(task.value.id, 'finalize_video')
    ElMessage.success('最终成片步骤已重新执行')
    loadDetail({ silent: true })
  } catch (error: any) {
    unlockStep('finalize_video')
    ElMessage.error(error?.data?.detail ?? '执行失败')
  } finally {
    rerunningFinalize.value = false
  }
}

const handleRetryScene = async (sceneId: number, stepType: 'image' | 'audio' | 'video' | 'merge') => {
  if (!task.value) return
  if (hasRunningStep.value) {
    ElMessage.warning('当前有步骤执行中，请稍后重试')
    return
  }
  try {
    await taskStore.retryScene(task.value.id, sceneId, stepType)
    ElMessage.success('已重新排队执行该分镜处理')
    if (stepType === 'merge') {
      assetStore.loadBgmAssets({ force: true }).catch(() => {})
    }
    loadDetail({ silent: true })
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '重新执行失败')
  }
}

const handleResetAudioPipeline = async () => {
  if (!task.value) return
  if (hasRunningStep.value) {
    ElMessage.warning('当前有步骤执行中，请稍后重置')
    return
  }

  try {
    await ElMessageBox.confirm(
      '将音频生成及其后续步骤重置为待处理状态？此操作会清空已生成的音频、合成视频和成片结果。',
      '确认重置',
      {
        type: 'warning',
        confirmButtonText: '重置',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  resettingAudio.value = true
  try {
    await taskStore.resetAudioPipeline(task.value.id)
    ElMessage.success('音频相关步骤已重置')
    loadDetail({ silent: false })
  } catch (error: any) {
    ElMessage.error(error?.data?.detail ?? '重置失败')
  } finally {
    resettingAudio.value = false
  }
}

const handleStartAudioPipeline = async () => {
  if (!task.value || !audioStartStep.value) return
  if (!canStartAudioPipeline.value) return
  const stepName = audioStartStep.value.step_name
  startingAudio.value = true
  lockStep(stepName)
  try {
    await taskStore.triggerStep(task.value.id, stepName)
    ElMessage.success('音频相关步骤已进入队列')
    loadDetail({ silent: true })
  } catch (error: any) {
    unlockStep(stepName)
    ElMessage.error(error?.data?.detail ?? '执行音频步骤失败')
  } finally {
    startingAudio.value = false
  }
}

const handleContinuePipeline = async () => {
  const step = nextAutoRunnableStep.value
  if (!task.value || !step) return
  const stepName = step.step_name
  continuingPipeline.value = true
  lockStep(stepName)
  try {
    await taskStore.triggerStep(task.value.id, stepName)
    ElMessage.success('后续步骤已进入队列')
    loadDetail({ silent: true })
  } catch (error: any) {
    unlockStep(stepName)
    ElMessage.error(error?.data?.detail ?? '执行步骤失败')
  } finally {
    continuingPipeline.value = false
  }
}

function toNumberOrNull(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return null
}

const toStringOrNull = (value: unknown): string | null => {
  if (typeof value === 'string' && value.trim().length > 0) {
    return value
  }
  return null
}

const extractFirstValue = (payload: unknown, keys: string[]): unknown => {
  if (!payload) return null
  if (Array.isArray(payload)) {
    for (const item of payload) {
      const result = extractFirstValue(item, keys)
      if (result !== null && result !== undefined) return result
    }
    return null
  }
  if (typeof payload === 'object') {
    const record = payload as Record<string, unknown>
    for (const key of keys) {
      if (key in record && record[key] !== null && record[key] !== undefined) {
        return record[key]
      }
    }
    for (const value of Object.values(record)) {
      const nested = extractFirstValue(value, keys)
      if (nested !== null && nested !== undefined) {
        return nested
      }
    }
  }
  return null
}

const findFirstNumber = (payload: unknown, keys: string[]): number | null => {
  const raw = extractFirstValue(payload, keys)
  return toNumberOrNull(raw)
}

const formatDurationLabel = (seconds: number | null): string | null => {
  if (seconds === null) return null
  const totalSeconds = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(totalSeconds / 60)
  const remain = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(remain).padStart(2, '0')}`
}

const getAudioDuration = (scene: SceneRecord): string | null => {
  const seconds =
    findFirstNumber(scene.audio_meta, ['duration', 'audio_duration']) ??
    findFirstNumber(scene.result, ['audio_duration'])
  return formatDurationLabel(seconds)
}

const getSceneVideoMeta = (scene: SceneRecord, source: SceneVideoSource): Record<string, unknown> | null => {
  if (source === 'merge') {
    if (scene.merge_meta && typeof scene.merge_meta === 'object') {
      return scene.merge_meta as Record<string, unknown>
    }
    return scene.video_meta as Record<string, unknown> | null
  }
  return scene.video_meta as Record<string, unknown> | null
}

const getSceneVideoDuration = (scene: SceneRecord, source: SceneVideoSource): string | null => {
  const targetMeta = getSceneVideoMeta(scene, source)
  const seconds =
    findFirstNumber(targetMeta, ['target_duration', 'duration', 'video_duration']) ??
    findFirstNumber(scene.result, ['video_duration'])
  return formatDurationLabel(seconds)
}

const getSceneVideoUrl = (scene: SceneRecord, source: SceneVideoSource): string | null => {
  if (source === 'merge') {
    return toStringOrNull(scene.merge_video_url) ?? toStringOrNull(scene.raw_video_url)
  }
  return toStringOrNull(scene.raw_video_url)
}

const formatTime = (value?: string | null) => {
  if (!value) return '-'
  return dayjs(value).format('YYYY-MM-DD HH:mm:ss')
}

const goBack = () => {
  router.back()
}

const reload = () => {
  loadDetail({ silent: false })
}
const interrupting = ref(false)

const handleInterruptStep = async (step: StepRow) => {
  if (!task.value) return
  if (!['generate_images', 'generate_videos'].includes(step.step_name)) return
  if (step.status !== 1) {
    ElMessage.warning('该步骤不在运行中')
    return
  }
  interrupting.value = true
  try {
    await taskStore.interruptStep(task.value.id, step.step_name)
    ElMessage.success('已发送中断请求')
    loadDetail({ silent: true })
  } catch (err: any) {
    ElMessage.error(err?.data?.detail ?? '中断失败')
  } finally {
    interrupting.value = false
  }
}

// Utility: wait for a single event on an element
function waitEvent(target: EventTarget, eventName: string, timeout = 3000) {
  return new Promise<Event>((resolve, reject) => {
    const onEvent = (e: Event) => {
      cleanup()
      resolve(e)
    }
    const onTimeout = () => {
      cleanup()
      reject(new Error('timeout'))
    }
    const cleanup = () => {
      target.removeEventListener(eventName, onEvent as EventListener)
      clearTimeout(timer)
    }
    const timer = setTimeout(onTimeout, timeout)
    target.addEventListener(eventName, onEvent as EventListener)
  })
}

// Try to capture the first frame of a video as a poster image (best-effort).
// Uses loadedmetadata -> seek to a small time -> draw frame. May still fail due to CORS.
const handleVideoLoaded = async (event: Event) => {
  const video = event.target as HTMLVideoElement
  if (!video) return
  try {
    // avoid running multiple times
    if ((video as any)._posterProcessed) return
    // If video already has an explicit poster attribute, skip
    if (video.getAttribute('poster')) {
      ;(video as any)._posterProcessed = true
      return
    }

    // If metadata not ready, wait for it
    if (!video.videoWidth || !video.videoHeight) {
      try {
        await waitEvent(video, 'loadedmetadata', 3000)
      } catch {}
    }

    // Seek slightly into the video to ensure frame availability (0 may be black on some sources)
    const originalTime = video.currentTime || 0
    const targetTime = Math.min(0.05, (video.duration || 0) * 0.01)
    try {
      video.currentTime = targetTime
      await waitEvent(video, 'seeked', 1500)
    } catch {}

    // draw frame
    const w = video.videoWidth || 320
    const h = video.videoHeight || 180
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(video, 0, 0, w, h)
    const dataUrl = canvas.toDataURL('image/png')
    video.setAttribute('poster', dataUrl)
    ;(video as any)._posterProcessed = true

    // restore original time if changed
    try {
      video.currentTime = originalTime
    } catch {}
  } catch (err) {
    // ignore errors (likely CORS); mark processed to avoid repeated attempts
    ;(video as any)._posterProcessed = true
  }
}

watch(
  () => steps.value.map((item) => ({ name: item.step_name, status: item.status })),
  () => {
    lockedSteps.value = lockedSteps.value.filter((name) => {
      const step = steps.value.find((item) => item.step_name === name)
      if (!step) {
        return false
      }
      return step.status === 0
    })
  },
  { deep: true }
)
</script>

<style scoped>
.detail-page {
  gap: var(--layout-section-gap);
}

.spacer {
  height: var(--space-2);
}

.card-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
}

.subtitles-card {
  margin-top: var(--space-4);
}

.subtitle-meta {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.subtitle-preview {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.subtitle-preview__label {
  font-weight: var(--font-weight-semibold);
  color: var(--color-neutral-600);
}

.subtitle-preview__content {
  padding: var(--space-3);
  border-radius: var(--radius-md);
  background-color: var(--color-neutral-100);
  border: 1px solid var(--color-neutral-200);
  color: var(--color-neutral-800);
  line-height: var(--line-height-relaxed);
  white-space: pre-wrap;
  word-break: break-word;
}

.subtitle-table {
  margin-top: var(--space-2);
}

.subtitle-empty {
  padding: var(--space-4) 0;
  text-align: center;
  color: var(--color-neutral-500);
}

.detail-page :deep(.el-card__body) {
  padding: var(--space-4);
}

.steps-card :deep(.el-card__body),
.scenes-card :deep(.el-card__body) {
  padding: var(--space-4);
}

.link-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.link-list a {
  color: var(--color-primary);
}

.preset-preview {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

.subtitle-style-preview {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-primary-soft);
  color: var(--color-neutral-700);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-base);
}

.preset-preview__name {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-1);
  color: var(--color-neutral-900);
}

.subtitle-style-preview__name {
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--space-1);
  color: var(--color-neutral-900);
}

.preset-preview p {
  margin: 2px 0;
}

.subtitle-style-preview p {
  margin: 2px 0;
}

.desc-label {
  width: 120px;
  color: var(--color-neutral-600);
}

.text-ellipsis {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}

.script-helper {
  margin-top: var(--space-2);
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--color-neutral-600);
}

.script-helper .script-hint {
  font-size: var(--font-size-xs);
}

.hidden-file-input {
  display: none;
}

.prompt-text {
  display: block;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.4;
  color: var(--color-neutral-800);
}

.scene-media-thumb,
.scene-video-thumb {
  width: 180px;
  height: 320px;
  max-width: 40vw;
  margin: 0 auto;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-color: var(--color-neutral-900);
  display: flex;
  align-items: center;
  justify-content: center;
}

.scene-media-thumb--video {
  margin-bottom: var(--space-2);
}

.scene-media-thumb--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-neutral-500);
  font-size: var(--font-size-sm);
}

.scene-media-image,
.scene-video-player {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: 100%;
  object-fit: contain;
  display: block;
  background-color: var(--color-neutral-900);
}

.scene-media-completed {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.scene-media-audio,
.scene-audio-player {
  width: 100%;
}

.scene-media-video {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.scene-media-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
}

.media-duration {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
}

@media (max-width: 960px) {
  .detail-page :deep(.el-descriptions__body) {
    font-size: var(--font-size-sm);
  }

  .link-list {
    gap: var(--space-2);
  }
}
</style>
