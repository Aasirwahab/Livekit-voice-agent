"""Healthcare booking agent.

Handles:
- Doctor lookup
- Appointment scheduling
- Insurance verification (simplified)
- Reason-for-visit capture
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any

from pydantic import Field

from livekit.agents import Agent, RunContext, function_tool

from .user_data import MedicalAppointment, UserData

logger = logging.getLogger("healthcare-agent")


VALID_INSURANCES = ["Anthem", "Aetna", "EmblemHealth", "HealthFirst", "United", "None"]

# Simplified doctor database. Replace with real EHR / scheduling API.
DOCTOR_DB: dict[str, dict[str, Any]] = {
    "Dr. Smith": {
        "specialty": "General Practice",
        "insurances": ["Anthem", "Aetna", "HealthFirst"],
        "availability": ["Monday 10:00", "Wednesday 14:00", "Friday 09:00"],
    },
    "Dr. Johnson": {
        "specialty": "Pediatrics",
        "insurances": ["Anthem", "EmblemHealth", "United"],
        "availability": ["Tuesday 11:00", "Thursday 15:00"],
    },
    "Dr. Patel": {
        "specialty": "Cardiology",
        "insurances": ["Aetna", "United", "HealthFirst"],
        "availability": ["Monday 13:00", "Wednesday 10:00"],
    },
}


class HealthcareAgent(Agent):
    """Specialized agent for healthcare appointment booking."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful healthcare scheduling assistant. Speak naturally "
                "for a voice call. No special characters or bullet points. Keep replies short. "
                "\n\n"
                "Your job: help the caller book, reschedule, or inquire about appointments. "
                "Do NOT give medical advice or diagnose anything. If the caller describes "
                "serious symptoms, advise them to call 911 or their provider directly. "
                "\n\n"
                "Flow: "
                "1. Ask what they need (new appointment, follow-up, reschedule). "
                "2. Ask their insurance if booking new. "
                "3. Use list_compatible_doctors to find matches. "
                "4. Book with book_medical_appointment. "
                "\n\n"
                "If the caller wants a different service, use return_to_main_menu."
            ),
        )

    async def on_enter(self) -> None:
        await self.session.say(
            "I can help with healthcare booking. Are you scheduling a new visit "
            "or following up on an existing one?"
        )

    @function_tool
    async def list_compatible_doctors(
        self,
        ctx: RunContext[UserData],
        insurance: Annotated[
            str,
            Field(
                description="Patient's insurance provider.",
                json_schema_extra={"enum": VALID_INSURANCES},
            ),
        ],
        specialty: Annotated[
            str | None,
            Field(description="Type of doctor needed. None for general."),
        ] = None,
    ) -> str:
        """List doctors who accept the patient's insurance."""
        matches = []
        for name, doc in DOCTOR_DB.items():
            if insurance != "None" and insurance not in doc["insurances"]:
                continue
            if specialty and specialty.lower() not in doc["specialty"].lower():
                continue
            matches.append((name, doc))

        if not matches:
            return (
                "I did not find a matching doctor for that insurance and specialty. "
                "Would you like to try a different specialty?"
            )

        lines = [f"{name}, {doc['specialty']}" for name, doc in matches]
        return "Available doctors: " + "; ".join(lines) + ". Which would you prefer?"

    @function_tool
    async def get_doctor_availability(
        self,
        ctx: RunContext[UserData],
        doctor_name: str,
    ) -> str:
        """Get available slots for a specific doctor."""
        doc = DOCTOR_DB.get(doctor_name)
        if not doc:
            return f"I could not find a doctor named {doctor_name}."
        slots = ", ".join(doc["availability"])
        return f"{doctor_name} has openings on: {slots}. Which works for you?"

    @function_tool
    async def book_medical_appointment(
        self,
        ctx: RunContext[UserData],
        doctor_name: str,
        appointment_time: Annotated[
            str,
            Field(description="Appointment time in ISO format (YYYY-MM-DDTHH:MM)."),
        ],
        patient_name: str,
        reason_for_visit: str,
    ) -> str:
        """Book a medical appointment.

        Args:
            doctor_name: The doctor's full name (e.g. "Dr. Smith").
            appointment_time: ISO-format datetime string.
            patient_name: Patient's full name.
            reason_for_visit: Brief reason for the visit.
        """
        if doctor_name not in DOCTOR_DB:
            return f"Doctor {doctor_name} was not found."

        try:
            when = datetime.fromisoformat(appointment_time)
        except ValueError:
            return "That appointment time format was not understood."

        appt = MedicalAppointment(
            doctor_name=doctor_name,
            appointment_time=when,
            reason=reason_for_visit,
            patient_name=patient_name,
        )
        ctx.userdata.medical_appointments.append(appt)
        ctx.userdata.profile.name = ctx.userdata.profile.name or patient_name

        readable = when.strftime("%A %B %d at %I:%M %p").replace(" 0", " ")
        return (
            f"Confirmed. {patient_name} is booked with {doctor_name} "
            f"on {readable}. Anything else?"
        )

    @function_tool
    async def return_to_main_menu(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Return to the main menu."""
        from .router import RouterAgent

        ctx.userdata.last_service = "healthcare"
        return RouterAgent(), "Taking you back to the main menu."
