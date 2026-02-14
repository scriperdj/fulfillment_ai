# fulfillment_ai - Architecture Document

## 1. System Overview & Goals

**Project Name:** fulfillment_ai  
**Purpose:** Autonomous AI-driven system for proactive detection and resolution of retail fulfillment operational issues  
**Use Case:** Celonis Garage - Process Mining + AI Agents for Order-to-Ship workflow

### Primary Goals
1. **Proactive Risk Detection** - Identify delivery delays before they happen (not reactive)
2. **Autonomous Resolution** - Trigger AI agents to simulate automatic issue resolution
3. **Operational Visibility** - Real-time KPI monitoring and deviation detection
4. **Extensible Design** - Support multiple agents, KPIs, and data sources

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      fulfillment_ai System                       │
└─────────────────────────────────────────────────────────────────┘

                         ┌──────────────────┐
                         │   Data Ingestion │
                         │   (CSV Dataset)  │
                         └────────┬─────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │  Data Layer (Pandas/CSV)   │
                    │  - Load & Preprocess       │
                    │  - Feature Engineering     │
                    └─────────────┬──────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
   ┌────▼─────┐          ┌────────▼────────┐      ┌────────▼────────┐
   │ KPI Calc │          │Risk Detection   │      │ Data Storage    │
   │ Module   │          │Module (ML/Rule) │      │ (In-Memory/DB)  │
   └────┬─────┘          └────────┬────────┘      └─────────────────┘
        │                         │
        └─────────────────────────┼─────────────────────┐
                                  │                     │
                          ┌───────▼──────────┐   ┌─────▼──────────────┐
                          │ Deviation/Risk   │   │  Threshold Engine  │
                          │ Assessment       │   │  (Rule-based)      │
                          └───────┬──────────┘   └────────────────────┘
                                  │
                                  │ (if risk detected)
                                  │
                          ┌───────▼──────────────┐
                          │  Event Queue / Pub   │
                          │  (Trigger Agent)     │
                          └───────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   AI Agent Orchestrator    │
                    │   - OpenAI/LangChain       │
                    │   - Multi-turn capability  │
                    │   - Simulate resolution    │
                    └─────────────┬──────────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
        ┌───────▼────────┐  ┌────▼────────┐  ┌────▼────────────┐
        │  Agent Logics  │  │  Refund     │  │  Reschedule    │
        │  - Draft Email │  │  Simulator  │  │  Simulator     │
        │  - Status Upd  │  │             │  │                │
        └────────────────┘  └─────────────┘  └────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   REST API Layer (FastAPI) │
                    │   - /detect-deviation      │
                    │   - /trigger-agent         │
                    │   - /view-response         │
                    │   - /kpi-dashboard         │
                    └─────────────┬──────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   Response Storage & Log   │
                    │   (Agent decisions/output) │
                    └────────────────────────────┘
