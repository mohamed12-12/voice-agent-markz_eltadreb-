import asyncio
import os
import platform
import warnings

from dotenv import load_dotenv

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
from livekit.agents import AgentSession, JobContext, RoomInputOptions, WorkerOptions
from livekit.plugins import google

from prompt import PROMPT
from tools import CarimAgent


base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))


def _get_env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


async def entrypoint(ctx: JobContext):
    try:
        print(f"--- Connecting to Room: {ctx.room.name} ---")
        await ctx.connect()

        model = google.realtime.RealtimeModel(
            model=os.environ.get(
                "GEMINI_MODEL", "gemini-live-2.5-flash-native-audio"
            ),
            api_key=os.environ.get("GOOGLE_API_KEY"),
            instructions=PROMPT,
            voice=os.environ.get("GEMINI_VOICE", "Orus"),
            language=os.environ.get("GEMINI_LANGUAGE", "ar-EG"),
            temperature=_get_env_float("GEMINI_TEMPERATURE", 0.45),
            max_output_tokens=_get_env_int("GEMINI_MAX_OUTPUT_TOKENS", 180),
            top_p=_get_env_float("GEMINI_TOP_P", 0.8),
            candidate_count=1,
        )

        agent = CarimAgent(instructions=PROMPT)
        session = AgentSession(
            llm=model,
            min_endpointing_delay=_get_env_float("MIN_ENDPOINTING_DELAY", 0.2),
            max_endpointing_delay=_get_env_float("MAX_ENDPOINTING_DELAY", 0.9),
            allow_interruptions=True,
            min_interruption_duration=_get_env_float("MIN_INTERRUPTION_DURATION", 0.25),
            resume_false_interruption=True,
            user_away_timeout=_get_env_float("USER_AWAY_TIMEOUT", 8.0),
            aec_warmup_duration=_get_env_float("AEC_WARMUP_DURATION", 1.0),
        )

        print("Starting AgentSession...")
        await session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                close_on_disconnect=False,
                pre_connect_audio=True,
            ),
        )

        print("Agent is live. Waiting for user input...")
        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)

    except Exception as e:
        import traceback

        print(f"CRITICAL SESSION ERROR: {e}")
        traceback.print_exc()
    finally:
        print(f"Session ended for room: {ctx.room.name}")


if __name__ == "__main__":
    print("Starting LiveKit Worker with Gemini Live...")
    os.environ["LIVEKIT_HTTP_PORT"] = "8085"
    agents.cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            ws_url=os.environ.get("LIVEKIT_URL"),
            api_key=os.environ.get("LIVEKIT_API_KEY"),
            api_secret=os.environ.get("LIVEKIT_API_SECRET"),
        )
    )
