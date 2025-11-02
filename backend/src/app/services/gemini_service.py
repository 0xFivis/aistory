"""
Google Gemini AI service for script generation
"""
import json
import logging
import re
import os
import time
from contextlib import contextmanager
from pathlib import Path
from string import Template
from typing import Dict, List, Any, Optional
from textwrap import dedent, indent

import google.generativeai as genai

from app.services.gemini_credential_pool import GeminiCredentialPool

from app.utils.timezone import aware_now

from app.config.settings import Settings
from app.core.proxy_config import get_proxy_for_service
from .base import BaseService
from .exceptions import (
    APIException,
    ConfigurationException,
    ValidationException,
)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_INVALID_RESPONSE_LOG = Path(__file__).resolve().parents[3] / "logs" / "gemini_storyboard_invalid.log"

_STORYBOARD_TEMPLATE: Optional[Template] = None
_VIDEO_TEMPLATES: Dict[str, Template] = {}

_DEBUG_MAX_CHARS = 2000


def _load_storyboard_template() -> Template:
    global _STORYBOARD_TEMPLATE
    if _STORYBOARD_TEMPLATE is None:
        path = PROMPTS_DIR / "storyboard_prompt.tmpl"
        if not path.exists():
            raise FileNotFoundError(f"Storyboard prompt template not found: {path}")
        _STORYBOARD_TEMPLATE = Template(path.read_text(encoding="utf-8"))
    return _STORYBOARD_TEMPLATE


def _load_video_templates() -> Dict[str, Template]:
    global _VIDEO_TEMPLATES
    if not _VIDEO_TEMPLATES:
        path = PROMPTS_DIR / "video_prompt.tmpl"
        if not path.exists():
            raise FileNotFoundError(f"Video prompt template not found: {path}")
        # Read the entire template file as a single default template.
        # Use the whole content (no [[section]] parsing) to avoid failures when
        # authors forget to include section tags. This mirrors the storyboard
        # template loading behavior which treats the whole file as one Template.
        content = path.read_text(encoding="utf-8")
        _VIDEO_TEMPLATES["default"] = Template(content)
    return _VIDEO_TEMPLATES