```

---

## 3. Component Roles

### 3.1 Data Ingestion & Storage
**Responsibility:** Load, validate, and store retail order-to-ship data  
**Technology:** Pandas, CSV in-memory cache  
**Key Tasks:**
- Parse Kaggle Customer Analytics Dataset
- Preprocess missing values, outliers
- Derive timestamp fields (promised date, expected delivery)
- Cache in DataFrame or SQLite for quick access

---

### 3.2 KPI Calculation Module
**Responsibility:** Compute operational KPIs from raw data  
**Technology:** Pandas, NumPy, rule-based logic  
**KPIs to Implement:**
- **Predicted Delivery Delay** - Heuristic/ML model to forecast late shipments
- **Segment Risk Score** - Aggregate delay frequency by customer segment
- **Fulfillment Gap** - Order shipped but delivery > promised + buffer
- **On-Time Delivery Rate** - % of orders delivered on time per period

**Output:** KPI DataFrame with timestamps and thresholds

---

### 3.3 Risk Detection & Deviation Engine
**Responsibility:** Identify orders/shipments that breach KPI thresholds  
**Technology:** Rule-based thresholds, optional lightweight ML  
**Logic:**
- Compare current KPIs against defined thresholds
- Flag high-risk orders (e.g., delay probability > 70%)
- Categorize severity (critical, warning, info)
- Generate deviation events

**Output:** Deviation alerts with order IDs, risk scores, reasons

---

### 3.4 Event Queue / Pub-Sub
**Responsibility:** Trigger agent when deviation detected  
**Technology:** Simple in-memory queue or Redis (optional)  
**Behavior:**
- Consumer listens for deviation events
- Queues agent execution requests
- Ensures no duplicate triggers
- Logs all events for audit

---

### 3.5 AI Agent Orchestrator
**Responsibility:** Execute autonomous resolution logic  
**Technology:** OpenAI API, LangChain, or custom rules  
**Multi-Turn Capabilities:**
- Receive deviation event → analyze context
- Generate resolution strategy (refund, reschedule, customer communication)
- Simulate multi-step resolution (e.g., "Check refund eligibility" → "Draft email" → "Update order status")
- Log decision trail for transparency

**Agents to Support:**
- **Delivery Agent** - Reschedule shipment, contact carrier
- **Customer Agent** - Draft apology email, offer compensation
- **Refund Agent** - Evaluate refund eligibility, simulate refund

---

### 3.6 REST API Layer
**Responsibility:** Expose system functionality via HTTP  
**Technology:** FastAPI with Swagger documentation  
**Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check |
| `/kpi/compute` | POST | Trigger KPI calculation |
| `/kpi/dashboard` | GET | View current KPI values |
| `/detect-deviation` | POST | Run deviation detection |
| `/deviations` | GET | List recent deviations |
| `/trigger-agent` | POST | Manually trigger agent on deviation |
| `/agent-response/{id}` | GET | Fetch agent resolution output |
| `/orders/{id}` | GET | Order status + KPI details |

---

### 3.7 Logging & Monitoring
**Responsibility:** Audit trail, error tracking, performance metrics  
**Technology:** Python logging, optional Prometheus/CloudWatch  
**Logs:**
- All KPI calculations
- Deviation events with timestamps
- Agent triggers and decisions
- API requests/responses

---

## 4. Tech Stack Justification

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Data Processing** | Pandas, NumPy | Fast, familiar, DSL for tabular data; ideal for CSV |
| **KPI Logic** | Python, Pandas | Type-safe, modular, easy to unit test |
| **API** | FastAPI | Async, auto-docs (Swagger), lightweight, modern |
| **ML/AI** | OpenAI API + LangChain | State-of-the-art LLM capabilities; abstracts prompt logic |
| **Scheduler** | APScheduler (Python) | Lightweight; run periodic KPI calculations |
| **Containerization** | Docker + Docker Compose | Cloud-native, reproducible environments |
| **VCS** | Git + GitHub | Standard, easy collaboration, CI/CD ready |
| **Testing** | pytest | Comprehensive, fixtures, plugin ecosystem |
| **Documentation** | Markdown + OpenAPI | Version-controlled, auto-generated API docs |

---

## 5. Deployment Setup

### 5.1 Local Development
```bash
# Clone repo
git clone https://github.com/scriperdj/fulfillment_ai.git
cd fulfillment_ai

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install deps
pip install -r requirements.txt

# Run API
uvicorn src.api:app --reload

# Run tests
pytest tests/
```

### 5.2 Docker Deployment
```bash
# Build image
docker build -t fulfillment_ai:latest .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  fulfillment_ai:latest

