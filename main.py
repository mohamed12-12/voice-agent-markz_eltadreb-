import asyncio
import logging
import os
import platform
import warnings
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from google.genai import types as google_types

# Avoid the Windows WMI timeout path that can slow or break startup on some machines.
if platform.system() == "Windows":
    from collections import namedtuple

    def _mock_uname():
        uname_result = namedtuple(
            "uname_result", "system node release version machine processor"
        )
        node_name = os.environ.get("COMPUTERNAME", "Windows-Host")
        return uname_result(
            "Windows",
            node_name,
            "10",
            "10.0.0",
            "AMD64",
            "Intel64 Family 6 Model 158 Stepping 10, GenuineIntel",
        )

    platform.uname = _mock_uname

warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic._internal._fields"
)

from livekit import agents, rtc
from livekit.agents import (
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
)
from livekit.plugins import google

from prompt import PROMPT
from tools import CarimAgent


# -----------------------------------------------------------------------------
# App bootstrap
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("carim-agent")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _get_env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid float for %s=%r. Falling back to %s", name, value, default)
        return default


def _get_env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid int for %s=%r. Falling back to %s", name, value, default)
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_env_str(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.environ.get(name)
    if value is None:
        return default
    stripped = value.strip()
    if stripped == "":
        return default
    return stripped


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _get_env_sensitivity(
    name: str,
    default: str,
    enum_type,
    prefix: str,
):
    value = os.environ.get(name, default).strip().lower()
    normalized = f"{prefix}_{value.upper()}"
    if hasattr(enum_type, normalized):
        return getattr(enum_type, normalized)

    logger.warning(
        "Invalid sensitivity for %s=%r. Falling back to %s",
        name,
        value,
        default,
    )
    fallback = f"{prefix}_{default.upper()}"
    return getattr(enum_type, fallback)


# -----------------------------------------------------------------------------
# Config
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class GeminiConfig:
    model: str
    api_key: Optional[str]
    voice: str
    language: str
    temperature: float
    max_output_tokens: int
    top_p: float
    candidate_count: int
    vertexai: bool
    project: Optional[str]
    location: Optional[str]
    vad_silence_duration_ms: int
    vad_prefix_padding_ms: int
    start_of_speech_sensitivity: google_types.StartSensitivity
    end_of_speech_sensitivity: google_types.EndSensitivity


@dataclass(frozen=True)
class SessionConfig:
    min_endpointing_delay: float
    max_endpointing_delay: float
    allow_interruptions: bool
    min_interruption_duration: float
    min_interruption_words: int
    resume_false_interruption: bool
    false_interruption_timeout: float
    user_away_timeout: float
    aec_warmup_duration: float
    preemptive_generation: bool
    min_consecutive_speech_delay: float


def build_gemini_config() -> GeminiConfig:
    use_vertexai = _get_env_bool("GEMINI_USE_VERTEXAI", False)

    default_model = (
        "gemini-live-2.5-flash-native-audio"
        if use_vertexai
        else "gemini-2.0-flash-exp"
    )

    # Tuned for:
    # - short voice responses
    # - strict prompt adherence
    # - lower hallucination risk
    return GeminiConfig(
        model=_get_env_str("GEMINI_MODEL", default_model),
        api_key=_get_env_str("GOOGLE_API_KEY"),
        voice=_get_env_str("GEMINI_VOICE", "Orus"),
        language=_get_env_str("GEMINI_LANGUAGE", "ar-EG"),
        temperature=_get_env_float("GEMINI_TEMPERATURE", 0.28),
        max_output_tokens=_get_env_int("GEMINI_MAX_OUTPUT_TOKENS", 520),
        top_p=_get_env_float("GEMINI_TOP_P", 0.75),
        candidate_count=1,
        vertexai=use_vertexai,
        project=_get_env_str("GOOGLE_CLOUD_PROJECT"),
        location=_get_env_str("GOOGLE_CLOUD_LOCATION"),
        vad_silence_duration_ms=_get_env_int("GEMINI_VAD_SILENCE_MS", 2600),
        vad_prefix_padding_ms=_get_env_int("GEMINI_VAD_PREFIX_PADDING_MS", 1000),
        start_of_speech_sensitivity=_get_env_sensitivity(
            "GEMINI_START_OF_SPEECH_SENSITIVITY",
            "high",
            google_types.StartSensitivity,
            "START_SENSITIVITY",
        ),
        end_of_speech_sensitivity=_get_env_sensitivity(
            "GEMINI_END_OF_SPEECH_SENSITIVITY",
            "low",
            google_types.EndSensitivity,
            "END_SENSITIVITY",
        ),
    )


def build_session_config() -> SessionConfig:
    # Tuned for voice assistant behavior:
    # - waits for the user to finish their thought
    # - avoids replying in the middle of a question
    # - reduces false cutoffs caused by noise or echo
    # Gemini Realtime uses server-side turn detection, so interruptions
    # must remain enabled at the session level in this SDK.
    return SessionConfig(
        min_endpointing_delay=_get_env_float("MIN_ENDPOINTING_DELAY", 1.6),
        max_endpointing_delay=_get_env_float("MAX_ENDPOINTING_DELAY", 3.4),
        allow_interruptions=_get_env_bool("ALLOW_INTERRUPTIONS", True),
        min_interruption_duration=_get_env_float("MIN_INTERRUPTION_DURATION", 1.2),
        min_interruption_words=_get_env_int("MIN_INTERRUPTION_WORDS", 1),
        resume_false_interruption=_get_env_bool("RESUME_FALSE_INTERRUPTION", True),
        false_interruption_timeout=_get_env_float("FALSE_INTERRUPTION_TIMEOUT", 3.2),
        user_away_timeout=_get_env_float("USER_AWAY_TIMEOUT", 12.0),
        aec_warmup_duration=_get_env_float("AEC_WARMUP_DURATION", 1.5),
        preemptive_generation=_get_env_bool("PREEMPTIVE_GENERATION", False),
        min_consecutive_speech_delay=_get_env_float("MIN_CONSECUTIVE_SPEECH_DELAY", 0.45),
    )


def create_realtime_model(config: GeminiConfig) -> google.realtime.RealtimeModel:
    if not config.vertexai and not config.api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is required when GEMINI_USE_VERTEXAI is disabled."
        )

    if config.vertexai:
        if not config.project:
            raise RuntimeError(
                "GOOGLE_CLOUD_PROJECT is required when GEMINI_USE_VERTEXAI is enabled."
            )
        if not config.location:
            raise RuntimeError(
                "GOOGLE_CLOUD_LOCATION is required when GEMINI_USE_VERTEXAI is enabled."
            )

    logger.info(
        "Initializing Gemini model | model=%s | voice=%s | language=%s | vertexai=%s",
        config.model,
        config.voice,
        config.language,
        config.vertexai,
    )
    logger.info(
        "Turn detection tuning | vad_silence_ms=%s | prefix_padding_ms=%s | start_sensitivity=%s | end_sensitivity=%s | max_output_tokens=%s",
        config.vad_silence_duration_ms,
        config.vad_prefix_padding_ms,
        config.start_of_speech_sensitivity.name,
        config.end_of_speech_sensitivity.name,
        config.max_output_tokens,
    )

    return google.realtime.RealtimeModel(
        model=config.model,
        api_key=config.api_key,
        instructions=PROMPT,
        voice=config.voice,
        language=config.language,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        top_p=config.top_p,
        candidate_count=config.candidate_count,
        vertexai=config.vertexai,
        project=config.project,
        location=config.location,
        realtime_input_config=google_types.RealtimeInputConfig(
            automatic_activity_detection=google_types.AutomaticActivityDetection(
                start_of_speech_sensitivity=config.start_of_speech_sensitivity,
                end_of_speech_sensitivity=config.end_of_speech_sensitivity,
                prefix_padding_ms=config.vad_prefix_padding_ms,
                silence_duration_ms=config.vad_silence_duration_ms,
            ),
            turn_coverage=google_types.TurnCoverage.TURN_INCLUDES_ALL_INPUT,
        ),
    )


