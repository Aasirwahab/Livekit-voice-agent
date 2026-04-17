"""Unified multi-service voice agent entrypoint.

This is a standalone entrypoint that runs the RouterAgent + specialist
agents (real estate, healthcare, orders, scheduling). It does NOT replace
agent.py - it is a separate agent_name so you can run both side by side.

Run:
    uv run python src/unified_agent.py console
    uv run python src/unified_agent.py dev
    uv run python src/unified_agent.py start
"""

import logging

from dotenv import load_dotenv

from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    room_io,
)
from livekit.plugins import ai_coustics, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from services import RouterAgent, UserData

logger = logging.getLogger("unified-agent")

load_dotenv(".env.local")

AGENT_MODEL = "openai/gpt-4o-mini"

server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="unified-agent")
async def unified_agent(ctx: JobContext):
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    session = AgentSession[UserData](
        userdata=UserData(),
        stt=inference.STT(model="deepgram/nova-3", language="en"),
        llm=inference.LLM(model=AGENT_MODEL),
        tts=inference.TTS(model="cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
        vad=ctx.proc.userdata["vad"],
        turn_handling={
            "turn_detection": MultilingualModel(),
            "endpointing": {"min_delay": 0.3},
            "preemptive_generation": {"preemptive_tts": True},
        },
    )

    await session.start(
        agent=RouterAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.SPARROW_S
                ),
            ),
        ),
    )

    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
