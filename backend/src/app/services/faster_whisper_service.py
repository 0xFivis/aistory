"""Service wrapper around the faster-whisper transcription model."""
from __future__ import annotations

import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

try:  # pragma: no cover - optional dependency guard
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - handled during validation
    WhisperModel = None  # type: ignore[assignment]

from app.config.settings import Settings, get_settings
from app.services.base import BaseService
from app.services.exceptions import ConfigurationException, ServiceException
from app.services.storage_service import StorageService


def _format_timestamp(value: float) -> str:
    milliseconds = max(int(round(value * 1000)), 0)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, ms = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{ms:03}"


@dataclass
class TranscriptionWord:
    start: float
    end: float
    text: str


@dataclass
class TranscriptionSegment:
    index: int
    start: float
    end: float
    text: str
    words: List[TranscriptionWord]


@dataclass
class TranscriptionResult:
    model: str
    source_path: str
    segments: List[TranscriptionSegment]
    text: str
    info: Dict[str, Any]
    options: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "source_path": self.source_path,
            "text": self.text,
            "segments": [
                {
                    "index": segment.index,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "words": [
                        {
                            "start": word.start,
                            "end": word.end,
                            "text": word.text,
                        }
                        for word in segment.words
                    ],
                }
                for segment in self.segments
            ],
            "info": self.info,
            "options": self.options,
        }

    def to_srt(self) -> str:
        lines: List[str] = []
        for segment in self.segments:
            lines.append(str(segment.index))
            lines.append(f"{_format_timestamp(segment.start)} --> {_format_timestamp(segment.end)}")
            lines.append(segment.text.strip())
            lines.append("")
        return "\n".join(lines).strip() + "\n"


