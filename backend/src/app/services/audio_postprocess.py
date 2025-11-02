"""Audio post-processing utilities (silence trimming, etc.)."""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import ffmpeg

from app.config.settings import get_settings
from app.services.storage_service import StorageReference, StorageService
from app.utils.timezone import naive_now

logger = logging.getLogger(__name__)


SILENCE_START_RE = re.compile(r"silence_start:\s*([-+]?\d*\.?\d+)")
SILENCE_END_RE = re.compile(
    r"silence_end:\s*([-+]?\d*\.?\d+)\s*\|\s*silence_duration:\s*([-+]?\d*\.?\d+)"
)


@dataclass(frozen=True)
class SilenceReport:
    """Summary of detected leading/trailing silence."""

    duration: float
    leading_silence: float
    trailing_silence: float
    raw_events: tuple[tuple[str, float, float], ...]

    def exceeds_limits(self, *, max_leading: float, max_trailing: float) -> bool:
        return self.leading_silence > max_leading or self.trailing_silence > max_trailing


@dataclass(frozen=True)
class AudioTrimResult:
    """Result from attempting to trim silence."""

    trimmed: bool
    reference: Optional[StorageReference]
    report: SilenceReport
    tool: str
    removed_leading: float = 0.0
    removed_trailing: float = 0.0


class BaseAudioTrimStrategy:
    """Interface for silence trimming strategies."""

    def analyze(self, source: Path, *, threshold_db: float) -> SilenceReport:
        raise NotImplementedError

    def trim(
        self,
        source: Path,
        target: Path,
        *,
        start: float,
        end: float,
    ) -> None:
        raise NotImplementedError

    @property
    def name(self) -> str:
        raise NotImplementedError


class FFMpegTrimStrategy(BaseAudioTrimStrategy):
    """Trim silence using ffmpeg/silenceremove."""

    def __init__(self, ffmpeg_bin: str = "ffmpeg", ffprobe_bin: str = "ffprobe") -> None:
        self._ffmpeg_bin = ffmpeg_bin
        self._ffprobe_bin = ffprobe_bin

    @property
    def name(self) -> str:  # pragma: no cover - trivial
        return "ffmpeg"

    def analyze(self, source: Path, *, threshold_db: float) -> SilenceReport:
        duration = self._probe_duration(source)
        pipeline = (
            ffmpeg
            .input(str(source))
            .output(
                "pipe:",
                format="null",
                af=f"silencedetect=noise={threshold_db}dB:d=0.02",
            )
            .global_args("-hide_banner", "-nostats")
        )
        stdout_raw, stderr_raw = self._run_ffmpeg(pipeline)
        stdout = stdout_raw.decode("utf-8", errors="ignore")
        stderr = stderr_raw.decode("utf-8", errors="ignore")
        # silencedetect only writes to stderr
        raw_events: list[tuple[str, float, float]] = []
        current_start: Optional[float] = None
        leading_silence = 0.0
        trailing_silence = 0.0

        for line in stderr.splitlines():
            start_match = SILENCE_START_RE.search(line)
            if start_match:
                current_start = float(start_match.group(1))
                raw_events.append(("start", current_start, 0.0))
                continue
            end_match = SILENCE_END_RE.search(line)
            if end_match:
                end_time = float(end_match.group(1))
                duration_value = float(end_match.group(2))
                raw_events.append(("end", end_time, duration_value))
                if current_start is not None:
                    if current_start <= 0.05:
                        leading_silence = max(leading_silence, duration_value)
                    if duration > 0 and abs(duration - end_time) <= 0.2:
                        trailing_silence = max(trailing_silence, duration_value)
                current_start = None

        # Handle trailing silence without a closing event
        if current_start is not None and duration > 0:
            trailing_silence = max(trailing_silence, max(0.0, duration - current_start))

        return SilenceReport(
            duration=duration,
            leading_silence=leading_silence,
            trailing_silence=trailing_silence,
            raw_events=tuple(raw_events),
        )

    def trim(
        self,
        source: Path,
        target: Path,
        *,
        start: float,
        end: float,
    ) -> None:
        # Ensure end is greater than start to avoid empty output
        start = max(0.0, float(start))
        end = max(start + 0.01, float(end))
        filter_args = f"atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS"
        pipeline = (
            ffmpeg
            .input(str(source))
            .output(
                str(target),
                af=filter_args,
            )
            .global_args("-hide_banner", "-nostats")
            .overwrite_output()
        )
        self._run_ffmpeg(pipeline)

    def _probe_duration(self, source: Path) -> float:
        try:
            probe = ffmpeg.probe(str(source), cmd=self._ffprobe_bin)
            duration_value = probe.get("format", {}).get("duration")
            return float(duration_value) if duration_value else 0.0
        except Exception:  # pragma: no cover - fall back
            logger.exception("Failed to probe duration for %s", source)
            return 0.0

    def _run_ffmpeg(self, pipeline: ffmpeg.nodes.OutputStream) -> tuple[bytes, bytes]:
        try:
            return ffmpeg.run(
                pipeline,
                cmd=self._ffmpeg_bin,
                capture_stdout=True,
                capture_stderr=True,
            )
        except ffmpeg.Error as exc:  # pragma: no cover - dependent on environment
            stderr = (exc.stderr or b"").decode("utf-8", errors="ignore")
            raise RuntimeError(f"ffmpeg command failed: {stderr}") from exc