def create_agent_session(model: google.realtime.RealtimeModel, config: SessionConfig) -> AgentSession:
    allow_interruptions = config.allow_interruptions
    if getattr(model.capabilities, "turn_detection", False) and not allow_interruptions:
        logger.warning(
            "ALLOW_INTERRUPTIONS=false is not supported with Gemini Realtime server-side turn detection. "
            "Forcing allow_interruptions=True and relying on stricter interruption timing instead."
        )
        allow_interruptions = True

    turn_handling = {
        "endpointing": {
            "min_delay": config.min_endpointing_delay,
            "max_delay": config.max_endpointing_delay,
        },
        "interruption": {
            "enabled": allow_interruptions,
            "discard_audio_if_uninterruptible": True,
            "min_duration": config.min_interruption_duration,
            "min_words": config.min_interruption_words,
            "resume_false_interruption": config.resume_false_interruption,
            "false_interruption_timeout": config.false_interruption_timeout,
        },
    }

    logger.info(
        "Session tuning | min_endpoint=%s | max_endpoint=%s | allow_interruptions=%s | min_interrupt=%s | min_interrupt_words=%s | false_interrupt_timeout=%s | min_consecutive_speech_delay=%s",
        config.min_endpointing_delay,
        config.max_endpointing_delay,
        allow_interruptions,
        config.min_interruption_duration,
        config.min_interruption_words,
        config.false_interruption_timeout,
        config.min_consecutive_speech_delay,
    )
    return AgentSession(
        llm=model,
        turn_handling=turn_handling,
        user_away_timeout=config.user_away_timeout,
        aec_warmup_duration=config.aec_warmup_duration,
        preemptive_generation=config.preemptive_generation,
        min_consecutive_speech_delay=config.min_consecutive_speech_delay,
    )


