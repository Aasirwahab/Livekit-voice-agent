"""Tests for the unified multi-service voice agent.

These are LLM-driven evals following the LiveKit Agents testing framework.
They exercise the router handoffs plus each specialist agent's core behaviors.
"""

from __future__ import annotations

import pytest

from livekit.agents import AgentSession, inference, llm
from services import (
    HealthcareAgent,
    OrderAgent,
    RealEstateAgent,
    RouterAgent,
    SchedulingAgent,
    UserData,
)
from services.orders import MENU
from services.real_estate import PROPERTY_DB

AGENT_MODEL = "openai/gpt-4o-mini"


def _agent_llm() -> llm.LLM:
    return inference.LLM(model=AGENT_MODEL)


def _judge_llm() -> llm.LLM:
    return inference.LLM(model="openai/gpt-4.1-mini")


# ---------------------------------------------------------------------------
# Router handoff tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_router_transfers_to_real_estate() -> None:
    """Router should call transfer_to_real_estate when the caller asks about
    property viewings."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RouterAgent())
        result = await session.run(user_input="I'd like to see a house for sale.")
        result.expect.next_event().is_function_call(name="transfer_to_real_estate")


@pytest.mark.asyncio
async def test_router_transfers_to_healthcare() -> None:
    """Router should call transfer_to_healthcare for medical requests."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RouterAgent())
        result = await session.run(user_input="I need to book a doctor's appointment.")
        result.expect.next_event().is_function_call(name="transfer_to_healthcare")


@pytest.mark.asyncio
async def test_router_transfers_to_orders() -> None:
    """Router should call transfer_to_orders when the caller wants to buy something."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RouterAgent())
        result = await session.run(user_input="I'd like to place a food order please.")
        result.expect.next_event().is_function_call(name="transfer_to_orders")


@pytest.mark.asyncio
async def test_router_transfers_to_scheduling() -> None:
    """Router should call transfer_to_scheduling for generic appointments."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RouterAgent())
        result = await session.run(user_input="I want to book a consultation meeting next week.")
        result.expect.next_event().is_function_call(name="transfer_to_scheduling")


# ---------------------------------------------------------------------------
# Real estate tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_real_estate_lists_properties() -> None:
    """Real estate agent should call list_available_properties when asked."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RealEstateAgent())
        result = await session.run(
            user_input="What 3 bedroom houses do you have under 500 thousand?"
        )
        result.expect.next_event().is_function_call(name="list_available_properties")


@pytest.mark.asyncio
async def test_real_estate_property_db_integrity() -> None:
    """Every property in the DB has the fields the agent assumes."""
    required = {"address", "price", "bedrooms", "bathrooms", "type", "sqft", "notice_hours"}
    for pid, prop in PROPERTY_DB.items():
        missing = required - set(prop.keys())
        assert not missing, f"{pid} missing fields: {missing}"


@pytest.mark.asyncio
async def test_real_estate_refuses_medical_advice() -> None:
    """Real estate agent should not try to answer healthcare questions -
    it should route away or gracefully redirect."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(RealEstateAgent())
        result = await session.run(user_input="Actually I need to book a doctor.")
        result.expect.next_event().is_function_call(name="return_to_main_menu")


# ---------------------------------------------------------------------------
# Order tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_order_agent_adds_item() -> None:
    """Order agent should call add_item_to_order when the caller picks something."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(OrderAgent())
        result = await session.run(user_input="I'll have a classic burger please.")
        result.expect.next_event().is_function_call(name="add_item_to_order")


def test_menu_has_all_categories() -> None:
    """The menu should cover main, side, and drink categories."""
    categories = {item["category"] for item in MENU.values()}
    assert {"main", "side", "drink"}.issubset(categories)


# ---------------------------------------------------------------------------
# UserData tests
# ---------------------------------------------------------------------------


def test_userdata_summary_empty() -> None:
    ud = UserData()
    assert ud.summary() == "no activity yet"


def test_userdata_summary_with_activity() -> None:
    from datetime import datetime

    from services.user_data import PropertyViewing

    ud = UserData()
    ud.profile.name = "Alice"
    ud.property_viewings.append(
        PropertyViewing(
            property_id="P001",
            address="123 Main",
            viewing_time=datetime.now(),
            viewer_name="Alice",
        )
    )
    summary = ud.summary()
    assert "Alice" in summary
    assert "1 property viewing" in summary


# ---------------------------------------------------------------------------
# Healthcare tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcare_lists_doctors() -> None:
    """Healthcare agent should call list_compatible_doctors once it has insurance info."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(HealthcareAgent())
        result = await session.run(
            user_input="I have Anthem insurance and I need a general doctor."
        )
        result.expect.next_event().is_function_call(name="list_compatible_doctors")


@pytest.mark.asyncio
async def test_healthcare_does_not_diagnose() -> None:
    """Healthcare agent must refuse to give medical advice."""
    async with (
        _agent_llm() as agent_llm,
        _judge_llm() as judge_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(HealthcareAgent())
        result = await session.run(
            user_input="I have a sharp chest pain - what do you think it is?"
        )
        await (
            result.expect.next_event()
            .is_message(role="assistant")
            .judge(
                judge_llm,
                intent=(
                    "Does not diagnose the chest pain or speculate about causes. "
                    "Advises the caller to call 911 or contact a provider directly, "
                    "or redirects to booking an appointment."
                ),
            )
        )


# ---------------------------------------------------------------------------
# Scheduling tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduling_lists_slots() -> None:
    """Scheduling agent should call list_open_slots when caller asks for available times."""
    async with (
        _agent_llm() as agent_llm,
        AgentSession[UserData](llm=agent_llm, userdata=UserData()) as session,
    ):
        await session.start(SchedulingAgent())
        result = await session.run(
            user_input="What times do you have open next week for a consultation?"
        )
        result.expect.next_event().is_function_call(name="list_open_slots")
