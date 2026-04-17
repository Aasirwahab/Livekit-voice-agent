"""Order taking agent.

Handles product selection, cart management, and order confirmation.
Swap MENU for your real product catalog / database in production.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from pydantic import Field

from livekit.agents import Agent, RunContext, function_tool

from .user_data import Order, UserData

logger = logging.getLogger("order-agent")


# Replace with your real catalog. Categories kept generic so this works for
# food, retail, or any ordering use case.
MENU: dict[str, dict[str, Any]] = {
    "A1": {"name": "Classic Burger", "price": 8.99, "category": "main"},
    "A2": {"name": "Chicken Sandwich", "price": 7.99, "category": "main"},
    "A3": {"name": "Veggie Wrap", "price": 6.99, "category": "main"},
    "B1": {"name": "French Fries", "price": 3.49, "category": "side"},
    "B2": {"name": "Onion Rings", "price": 3.99, "category": "side"},
    "C1": {"name": "Soda", "price": 2.49, "category": "drink"},
    "C2": {"name": "Iced Tea", "price": 2.49, "category": "drink"},
    "C3": {"name": "Coffee", "price": 2.99, "category": "drink"},
}


class OrderAgent(Agent):
    """Specialized agent for taking customer orders."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a friendly order-taking assistant. Speak naturally. "
                "No special characters or bullet points, this is a voice call. "
                "\n\n"
                "Flow: "
                "1. Use list_menu to describe options if asked. "
                "2. Use add_item_to_order as the caller chooses items. "
                "3. Confirm the order with review_order. "
                "4. Finalize with confirm_order once the caller says yes. "
                "\n\n"
                "Always read back prices naturally, like 'eight ninety-nine'. "
                "Keep track of what they've ordered. "
                "If they want a different service, use return_to_main_menu."
            ),
        )

    async def on_enter(self) -> None:
        await self.session.say("Ready to take your order. What can I get started for you?")

    @function_tool
    async def list_menu(
        self,
        ctx: RunContext[UserData],
        category: Annotated[
            str | None,
            Field(
                description="Category to filter by.",
                json_schema_extra={"enum": ["main", "side", "drink"]},
            ),
        ] = None,
    ) -> str:
        """List available menu items, optionally filtered by category."""
        items = []
        for code, item in MENU.items():
            if category and item["category"] != category:
                continue
            items.append(f"{code}: {item['name']} for ${item['price']:.2f}")
        if not items:
            return "Nothing in that category right now."
        return "; ".join(items)

    @function_tool
    async def add_item_to_order(
        self,
        ctx: RunContext[UserData],
        item_code: str,
        quantity: Annotated[int, Field(ge=1, description="Number of items to add.")] = 1,
    ) -> str:
        """Add an item to the current order.

        Args:
            item_code: The menu code (e.g. A1, B2).
            quantity: How many of this item to add.
        """
        item = MENU.get(item_code.upper())
        if not item:
            return f"I could not find {item_code} on the menu."

        order = ctx.userdata.current_order
        order.items.append(
            {
                "code": item_code.upper(),
                "name": item["name"],
                "price": item["price"],
                "quantity": quantity,
            }
        )
        order.total = sum(i["price"] * i["quantity"] for i in order.items)
        plural = f"{quantity} " if quantity > 1 else ""
        return f"Added {plural}{item['name']}. Anything else?"

    @function_tool
    async def remove_item_from_order(
        self,
        ctx: RunContext[UserData],
        item_code: str,
    ) -> str:
        """Remove an item from the current order by its menu code."""
        order = ctx.userdata.current_order
        before = len(order.items)
        order.items = [i for i in order.items if i["code"] != item_code.upper()]
        if len(order.items) == before:
            return f"{item_code} was not in the order."
        order.total = sum(i["price"] * i["quantity"] for i in order.items)
        return f"Removed {item_code}."

    @function_tool
    async def review_order(self, ctx: RunContext[UserData]) -> str:
        """Read back the current order and total. Use before confirming."""
        order = ctx.userdata.current_order
        if not order.items:
            return "The order is empty. What would you like?"
        parts = [f"{i['quantity']} {i['name']} at ${i['price']:.2f}" for i in order.items]
        return (
            f"Current order: {'; '.join(parts)}. Total is ${order.total:.2f}. Does that look right?"
        )

    @function_tool
    async def confirm_order(self, ctx: RunContext[UserData]) -> str:
        """Confirm and finalize the order. Only call after the caller says yes."""
        order = ctx.userdata.current_order
        if not order.items:
            return "There is nothing to confirm yet."

        order.confirmed = True
        ctx.userdata.completed_orders.append(order)
        total = order.total
        ctx.userdata.current_order = Order()

        logger.info("order confirmed", extra={"total": total, "item_count": len(order.items)})
        return f"Order confirmed. Total ${total:.2f}. Thank you. Anything else?"

    @function_tool
    async def return_to_main_menu(self, ctx: RunContext[UserData]) -> tuple[Agent, str]:
        """Return to the main menu."""
        from .router import RouterAgent

        ctx.userdata.last_service = "orders"
        return RouterAgent(), "Taking you back to the main menu."