class GeminiService(BaseService):
    """Wrapper around Google Gemini for storyboard and video prompt generation."""

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        self.model: Optional[genai.GenerativeModel] = None
        self.api_key: Optional[str] = None
        self.model_name: Optional[str] = None
        self.generation_config: Dict[str, Any] = {
            "temperature": 0.9,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        self.safety_settings: List[Dict[str, Any]] = []
        self._client_ready = False
        self._setup_client()

    def generate_prompt_text(
        self,
        prompt: str,
        *,
        generation_config: Optional[Dict[str, Any]] = None,
        safety_settings: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: int = 180,
    ) -> str:
        """Generate free-form content using Gemini with the given prompt."""

        if not prompt or not prompt.strip():
            raise ValidationException("prompt 不能为空", field="prompt")

        call_kwargs: Dict[str, Any] = {}
        if generation_config:
            call_kwargs["generation_config"] = generation_config
        if safety_settings:
            call_kwargs["safety_settings"] = safety_settings

        self._log_request("generate_content", method="POST", mode="console")
        self._log_debug("console_prompt", prompt)

        start_time = time.perf_counter()
        try:
            with self._proxy_context():
                self._prepare_model_for_request()
                response = self.model.generate_content(
                    prompt,
                    request_options={"timeout": timeout_seconds},
                    **call_kwargs,
                )
        except Exception as exc:
            self._log_error(exc, {"prompt_length": len(prompt)})
            if isinstance(exc, (APIException, ValidationException, ConfigurationException)):
                raise
            raise APIException(
                message=f"Failed to generate Gemini completion: {exc}",
                service_name=self.service_name,
            ) from exc

        duration_ms = (time.perf_counter() - start_time) * 1000

        response_text = getattr(response, "text", None)
        self._log_debug("console_response", response_text or "<empty>")

        if not response_text:
            raise APIException(
                message="Empty response from Gemini",
                service_name=self.service_name,
            )

        self._log_response("generate_content", 200, duration_ms)
        return response_text

    def _log_debug(self, label: str, content: Optional[str]) -> None:
        """Log debug information with optional truncation."""

        if not self.logger.isEnabledFor(logging.DEBUG):
            return
        if content is None:
            snippet = "<None>"
        else:
            text = content.strip()
            if len(text) > _DEBUG_MAX_CHARS:
                snippet = f"{text[:_DEBUG_MAX_CHARS]}... [truncated {len(text) - _DEBUG_MAX_CHARS} chars]"
            else:
                snippet = text
        self.logger.debug("[%s] %s", self.service_name, f"{label}: {snippet}")

    @contextmanager
    def _proxy_context(self):
        proxies = get_proxy_for_service(self.service_name)
        if not proxies:
            yield None
            return

        previous: Dict[str, Optional[str]] = {}
        try:
            for scheme, keys in {
                "http": ("HTTP_PROXY", "http_proxy"),
                "https": ("HTTPS_PROXY", "https_proxy"),
            }.items():
                proxy_url = proxies.get(scheme)
                if not proxy_url:
                    continue
                for key in keys:
                    previous[key] = os.environ.get(key)
                    os.environ[key] = proxy_url
            yield proxies
        finally:
            for key, old in previous.items():
                if old is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old

    def _configure_model(self, api_key: Optional[str]) -> None:
        if not api_key:
            raise ConfigurationException("Gemini API key is not configured", service_name=self.service_name)
        if not self.model_name:
            raise ConfigurationException("Gemini model name is not configured", service_name=self.service_name)

        genai.configure(api_key=api_key)
        model_kwargs: Dict[str, Any] = {"model_name": self.model_name}
        if self.generation_config:
            model_kwargs["generation_config"] = self.generation_config
        if self.safety_settings:
            model_kwargs["safety_settings"] = self.safety_settings

        self.model = genai.GenerativeModel(**model_kwargs)
        self._client_ready = True

    def _prepare_model_for_request(self) -> None:
        credential = None
        try:
            credential = GeminiCredentialPool.acquire()
        except Exception as exc:  # pragma: no cover - pool fallback
            credential = None
            self.logger.debug("Gemini credential pool unavailable, fallback to default key: %s", exc)

        api_key = None
        if credential and getattr(credential, "credential_key", None):
            api_key = credential.credential_key
        else:
            api_key = self.api_key

        self._configure_model(api_key)

    @property
    def service_name(self) -> str:
        return "gemini"

    def _validate_configuration(self) -> None:
        if not self.api_key:
            raise ConfigurationException("Gemini API key is not configured", service_name=self.service_name)
        if not self.model_name:
            raise ConfigurationException("Gemini model name is not configured", service_name=self.service_name)

    def _resolve_api_key(self) -> Optional[str]:
        if getattr(self.settings, "resolved_gemini_api_key", None):
            return self.settings.resolved_gemini_api_key
        if self.settings.GOOGLE_GEMINI_API_KEY:
            return self.settings.GOOGLE_GEMINI_API_KEY
        if self.settings.GEMINI_API_KEYS:
            for candidate in self.settings.GEMINI_API_KEYS.split(","):
                candidate = candidate.strip()
                if candidate:
                    return candidate
        return None

    def _resolve_model_name(self) -> Optional[str]:
        candidates = [
            getattr(self.settings, "resolved_gemini_model", None),
            self.settings.GOOGLE_GEMINI_MODEL,
            self.settings.GEMINI_MODEL_ID,
        ]
        for candidate in candidates:
            if candidate:
                return candidate
        return None

    def _setup_client(self) -> None:
        # Keep existing resolution as fallback, but do not finalise api_key here.
        # The live api_key will be acquired per-request from the credential pool
        # when credentials are available in DB. We still resolve a configured
        # key from settings as a fallback for environments without DB-managed keys.
        self.api_key = self._resolve_api_key()
        self.model_name = self._resolve_model_name()
        self._validate_configuration()

        try:
            with self._proxy_context():
                self._configure_model(self.api_key)
        except ConfigurationException:
            self._client_ready = False
            raise
        except Exception as exc:  # pragma: no cover - defensive configuration guard
            self._client_ready = False
            raise ConfigurationException(
                f"Failed to initialise Gemini client: {exc}",
                service_name=self.service_name,
            ) from exc

    def generate_storyboard(
        self,
        video_content: str,
        reference_video: Optional[str],
        num_scenes: int,
        language: str,
        word_count_strategy: Optional[str] = None,
        prompt_example: Optional[str] = None,
        trigger_words: Optional[str] = None,
        channel_identity: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate storyboard JSON via Gemini."""

        if not video_content or not video_content.strip():
            raise ValidationException("video_content cannot be empty", field="video_content")

        max_scenes = getattr(self.settings, "MAX_SCENES_PER_TASK", None)
        if max_scenes is None:
            fallback = getattr(self.settings, "DEFAULT_SCENES_COUNT", None)
            if isinstance(fallback, (int, float)) and fallback > 0:
                max_scenes = max(0, int(fallback))
            else:
                max_scenes = 1000
        elif not isinstance(max_scenes, (int, float)):
            raise ConfigurationException(
                "MAX_SCENES_PER_TASK 必须是正整数",
                service_name=self.service_name,
            )
        else:
            max_scenes = int(max(0, max_scenes))

        try:
            requested_scenes = int(num_scenes)
        except (TypeError, ValueError):
            requested_scenes = 0

        if requested_scenes < 0:
            raise ValidationException(
                "num_scenes must be non-negative",
                field="num_scenes",
            )

        if requested_scenes > max_scenes:
            raise ValidationException(
                f"num_scenes must be between 0 and {max_scenes}",
                field="num_scenes",
            )

        expected_count = requested_scenes if requested_scenes > 0 else 0

        prompt = self._build_storyboard_prompt(
            video_content=video_content,
            reference_video=reference_video,
            num_scenes=requested_scenes,
            language=language,
            word_count_strategy=word_count_strategy,
            prompt_example=prompt_example,
            trigger_words=trigger_words,
            channel_identity=channel_identity,
        )

        try:
            self._log_request("generate_content", method="POST", num_scenes=requested_scenes)

            with self._proxy_context():
                self._prepare_model_for_request()
                self._log_debug("storyboard_prompt", prompt)
                response = self.model.generate_content(
                    prompt,
                    request_options={"timeout": 180},
                )

            response_text = getattr(response, "text", None)
            self._log_debug("storyboard_response", response_text or "<empty>")

            if not response_text:
                raise APIException(
                    message="Empty response from Gemini",
                    service_name=self.service_name,
                )

            scenes = self._parse_storyboard_response(response_text, expected_count)
            self.logger.info("Successfully generated %s scenes", len(scenes))
            return scenes

        except Exception as exc:
            self._log_error(
                exc,
                {
                    "video_content_length": len(video_content),
                    "num_scenes": requested_scenes,
                },
            )

            if isinstance(exc, (APIException, ValidationException, ConfigurationException)):
                raise

            raise APIException(
                message=f"Failed to generate storyboard: {exc}",
                service_name=self.service_name,
            ) from exc

    def _build_storyboard_prompt(
        self,
        video_content: str,
        reference_video: Optional[str],
        num_scenes: int,
        language: str,
        word_count_strategy: Optional[str] = None,
        prompt_example: Optional[str] = None,
        trigger_words: Optional[str] = None,
        channel_identity: Optional[str] = None,
    ) -> str:
        """Render the storyboard prompt using the template file."""

        word_count_text = (
            word_count_strategy or "每个分镜旁白字数在2到28字之间动态变化根据内容重要性和情感节奏灵活调节"
        ).strip()
        prompt_example_text = (prompt_example or "未提供").strip()
        trigger_words_text = (trigger_words or "未提供").strip()
        channel_identity_text = (channel_identity or "人物故事").strip()
        reference_text = (reference_video or "未提供").strip()
        video_content_text = (video_content or "未提供").strip()

        formatted_video_content = indent(video_content_text, "  ") if video_content_text else "  未提供"
        formatted_prompt_example = indent(prompt_example_text, "  ") if prompt_example_text else "  未提供"
        formatted_trigger_words = indent(trigger_words_text, "  ") if trigger_words_text else "  未提供"
        formatted_word_count = indent(word_count_text, "    ") if word_count_text else "    未提供"

        template = _load_storyboard_template()
        rendered = template.substitute(
            reference_text=reference_text,
            formatted_video_content=formatted_video_content,
            num_scenes=num_scenes,
            language=language,
            formatted_word_count=formatted_word_count,
            formatted_prompt_example=formatted_prompt_example,
            formatted_trigger_words=formatted_trigger_words,
            channel_identity_text=channel_identity_text,
        )
        return rendered.strip()

    def _parse_storyboard_response(self, response_text: str, expected_count: int) -> List[Dict[str, Any]]:
        """Parse Gemini response and extract JSON array."""

        candidates: List[str] = []

        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)
        if json_match:
            candidates.append(json_match.group(1))
        else:
            json_match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", response_text)
            if json_match:
                candidates.append(json_match.group(0))
            else:
                stripped = response_text.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    candidates.append(stripped)
                first_brace = response_text.find("{")
                last_brace = response_text.rfind("}")
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    candidates.append(response_text[first_brace : last_brace + 1])

        parsed: Optional[Any] = None
        json_text: Optional[str] = None
        last_error: Optional[json.JSONDecodeError] = None

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                json_text = candidate
                break
            except json.JSONDecodeError as exc:
                last_error = exc
                continue

        if parsed is None:
            self._record_invalid_response(response_text)
            if last_error is not None and candidates:
                raise ValidationException(
                    f"Invalid JSON in response: {last_error}",
                    json_text=candidates[-1][:200],
                )
            raise ValidationException(
                "Could not extract JSON from response",
                response_preview=response_text[:200],
            )

        if isinstance(parsed, dict):
            if "分镜" in parsed and isinstance(parsed["分镜"], list):
                scenes = parsed.get("分镜", [])
            elif "scenes" in parsed and isinstance(parsed["scenes"], list):
                scenes = parsed.get("scenes", [])
            else:
                self._record_invalid_response(response_text)
                raise ValidationException("Response JSON object does not contain '分镜' or 'scenes' array")
        elif isinstance(parsed, list):
            scenes = parsed
        else:
            self._record_invalid_response(response_text)
            raise ValidationException("Response JSON must be an array or contain a '分镜' array")

        validated_scenes: List[Dict[str, Any]] = []
        for idx, scene in enumerate(scenes, 1):
            if not isinstance(scene, dict):
                self.logger.warning("Scene %s is not a dictionary, skipping", idx)
                continue

            scene_number_raw = scene.get("分镜序号") or scene.get("scene_number") or scene.get("序号")
            try:
                scene_number = int(str(scene_number_raw).strip()) if scene_number_raw is not None else idx
            except (ValueError, TypeError):
                scene_number = idx

            narration_text = (scene.get("旁白内容") or scene.get("narration") or "").strip()
            image_prompt_text = (
                scene.get("图片提示词")
                or scene.get("image_prompt")
                or scene.get("imagePrompt")
                or ""
            ).strip()
            word_count_raw = (
                scene.get("旁白字数")
                or scene.get("narration_word_count")
                or scene.get("narrationWordCount")
            )

            def _normalize_word_count(raw_value: Any, narration: str) -> int:
                if isinstance(raw_value, (int, float)):
                    return int(raw_value)
                if isinstance(raw_value, str):
                    digits = re.findall(r"\d+", raw_value)
                    if digits:
                        try:
                            return int(digits[0])
                        except ValueError:
                            pass
                return len(narration)

            narration_word_count = _normalize_word_count(word_count_raw, narration_text)

            validated_scene = {
                "scene_number": scene_number,
                "narration": narration_text,
                "narration_word_count": narration_word_count,
                "image_prompt": image_prompt_text,
            }

            if not validated_scene["narration"]:
                self.logger.warning("Scene %s has empty narration, skipping", idx)
                continue

            if not validated_scene["image_prompt"]:
                self.logger.warning("Scene %s has empty image_prompt, skipping", idx)
                continue

            validated_scenes.append(validated_scene)

        if not validated_scenes:
            raise ValidationException("No valid scenes in response")

        if expected_count and len(validated_scenes) != expected_count:
            self.logger.warning(
                "Storyboard scene count mismatch: expected %s, got %s",
                expected_count,
                len(validated_scenes),
            )

        self.logger.info(
            "Parsed %s valid scenes (expected %s)",
            len(validated_scenes),
            expected_count,
        )

        return validated_scenes

    def _record_invalid_response(self, response_text: str) -> None:
        """Persist invalid Gemini responses for debugging."""

        try:
            _INVALID_RESPONSE_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _INVALID_RESPONSE_LOG.open("a", encoding="utf-8") as fp:
                fp.write(f"{aware_now().isoformat()}\n")
                fp.write(response_text)
                if not response_text.endswith("\n"):
                    fp.write("\n")
                fp.write("-" * 80 + "\n")
        except Exception as exc:
            self.logger.warning("Failed to record invalid Gemini response: %s", exc)

    def generate_video_prompt(
        self,
        target: str,
        narration: str,
        scene_seq: int,
        image_prompt: Optional[str] = None,
        image_url: Optional[str] = None,
        storyboard_context: Optional[str] = None,
        duration_hint: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate a motion prompt for downstream video providers."""

        if not narration or not narration.strip():
            raise ValidationException("narration cannot be empty", field="narration")

        self._log_request(
            "generate_video_prompt",
            method="POST",
            target=target,
            scene_seq=scene_seq,
        )

        prompt_text = self._build_video_prompt_prompt(
            target=target,
            narration=narration,
            scene_seq=scene_seq,
            image_prompt=image_prompt,
            image_url=image_url,
            storyboard_context=storyboard_context,
            duration_hint=duration_hint,
        )

        self._log_debug("video_prompt_request", prompt_text)

        try:
            with self._proxy_context():
                self._prepare_model_for_request()
                response = self.model.generate_content(
                    prompt_text,
                    request_options={"timeout": 60},
                )
        except Exception as exc:
            self._log_error(exc, {"feature": "video_prompt", "target": target})
            if isinstance(exc, (ConfigurationException, APIException, ValidationException)):
                raise
            raise APIException(
                message=f"Failed to generate video prompt: {exc}",
                service_name=self.service_name,
            ) from exc

        raw_text = getattr(response, "text", "") or ""
        self._log_debug("video_prompt_response", raw_text or "<empty>")
        if not raw_text.strip():
            raise APIException(
                message="Empty response from Gemini",
                service_name=self.service_name,
            )

        prompt = self._parse_video_prompt_response(raw_text)
        if not prompt:
            raise ValidationException(
                "Failed to locate <prompt_en> tag in Gemini response",
                response_preview=raw_text[:200],
            )

        return {"prompt": prompt, "raw_text": raw_text}

    def _build_video_prompt_prompt(
        self,
        target: str,
        narration: str,
        scene_seq: int,
        image_prompt: Optional[str],
        image_url: Optional[str],
        storyboard_context: Optional[str],
        duration_hint: Optional[float],
    ) -> str:
        normalized_target = (target or "").strip().lower()
        templates = _load_video_templates()
        template = templates.get("fal" if normalized_target == "fal" else "default")
        if template is None:
            template = templates.get("default")
        if template is None:
            raise ConfigurationException(
                "Video prompt template is missing required sections",
                service_name=self.service_name,
            )

        context = (storyboard_context or "").strip()
        if len(context) > 6000:
            context = context[:6000] + "\n...[truncated]"

        context_block = context or "(未提供，可结合旁白与图片提示词补全)"

        def _sanitize_backticks(value: str) -> str:
            return value.replace("`", "'")

        narration_block = _sanitize_backticks((narration or "").strip() or "(未提供)")
        image_prompt_block = _sanitize_backticks((image_prompt or "").strip() or "(未提供)")
        context_block = _sanitize_backticks(context_block)
        image_url_block = image_url or "[提供首帧图片，作为视频动态生成的起始画面]"
        scene_seq_block = scene_seq
        if duration_hint and duration_hint > 0:
            duration_block = f"约 {duration_hint:.0f} 秒"
        else:
            duration_block = "3-12 秒范围内"

        rendered = template.substitute(
            narration=narration_block,
            scene_seq=scene_seq_block,
            image_prompt=image_prompt_block,
            image_url=image_url_block,
            storyboard_context=context_block,
            duration_hint=duration_block,
        )
        return dedent(rendered).strip()

    def _parse_video_prompt_response(self, response_text: str) -> Optional[str]:
        match = re.search(r"<prompt_en>([\s\S]*?)</prompt_en>", response_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return response_text.strip()
