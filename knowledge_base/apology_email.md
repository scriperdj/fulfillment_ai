# Apology Email Template

## Usage
This template is used by the CustomerAgent when a delay has been detected and the customer needs to be proactively informed. Fill in all placeholders before sending.

## Template

---

**Subject:** Important Update About Your Order {order_id}

Dear {customer_name},

We are writing to sincerely apologize for the delay with your recent order ({order_id}).

**What happened:**
{delay_reason}

**What we are doing about it:**
Our fulfillment team has been notified and is actively working to expedite your shipment. We have taken the following steps:
- Your order has been prioritized for immediate processing.
- We are coordinating with our carrier partner to ensure the fastest possible delivery.
- A dedicated case agent has been assigned to monitor your order until it arrives.

**Your new estimated delivery date:**
{new_eta}

**How we are making this right:**
As a token of our apology, we would like to offer you:
- Free expedited shipping on your next order (code: EXPEDITE-{order_id})
- A 10% discount on your next purchase (code: SORRY10-{order_id})

These codes are valid for 90 days and can be applied at checkout.

**Need further assistance?**
If you have any questions or concerns, please do not hesitate to reach out:
- Reply directly to this email
- Call us at 1-800-555-HELP (available 24/7)
- Chat with us at support.fulfillment.com

We truly value your business and are committed to ensuring your satisfaction. Thank you for your patience and understanding.

Warm regards,
The Fulfillment AI Customer Care Team

---

## Placeholder Reference
| Placeholder       | Source                              | Example                          |
|-------------------|-------------------------------------|----------------------------------|
| {customer_name}   | Customer record / CRM               | Jane Smith                       |
| {order_id}        | Order management system              | ORD-2024-78542                   |
| {delay_reason}    | Deviation detection system           | Weather-related carrier delays   |
| {new_eta}         | Updated carrier tracking estimate    | February 20, 2025                |

## Sending Rules
- Send within 1 hour of deviation detection for critical severity.
- Send within 4 hours for warning severity.
- Do not send for info-level deviations.
- Maximum one apology email per order per 48-hour period.
