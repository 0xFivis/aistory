"""Local FFmpeg integration utilities."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shlex
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple
from urllib.parse import urlparse

import ffmpeg
import httpx

from .base import BaseService
from .exceptions import APIException, ValidationException, ConfigurationException
from app.config.settings import get_settings
from app.services.storage_service import StorageService, StorageReference



class FFmpegService(BaseService):
    """Provide thin wrappers around local ffmpeg/ffprobe commands."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(settings)
        self.settings = settings
        if not settings.STORAGE_BASE_PATH:
            raise ConfigurationException("STORAGE_BASE_PATH is not configured", service_name=self.service_name)
        self.ffmpeg_bin = getattr(settings, "FFMPEG_BIN", "ffmpeg") or "ffmpeg"
        self.ffprobe_bin = getattr(settings, "FFPROBE_BIN", "ffprobe") or "ffprobe"
        self.storage_base = Path(settings.STORAGE_BASE_PATH).resolve()
        self.storage_service = StorageService(settings)
        os.environ.setdefault("FFMPEG_BINARY", self.ffmpeg_bin)
        os.environ.setdefault("FFPROBE_BINARY", self.ffprobe_bin)

    @property
    def service_name(self) -> str:
        return "FFmpeg"

    def _validate_configuration(self) -> None:
        # Local ffmpeg assumes binaries are installed and reachable via PATH.
        pass

    # Internal helpers -------------------------------------------------

    def _normalise_media_input(self, value: str) -> str:
        if not value:
            return value
        try:
            local_path = self.storage_service.ensure_local_path(value)
            return str(local_path)
        except ValueError:
            reference = self.storage_service.resolve_reference(value)
            if reference and reference.absolute_path:
                return str(reference.absolute_path)
        parsed = urlparse(str(value))
        if parsed.scheme in {"http", "https"}:
            cached = self._cache_remote_input(str(value))
            if cached:
                return str(cached)
        return value

    def _reference_from_output(self, file_path: Path) -> StorageReference:
        return self.storage_service.reference_from_absolute(file_path)

    @staticmethod
    def _parse_ass_play_res(subtitle_file: Path) -> Optional[Tuple[int, int]]:
        width: Optional[int] = None
        height: Optional[int] = None
        try:
            with subtitle_file.open("r", encoding="utf-8") as handle:
                for _ in range(200):
                    line = handle.readline()
                    if not line:
                        break
                    text = line.strip()
                    if not text or text.startswith(";"):
                        continue
                    lower = text.lower()
                    if lower.startswith("playresx"):
                        parts = text.split(":", 1)
                        if len(parts) == 2:
                            try:
                                width = int(parts[1].strip())
                            except ValueError:
                                width = None
                    elif lower.startswith("playresy"):
                        parts = text.split(":", 1)
                        if len(parts) == 2:
                            try:
                                height = int(parts[1].strip())
                            except ValueError:
                                height = None
                    elif lower.startswith("[v4+") or lower.startswith("[events]"):
                        break
            if width and height and width > 0 and height > 0:
                return width, height
        except OSError:
            return None
        return None

    def _cache_remote_input(self, url: str) -> Optional[Path]:
        cache_dir = self._ensure_dir("tmp", "ffmpeg-cache")
        suffix = Path(urlparse(url).path).suffix or ".bin"
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        target = cache_dir / f"{digest}{suffix}"
        if target.exists():
            return target
        tmp_path = target.with_suffix(target.suffix + ".part")
        try:
            with httpx.stream(
                "GET",
                url,
                timeout=60.0,
                follow_redirects=True,
                trust_env=False,
                verify=True,
            ) as response:
                response.raise_for_status()
                with tmp_path.open("wb") as handle:
                    for chunk in response.iter_bytes():
                        if chunk:
                            handle.write(chunk)
            tmp_path.replace(target)
            return target
        except httpx.HTTPError as exc:
            self._log_error(
                exc,
                context={
                    "operation": "cache_remote_input",
                    "url": url,
                    "trust_env": False,
                },
            )
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        return None

    def _run_stream(self, stream: ffmpeg.nodes.Stream) -> tuple[str, str]:
        command = stream.compile(cmd=self.ffmpeg_bin)
        if self.logger.isEnabledFor(logging.DEBUG):
            joined = " ".join(shlex.quote(part) for part in command)
            self.logger.debug("[%s] Executing: %s", self.service_name, joined)
        try:
            stdout, stderr = ffmpeg.run(
                stream,
                cmd=self.ffmpeg_bin,
                capture_stdout=True,
                capture_stderr=True,
            )
        except ffmpeg.Error as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
            self._log_error(
                exc,
                context={
                    "operation": "ffmpeg.run",
                    "command": command,
                    "stderr": stderr,
                },
            )
            raise APIException(
                f"ffmpeg 执行失败: {stderr.strip() or str(exc)}",
                service_name=self.service_name,
                response_data={"stderr": stderr, "command": command},
            ) from exc
        return (
            stdout.decode("utf-8", errors="ignore") if isinstance(stdout, bytes) else stdout,
            stderr.decode("utf-8", errors="ignore") if isinstance(stderr, bytes) else stderr,
        )

    def _ensure_dir(self, *parts: str) -> Path:
        target = self.storage_base.joinpath(*parts)
        target.mkdir(parents=True, exist_ok=True)
        return target

    def resolve_media_url(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        value_str = str(value).strip()
        if value_str.startswith("http://") or value_str.startswith("https://"):
            return value_str
        reference = self.storage_service.resolve_reference(value_str)
        if reference:
            return reference.public_url or reference.api_path
        return value_str

    # Metadata ---------------------------------------------------------

    def get_media_metadata(self, media_url: str) -> Dict[str, Any]:
        if not media_url:
            raise ValidationException("media_url is required", field="media_url")
        try:
            data = ffmpeg.probe(
                self._normalise_media_input(media_url),
                cmd=self.ffprobe_bin,
            )
        except ffmpeg.Error as exc:
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
            raise APIException(
                f"ffprobe failed: {stderr.strip() or str(exc)}",
                service_name=self.service_name,
                response_data={"stderr": stderr},
            ) from exc

        format_section = data.get("format", {}) if isinstance(data, dict) else {}
        try:
            duration = float(format_section.get("duration")) if format_section.get("duration") else None
        except (TypeError, ValueError):
            duration = None

        return {
            "source": "ffmpeg",
            "duration": duration,
            "format": format_section,
            "streams": data.get("streams", []) if isinstance(data, dict) else [],
            "raw": data,
        }

    # Scene-level AV composition --------------------------------------

    def compose_scene_with_audio(
        self,
        *,
        video_url: str,
        audio_url: str,
        frame_rate: int,
        task_id: int,
        scene_id: int,
        scene_seq: int,
    ) -> Dict[str, Any]:
        video_meta = self.get_media_metadata(video_url)
        audio_meta = self.get_media_metadata(audio_url)

        video_duration = video_meta.get("duration")
        audio_duration = audio_meta.get("duration")
        if not video_duration or video_duration <= 0:
            raise APIException("无法获取视频时长", service_name=self.service_name)
        if not audio_duration or audio_duration <= 0:
            raise APIException("无法获取音频时长", service_name=self.service_name)

        required_frames = int((audio_duration * frame_rate) + 0.9999)
        target_duration = required_frames / frame_rate
        speed_ratio = target_duration / video_duration if video_duration else 1.0

        filter_video = (
            ffmpeg
            .input(self._normalise_media_input(video_url))
            .video
            .filter("setpts", f"{speed_ratio:.10f}*PTS")
            .filter("fps", frame_rate)
        )
        filter_audio = (
            ffmpeg
            .input(self._normalise_media_input(audio_url))
            .audio
            .filter("apad", whole_dur=f"{target_duration:.10f}")
            .filter("asetpts", "PTS-STARTPTS")
        )

        output_dir = self._ensure_dir("video", "scene_merge")
        timestamp = int(time.time() * 1000)
        filename = f"task{task_id}_scene{scene_seq}_{timestamp}.mp4"
        output_path = output_dir / filename

        stream = (
            ffmpeg
            .output(
                filter_video,
                filter_audio,
                str(output_path),
                **{
                    "c:v": "libx264",
                    "preset": "fast",
                    "crf": "23",
                    "c:a": "aac",
                    "shortest": None,
                },
            )
            .overwrite_output()
        )

        self._run_stream(stream)
        self.logger.info(
            "[%s] compose_scene_with_audio -> %s",
            self.service_name,
            output_path.name,
            extra={
                "service": self.service_name,
                "operation": "compose_scene_with_audio",
                "output_path": str(output_path),
            },
        )

        access = self._reference_from_output(output_path)
        public_url = access.public_url
        merged_meta = self.get_media_metadata(str(output_path))

        return {
            "video_url": public_url,
            "video_api_path": access.api_path,
            "video_relative_path": access.relative_path,
            "video_url_raw": str(output_path),
            "speed_ratio": speed_ratio,
            "required_frames": required_frames,
            "target_duration": target_duration,
            "video_duration": video_duration,
            "audio_duration": audio_duration,
            "video_metadata": video_meta,
            "audio_metadata": audio_meta,
            "output_metadata": merged_meta,
        }

    # Finalize helpers -------------------------------------------------

    def mix_background_music(
        self,
        *,
        base_video_url: str,
        bgm_url: str,
        fade_start: float,
        fade_duration: float,
        volume_db: float,
        task_id: int,
    ) -> Dict[str, Any]:
        video_input = ffmpeg.input(self._normalise_media_input(base_video_url))
        video_stream = video_input.video
        main_audio = video_input.audio.filter("aresample", **{"async": 1, "first_pts": 0})

        bgm_audio = (
            ffmpeg
            .input(self._normalise_media_input(bgm_url))
            .audio
            .filter("volume", f"{volume_db}dB")
            .filter("aloop", loop=-1)
            .filter("atrim", start=0, end=fade_start + fade_duration)
            .filter("asetpts", "PTS-STARTPTS")
            .filter("afade", t="out", st=fade_start, d=fade_duration)
        )

        mixed_audio = ffmpeg.filter(
            [main_audio, bgm_audio],
            "amix",
            inputs=2,
            duration="first",
            normalize=False,
            weights="1 1",
        )

        output_dir = self._ensure_dir("video", "finalize")
        filename = f"final_{task_id}_{int(time.time() * 1000)}.mp4"
        output_path = output_dir / filename

        stream = (
            ffmpeg
            .output(
                video_stream,
                mixed_audio,
                str(output_path),
                **{"c:v": "copy", "c:a": "aac", "shortest": None},
            )
            .overwrite_output()
        )

        self._run_stream(stream)
        self.logger.info(
            "[%s] mix_background_music -> %s",
            self.service_name,
            output_path.name,
            extra={
                "service": self.service_name,
                "operation": "mix_background_music",
                "output_path": str(output_path),
            },
        )

        access = self._reference_from_output(output_path)
        public_url = access.public_url
        meta = self.get_media_metadata(str(output_path))
        return {
            "video_url": public_url,
            "video_api_path": access.api_path,
            "video_relative_path": access.relative_path,
            "video_url_raw": str(output_path),
            "output_metadata": meta,
        }

    def embed_subtitles(
        self,
        *,
        base_video_url: str,
        subtitle_path: str,
        task_id: int,
        subtitle_style: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not subtitle_path:
            raise ValidationException("subtitle_path is required", field="subtitle_path")

        video_input_path = self._normalise_media_input(base_video_url)
        subtitle_input_path = self._normalise_media_input(subtitle_path)

        subtitle_path_resolved = Path(subtitle_input_path)
        if not subtitle_path_resolved.exists():
            raise ValidationException("subtitle file not found", field="subtitle_path")

        resolved_subtitle = subtitle_path_resolved.resolve()
        subtitles_arg = resolved_subtitle.as_posix()

        target_play_res = self._parse_ass_play_res(resolved_subtitle)
        video_meta: Dict[str, Any] = {}
        try:
            video_meta = self.get_media_metadata(base_video_url)
        except Exception as exc:  # pragma: no cover - best effort metadata fetch
            self._log_error(
                exc,
                context={
                    "operation": "embed_subtitles_metadata",
                    "video": base_video_url,
                },
            )

        video_width: Optional[int] = None
        video_height: Optional[int] = None
        if isinstance(video_meta, dict):
            for stream in video_meta.get("streams", []):
                if isinstance(stream, dict) and stream.get("codec_type") == "video":
                    try:
                        vw = int(stream.get("width")) if stream.get("width") else None
                        vh = int(stream.get("height")) if stream.get("height") else None
                    except (TypeError, ValueError):
                        vw = vh = None
                    video_width = vw if vw and vw > 0 else video_width
                    video_height = vh if vh and vh > 0 else video_height
                    if video_width and video_height:
                        break

        scale_target: Optional[Tuple[int, int]] = None
        if target_play_res:
            target_w, target_h = target_play_res
            if target_w > 0 and target_h > 0:
                scale_needed = True
                if video_width and video_height:
                    scale_needed = abs(target_w - video_width) > 1 or abs(target_h - video_height) > 1
                if scale_needed:
                    scale_target = (target_w, target_h)

        input_stream = ffmpeg.input(video_input_path)
        filter_kwargs: Dict[str, Any] = {"filename": subtitles_arg}
        if subtitle_style:
            filter_kwargs["force_style"] = subtitle_style
        video_stream = input_stream.video
        if scale_target:
            target_w, target_h = scale_target
            video_stream = video_stream.filter("scale", target_w, target_h, flags="lanczos").filter("setsar", "1")
        video_stream = video_stream.filter("subtitles", **filter_kwargs)

        audio_stream = None
        try:
            audio_stream = input_stream.audio
        except AttributeError:
            audio_stream = None

        output_dir = self._ensure_dir("video", "finalize")
        filename = f"final_{task_id}_{int(time.time() * 1000)}_subtitled.mp4"
        output_path = output_dir / filename

        output_kwargs: Dict[str, Any] = {
            "c:v": "libx264",
            "preset": "medium",
            "crf": "18",
            "pix_fmt": "yuv420p",
            "movflags": "+faststart",
        }
        if audio_stream is not None:
            output_kwargs["c:a"] = "copy"

        stream_inputs = [video_stream]
        if audio_stream is not None:
            stream_inputs.append(audio_stream)

        stream = ffmpeg.output(*stream_inputs, str(output_path), **output_kwargs).overwrite_output()

        self._run_stream(stream)
        self.logger.info(
            "[%s] embed_subtitles -> %s",
            self.service_name,
            output_path.name,
            extra={
                "service": self.service_name,
                "operation": "embed_subtitles",
                "output_path": str(output_path),
            },
        )

        access = self._reference_from_output(output_path)
        public_url = access.public_url
        meta = self.get_media_metadata(str(output_path))
        return {
            "video_url": public_url,
            "video_api_path": access.api_path,
            "video_relative_path": access.relative_path,
            "video_url_raw": str(output_path),
            "output_metadata": meta,
            "subtitle_source": subtitle_path,
            "subtitle_style": subtitle_style,
            "scale_resolution": scale_target,
        }

    # Concat helpers ---------------------------------------------------

    def concat_with_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        inputs = payload.get("inputs", [])
        if not inputs:
            raise ValidationException("concat payload requires inputs", field="inputs")

        output_defs = payload.get("outputs", [])
        output_options: Sequence[Dict[str, Any]] = []
        if output_defs and isinstance(output_defs[0], dict):
            output_options = output_defs[0].get("options", [])
        global_options = payload.get("global_options", [])

        output_dir = self._ensure_dir("video", "merge")
        filename = f"concat_{int(time.time() * 1000)}.mp4"
        output_path = output_dir / filename

        if not inputs:
            raise ValidationException("concat payload requires inputs", field="inputs")

        input_streams = []
        for item in inputs:
            file_url = item.get("file_url") if isinstance(item, dict) else None
            if not file_url:
                raise ValidationException("each input requires file_url", field="inputs")
            input_streams.append(ffmpeg.input(self._normalise_media_input(str(file_url))))

        output_kwargs: Dict[str, Any] = {}
        global_args: list[str] = []

        video_streams = []
        audio_streams = []
        for stream in input_streams:
            video_chain = (
                stream.video
                .filter("format", "yuv420p")
                .filter("setpts", "PTS-STARTPTS")
            )
            video_streams.append(video_chain)
            try:
                audio_chain = stream.audio.filter("asetpts", "PTS-STARTPTS")
                audio_streams.append(audio_chain)
            except ffmpeg.Error:
                audio_streams.append(None)

        concat_args = []
        has_audio = all(audio_streams)
        if has_audio:
            for video_chain, audio_chain in zip(video_streams, audio_streams):
                concat_args.extend([video_chain, audio_chain])
            concat_node = ffmpeg.concat(*concat_args, v=1, a=1).node
            video_output, audio_output = concat_node[0], concat_node[1]
        else:
            concat_node = ffmpeg.concat(*video_streams, v=1, a=0)
            video_output = concat_node
            audio_output = None

        option_map: Dict[str, str] = {
            "c:v": "c:v",
            "c:a": "c:a",
            "pix_fmt": "pix_fmt",
            "crf": "crf",
            "preset": "preset",
            "shortest": "shortest",
            "movflags": "movflags",
        }

        for opt in output_options:
            option = opt.get("option")
            if not option:
                continue
            key = option.lstrip("-")
            target_key = option_map.get(key)
            argument = opt.get("argument")
            if target_key:
                output_kwargs[target_key] = argument if argument is not None else None
            elif key == "map":
                # handled implicitly by concat outputs
                continue
            else:
                global_args.append(option)
                if argument is not None:
                    global_args.append(str(argument))

        stream_inputs: list[ffmpeg.nodes.Stream] = [video_output]
        if audio_output is not None:
            stream_inputs.append(audio_output)

        stream = ffmpeg.output(*stream_inputs, str(output_path), **output_kwargs)
        if global_args:
            stream = stream.global_args(*global_args)
        for opt in global_options:
            option = opt.get("option") if isinstance(opt, dict) else None
            if not option:
                continue
            args = [option]
            argument = opt.get("argument") if isinstance(opt, dict) else None
            if argument is not None:
                args.append(str(argument))
            stream = stream.global_args(*args)

        stream = stream.overwrite_output()

        self._run_stream(stream)
        self.logger.info(
            "[%s] concat_with_payload -> %s",
            self.service_name,
            output_path.name,
            extra={
                "service": self.service_name,
                "operation": "concat_with_payload",
                "output_path": str(output_path),
            },
        )

        access = self._reference_from_output(output_path)
        public_url = access.public_url
        meta = self.get_media_metadata(str(output_path))
        return {
            "video_url": public_url,
            "video_api_path": access.api_path,
            "video_relative_path": access.relative_path,
            "video_url_raw": str(output_path),
            "output_metadata": meta,
        }


__all__ = ["FFmpegService"]
