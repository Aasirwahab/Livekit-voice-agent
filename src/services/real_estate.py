"""Real estate agent for property listings, showings, and lead qualification.

Handles:
- Listing available properties (filtered by criteria)
- Scheduling property viewings
- Lead qualification (pre-approval, budget, timeline)
- Property detail lookup
- Open house registration
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Annotated, Any

from pydantic import Field

from livekit.agents import Agent, RunContext, function_tool

from .user_data import PropertyViewing, UserData

logger = logging.getLogger("real-estate-agent")


# Demo property database. Swap this for a real CRM / MLS API in production.
PROPERTY_DB: dict[str, dict[str, Any]] = {
    "P001": {
        "address": "123 Main Street, Springfield",
        "price": 450000,
        "bedrooms": 3,
        "bathrooms": 2,
        "type": "house",
        "sqft": 1800,
        "amenities": ["garage", "backyard", "updated kitchen"],
        "notice_hours": 24,
        "available_times": ["weekdays 9am-6pm", "saturdays 10am-4pm"],
    },
    "P002": {
        "address": "456 Oak Avenue, Unit 3B, Springfield",
        "price": 275000,
        "bedrooms": 2,
        "bathrooms": 1,
        "type": "condo",
        "sqft": 950,
        "amenities": ["pool", "gym", "doorman"],
        "notice_hours": 2,
        "available_times": ["anytime"],
    },
    "P003": {
        "address": "789 Pine Road, Springfield",
        "price": 625000,
        "bedrooms": 4,
        "bathrooms": 3,
        "type": "house",
        "sqft": 2400,
        "amenities": ["pool", "garage", "office", "finished basement"],
        "notice_hours": 48,
        "available_times": ["tuesdays to saturdays 10am-6pm"],
    },
    "P004": {
        "address": "321 Elm Court, Springfield",
        "price": 320000,
        "bedrooms": 2,
        "bathrooms": 2,
        "type": "townhouse",
        "sqft": 1400,
        "amenities": ["garage", "patio"],
        "notice_hours": 24,
        "available_times": ["weekdays 10am-5pm"],
    },
}


class RealEstateAgent(Agent):
    """Specialized agent for real estate inquiries and property viewings."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a friendly real estate assistant helping the caller find "
                "and view properties. Speak naturally and conversationally — this is "
                "a voice call. No special characters, emojis, or bullet points. "
                "Keep replies concise. "
                "\n\n"
                "Your goals in order: "
                "1. Understand what the caller is looking for (budget, bedrooms, property type). "
                "2. Offer matching properties using list_available_properties. "
                "3. Qualify the lead by asking if they are pre-approved and their timeline. "
                "4. Schedule a viewing using schedule_property_viewing. "
                "\n\n"
                "When listing properties, read 2-3 at a time and wait for the caller "
                "to respond. Do not dump the whole database. "
                "When giving prices say them naturally, like 'four hundred fifty thousand'. "
                "If the caller wants something you cannot help with, use return_to_main_menu."
            ),
        )

    async def on_enter(self) -> None:
        await self.session.say(
            "I can help you with real estate. Are you looking to buy or rent, "
            "and what kind of property do you have in mind?"
        )

    @function_tool
    async def list_available_properties(
        self,
        ctx: RunContext[UserData],
        max_price: Annotated[
            float | None,
            Field(description="Maximum price in USD. None if not specified."),
        ] = None,
        min_bedrooms: Annotated[
            int | None,
            Field(description="Minimum number of bedrooms. None if not specified."),
        ] = None,
        property_type: Annotated[
            str | None,
            Field(
                description="Type of property.",
                json_schema_extra={"enum": ["house", "condo", "townhouse"]},
            ),
        ] = None,
    ) -> str:
        """List properties matching the caller's criteria.

        Use this when the caller asks what's available or describes what they want.
        """
        matches = []
        for pid, prop in PROPERTY_DB.items():
            if max_price is not None and prop["price"] > max_price:
                continue
            if min_bedrooms is not None and prop["bedrooms"] < min_bedrooms:
                continue
            if property_type is not None and prop["type"] != property_type:
                continue
            matches.append((pid, prop))

        if not matches:
            return (
                "No properties match those criteria right now. "
                "Would you like to broaden the search?"
            )

        lines = []
        for pid, prop in matches[:4]:
            lines.append(
                f"{pid}: {prop['address']}, a {prop['bedrooms']} bedroom "
                f"{prop['type']} at ${prop['price']:,}, {prop['sqft']} square feet."
            )
        return "\n".join(lines)

    @function_tool
    async def get_property_details(
        self,
        ctx: RunContext[UserData],
        property_id: str,
    ) -> str:
        """Get full details on a specific property.

        Args:
            property_id: The property code (e.g. P001).
        """
        prop = PROPERTY_DB.get(property_id.upper())
        if not prop:
            return f"Property {property_id} was not found."

        # Remember this as an interest for smarter follow-up later
        if property_id.upper() not in ctx.userdata.interested_properties:
            ctx.userdata.interested_properties.append(property_id.upper())

        amenities = ", ".join(prop["amenities"])
        return (
            f"{prop['address']} is a {prop['bedrooms']} bedroom, {prop['bathrooms']} "
            f"bathroom {prop['type']} at ${prop['price']:,}. It has {prop['sqft']} "
            f"square feet and features: {amenities}. Showings are available "
            f"{prop['available_times'][0]}. Would you like to schedule a viewing?"
        )

    @function_tool
    async def qualify_lead(
        self,
        ctx: RunContext[UserData],
        pre_approved: Annotated[
            bool,
            Field(description="Whether the buyer is pre-approved for a mortgage."),
        ],
        budget: Annotated[float, Field(description="Their target budget in USD.")],
        timeline: Annotated[
            str,
            Field(
                description="When they plan to buy.",
                json_schema_extra={
                    "enum": ["immediately", "1-3 months", "3-6 months", "6+ months", "browsing"]
                },
            ),
        ],
        working_with_agent: Annotated[
            bool,
            Field(description="Whether they are already working with an agent."),
        ],
    ) -> str:
        """Record lead qualification info. Call this once you've gathered buyer details.

        Ask naturally during the conversation - don't interrogate the caller.
        """
        tier = (
            "priority" if pre_approved and timeline in {"immediately", "1-3 months"} else "standard"
        )
        logger.info(
            "lead qualified",
            extra={
                "tier": tier,
                "pre_approved": pre_approved,
                "budget": budget,
                "timeline": timeline,
            },
        )
        return f"Lead recorded as {tier}. Continue helping the caller find a property."

    @function_tool
    async def schedule_property_viewing(
        self,
        ctx: RunContext[UserData],
        property_id: str,
        viewing_date: Annotated[
            str,
            Field(description="Date of viewing in YYYY-MM-DD format."),
        ],
        viewing_time: Annotated[
            str,
            Field(description="Time of viewing in HH:MM 24-hour format."),
        ],
        viewer_name: str,
    ) -> str:
        """Book a property viewing.

        Args:
            property_id: The property code (e.g. P001).
            viewing_date: Date in YYYY-MM-DD format.
            viewing_time: Time in HH:MM 24-hour format.
            viewer_name: Name of the person viewing.
        """
        prop = PROPERTY_DB.get(property_id.upper())
        if not prop:
            return f"Property {property_id} was not found."

        try:
            when = datetime.fromisoformat(f"{viewing_date}T{viewing_time}")
        except ValueError:
            return "That date or time format was not understood. Please try again."

        notice_required = timedelta(hours=prop["notice_hours"])
        if when - datetime.now() < notice_required:
            return (
                f"That property needs at least {prop['notice_hours']} hours notice. "
                "Could you pick a later time?"
            )

        viewing = PropertyViewing(
            property_id=property_id.upper(),
            address=prop["address"],
            viewing_time=when,
            viewer_name=viewer_name,
        )
        ctx.userdata.property_viewings.append(viewing)
        ctx.userdata.profile.name = ctx.userdata.profile.name or viewer_name

        readable = when.strftime("%A %B %d at %I:%M %p").replace(" 0", " ")
        return (
            f"Booked. I have {viewer_name} down to view {prop['address']} on "
            f"{readable}. You will receive a confirmation. Anything else?"
        )

    @function_tool
    async def return_to_main_menu(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Return to the main menu if the caller wants a different service."""
        from .router import RouterAgent

        ctx.userdata.last_service = "real_estate"
        return RouterAgent(), "Taking you back to the main menu."
