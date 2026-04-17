"""Shared user data across all services.

UserData is passed through the AgentSession so all specialized agents
(real estate, healthcare, orders, scheduling) share context about the
caller, their profile, and any in-progress transactions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CustomerProfile:
    """Basic customer info collected once and reused across services."""

    name: str | None = None
    phone: str | None = None
    email: str | None = None


@dataclass
class PropertyViewing:
    """A booked real estate showing."""

    property_id: str
    address: str
    viewing_time: datetime
    viewer_name: str


@dataclass
class MedicalAppointment:
    """A booked healthcare appointment."""

    doctor_name: str
    appointment_time: datetime
    reason: str
    patient_name: str


@dataclass
class Order:
    """An in-progress or completed order."""

    items: list[dict[str, Any]] = field(default_factory=list)
    total: float = 0.0
    confirmed: bool = False


@dataclass
class UserData:
    """Shared state across all services in a single session."""

    profile: CustomerProfile = field(default_factory=CustomerProfile)

    # Real estate
    property_viewings: list[PropertyViewing] = field(default_factory=list)
    interested_properties: list[str] = field(default_factory=list)

    # Healthcare
    medical_appointments: list[MedicalAppointment] = field(default_factory=list)

    # Orders
    current_order: Order = field(default_factory=Order)
    completed_orders: list[Order] = field(default_factory=list)

    # General appointments
    general_appointments: list[dict[str, Any]] = field(default_factory=list)

    # Where the user is in the flow (used by router for smarter greetings)
    last_service: str | None = None

    def summary(self) -> str:
        """Short human-readable summary of what's happened in the session."""
        parts = []
        if self.profile.name:
            parts.append(f"customer: {self.profile.name}")
        if self.property_viewings:
            parts.append(f"{len(self.property_viewings)} property viewing(s) booked")
        if self.medical_appointments:
            parts.append(f"{len(self.medical_appointments)} medical appointment(s) booked")
        if self.completed_orders:
            parts.append(f"{len(self.completed_orders)} order(s) placed")
        return "; ".join(parts) if parts else "no activity yet"
