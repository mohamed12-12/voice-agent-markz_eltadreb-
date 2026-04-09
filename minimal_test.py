import os
import asyncio
import platform
from dotenv import load_dotenv

# --- CRITICAL FIX: Windows WMI Timeout Monkeypatch ---
if platform.system() == "Windows":
    _original_uname = platform.uname
    def _mock_uname():
        from collections import namedtuple
        UnameResult = namedtuple("uname_result", "system node release version machine processor")
        node_name = os.environ.get("COMPUTERNAME", "Windows-Host")
        return UnameResult("Windows", node_name, "10", "10.0.0", "AMD64", "Intel64 Family 6 Model 158 Stepping 10, GenuineIntel")
    platform.uname = _mock_uname

from livekit.agents import JobContext, WorkerOptions, cli, voice
from livekit.plugins import google

load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect()
    print("🤖 Initializing Minimal Gemini Realtime model...")
    model = google.beta.realtime.RealtimeModel(
        model="gemini-2.0-flash-exp",
        voice="Puck",
        temperature=0.6,
    )
    
    print("🧠 Creating agent (no tools)...")
    agent = voice.Agent(
        instructions="You are a helpful assistant. Just say hello and ask how you can help.",
        llm=model
    )

    print("🎙️ Starting session...")
    session = voice.AgentSession(
        llm=model,
        vad=None,
        turn_detection="realtime_llm"
    )

    await session.start(agent, room=ctx.room)
    print("✅ Minimal Test Running! Speak to the agent.")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