# Or use docker-compose
docker-compose up -d
```

### 5.3 Production Considerations
- Environment-based config (`.env` files)
- API key management (secrets, not in code)
- Persistent storage for agent responses (PostgreSQL/MongoDB optional)
- Monitoring & alerting setup
- CI/CD pipeline (GitHub Actions)

---

## 6. Assumptions & Limitations

### Assumptions
1. **Data Quality** - Kaggle dataset is representative of real retail order flows
2. **Single Agent Instance** - One agent at a time (can extend to multi-agent later)
3. **Simulated Resolutions** - Refund/reschedule are simulated, not real transactions
4. **Synchronous Processing** - KPI calc runs on-demand (can make async with scheduler)
5. **No Authentication** - Open API for Garage demo (add OAuth in production)
6. **In-Memory Cache** - Data cached in RAM for this phase (use DB for scale)

### Limitations
1. **ML Models** - Using heuristics for delay prediction (can train real ML model)
2. **No Streaming** - Batch KPI calculation, not real-time (Kafka optional extension)
3. **Single Data Source** - Only CSV input (extend with APIs later)
4. **No Multi-Agent Coordination** - Agents don't communicate (future work)
5. **Limited Agent Memory** - Agent context window is basic (can enhance with RAG)

---

## 7. Future Extensions

### Near-term
- [ ] Multi-agent system (shipment, payment, customer agents)
- [ ] Lightweight RAG knowledge base for agent context
- [ ] Streaming KPI updates via APScheduler
- [ ] Streamlit UI for monitoring/interaction
- [ ] PostgreSQL for persistent data & audit logs
- [ ] GitHub Actions for CI/CD + Docker push

### Medium-term
- [ ] Kafka-based event streaming for real-time KPI
- [ ] ML-based delay prediction (XGBoost/LightGBM)
- [ ] Multi-turn conversation history in agent
- [ ] Email/SMS integration for customer communication
- [ ] Metrics dashboard (Prometheus + Grafana)

### Long-term
- [ ] Process Mining integration (Celonis platform)
- [ ] Advanced RL agent for optimization
- [ ] Multi-tenant architecture
- [ ] Mobile app for monitoring
- [ ] Integration with ERP/WMS systems

---

## 8. Project Structure

```
fulfillment_ai/
├── ARCHITECTURE.md          # This document
├── README.md                # Getting started guide
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container image
├── docker-compose.yml       # Local dev setup
├── .gitignore               # Git ignore rules
├── .env.example             # Environment template
│
├── src/
│   ├── __init__.py
│   ├── api.py               # FastAPI app
│   ├── config.py            # Config & env vars
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py        # CSV loading logic
│   │   └── preprocessor.py  # Data cleaning
│   │
│   ├── kpi/
│   │   ├── __init__.py
│   │   ├── calculator.py    # KPI computation
│   │   └── definitions.py   # KPI specs/thresholds
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── deviation.py     # Deviation detection logic
│   │   └── threshold.py     # Threshold rules
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # Agent coordinator
│   │   ├── prompts.py       # LLM prompts
│   │   └── handlers/
│   │       ├── delivery.py  # Delivery agent
│   │       ├── customer.py  # Customer agent
│   │       └── refund.py    # Refund agent
│   │
│   └── models/
│       ├── __init__.py
│       ├── schemas.py       # Pydantic models
│       └── database.py      # Optional DB models
│
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_kpi.py
│   ├── test_detection.py
│   ├── test_agent.py
│   └── test_api.py
│
├── data/
│   ├── raw/                 # Original CSV files
│   └── processed/           # Preprocessed data
│
├── logs/
│   └── app.log              # Application logs
│
└── docs/
    ├── setup.md             # Detailed setup
    ├── api_examples.md      # API usage examples
    └── kpi_definitions.md   # KPI specifications
```

---

## 9. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI over Flask** | Auto-generated OpenAPI docs, async support, modern Python |
| **Pandas for data** | Familiar, fast, good for one-off CSV analysis; SQLite for scale |
| **OpenAI API (not local LLM)** | Quality & speed tradeoff; can add local models later |
| **Synchronous API calls** | Simpler for demo; can make async with Celery/RQ |
| **Rule-based thresholds first** | Faster to build; ML models can be plugged in later |
| **No DB by default** | Simplify setup; SQLite/PostgreSQL optional for state |
| **Docker from day 1** | Cloud-native mindset; production-ready from start |

---

## 10. Success Criteria

- ✅ System loads Kaggle dataset without errors
- ✅ KPIs compute and refresh on-demand
- ✅ Deviation detection identifies high-risk orders
- ✅ Agent triggers automatically and generates resolution
- ✅ REST API responds with correct data
- ✅ System is Dockerized and runs in container
- ✅ Code is modular, tested, and documented
- ✅ Architecture justifies design choices

---

## 11. Open Questions / Next Steps

1. **Which KPIs matter most** for the demo? (Delay prediction vs. segment risk?)
2. **How detailed should agent responses** be? (Simple email draft vs. multi-turn conversation?)
3. **Threshold values** - What constitute "high risk"? (70% delay probability? X days late?)
4. **Data enrichment** - Generate synthetic delivery dates or use CSV as-is?
5. **Agent training** - Will you provide sample agent responses to learn from?

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-14  
**Author:** scriperdj  
**Status:** Draft (ready for implementation)
