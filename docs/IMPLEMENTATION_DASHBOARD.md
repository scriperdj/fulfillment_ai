# Operations Dashboard - Implementation Plan

## Overview
This plan outlines the steps to build the Next.js Operations Dashboard for the Fulfillment AI system. We will address the identified data gaps with frontend-side workarounds (Network Graph, IDs) and implement a new dedicated backend API endpoint for the live activity feed.

## Phase 1: Backend API Enhancement
**Goal:** Expose the necessary data for the "Live Agent Activity" feed.

1.  **Update `src/api/routes/agents.py`**:
    *   Add a new endpoint: `GET /agents/activity`
    *   Logic: Query the `agent_responses` table, joined with `deviations` and `predictions`, sorted by `created_at desc`, limit 50.
    *   Response Schema:
        ```json
        [
          {
            "id": "uuid",
            "agent_type": "shipment",
            "action": "rescheduled",
            "order_id": "12345",
            "timestamp": "iso-date",
            "details": { ... }
          }
        ]
        ```

## Phase 2: Next.js Project Foundation
**Goal:** logical project structure with design system basics.

1.  **Initialize App:**
    *   Command: `npx create-next-app@latest web --typescript --tailwind --eslint`
    *   Install dependencies: `lucide-react` (icons), `framer-motion` (animations), `clsx`, `tailwind-merge` (utils), `recharts` (charts), `swr` (data fetching).

2.  **Theme Setup:**
    *   Configure `tailwind.config.ts` with the custom palette (Slate/Cyan/Violet) defined in `DESIGN_SYSTEM.md`.
    *   Create base `globals.css` with dark mode defaults.

3.  **Layout Components:**
    *   `components/layout/Sidebar.tsx`: Navigation (Dashboard, Orders, Agents, Settings).
    *   `components/layout/TopBar.tsx`: Breadcrumbs, User Profile, global search.
    *   `components/ui/GlassCard.tsx`: The primary container component.

## Phase 3: Dashboard View (`/`)
**Goal:** The main "Control Center" view.

1.  **Top KPI Grid:**
    *   Create `components/dashboard/KPIGrid.tsx`.
    *   Fetch data from `GET /kpi/dashboard`.
    *   Display: Total Orders, On-Time Rate, Active Risks.

2.  **Network Graph (The "Map"):**
    *   Create `components/dashboard/NetworkGraph.tsx`.
    *   Use `recharts` ScatterChart or a custom SVG to visualize nodes (Warehouse A-E) and edges (Shipment Routes).
    *   Color nodes based on aggregate risk score (Red/Green).

3.  **Live Agent Feed:**
    *   Create `components/dashboard/AgentFeed.tsx`.
    *   Fetch data from the new `GET /agents/activity` endpoint (using SWR for polling).
    *   Render as a scrolling list with entry animations.

4.  **Deviation Queue:**
    *   Create `components/dashboard/DeviationTable.tsx`.
    *   Fetch from `GET /deviations?status=pending`.
    *   Columns: Order ID, Severity (Badge), Reason, Age.

## Phase 4: Order Detail View (`/orders/[id]`)
**Goal:** Deep-dive analysis and explainability.

1.  **Header & Metrics:**
    *   Show Order ID, Current Status, and a large "Risk Gauge" (using Recharts PieChart).
    *   Display metadata (Warehouse Block, Weight, Cost).

2.  **Resolution Timeline:**
    *   Create `components/order/ResolutionTimeline.tsx`.
    *   Fetch full history from `GET /orders/{id}`.
    *   Map events: Prediction -> Deviation -> Agent Action 1 -> Agent Action 2.
    *   Visualize as a vertical step flow.

## Phase 5: Agents View (`/agents`)
**Goal:** System introspection.

1.  **Agent Cards:**
    *   Display 4 cards: Shipment, Customer, Payment, Escalation.
    *   Show static capabilities (description) and dynamic stats (action count).

2.  **Global Activity Log:**
    *   A full-page version of the dashboard feed, with filters by Agent Type.

## Execution Order
1.  **Backend:** Implement `GET /agents/activity`.
2.  **Frontend Setup:** Initialize project & styles.
3.  **Components:** Build Layout & GlassCard.
4.  **Feature:** Build Dashboard (KPIs, Activity Feed, Network Graph).
5.  **Feature:** Build Order Detail (Timeline).
