# Warehouse Service Level Agreements

## Overview
Our fulfillment network consists of five warehouse blocks (A through E), each serving specific regions and product categories. Processing time SLAs ensure orders move from received to shipped within guaranteed windows.

## Per-Block Processing Times

### Block A — East Region Hub
- **Standard processing**: 24 hours from order placement to shipment handoff.
- **Express processing**: 4 hours for Flight/air shipments.
- **Capacity**: 5,000 orders per day.
- **Specialization**: Electronics, high-value items.
- **Peak buffer**: Can surge to 7,000 orders/day with overtime authorization.

### Block B — West Region Hub
- **Standard processing**: 24 hours from order placement to shipment handoff.
- **Express processing**: 6 hours for Flight/air shipments.
- **Capacity**: 4,500 orders per day.
- **Specialization**: General merchandise, apparel.
- **Peak buffer**: Can surge to 6,000 orders/day with temporary staff.

### Block C — Central Distribution Center
- **Standard processing**: 18 hours (optimized for ground shipping routes).
- **Express processing**: 4 hours.
- **Capacity**: 8,000 orders per day (largest facility).
- **Specialization**: Bulk orders, heavy items (>5 kg).
- **Peak buffer**: Can surge to 11,000 orders/day.

### Block D — South Region Hub
- **Standard processing**: 24 hours.
- **Express processing**: 5 hours.
- **Capacity**: 4,000 orders per day.
- **Specialization**: Seasonal products, perishable-adjacent items.
- **Peak buffer**: Can surge to 5,500 orders/day.

### Block E — Returns & Overflow
- **Standard processing**: 36 hours (lower priority).
- **Express processing**: 8 hours.
- **Capacity**: 3,000 orders per day.
- **Specialization**: Return processing, overflow from other blocks.
- **Peak buffer**: Can surge to 4,000 orders/day.

## Peak Season Handling
- **Defined peak periods**: Black Friday through Cyber Monday, December 15–24, Prime-equivalent events.
- **Auto-scaling**: Blocks A–D increase staffing by 40% during peak.
- **Overflow routing**: When any block reaches 90% capacity, new orders route to Block E or nearest available block.
- **SLA adjustment**: During declared peak events, standard processing extends to 36 hours.

## SLA Breach Protocol
1. If processing exceeds SLA by >2 hours, warehouse manager is notified.
2. If processing exceeds SLA by >6 hours, order is flagged as critical and expedited.
3. Persistent SLA breaches (>5 per day per block) trigger operations review.
4. Blocks with >10% breach rate in a week get a corrective action plan.

## Quality Metrics
- Target pick accuracy: 99.5%
- Target pack accuracy: 99.8%
- Target ship-on-time rate: 98%
- Inventory accuracy target: 99.2%
