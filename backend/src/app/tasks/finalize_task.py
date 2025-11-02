"""Celery 任务：成片收尾处理（finalize_video）"""
from __future__ import annotations

import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from celery import shared_task
from sqlalchemy.orm import Session

from app.database import get_db_session
from app.models.task import Task, TaskStep
from app.models.subtitle_style import SubtitleStyle
from app.models.media_asset import MediaAsset
from app.services.nca_service import NCAService
from app.services.ffmpeg_service import FFmpegService
from app.services.storage_service import StorageService
from app.services.subtitle_service import SubtitleService
from app.services.subtitle_style_service import SubtitleStyleService
from app.services.faster_whisper_service import get_faster_whisper_service
from app.services.providers.utils import collect_provider_candidates
from app.tasks.utils import ensure_provider_map
from app.config.settings import get_settings


_storage_service = StorageService()
_subtitle_service = SubtitleService()
_subtitle_style_helper = SubtitleStyleService()


def _extract_first_value(payload: Any, keys: Tuple[str, ...]) -> Optional[Any]:
    if isinstance(payload, dict):
        for key in keys:
            if key in payload and payload[key] is not None:
                return payload[key]
        for value in payload.values():
            found = _extract_first_value(value, keys)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _extract_first_value(item, keys)
            if found is not None:
                return found
    return None


def _extract_media_url(payload: Any) -> Optional[str]:
    value = _extract_first_value(payload, ("video_url", "file_url", "url"))
    if value is None:
        return None
    return str(value)


def _extract_duration(payload: Any) -> Optional[float]:
    value = _extract_first_value(payload, ("duration",))
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _resolve_subtitle_style_snapshot(task: Task, db: Session) -> Optional[Dict[str, Any]]:
    snapshot = task.subtitle_style_snapshot if isinstance(task.subtitle_style_snapshot, dict) else None
    if snapshot:
        return dict(snapshot)

    style_id = getattr(task, "subtitle_style_id", None)
    if not style_id:
        return None

    style = db.get(SubtitleStyle, style_id)
    if not style or (hasattr(style, "is_active") and not style.is_active):
        return None

    style_fields, script_settings, effect_settings = _subtitle_style_helper.split_sections(style.style_payload)
    style_payload = style.style_payload if isinstance(style.style_payload, dict) else {}
    snapshot_payload = {
        "id": style.id,
        "name": style.name,
        "description": style.description,
        "style_fields": style_fields,
        "script_settings": script_settings,
        "effect_settings": effect_settings,
        "style": style_fields or style_payload,
        "style_payload": style_payload,
        "sample_text": style.sample_text,
        "is_active": bool(style.is_active),
        "is_default": bool(getattr(style, "is_default", False)),
    }
    if style.created_at:
        snapshot_payload["created_at"] = style.created_at.isoformat()
    if style.updated_at:
        snapshot_payload["updated_at"] = style.updated_at.isoformat()
    return snapshot_payload