class FasterWhisperService(BaseService):
    """Encapsulate faster-whisper model lifecycle and transcription helpers."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        self._model = None
        self._storage = StorageService(self.settings)
        self.model_id = (self.settings.FASTER_WHISPER_MODEL or "medium").strip()
        self.device = (self.settings.FASTER_WHISPER_DEVICE or "cuda").strip()
        self.compute_type = (self.settings.FASTER_WHISPER_COMPUTE_TYPE or "float16").strip()
        self.download_root = (self.settings.FASTER_WHISPER_DOWNLOAD_ROOT or "").strip() or None
        self.device_index = self._parse_device_index(self.settings.FASTER_WHISPER_DEVICE_INDEX)
        self.default_beam_size = self.settings.FASTER_WHISPER_BEAM_SIZE or 5
        self.default_vad_filter = (
            self.settings.FASTER_WHISPER_VAD_FILTER
            if self.settings.FASTER_WHISPER_VAD_FILTER is not None
            else True
        )
        self.default_word_timestamps = (
            self.settings.FASTER_WHISPER_WORD_TIMESTAMPS
            if self.settings.FASTER_WHISPER_WORD_TIMESTAMPS is not None
            else True
        )
        self.default_task = (self.settings.FASTER_WHISPER_TASK or "transcribe").strip()
        self.default_language = (
            self.settings.FASTER_WHISPER_LANGUAGE.strip()
            if isinstance(self.settings.FASTER_WHISPER_LANGUAGE, str)
            else None
        )
        self.default_temperature = (
            float(self.settings.FASTER_WHISPER_TEMPERATURE)
            if self.settings.FASTER_WHISPER_TEMPERATURE is not None
            else None
        )
        self.default_chunk_length = (
            float(self.settings.FASTER_WHISPER_CHUNK_LENGTH)
            if self.settings.FASTER_WHISPER_CHUNK_LENGTH is not None
            else None
        )
        self.default_prompt = (
            self.settings.FASTER_WHISPER_INITIAL_PROMPT.strip()
            if isinstance(self.settings.FASTER_WHISPER_INITIAL_PROMPT, str)
            else None
        )
        self.download_timeout = 120.0
        self._validate_configuration()

    @property
    def service_name(self) -> str:
        return "FasterWhisper"

    def _validate_configuration(self) -> None:
        if not self.model_id:
            raise ConfigurationException("Model identifier is not configured", self.service_name)
        if WhisperModel is None:
            raise ConfigurationException(
                "faster-whisper is not installed. Did you add it to requirements?",
                self.service_name,
            )

    def _parse_device_index(self, value: Optional[str]) -> Optional[Any]:
        if value is None:
            return None
        raw = str(value).strip()
        if not raw:
            return None
        parts = [p for p in raw.split(",") if p.strip()]
        try:
            if len(parts) == 1:
                return int(parts[0])
            return [int(part) for part in parts]
        except ValueError as exc:
            raise ConfigurationException(
                f"Invalid device index value: {value}",
                self.service_name,
            ) from exc

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model

        kwargs: Dict[str, Any] = {}
        if self.download_root:
            kwargs["download_root"] = self.download_root
        if self.device_index is not None:
            kwargs["device_index"] = self.device_index

        self.logger.info(
            "Loading faster-whisper model",
            extra={
                "service": self.service_name,
                "model": self.model_id,
                "device": self.device,
                "compute_type": self.compute_type,
                "device_index": self.device_index,
                "download_root": self.download_root,
            },
        )

        self._model = WhisperModel(
            self.model_id,
            device=self.device,
            compute_type=self.compute_type,
            **kwargs,
        )
        return self._model

    def _resolve_source(self, source: str) -> Tuple[Path, Optional[Path]]:
        try:
            local_path = self._storage.ensure_local_path(source)
            return local_path, None
        except Exception:
            pass

        parsed = urlparse(source)
        if parsed.scheme not in {"http", "https"}:
            raise ServiceException(
                f"Unable to resolve local path for source: {source}",
                code="TRANSCRIBE_INPUT_ERROR",
            )

        suffix = Path(parsed.path or "").suffix or ".tmp"
        temp_dir = (
            Path(self.settings.STORAGE_TEMP_PATH)
            if self.settings.STORAGE_TEMP_PATH
            else Path(tempfile.gettempdir())
        )
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_name = f"whisper_{secrets.token_hex(8)}_{os.getpid()}{suffix}"
        temp_path = temp_dir / temp_name

        try:
            with httpx.stream("GET", source, follow_redirects=True, timeout=self.download_timeout) as response:
                response.raise_for_status()
                with temp_path.open("wb") as buffer:
                    for chunk in response.iter_bytes():
                        if chunk:
                            buffer.write(chunk)
        except httpx.HTTPError as exc:
            if temp_path.exists():  # best effort cleanup
                try:
                    temp_path.unlink()
                except Exception:  # pragma: no cover - cleanup best effort
                    pass
            raise ServiceException(
                f"Failed to download media source: {exc}",
                code="TRANSCRIBE_DOWNLOAD_FAILED",
            ) from exc

        return temp_path, temp_path

    def transcribe(
        self,
        source: str,
        *,
        language: Optional[str] = None,
        beam_size: Optional[int] = None,
        vad_filter: Optional[bool] = None,
        word_timestamps: Optional[bool] = None,
        task: Optional[str] = None,
        initial_prompt: Optional[str] = None,
        chunk_length: Optional[float] = None,
        temperature: Optional[float] = None,
    ) -> TranscriptionResult:
        model = self._load_model()
        local_path, cleanup_path = self._resolve_source(source)

        options: Dict[str, Any] = {
            "language": language or self.default_language,
            "beam_size": beam_size or self.default_beam_size,
            "vad_filter": (
                self.default_vad_filter
                if vad_filter is None
                else vad_filter
            ),
            "word_timestamps": (
                self.default_word_timestamps
                if word_timestamps is None
                else word_timestamps
            ),
            "task": (task or self.default_task or "transcribe"),
            "initial_prompt": initial_prompt or self.default_prompt,
            "chunk_length": chunk_length or self.default_chunk_length,
            "temperature": temperature if temperature is not None else self.default_temperature,
        }

        if options["beam_size"] is not None:
            try:
                options["beam_size"] = int(options["beam_size"])
            except (TypeError, ValueError) as exc:
                raise ServiceException(
                    "Invalid beam_size value",
                    code="TRANSCRIBE_CONFIG",
                ) from exc

        if options["chunk_length"] is not None:
            try:
                options["chunk_length"] = float(options["chunk_length"])
            except (TypeError, ValueError) as exc:
                raise ServiceException(
                    "Invalid chunk_length value",
                    code="TRANSCRIBE_CONFIG",
                ) from exc

        if options["temperature"] is not None:
            try:
                options["temperature"] = float(options["temperature"])
            except (TypeError, ValueError) as exc:
                raise ServiceException(
                    "Invalid temperature value",
                    code="TRANSCRIBE_CONFIG",
                ) from exc

        if options["task"]:
            options["task"] = str(options["task"]).strip() or "transcribe"

        # Remove None entries to avoid passing unsupported parameters
        invoke_options = {key: value for key, value in options.items() if value is not None}

        self._log_request(
            endpoint="transcribe",
            method="RUN",
            source=str(local_path),
            options={key: value for key, value in invoke_options.items() if key != "initial_prompt"},
        )

        segments_payload: List[TranscriptionSegment] = []
        combined_text: List[str] = []
        start_time = time.perf_counter()
        try:
            segments_iter, info = model.transcribe(str(local_path), **invoke_options)
            for index, segment in enumerate(segments_iter, start=1):
                words: List[TranscriptionWord] = []
                if getattr(segment, "words", None):
                    words = [
                        TranscriptionWord(
                            start=float(word.start),
                            end=float(word.end),
                            text=str(getattr(word, "word", "")).strip(),
                        )
                        for word in segment.words
                    ]
                text = str(getattr(segment, "text", "")).strip()
                combined_text.append(text)
                segments_payload.append(
                    TranscriptionSegment(
                        index=index,
                        start=float(getattr(segment, "start", 0.0) or 0.0),
                        end=float(getattr(segment, "end", 0.0) or 0.0),
                        text=text,
                        words=words,
                    )
                )
        except Exception as exc:
            self._log_error(exc, {"operation": "transcribe"})
            raise ServiceException(
                f"Faster Whisper transcription failed: {exc}",
                code="TRANSCRIBE_FAILED",
            ) from exc
        finally:
            if cleanup_path is not None:
                try:
                    cleanup_path.unlink()
                except Exception:  # pragma: no cover - best effort cleanup
                    pass

        info_payload: Dict[str, Any] = {}
        if info is not None:
            info_payload = {
                "language": getattr(info, "language", None),
                "language_probability": getattr(info, "language_probability", None),
                "duration": getattr(info, "duration", None),
                "duration_after_vad": getattr(info, "duration_after_vad", None),
            }

        result = TranscriptionResult(
            model=self.model_id,
            source_path=str(local_path),
            segments=segments_payload,
            text=" ".join(part for part in combined_text if part).strip(),
            info=info_payload,
            options=dict(invoke_options),
        )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        self._log_response(
            endpoint="transcribe",
            status_code=200,
            duration_ms=duration_ms,
        )

        return result


_default_service: Optional[FasterWhisperService] = None


def get_faster_whisper_service() -> FasterWhisperService:
    global _default_service
    if _default_service is None:
        settings = get_settings()
        _default_service = FasterWhisperService(settings)
    return _default_service


__all__ = [
    "FasterWhisperService",
    "TranscriptionResult",
    "TranscriptionSegment",
    "TranscriptionWord",
    "get_faster_whisper_service",
]