class AudioPostProcessor:
    """Coordinates silence detection/trimming for generated audio files."""

    def __init__(
        self,
        *,
        storage_service: Optional[StorageService] = None,
        strategy: Optional[BaseAudioTrimStrategy] = None,
    ) -> None:
        self._storage = storage_service or StorageService()
        if strategy is None:
            settings = get_settings()
            strategy = FFMpegTrimStrategy(
                ffmpeg_bin=settings.FFMPEG_BIN or "ffmpeg",
                ffprobe_bin=settings.FFPROBE_BIN or "ffprobe",
            )
        self._strategy = strategy

    @property
    def strategy_name(self) -> str:
        return self._strategy.name

    def process(
        self,
        api_path: str,
        *,
        threshold_db: float,
        max_leading: float,
        max_trailing: float,
    ) -> AudioTrimResult:
        local_path = self._resolve_local_path(api_path)
        if not local_path:
            report = SilenceReport(0.0, 0.0, 0.0, tuple())
            return AudioTrimResult(False, None, report, self._strategy.name)

        report = self._strategy.analyze(local_path, threshold_db=threshold_db)
        if not report.exceeds_limits(max_leading=max_leading, max_trailing=max_trailing):
            return AudioTrimResult(False, None, report, self._strategy.name)

        remove_leading = max(0.0, report.leading_silence - max_leading)
        remove_trailing = max(0.0, report.trailing_silence - max_trailing)

        if remove_leading <= 0.0 and remove_trailing <= 0.0:
            return AudioTrimResult(False, None, report, self._strategy.name)

        start = remove_leading
        end = max(report.duration - remove_trailing, start + 0.01)

        target_path = self._allocate_target_path(local_path)
        self._strategy.trim(
            local_path,
            target_path,
            start=start,
            end=end,
        )
        reference = self._storage.reference_from_absolute(target_path)
        return AudioTrimResult(
            True,
            reference,
            report,
            self._strategy.name,
            removed_leading=remove_leading,
            removed_trailing=remove_trailing,
        )

    def _resolve_local_path(self, api_path: str) -> Optional[Path]:
        try:
            return self._storage.ensure_local_path(api_path)
        except Exception:
            logger.warning("Unable to resolve local path for %s; skipping silence trim", api_path)
            return None

    def _allocate_target_path(self, source: Path) -> Path:
        timestamp = naive_now().strftime("%Y%m%d%H%M%S")
        stem = source.stem
        suffix = source.suffix or ".wav"
        candidate = source.with_name(f"{stem}_trim_{timestamp}{suffix}")
        counter = 1
        while candidate.exists():
            candidate = source.with_name(f"{stem}_trim_{timestamp}_{counter}{suffix}")
            counter += 1
        return candidate


_default_post_processor: Optional[AudioPostProcessor] = None


def get_audio_post_processor() -> AudioPostProcessor:
    global _default_post_processor
    if _default_post_processor is None:
        _default_post_processor = AudioPostProcessor()
    return _default_post_processor