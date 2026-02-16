# Fulfillment AI - Design System & UI/UX Specification

## 1. Design Philosophy
**"The Control Center of the Future"**
The interface must convey trust, intelligence, and immediate situational awareness. It is not just a reporting tool; it is an active command center where the user watches AI agents solve problems in real-time.

**Key Attributes:**
*   **Futuristic yet Professional:** Cyberpunk influences (neon accents, dark mode) tempered by enterprise clean lines.
*   **Glassmorphism:** Use semi-transparent layers to create depth and hierarchy.
*   **Motion:** Subtle animations (pulsing status lights, smooth timeline updates) to show the system is "alive".
*   **Explainability:** Visual priority given to *why* an action was taken (Resolution Timelines).

---

## 2. Color Palette (Tailwind CSS)

### Backgrounds
*   **Void:** `#020617` (Slate 950) - Main background.
*   **Glass Surface:** `rgba(15, 23, 42, 0.6)` with `backdrop-filter: blur(12px)` - Cards and panels.
*   **Overlay:** `rgba(30, 41, 59, 0.4)` - Hover states.

### Semantic Colors
*   **Primary (System):** Cyan `#06b6d4` (Cyan 500) - Navigation, active states.
*   **AI Action (The "Brain"):** Violet `#8b5cf6` (Violet 500) - Agent activities, generative text.
*   **Critical Risk:** Crimson `#f43f5e` (Rose 500) - High probability delays (>70%).
*   **Warning:** Amber `#f59e0b` (Amber 500) - Medium probability delays (50-70%).
*   **Success/On-Time:** Emerald `#10b981` (Emerald 500) - Resolved orders.

### Gradients
*   **Agent Glow:** `linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(6, 182, 212, 0.1))` - Used behind AI chat bubbles.
*   **Critical Alert:** `linear-gradient(to right, rgba(244, 63, 94, 0.1), transparent)` - Used on critical order rows.

---

## 3. Typography
*   **Primary Font:** `Inter` (Google Fonts) - Clean, high legibility for UI text.
*   **Monospace:** `JetBrains Mono` - For "Order ID", "SKU", and log headers.

**Hierarchy:**
*   **H1 (Page Title):** Inter, Bold, 24px, Tracking-tight.
*   **H2 (Section Header):** Inter, Medium, 18px, Text-Slate-200.
*   **KPI Value:** Inter, ExtraBold, 32px, Gradient text.
*   **Body:** Inter, Regular, 14px, Text-Slate-400.

---

## 4. Core UI Components

### 4.1. Neumorphic/Glass Cards
Container for all main widgets.
*   **Style:** `bg-slate-900/50`, `border border-slate-800`, `rounded-xl`, `backdrop-blur-md`.
*   **Hover:** Glow effect `shadow-[0_0_15px_rgba(6,182,212,0.1)]`.

### 4.2. "Live" Status Badges
Indicators that feel responsive.
*   **Structure:** Flex container with a text label and a pulsing dot.
*   **Animation:** `animate-pulse` on the colored dot.
*   **Usage:** "Agent Active", "Processing", "Monitoring".

### 4.3. The Resolution Timeline
Visualizing the chain of events for a delayed order.
*   **Vertical Line:** Connected dots representing time steps.
*   **Event Node:**
    *   **Risk Detected:** Red icon 🚨
    *   **Agent Thinking:** Pulsing Purple icon 🧠 (w/ typing text effect)
    *   **Action Taken:** Solid Blue icon ✈️ (Static final state)
*   **Connectors:** Gradient lines that light up as the step completes.

### 4.4. AI Agent "Thought Bubble"
When an agent is working, show its internal monologue (simplified).
*   **Appearance:** Violet-tinted glass card.
*   **Text:** Typewriter effect: *"Analyzing carrier routes... Found congestion in Sector 7..."*

---

## 5. Page Layouts (Next.js App Router)

### 5.1. Dashboard (Home)
*   **Top Bar:** Global Search, Notification Bell, User Avatar.
*   **Grid:** 3 columns.
    *   **Left (25%):** Navigation Sidebar (Icons + labels).
    *   **Center Top (75%):** KPI Cards (Risk Score, Active Agents, On-Time %).
    *   **Center Mid (50%):** World Map (React-Simple-Maps) showing route health.
    *   **Right Mid (25%):** Live Agent Feed (Scrolling list of actions).
    *   **Bottom (75%):** Deviation Queue Table.

### 5.2. Order Detail View (`/orders/[id]`)
*   **Header:** Order ID, Customer Name, Current Status (Badge).
*   **Split Layout:**
    *   **Left Panel (30%):** Order Metadata (SKU, Value, Warehouse).
    *   **Center Panel (70%):** Large Resolution Timeline.
        *   Displays the *entire* lifecycle from prediction to resolution.
        *   Expandable "Agent Logs" for deep diving into the JSON response.

### 5.3. Agents View (`/agents`)
*   **Card Grid:** One card per specialist agent (Shipment, Customer, Payment, Escalation).
*   **Stats per Agent:** "Interventions today", "Success Rate".
*   **Live Terminal:** A "Matrix-style" scrolling log of all agent API calls for debugging.

---

## 6. Implementation Notes (UI Stack)
*   **Framework:** Next.js 14+ (App Router).
*   **Styling:** Tailwind CSS + `clsx`/`tailwind-merge`.
*   **Animations:** `framer-motion` (for layout transitions, timeline growth).
*   **Icons:** `lucide-react` (modern, clean SVG icons).
*   **Charts:** `recharts` (customized to match dark theme) or `visx`.
*   **Map:** `react-simple-maps` or Mapbox (dark style).

## 7. Interaction Polish
*   **Loading States:** Skeleton loaders with a "shimmer" effect, not spinners.
*   **Toast Notifications:** Slide-in alerts when a new critical deviation is found.
*   **Data Updates:** SWR or React Query for polling freshness without full page reloads.