def _generate_subtitles(
    _service: Any,
    _provider_name: str,
    task: Task,
    _db: Session,
    context: Dict[str, Any],
    finalize_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    db: Session = _db
    subtitles_config = finalize_config.get("subtitles") if isinstance(finalize_config.get("subtitles"), dict) else {}
    if not subtitles_config.get("enabled", True):
        return context, {
            "operation": "generate_subtitles",
            "status": "skipped",
            "reason": "disabled",
        }

    source_video = context.get("current_video_url") or task.merged_video_url
    if not source_video:
        return context, {
            "operation": "generate_subtitles",
            "status": "skipped",
            "reason": "missing_video",
        }

    whisper_service = get_faster_whisper_service()
    transcription = whisper_service.transcribe(
        source_video,
        language=subtitles_config.get("language"),
        beam_size=subtitles_config.get("beam_size"),
        vad_filter=subtitles_config.get("vad_filter"),
        word_timestamps=subtitles_config.get("word_timestamps"),
        task=subtitles_config.get("task"),
        initial_prompt=subtitles_config.get("initial_prompt"),
        chunk_length=subtitles_config.get("chunk_length"),
        temperature=subtitles_config.get("temperature"),
    )

    asset_type = subtitles_config.get("asset_type") or "subtitles"
    style_snapshot = context.get("subtitle_style_snapshot") if isinstance(context.get("subtitle_style_snapshot"), dict) else None
    style_override = subtitles_config.get("style") if isinstance(subtitles_config.get("style"), dict) else None
    ass_overrides = subtitles_config.get("ass") if isinstance(subtitles_config.get("ass"), dict) else None

    subtitle_result = _subtitle_service.persist_transcription(
        db,
        task_id=task.id,
        transcription=transcription,
        asset_type=asset_type,
        style_snapshot=style_snapshot,
        style_override=style_override,
        ass_overrides=ass_overrides,
        source_video=source_video,
    )

    document = subtitle_result.document
    srt_reference = subtitle_result.srt_reference
    ass_reference = subtitle_result.ass_reference

    context["subtitle_document_id"] = document.id
    context["subtitle_segments"] = subtitle_result.segments
    context["subtitle_force_style"] = subtitle_result.force_style
    context["subtitle_style_name"] = subtitle_result.style_name

    subtitle_artifact: Dict[str, Any] = {
        "document_id": document.id,
        "language": document.language,
        "segments": document.segment_count,
        "model": document.model_name,
        "info": document.info,
        "options": document.options,
        "text": document.text,
        "style_name": subtitle_result.style_name,
        "force_style": subtitle_result.force_style,
    }

    if style_snapshot:
        subtitle_artifact["style_snapshot"] = style_snapshot
    if style_override:
        subtitle_artifact["style_override"] = style_override
    if ass_overrides:
        subtitle_artifact["ass_overrides"] = ass_overrides

    if srt_reference:
        context["subtitle_api_path"] = srt_reference.api_path
        context["subtitle_srt_api_path"] = srt_reference.api_path
        subtitle_artifact["subtitle_api_path"] = srt_reference.api_path
        subtitle_artifact["subtitle_relative_path"] = srt_reference.relative_path
        subtitle_artifact["srt"] = {
            "api_path": srt_reference.api_path,
            "relative_path": srt_reference.relative_path,
        }
        if srt_reference.absolute_path:
            context["subtitle_srt_local_path"] = str(srt_reference.absolute_path)

    if ass_reference:
        context["subtitle_ass_api_path"] = ass_reference.api_path
        subtitle_artifact["ass"] = {
            "api_path": ass_reference.api_path,
            "relative_path": ass_reference.relative_path,
        }
        if ass_reference.absolute_path:
            context["subtitle_ass_local_path"] = str(ass_reference.absolute_path)
            context["subtitle_local_path"] = str(ass_reference.absolute_path)
        if not context.get("subtitle_api_path"):
            context["subtitle_api_path"] = ass_reference.api_path

    preview_text = (document.text or "").strip()[:200]
    if preview_text:
        subtitle_artifact["preview"] = preview_text

    subtitle_public_url = _storage_service.get_external_url(context.get("subtitle_api_path")) if context.get("subtitle_api_path") else None
    if subtitle_public_url:
        subtitle_artifact["public_url"] = subtitle_public_url

    context.setdefault("artifacts", {})["subtitles"] = subtitle_artifact

    return context, {
        "operation": "generate_subtitles",
        "status": "completed",
        "subtitle_document_id": document.id,
        "subtitle_api_path": context.get("subtitle_api_path"),
        "subtitle_srt_api_path": srt_reference.api_path if srt_reference else None,
        "subtitle_ass_api_path": ass_reference.api_path if ass_reference else None,
        "subtitle_relative_path": (srt_reference.relative_path if srt_reference else ass_reference.relative_path if ass_reference else None),
        "public_url": subtitle_public_url,
        "subtitle_local_path": context.get("subtitle_local_path"),
        "subtitle_srt_local_path": context.get("subtitle_srt_local_path"),
        "subtitle_ass_local_path": context.get("subtitle_ass_local_path"),
        "segments": document.segment_count,
        "language": document.language,
        "model": document.model_name,
        "style_name": subtitle_result.style_name,
        "provider": "faster_whisper",
    }


def _resolve_bgm_source(
    db: Session,
    task: Task,
    finalize_config: Dict[str, Any],
) -> Tuple[Optional[str], Dict[str, Any]]:
    task_config = task.task_config or {}
    bgm_config = finalize_config.get("bgm") if isinstance(finalize_config.get("bgm"), dict) else {}

    candidate_asset_id = (
        bgm_config.get("asset_id")
        or finalize_config.get("bgm_asset_id")
        or task_config.get("bgm_asset_id")
    )
    candidate_url = (
        bgm_config.get("url")
        or finalize_config.get("bgm_url")
        or task_config.get("bgm_url")
    )

    if candidate_asset_id:
        asset = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.id == candidate_asset_id,
                MediaAsset.asset_type == "bgm",
                MediaAsset.is_active == True,
            )
            .first()
        )
        if asset:
            return asset.file_url, {
                "source": "asset",
                "asset_id": asset.id,
                "asset_name": asset.asset_name,
                "duration": asset.duration,
            }

    if candidate_url:
        return str(candidate_url), {"source": "config", "url": str(candidate_url)}

    return None, {"source": "missing"}


