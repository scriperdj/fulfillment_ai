# Escalation Criteria

## Overview
Escalation procedures ensure that high-impact issues receive appropriate attention and resolution within defined SLAs. All deviations are categorized by severity and routed through escalation tiers accordingly.

## Severity-to-Action Mapping

### Critical (delay probability >= 0.70)
- **Response time**: 15 minutes
- **Actions**: Immediate carrier contact, proactive customer notification, shipment rerouting if possible
- **Assigned to**: Senior Operations Specialist
- **Notification**: Slack alert to #ops-critical channel, email to shift manager

### Warning (delay probability >= 0.50)
- **Response time**: 1 hour
- **Actions**: Monitor shipment status, prepare contingency plan, draft customer communication
- **Assigned to**: Operations Agent
- **Notification**: Dashboard alert, daily digest email

### Info (delay probability >= 0.30)
- **Response time**: 4 hours
- **Actions**: Log for trend analysis, no immediate action required
- **Assigned to**: Monitoring system (automated)
- **Notification**: Weekly summary report only

## SLA Breach Triggers
1. **Delivery SLA breach**: Shipment not delivered within promised window → auto-escalate to Warning.
2. **Customer complaint**: Any complaint about an existing deviation → escalate one tier up.
3. **Repeated delays**: Same warehouse block has >5 critical deviations in 24 hours → escalate to management.
4. **Carrier SLA breach**: Carrier misses guaranteed timeline → trigger penalty clause review.
5. **Financial threshold**: Order value >$500 with any deviation → auto-escalate to Critical.

## Escalation Tiers

### Tier 1 — Automated System
- Handles all Info-level deviations
- Monitors trends and generates reports
- Auto-resolves if shipment status updates to "delivered"

### Tier 2 — Operations Agent
- Handles Warning-level deviations
- Can authorize shipping upgrades up to $25
- Must resolve or escalate within 4 hours

### Tier 3 — Senior Operations Specialist
- Handles Critical-level deviations
- Can authorize refunds up to $200 and shipping upgrades
- Must resolve or escalate within 1 hour

### Tier 4 — Operations Manager
- Handles unresolved Tier 3 escalations and systemic issues
- Can authorize any refund amount and carrier penalties
- Reviews weekly escalation reports

## Contact Information
- Tier 2 Queue: ops-agents@fulfillment.internal
- Tier 3 Queue: ops-senior@fulfillment.internal
- Tier 4 Direct: ops-manager@fulfillment.internal
- Emergency (after hours): +1-555-OPS-HELP

## Documentation Requirements
- All escalations must include: order_id, deviation_id, severity, actions taken, and resolution.
- Critical escalations require a post-incident report within 24 hours.