# -----------------------------------------------------------------------------
# LiveKit Entrypoint
# -----------------------------------------------------------------------------

async def entrypoint(ctx: JobContext):
    try:
        logger.info("Connecting to room: %s", ctx.room.name)
        await ctx.connect()

        gemini_config = build_gemini_config()
        session_config = build_session_config()

        model = create_realtime_model(gemini_config)
        agent = CarimAgent(instructions=PROMPT)
        session = create_agent_session(model, session_config)

        logger.info("Starting AgentSession")
        await session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                audio_enabled=True,
                participant_identity=os.environ.get("CLIENT_PARTICIPANT_IDENTITY", "Client-Guest"),
                close_on_disconnect=False,
                pre_connect_audio=True,
                pre_connect_audio_timeout=_get_env_float("PRE_CONNECT_AUDIO_TIMEOUT", 10.0),
            ),
        )

        logger.info("Agent is live and waiting for user input")
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)

    except Exception:
        logger.exception("Critical session error")
    finally:
        logger.info("Session ended for room: %s", getattr(ctx.room, "name", "unknown"))


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        logger.info("Starting LiveKit Worker with Gemini Live")

        os.environ["LIVEKIT_HTTP_PORT"] = os.environ.get("LIVEKIT_HTTP_PORT", "8085")

        worker_options = WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=os.environ.get("AGENT_NAME", "carim-agent"),
            ws_url=_get_required_env("LIVEKIT_URL"),
            api_key=_get_required_env("LIVEKIT_API_KEY"),
            api_secret=_get_required_env("LIVEKIT_API_SECRET"),
        )

        agents.cli.run_app(worker_options)

    except Exception:
        logger.exception("Failed to start worker")
        raise
