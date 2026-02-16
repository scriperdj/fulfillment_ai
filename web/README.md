# Fulfillment AI - Operations Dashboard

This is the Next.js frontend for the Fulfillment AI system.

## Setup

1.  **Install dependencies:**
    ```bash
    npm install
    ```

2.  **Run Development Server:**
    ```bash
    npm run dev
    ```
    Access at http://localhost:3000

## Configuration

-   **API URL:** Configured in `lib/api.ts` (default: `http://localhost:8000`).
-   **Theme:** Colors defined in `app/globals.css`.

## Project Structure

-   `app/`: App Router pages and layout.
-   `components/dashboard/`: Dashboard widgets (KPI, Graph, Feed, Deviation Table).
-   `components/order/`: Order detail components (Resolution Timeline).
-   `components/ui/`: Reusable primitives (GlassCard).
-   `lib/`: Utilities (API fetcher, Tailwind merge).