def _apply_bgm_mix(
    service: Any,
    provider_name: str,
    task: Task,
    db: Session,
    context: Dict[str, Any],
    finalize_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bgm_settings = finalize_config.get("bgm") if isinstance(finalize_config.get("bgm"), dict) else {}
    bgm_enabled = bgm_settings.get("enabled", True)
    if not bgm_enabled:
        return context, {"operation": "bgm_mix", "status": "skipped", "reason": "disabled"}

    bgm_url, bgm_meta = _resolve_bgm_source(db, task, finalize_config)
    if not bgm_url:
        return context, {"operation": "bgm_mix", "status": "skipped", "reason": "missing_bgm"}

    current_video_url = context.get("current_video_url")
    if not current_video_url:
        raise RuntimeError("缺少可用的视频输入，无法进行配乐")

    video_source = current_video_url
    bgm_source = bgm_url
    if provider_name == "nca":
        video_source = _storage_service.build_full_url(current_video_url)
        bgm_source = _storage_service.build_full_url(bgm_url)

    video_metadata = service.get_media_metadata(video_source)
    bgm_metadata = service.get_media_metadata(bgm_source)

    video_duration = _extract_duration(video_metadata)
    bgm_duration = _extract_duration(bgm_metadata)
    if not video_duration or video_duration <= 0:
        raise RuntimeError("无法获取视频时长，配乐失败")

    fade_duration = bgm_settings.get("fade_out", 5.0)
    try:
        fade_duration = float(fade_duration)
    except (TypeError, ValueError):
        fade_duration = 5.0
    fade_duration = max(0.0, min(fade_duration, video_duration))
    fade_start = max(video_duration - fade_duration, 0.0)

    volume_db = bgm_settings.get("volume_db", -20.0)
    try:
        volume_db = float(volume_db)
    except (TypeError, ValueError):
        volume_db = -20.0
    volume_expr = f"{volume_db}dB"

    artifacts_entry: Dict[str, Any] = {
        "bgm_url": bgm_url,
        "bgm_meta": bgm_meta,
        "bgm_duration": bgm_duration,
        "fade_duration": fade_duration,
        "fade_start": fade_start,
        "volume_db": volume_db,
        "provider": provider_name,
        "video_metadata": video_metadata,
    }

    if provider_name == "ffmpeg":
        result = service.mix_background_music(
            base_video_url=current_video_url,
            bgm_url=bgm_url,
            fade_start=fade_start,
            fade_duration=fade_duration,
            volume_db=volume_db,
            task_id=task.id,
        )

        candidate_values = [
            result.get("video_api_path"),
            result.get("video_relative_path"),
            result.get("video_url"),
        ]

        final_reference = None
        for candidate in candidate_values:
            if not candidate:
                continue
            final_reference = _storage_service.resolve_reference(candidate)
            if final_reference:
                break

        final_api_path: Optional[str] = None
        if final_reference:
            final_api_path = final_reference.api_path
        else:
            for candidate in candidate_values:
                if not candidate:
                    continue
                try:
                    final_api_path = _storage_service.ensure_api_path(str(candidate))
                    break
                except ValueError:
                    continue

        if not final_api_path:
            raise RuntimeError("配乐合成未返回视频地址")

        artifacts_entry["bgm_metadata"] = bgm_metadata
        context["current_video_url"] = final_api_path
        context.setdefault("artifacts", {})["bgm"] = artifacts_entry

        return context, {
            "operation": "bgm_mix",
            "status": "completed",
            "video_url": final_api_path,
            "video_api_path": final_api_path,
            "video_url_raw": result.get("video_url_raw"),
            "video_duration": video_duration,
            "bgm_duration": bgm_duration,
            "bgm_meta": bgm_meta,
            "bgm_metadata": bgm_metadata,
            "video_metadata": video_metadata,
            "result": result,
            "provider": provider_name,
        }

    filter_string = (
        f"[0:a]aresample=async=1:first_pts=0[a_main];"
        f"[1:a]volume={volume_expr},aloop=-1,atrim=0:{video_duration:.3f},asetpts=PTS-STARTPTS[a_bgm];"
        f"[a_bgm]afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}[a_bgm_faded];"
        f"[a_main][a_bgm_faded]amix=inputs=2:duration=first:normalize=false:weights='1 1'[aout]"
    )

    payload = {
        "id": f"finalize-bgm-{int(time.time() * 1000)}",
        "inputs": [
            {"file_url": video_source},
            {"file_url": bgm_source},
        ],
        "filters": [
            {"filter": filter_string},
        ],
        "outputs": [
            {
                "options": [
                    {"option": "-map", "argument": "0:v:0"},
                    {"option": "-map", "argument": "[aout]"},
                    {"option": "-c:v", "argument": "copy"},
                    {"option": "-c:a", "argument": "aac"},
                    {"option": "-shortest"},
                ]
            }
        ],
        "global_options": [{"option": "-y"}],
        "metadata": {
            "thumbnail": True,
            "duration": True,
            "filesize": True,
        },
    }

    response = service.compose(payload)
    final_url_raw = _extract_media_url(response)
    final_url = service.resolve_media_url(final_url_raw)
    if not final_url:
        raise RuntimeError("配乐合成未返回视频地址")

    job_id = _extract_first_value(response, ("job_id", "task_id"))

    artifacts_entry["bgm_metadata"] = bgm_metadata
    context["current_video_url"] = final_url
    context.setdefault("artifacts", {})["bgm"] = artifacts_entry

    return context, {
        "operation": "bgm_mix",
        "status": "completed",
        "video_url": final_url,
        "video_url_raw": final_url_raw,
        "job_id": job_id,
        "payload": payload,
        "response": response,
        "video_duration": video_duration,
        "bgm_duration": bgm_duration,
        "bgm_meta": bgm_meta,
        "bgm_metadata": bgm_metadata,
        "video_metadata": video_metadata,
        "provider": provider_name,
    }


def _embed_subtitles(
    service: Any,
    provider_name: str,
    task: Task,
    db: Session,
    context: Dict[str, Any],
    finalize_config: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    subtitles_config = finalize_config.get("subtitles") if isinstance(finalize_config.get("subtitles"), dict) else {}
    embed_enabled = subtitles_config.get("embed", True)
    if not embed_enabled:
        return context, {
            "operation": "embed_subtitles",
            "status": "skipped",
            "reason": "disabled",
        }

    if provider_name != "ffmpeg":
        return context, {
            "operation": "embed_subtitles",
            "status": "skipped",
            "reason": "provider_not_supported",
            "provider": provider_name,
        }

    subtitle_ass_api_path = context.get("subtitle_ass_api_path")
    subtitle_ass_local_path = context.get("subtitle_ass_local_path")
    if not subtitle_ass_local_path:
        return context, {
            "operation": "embed_subtitles",
            "status": "skipped",
            "reason": "missing_ass_subtitles",
        }

    subtitle_local_path = subtitle_ass_local_path
    subtitle_api_path = subtitle_ass_api_path or context.get("subtitle_api_path")

    current_video_url = context.get("current_video_url") or task.merged_video_url
    if not current_video_url:
        raise RuntimeError("缺少可用的视频输入，无法内嵌字幕")

    if not isinstance(service, FFmpegService):  # safety guard
        raise RuntimeError("当前 finalize 服务不支持内嵌字幕")

    subtitle_style: Optional[str] = None

    result = service.embed_subtitles(
        base_video_url=current_video_url,
        subtitle_path=subtitle_local_path,
        task_id=task.id,
        subtitle_style=subtitle_style,
    )

    candidate_values = [
        result.get("video_api_path"),
        result.get("video_relative_path"),
        result.get("video_url"),
    ]

    final_reference = None
    for candidate in candidate_values:
        if not candidate:
            continue
        final_reference = _storage_service.resolve_reference(candidate)
        if final_reference:
            break

    final_api_path: Optional[str] = None
    if final_reference:
        final_api_path = final_reference.api_path
    else:
        for candidate in candidate_values:
            if not candidate:
                continue
            try:
                final_api_path = _storage_service.ensure_api_path(str(candidate))
                break
            except ValueError:
                continue

    if not final_api_path:
        raise RuntimeError("内嵌字幕处理未返回视频地址")

    subtitles_artifact = context.setdefault("artifacts", {}).setdefault("subtitles", {})
    embed_format = "ass" if subtitle_local_path.lower().endswith(".ass") else "srt"
    subtitles_artifact["embedded_video_api_path"] = final_api_path
    subtitles_artifact["embedded_video_relative_path"] = result.get("video_relative_path")
    subtitles_artifact["embedded_video_url"] = result.get("video_url")
    if subtitle_style:
        subtitles_artifact["embedded_style"] = subtitle_style
    subtitles_artifact["embedded_format"] = embed_format
    subtitles_artifact["embedded_subtitle_api_path"] = subtitle_api_path

    context["current_video_url"] = final_api_path

    return context, {
        "operation": "embed_subtitles",
        "status": "completed",
        "video_api_path": final_api_path,
        "video_url": result.get("video_url") or final_api_path,
        "video_relative_path": result.get("video_relative_path"),
        "source_video": current_video_url,
        "subtitle_api_path": subtitle_api_path,
        "subtitle_format": embed_format,
        "provider": provider_name,
        "subtitle_style": subtitle_style,
    }


_PIPELINE_HANDLERS = {
    "generate_subtitles": _generate_subtitles,
    "bgm_mix": _apply_bgm_mix,
    "embed_subtitles": _embed_subtitles,
}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def finalize_video_task(self, task_id: int):
    """异步最终成片处理任务"""
    db: Session = get_db_session()
    try:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": "任务不存在"}

        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "finalize_video")
            .first()
        )
        if not step:
            return {"error": "成片步骤不存在"}

        step.status = 1
        step.error_msg = None
        db.commit()

        settings = get_settings()
        provider_candidates = collect_provider_candidates(task)
        default_provider = settings.provider_defaults.get("finalize") if settings else None
        provider_name = (
            provider_candidates.get("finalize")
            or provider_candidates.get("media_compose")
            or default_provider
        )
        if not provider_name:
            raise RuntimeError("未配置 finalize provider")
        provider_name = str(provider_name).strip().lower()
        if provider_name not in {"nca", "ffmpeg"}:
            raise RuntimeError("不支持的 finalize provider")

        step.provider = provider_name
        db.commit()

        providers_map = ensure_provider_map(task.providers)
        providers_map["finalize"] = provider_name
        task.providers = providers_map
        db.commit()

        if not task.merged_video_url:
            step.status = 3
            step.error_msg = "缺少合并后的视频结果"
            db.commit()
            return {"error": "缺少合并后的视频结果"}

        task_config_data = task.task_config if isinstance(task.task_config, dict) else {}
        finalize_config_source = task_config_data.get("finalize") if isinstance(task_config_data, dict) else None
        finalize_config = deepcopy(finalize_config_source) if isinstance(finalize_config_source, dict) else {}

        style_snapshot = _resolve_subtitle_style_snapshot(task, db)
        if style_snapshot:
            subtitles_section = finalize_config.get("subtitles") if isinstance(finalize_config.get("subtitles"), dict) else {}
            subtitles_section.setdefault("enabled", True)
            subtitles_section.setdefault("embed", True)
            if not subtitles_section.get("style"):
                subtitles_section["style"] = style_snapshot.get("style")
            subtitles_section.setdefault("style_id", style_snapshot.get("id"))
            subtitles_section.setdefault("style_name", style_snapshot.get("name"))
            finalize_config["subtitles"] = subtitles_section

        pipeline: List[str] = []
        raw_pipeline = finalize_config.get("pipeline")
        if isinstance(raw_pipeline, list):
            pipeline = [str(op) for op in raw_pipeline if isinstance(op, (str,))]
        elif isinstance(raw_pipeline, str):
            pipeline = [raw_pipeline]

        subtitles_config = finalize_config.get("subtitles") if isinstance(finalize_config.get("subtitles"), dict) else {}
        subtitles_enabled = subtitles_config.get("enabled", True)
        subtitles_embed_enabled = subtitles_config.get("embed", True)

        if not pipeline:
            if subtitles_enabled:
                pipeline.append("generate_subtitles")
            bgm_url, _ = _resolve_bgm_source(db, task, finalize_config)
            if bgm_url:
                pipeline.append("bgm_mix")
            if subtitles_embed_enabled:
                insert_index = len(pipeline)
                if "bgm_mix" in pipeline:
                    insert_index = pipeline.index("bgm_mix") + 1
                pipeline.insert(insert_index, "embed_subtitles")
        else:
            if subtitles_enabled and "generate_subtitles" not in pipeline:
                insert_index = pipeline.index("bgm_mix") if "bgm_mix" in pipeline else len(pipeline)
                pipeline.insert(insert_index, "generate_subtitles")
            if subtitles_embed_enabled and "embed_subtitles" not in pipeline:
                if "bgm_mix" in pipeline:
                    insert_index = pipeline.index("bgm_mix") + 1
                elif "generate_subtitles" in pipeline:
                    insert_index = pipeline.index("generate_subtitles") + 1
                else:
                    insert_index = len(pipeline)
                pipeline.insert(insert_index, "embed_subtitles")

        context: Dict[str, Any] = {
            "base_video_url": task.merged_video_url,
            "current_video_url": task.merged_video_url,
            "artifacts": {},
        }
        if style_snapshot:
            context["subtitle_style_snapshot"] = style_snapshot
            context.setdefault("artifacts", {}).setdefault("subtitle_style", style_snapshot)
        if provider_name == "ffmpeg":
            finalize_service: Any = FFmpegService()
        else:
            finalize_service = NCAService(db)
        pipeline_logs: List[Dict[str, Any]] = []

        for operation in pipeline:
            handler = _PIPELINE_HANDLERS.get(operation)
            if not handler:
                pipeline_logs.append({
                    "operation": operation,
                    "status": "skipped",
                    "reason": "handler_not_found",
                })
                continue

            try:
                context, entry = handler(finalize_service, provider_name, task, db, context, finalize_config)
            except Exception as op_exc:  # pragma: no cover - remote failure
                pipeline_logs.append({
                    "operation": operation,
                    "status": "failed",
                    "error": str(op_exc),
                    "provider": provider_name,
                })
                raise
            else:
                pipeline_logs.append(entry)

        final_video_candidate = context.get("current_video_url") or task.merged_video_url
        final_reference = _storage_service.resolve_reference(final_video_candidate) if final_video_candidate else None
        if final_reference:
            final_video_url = final_reference.api_path
        elif final_video_candidate:
            try:
                final_video_url = _storage_service.ensure_api_path(str(final_video_candidate))
            except ValueError:
                final_video_url = str(final_video_candidate)
        else:
            final_video_url = None

        step.status = 2
        step.progress = 100
        artifacts = context.get("artifacts") if isinstance(context.get("artifacts"), dict) else {}
        subtitle_api_path = context.get("subtitle_api_path")
        subtitle_srt_api_path = context.get("subtitle_srt_api_path")
        subtitle_ass_api_path = context.get("subtitle_ass_api_path")
        subtitle_document_id = context.get("subtitle_document_id")
        subtitle_public_url = _storage_service.get_external_url(subtitle_api_path) if subtitle_api_path else None
        subtitle_ass_public_url = _storage_service.get_external_url(subtitle_ass_api_path) if subtitle_ass_api_path else None

        step.result = {
            "provider": provider_name,
            "pipeline": pipeline_logs,
            "base_video_url": task.merged_video_url,
            "final_video_url": final_video_url,
            "artifacts": artifacts,
        }

        if subtitle_api_path:
            step.result["subtitle_api_path"] = subtitle_api_path
        if subtitle_srt_api_path:
            step.result["subtitle_srt_api_path"] = subtitle_srt_api_path
        if subtitle_ass_api_path:
            step.result["subtitle_ass_api_path"] = subtitle_ass_api_path
        if subtitle_document_id:
            step.result["subtitle_document_id"] = subtitle_document_id

        task_result = task.result or {}
        task_result.update({
            "final_video_url": final_video_url,
            "finalize_pipeline": pipeline_logs,
        })
        if subtitle_api_path:
            task_result["subtitle_api_path"] = subtitle_api_path
        if subtitle_srt_api_path:
            task_result["subtitle_srt_api_path"] = subtitle_srt_api_path
        if subtitle_ass_api_path:
            task_result["subtitle_ass_api_path"] = subtitle_ass_api_path
        if subtitle_document_id:
            task_result["subtitle_document_id"] = subtitle_document_id
        if artifacts:
            task_result["finalize_artifacts"] = artifacts
        task.result = task_result
        task.final_video_url = final_video_url
        task.status = 2
        task.progress = 100
        if task.total_scenes and task.completed_scenes < task.total_scenes:
            task.completed_scenes = task.total_scenes

        db.commit()
        response_payload: Dict[str, Any] = {"video_url": final_video_url}
        if subtitle_api_path:
            response_payload["subtitle_api_path"] = subtitle_api_path
        if subtitle_srt_api_path:
            response_payload["subtitle_srt_api_path"] = subtitle_srt_api_path
        if subtitle_ass_api_path:
            response_payload["subtitle_ass_api_path"] = subtitle_ass_api_path
        if subtitle_public_url:
            response_payload["subtitle_public_url"] = subtitle_public_url
        if subtitle_ass_public_url:
            response_payload["subtitle_ass_public_url"] = subtitle_ass_public_url
        if subtitle_document_id:
            response_payload["subtitle_document_id"] = subtitle_document_id
        return response_payload

    except Exception as exc:
        db.rollback()
        step = (
            db.query(TaskStep)
            .filter(TaskStep.task_id == task_id, TaskStep.step_name == "finalize_video")
            .first()
        )
        if step:
            step.status = 3
            step.error_msg = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()
