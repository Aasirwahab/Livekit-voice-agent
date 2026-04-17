"""Main router / customer service entry agent.

Greets the caller, figures out what they need, then hands off to a
specialized agent. Specialized agents can also hand back to this router.

Uses LiveKit's agent handoff pattern: a tool returns a new Agent to
switch the session to that agent.
"""

from __future__ import annotations

import logging

from livekit.agents import Agent, RunContext, function_tool

from .user_data import UserData

logger = logging.getLogger("router-agent")


class RouterAgent(Agent):
    """Customer service entry point. Routes callers to specialized services."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are the main customer service assistant. Speak naturally "
                "for a voice call - no special characters, no bullet points, "
                "keep replies short. "
                "\n\n"
                "When the caller indicates what they need, route them immediately: "
                "- Real estate (property viewings, listings, rentals, houses, apartments): call transfer_to_real_estate. "
                "- Healthcare (medical appointments, doctor, health booking): call transfer_to_healthcare. "
                "- Orders (food, products, purchases, ordering): call transfer_to_orders. "
                "- General appointments (consultations, meetings, appointments): call transfer_to_scheduling. "
                "\n\n"
                "If the caller is vague or unsure, ask a friendly clarifying question. "
                "But if their intent is clear, transfer immediately - do not ask additional questions. "
                "Do NOT try to handle a specialized request yourself - always transfer. "
                "If the caller has already used a service and comes back, greet them "
                "by acknowledging the prior activity briefly."
            ),
        )

    async def on_enter(self) -> None:
        ud: UserData = self.session.userdata
        if ud.last_service is None:
            await self.session.say(
                "Hi, thanks for calling. I can help with real estate, healthcare "
                "bookings, placing an order, or scheduling an appointment. "
                "What do you need today?"
            )
        else:
            # Returning from a sub-agent
            summary = ud.summary()
            await self.session.say(
                f"You're back. Quick recap: {summary}. Anything else I can help with?"
            )

    @function_tool
    async def transfer_to_real_estate(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Transfer the caller to the real estate specialist for property viewings,
        listings, buying, renting, or real estate questions."""
        from .real_estate import RealEstateAgent

        logger.info("routing to real estate")
        return RealEstateAgent(), "Connecting you to our real estate specialist."

    @function_tool
    async def transfer_to_healthcare(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Transfer the caller to the healthcare booking specialist for medical
        appointments, doctor visits, or healthcare inquiries."""
        from .healthcare import HealthcareAgent

        logger.info("routing to healthcare")
        return HealthcareAgent(), "Connecting you to healthcare booking."

    @function_tool
    async def transfer_to_orders(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Transfer the caller to the order-taking specialist for placing
        food, product, or purchase orders."""
        from .orders import OrderAgent

        logger.info("routing to orders")
        return OrderAgent(), "Connecting you to place your order."

    @function_tool
    async def transfer_to_scheduling(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Transfer the caller to the general scheduling specialist for
        consultations, meetings, or service appointments that are not
        healthcare or real estate."""
        from .scheduling import SchedulingAgent

        logger.info("routing to scheduling")
        return SchedulingAgent(), "Connecting you to scheduling."
