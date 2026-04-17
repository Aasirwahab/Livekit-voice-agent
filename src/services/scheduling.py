"""General appointment scheduling agent.

For generic bookings that aren't healthcare or real estate specific —
e.g. sales consultations, service appointments, meetings.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Annotated

from pydantic import Field

from livekit.agents import Agent, RunContext, function_tool

from .user_data import UserData

logger = logging.getLogger("scheduling-agent")


# Simple fake availability. Replace with Cal.com / Google Calendar / Outlook API.
def _fake_slots(days_ahead: int = 7) -> list[datetime]:
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    slots = []
    for day in range(1, days_ahead + 1):
        base = now + timedelta(days=day)
        for hour in (10, 14, 16):
            slots.append(base.replace(hour=hour))
    return slots


class SchedulingAgent(Agent):
    """Specialized agent for general-purpose appointment scheduling."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a scheduling assistant for general appointments like "
                "consultations, meetings, or service calls. Speak naturally for "
                "a voice call. Keep replies concise. "
                "\n\n"
                "Flow: "
                "1. Ask what the appointment is for. "
                "2. Use list_open_slots to offer times. "
                "3. Book with book_appointment. "
                "\n\n"
                "When saying times, speak naturally like 'Monday at two in the afternoon'. "
                "If the caller wants a different service, use return_to_main_menu."
            ),
        )

    async def on_enter(self) -> None:
        await self.session.say(
            "I can help you book an appointment. What's the appointment for, "
            "and do you have a preferred day?"
        )

    @function_tool
    async def list_open_slots(
        self,
        ctx: RunContext[UserData],
        days_ahead: Annotated[
            int, Field(ge=1, le=30, description="How many days out to search.")
        ] = 7,
    ) -> str:
        """List available appointment slots."""
        slots = _fake_slots(days_ahead)
        if not slots:
            return "No slots available in that window."
        lines = []
        for s in slots[:6]:
            lines.append(s.strftime("%A %B %d at %I:%M %p").replace(" 0", " "))
        return "Open times: " + "; ".join(lines) + ". Which works?"

    @function_tool
    async def book_appointment(
        self,
        ctx: RunContext[UserData],
        appointment_time: Annotated[
            str, Field(description="Appointment time in ISO format (YYYY-MM-DDTHH:MM).")
        ],
        purpose: str,
        attendee_name: str,
    ) -> str:
        """Book the appointment.

        Args:
            appointment_time: ISO-format datetime string.
            purpose: What the appointment is for.
            attendee_name: Name of the person attending.
        """
        try:
            when = datetime.fromisoformat(appointment_time)
        except ValueError:
            return "That time format was not understood."

        ctx.userdata.general_appointments.append(
            {
                "time": when,
                "purpose": purpose,
                "attendee": attendee_name,
            }
        )
        ctx.userdata.profile.name = ctx.userdata.profile.name or attendee_name

        readable = when.strftime("%A %B %d at %I:%M %p").replace(" 0", " ")
        return f"Booked. {attendee_name} for {purpose} on {readable}. Anything else?"

    @function_tool
    async def return_to_main_menu(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Return to the main menu."""
        from .router import RouterAgent

        ctx.userdata.last_service = "scheduling"
        return RouterAgent(), "Taking you back to the main menu."
