"""Simulated business logic tools for multi-agent system.

Each tool is a plain sync function returning a structured dict.
No real API calls — simulate realistic business responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Shipment tools
# ---------------------------------------------------------------------------


@tool
def reschedule_shipment(order_id: str, new_mode: str, reason: str) -> dict[str, Any]:
    """Reschedule a shipment to a different delivery mode."""
    carriers = {"Flight": "FedEx Express", "Ship": "Maersk", "Road": "UPS Ground"}
    eta_days = {"Flight": 2, "Ship": 7, "Road": 5}
    new_eta = datetime.now(timezone.utc) + timedelta(days=eta_days.get(new_mode, 5))
    return {
        "status": "rescheduled",
        "order_id": order_id,
        "new_mode": new_mode,
        "new_eta": new_eta.isoformat(),
        "carrier": carriers.get(new_mode, "Default Carrier"),
        "reason": reason,
    }


@tool
def check_carrier_status(order_id: str, carrier: str) -> dict[str, Any]:
    """Check the current status of a carrier shipment."""
    return {
        "carrier": carrier,
        "order_id": order_id,
        "status": "in_transit",
        "current_location": "Regional Distribution Center",
        "eta": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "last_update": datetime.now(timezone.utc).isoformat(),
    }


@tool
def transfer_warehouse(order_id: str, from_block: str, to_block: str) -> dict[str, Any]:
    """Transfer an order to a different warehouse block."""
    processing_hours = {"A": 24, "B": 36, "C": 48, "D": 24, "E": 30}
    return {
        "status": "transferred",
        "order_id": order_id,
        "from_block": from_block,
        "new_block": to_block,
        "processing_time": f"{processing_hours.get(to_block, 36)} hours",
    }


# ---------------------------------------------------------------------------
# Customer tools
# ---------------------------------------------------------------------------


@tool
def draft_email(order_id: str, template: str, context: str) -> dict[str, Any]:
    """Draft a customer email using a specified template."""
    templates = {
        "apology": "Important Update About Your Order",
        "refund_confirmation": "Refund Confirmed for Your Order",
        "delay_notification": "Shipping Update for Your Order",
    }
    subject = templates.get(template, f"Update About Order {order_id}")
    return {
        "subject": f"{subject} {order_id}",
        "body": f"Dear Customer,\n\n{context}\n\nBest regards,\nFulfillment AI Team",
        "recipient": f"customer-{order_id}@example.com",
        "template_used": template,
    }


@tool
def send_notification(order_id: str, channel: str, message: str) -> dict[str, Any]:
    """Send a notification to the customer via the specified channel."""
    return {
        "status": "sent",
        "order_id": order_id,
        "channel": channel,
        "message": message,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }


@tool
def log_interaction(order_id: str, interaction_type: str, details: str) -> dict[str, Any]:
    """Log a customer interaction for audit purposes."""
    return {
        "logged": True,
        "order_id": order_id,
        "interaction_id": str(uuid.uuid4()),
        "interaction_type": interaction_type,
        "details": details,
        "logged_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Payment tools
# ---------------------------------------------------------------------------


@tool
def check_refund_eligibility(order_id: str, amount: float) -> dict[str, Any]:
    """Check if an order is eligible for a refund."""
    eligible = amount <= 500.0
    return {
        "eligible": eligible,
        "order_id": order_id,
        "reason": "Within refund policy limits" if eligible else "Exceeds auto-refund limit",
        "max_amount": min(amount, 500.0),
    }


@tool
def issue_refund(order_id: str, amount: float, method: str) -> dict[str, Any]:
    """Issue a refund to the customer."""
    return {
        "status": "processed",
        "order_id": order_id,
        "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
        "amount": amount,
        "method": method,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


@tool
def apply_credit(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Apply store credit to a customer account."""
    expiry = datetime.now(timezone.utc) + timedelta(days=90)
    return {
        "status": "applied",
        "order_id": order_id,
        "credit_id": f"CRD-{uuid.uuid4().hex[:8].upper()}",
        "amount": amount,
        "reason": reason,
        "expiry": expiry.isoformat(),
    }


# ---------------------------------------------------------------------------
# Escalation tools
# ---------------------------------------------------------------------------


@tool
def create_ticket(order_id: str, severity: str, description: str) -> dict[str, Any]:
    """Create a support ticket for escalated issues."""
    priority_map = {"critical": "P1", "warning": "P2", "info": "P3"}
    team_map = {"critical": "Senior Support", "warning": "Support Team", "info": "General Queue"}
    return {
        "ticket_id": f"TKT-{uuid.uuid4().hex[:8].upper()}",
        "order_id": order_id,
        "priority": priority_map.get(severity, "P3"),
        "assigned_team": team_map.get(severity, "General Queue"),
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@tool
def assign_human(order_id: str, team: str, reason: str) -> dict[str, Any]:
    """Assign a human agent to handle the case."""
    return {
        "status": "assigned",
        "order_id": order_id,
        "agent_name": f"Agent-{team[:3].upper()}-{uuid.uuid4().hex[:4]}",
        "team": team,
        "queue_position": 1,
        "reason": reason,
    }


@tool
def flag_priority(order_id: str, level: str, reason: str) -> dict[str, Any]:
    """Flag an order with a specific priority level."""
    return {
        "status": "flagged",
        "order_id": order_id,
        "priority_level": level,
        "reason": reason,
        "flagged_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Tool collections by agent type
# ---------------------------------------------------------------------------

SHIPMENT_TOOLS = [reschedule_shipment, check_carrier_status, transfer_warehouse]
CUSTOMER_TOOLS = [draft_email, send_notification, log_interaction]
PAYMENT_TOOLS = [check_refund_eligibility, issue_refund, apply_credit]
ESCALATION_TOOLS = [create_ticket, assign_human, flag_priority]
ALL_TOOLS = SHIPMENT_TOOLS + CUSTOMER_TOOLS + PAYMENT_TOOLS + ESCALATION_TOOLS
