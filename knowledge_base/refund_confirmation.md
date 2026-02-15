# Refund Confirmation Email Template

## Usage
This template is used by the PaymentAgent after a refund has been approved and processed. It confirms the refund details to the customer. Fill in all placeholders before sending.

## Template

---

**Subject:** Refund Confirmed for Order {order_id}

Dear {customer_name},

We are writing to confirm that your refund has been processed for order {order_id}.

**Refund Details:**
- **Refund Amount:** ${refund_amount}
- **Refund Method:** {method}
- **Processing Date:** {processing_date}
- **Expected Arrival:** 3–7 business days depending on your financial institution

**What to expect next:**
- You will see the refund appear in your {method} account within 3–7 business days.
- A separate confirmation from your financial institution may follow.
- If you do not see the refund after 10 business days, please contact us.

**Refund Breakdown:**
| Item                    | Amount        |
|------------------------|---------------|
| Product cost           | ${product_cost} |
| Shipping cost refund   | ${shipping_refund} |
| Tax refund             | ${tax_refund}   |
| **Total Refund**       | **${refund_amount}** |

**We value your feedback:**
We are sorry for the experience that led to this refund. Your satisfaction is our top priority, and we would love the opportunity to serve you better in the future.

As a gesture of goodwill, here is a 15% discount code for your next order: WELCOME-BACK-{order_id}
This code is valid for 60 days.

**Questions?**
If you have any questions about this refund, please contact us:
- Email: refunds@fulfillment.support
- Phone: 1-800-555-HELP (Mon–Fri, 8 AM – 8 PM EST)
- Live Chat: support.fulfillment.com

Thank you for your patience, and we hope to see you again soon.

Best regards,
The Fulfillment AI Payments Team

---

## Placeholder Reference
| Placeholder        | Source                         | Example               |
|--------------------|-------------------------------|-----------------------|
| {customer_name}    | Customer record / CRM          | John Doe              |
| {order_id}         | Order management system         | ORD-2024-78542        |
| {refund_amount}    | Payment processing system       | 149.99                |
| {method}           | Original payment method          | Visa ending in 4242   |
| {processing_date}  | Current date                    | February 15, 2025     |
| {product_cost}     | Order line item total           | 129.99                |
| {shipping_refund}  | Shipping cost (if applicable)   | 12.00                 |
| {tax_refund}       | Tax amount                      | 8.00                  |

## Sending Rules
- Send immediately after refund is processed in payment system.
- Include full breakdown only for refunds over $50.
- For partial refunds, add a note explaining why the refund is partial.
- Copy the customer service lead on refunds over $500.
