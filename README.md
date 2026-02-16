# Fulfillment AI

AI-driven retail fulfillment platform that predicts delivery delays, detects operational deviations, and triggers autonomous resolution agents — all orchestrated through Airflow with Kafka event streaming.

## What It Does

1. **Predicts delays** — A trained XGBoost/LightGBM classifier scores every order with a delay probability (0.0–1.0)
2. **Detects deviations** — Threshold-based rules flag orders as critical (>0.7), warning (>0.5), or info (>0.3)
3. **Resolves autonomously** — LLM-powered specialist agents (Shipment, Customer, Payment, Escalation) take action using RAG-retrieved knowledge
4. **Monitors in real-time** — Next.js dashboard with KPI visualization, batch upload, agent activity feed, and order tracking

## Architecture

```
CSV Upload / Kafka Stream
        │
        ▼
  Unified Pipeline (transform → ML inference → KPI → deviation detection)
        │
        ▼
  Kafka deviation-events
        │
        ▼
  Agent Orchestrator (LLM router → specialist agents → RAG knowledge)
        │
        ▼
  PostgreSQL (predictions, deviations, agent responses) → Dashboard
```

Three Airflow DAGs drive the system:
- **batch_processing** — Triggered by CSV upload via API
- **streaming_dag** — Continuous Kafka consumer, micro-batches every 15s
- **agent_orchestration** — Consumes deviation events, runs multi-agent resolution

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full C4 diagrams, component details, and design decisions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML | scikit-learn, XGBoost, LightGBM |
| API | FastAPI, Pydantic |
| Orchestration | Apache Airflow 3.x |
| Streaming | Redpanda (Kafka-compatible) |
| Database | PostgreSQL 16 |
| AI Agents | OpenAI (gpt-4o-mini), LangChain |
| RAG | Chroma, OpenAI Embeddings |
| Dashboard | Next.js, Tailwind CSS, SWR, Recharts |
| Infra | Docker Compose |

## Project Structure

```
├── dags/                   # Airflow DAGs (batch, streaming, agent)
├── data/                   # Uploads, raw data, Chroma vector DB
├── docker/                 # Docker configs (Airflow, Postgres init)
├── docs/                   # Architecture docs (C4 diagrams)
├── knowledge_base/         # Policy documents for RAG (shipping, refund, SLAs)
├── models/                 # Trained model artifacts (joblib)
├── notebooks/              # model_training.ipynb (EDA + training)
├── src/
│   ├── agents/             # Orchestrator, specialists, tools
│   ├── api/                # FastAPI app, routes, schemas
│   ├── config/             # Settings
│   ├── db/                 # SQLAlchemy models
│   ├── detection/          # Deviation detector, Kafka publisher
│   ├── features/           # Feature engineering / transform
│   ├── ingestion/          # CSV handler, schema validator
│   ├── kafka/              # Kafka producer/consumer helpers
│   ├── kpi/                # KPI calculator
│   ├── ml/                 # Model loading, inference
│   ├── pipeline/           # Unified pipeline orchestrator
│   └── rag/                # Chroma ingestion & retrieval
├── tests/                  # pytest suite (unit + integration)
├── web/                    # Next.js dashboard
│   ├── app/                # Pages (dashboard, orders, batch, agents, knowledge, settings)
│   ├── components/         # UI components (GlassCard, Sidebar, charts)
│   └── lib/                # API client, types, utilities
├── docker-compose.yml
├── Dockerfile              # FastAPI service
├── Dockerfile.airflow      # Airflow services
├── Dockerfile.producer     # Kafka stream simulator
└── requirements.txt
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for the dashboard)
- An OpenAI API key

### 1. Clone and configure

```bash
git clone https://github.com/scriperdj/fulfillment_ai.git
cd fulfillment_ai
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```
OPENAI_API_KEY=sk-your-key-here
```

### 2. Start backend services

```bash
docker-compose up -d
```

This starts PostgreSQL, Redpanda, Airflow (webserver + scheduler + DAG processor), the FastAPI API, and the Kafka stream producer.

| Service | URL |
|---------|-----|
| FastAPI (API docs) | http://localhost:8000/docs |
| Airflow UI | http://localhost:8080 |
| Redpanda Console | http://localhost:8085 |

### 3. Start the dashboard

```bash
cd web
npm install
npm run dev
```

Dashboard available at http://localhost:3000.

### 4. Train the model (optional)

A pre-trained model is included in `models/`. To retrain:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
jupyter notebook notebooks/model_training.ipynb
```

## Usage

### Upload a batch CSV

Navigate to **/batch** in the dashboard, drag-and-drop a CSV file, and click "Upload & Process". The job status polls automatically (queued → running → completed). Click a completed job to see predictions, deviations, and agent responses.

Or via API:

```bash
curl -X POST http://localhost:8000/batch/upload \
  -F "file=@your_orders.csv"
```

### Single prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-001",
    "warehouse_block": "A",
    "mode_of_shipment": "Flight",
    "customer_care_calls": 4,
    "customer_rating": 2,
    "cost_of_the_product": 250,
    "prior_purchases": 3,
    "product_importance": "High",
    "gender": "F",
    "discount_offered": 10,
    "weight_in_gms": 4000
  }'
```

### Trigger an agent manually

```bash
curl -X POST http://localhost:8000/agents/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD-001",
    "severity": "critical",
    "reason": "High delay probability with premium customer",
    "delay_probability": 0.85
  }'
```

### Streaming

The stream producer starts automatically with Docker Compose, generating ~5 enriched order events/second to Kafka. The streaming DAG processes them in 15-second micro-batches.

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/predict` | POST | Single order prediction |
| `/predict/batch` | POST | CSV upload (async) |
| `/batch/` | GET | List all batch jobs |
| `/batch/{id}/status` | GET | Batch job status |
| `/batch/{id}/predictions` | GET | Predictions for a batch |
| `/batch/{id}/deviations` | GET | Deviations for a batch |
| `/batch/{id}/agent-responses` | GET | Agent actions for a batch |
| `/kpi/dashboard` | GET | KPI summary |
| `/deviations` | GET | Recent deviations |
| `/agents/trigger` | POST | Manually trigger agents |
| `/orders/{id}` | GET | Order detail (predictions + deviations + agents) |
| `/knowledge/ingest` | POST | Add document to RAG |
| `/knowledge/search` | POST | Search knowledge base |

Full Swagger docs at http://localhost:8000/docs.

## Testing

```bash
# Unit tests (no Docker required)
pytest

# Integration tests (requires Docker Compose running)
pytest -m integration
```

## Dashboard Pages

- **Dashboard** — KPI cards, severity breakdown charts, warehouse performance, deviation table, agent feed
- **Orders** — Search and drill-down with prediction scores, deviation history, agent responses
- **Batch Jobs** — CSV drag-and-drop upload, job monitor with live status polling, detail drill-down
- **Agents** — Activity feed filtered by agent type, manual trigger form
- **Knowledge Base** — View ingested documents, add new policies, semantic search
- **Settings** — Configuration and thresholds

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key for agents and embeddings |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model for agent reasoning |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model for RAG |
| `POSTGRES_USER` | `fulfillment` | Database user |
| `POSTGRES_PASSWORD` | `fulfillment_pass` | Database password |
| `POSTGRES_DB` | `fulfillment_ai` | Database name |
| `KAFKA_BROKER` | `redpanda:9092` | Kafka broker address |
| `EVENTS_PER_SECOND` | `5` | Stream producer event rate |

