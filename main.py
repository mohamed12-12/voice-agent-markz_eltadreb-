import os
import asyncio
import warnings
from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic._internal._fields")

from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, AgentSession, voice
from livekit.plugins import google

from prompt import PROMPT

load_dotenv()


async def entrypoint(ctx: JobContext):
    try:
        print("🔌 Connecting to room...")
        await ctx.connect()  # ✅ FIXED

        print("🤖 Initializing Gemini Realtime model...")
        llm = google.beta.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025",
            voice="Aoede",
            temperature=0.8,
        )

        print("🧠 Creating agent...")
        agent = voice.Agent(
            instructions=PROMPT,
            llm=llm
        )

        print("🎙️ Starting session...")
        session = AgentSession(
            llm=llm,
            vad=None,
            turn_detection="realtime_llm"
        )

        await session.start(agent, room=ctx.room)

        print("✅ Agent running...")

        while ctx.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)

    except Exception as e:
        import traceback
        print("❌ ERROR:", e)
        traceback.print_exc()

    finally:
        print("🔌 Disconnected")


if __name__ == "__main__":
    print("🚀 Starting LiveKit Worker...")
    agents.cli.run_app(
        WorkerOptions(entrypoint_fnc=entrypoint)
    )