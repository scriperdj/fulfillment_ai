# fulfillment_ai - Architecture Document

## 1. System Overview & Goals

**Project Name:** fulfillment_ai  
**Purpose:** Autonomous AI-driven system for proactive detection and resolution of retail fulfillment operational issues  
**Use Case:** Process Mining + AI Agents for Order-to-Ship workflow

### Primary Goals
1. **Proactive Risk Detection** - Identify delivery delays before they happen 
2. **Autonomous Resolution** - Trigger AI agents to simulate automatic issue resolution
3. **Operational Visibility** - Real-time KPI monitoring and deviation detection
4. **Extensible Design** - Support multiple agents, KPIs, and data sources

---

## 2. Architecture Diagram (Including Stretch Goals)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           fulfillment_ai System                              │
│                   (Core + Stretch Goals: Streaming, Multi-Agent, RAG, UI)    │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────┐
                    │     Data Ingestion Layer     │
                    ├──────────────────────────────┤
                    │ CSV (Kaggle)  │  Kafka Topics
                    │               │  (Real-time)
                    └────────┬───────────┬──────────┘
                             │           │
          ┌──────────────────▼─┐   ┌─────▼──────────────┐
          │  Batch Processing  │   │  Stream Processing │
          │  (Pandas/Spark)    │   │  (Kafka Consumer)  │
          └──────────┬─────────┘   └─────┬──────────────┘
                     │                   │
                     └────────┬──────────┘
                              │
              ┌───────────────▼──────────────┐
              │   Unified Data Layer         │
              │   (In-Memory + PostgreSQL)   │
              └───────────────┬──────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
     ┌────▼─────┐    ┌────────▼────────┐    ┌────▼──────────────┐
     │ KPI Calc │    │Risk Detection   │    │   RAG Module      │
     │ Module   │    │(ML/Rule-based)  │    │ (Knowledge Base)  │
     │(Async)   │    │                 │    │ - Vector Store    │
     └────┬─────┘    └────────┬────────┘    │ - Embeddings      │
          │                   │              └────┬──────────────┘
          └───────────────────┼──────────────────┘
                              │
                    ┌─────────▼──────────────┐
                    │ Deviation Detector     │
                    │ - Threshold breaches   │
                    │ - Anomaly detection    │
                    └─────────┬──────────────┘
                              │
                ┌─────────────▼──────────────┐
                │  Event Stream / Message Q  │
                │  (Kafka / Redis / RabbitMQ)│
                │  - Deviation events        │
                │  - Agent triggers          │
                └─────────┬──────────────────┘
                          │
        ┌─────────────────┼──────────────────────┐
        │                 │                      │
        │    ┌────────────▼────────────┐   ┌────▼────────────────────┐
        │    │ Multi-Agent Orchestrator│   │  Streaming KPI Scheduler │
        │    │ (LangChain + OpenAI)    │   │  (APScheduler + Kafka)   │
        │    │ - Agent Router          │   │  - Async KPI updates     │
        │    │ - Context Management    │   │  - Real-time streaming   │
        │    │ - Conversation History  │   └────┬────────────────────┘
        │    └────────────┬────────────┘        │
        │                 │                     │
        │  ┌──────────────┴──────────────┐      │
        │  │ Agent Types (Extensible)    │      │
        │  ├──────────────────────────┤      │
        │  │ • Shipment Agent         │      │
        │  │ • Customer Service Agent │      │
        │  │ • Payment/Refund Agent   │      │
        │  │ • (Add more as needed)   │      │
        │  └────────────┬─────────────┘      │
        │               │                    │
        └───────────────┼────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  Response Storage & Audit  │
          │  (PostgreSQL/MongoDB)      │
          │  - Agent decisions         │
          │  - Resolution logs         │
          │  - Conversation history    │
          └─────────────┬──────────────┘
                        │
        ┌───────────────┼──────────────────┐
        │               │                  │
   ┌────▼────────┐ ┌───▼──────────┐  ┌──▼──────────────────┐
   │  REST API   │ │ WebSocket API│  │  Streamlit UI       │
   │  (FastAPI)  │ │ (Real-time)  │  │  (Monitoring Dash)  │
   │  - CRUD     │ │ - KPI stream │  │  - KPI dashboard    │
   │  - Agent    │ │ - Live alerts│  │  - Agent logs       │
   │  - Triggers │ │              │  │  - Order tracking   │
   └─────────────┘ └──────────────┘  │  - Manual triggers  │
                                      └─────────────────────┘
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

### 3.5 Multi-Agent Orchestrator (Core + Stretch Goal)
**Responsibility:** Execute autonomous resolution logic via specialized agents  
**Technology:** OpenAI API, LangChain, RAG modules  
**Core Capabilities:**
- Receive deviation event → analyze context
- Route to appropriate agent (shipment, customer, payment)
- Generate resolution strategy (refund, reschedule, communication)
- Simulate multi-step resolution with conversation history
- Log full decision trail for transparency

**Agent Types (Extensible):**
- **Shipment Agent** - Reschedule shipment, contact carrier, track status
- **Customer Service Agent** - Draft apology/communication, offer compensation
- **Payment/Refund Agent** - Evaluate refund eligibility, simulate refund processing
- **Escalation Agent** - Route complex cases to human support

**Context Management:**
- RAG-powered knowledge base for customer/order context
- Multi-turn conversation memory
- Agent state persistence

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

### 3.7 RAG Knowledge Base (Stretch Goal)
**Responsibility:** Provide context-aware information for agent decision-making  
**Technology:** LangChain, Vector Database (Chroma/Pinecone), OpenAI Embeddings  
**Key Features:**
- Vector store of customer policies, refund rules, SLAs
- Order history embeddings for similarity search
- Real-time knowledge updates
- Retrieval augmentation for agent prompts

**Knowledge Types:**
- Company policies (refund, warranty, shipping)
- Historical agent responses (learning database)
- Customer communication templates
- Regulatory/compliance information

---

### 3.8 Streaming KPI Module (Stretch Goal)
**Responsibility:** Real-time KPI updates and streaming to clients  
**Technology:** Kafka, APScheduler, WebSocket (FastAPI)  
**Architecture:**
- **Kafka Producer** - KPI calc module publishes updates to Kafka topics
- **Kafka Consumer** - Subscribes to KPI streams, updates in-memory cache
- **APScheduler** - Triggers periodic KPI recalculation
- **WebSocket API** - Push KPI updates to connected clients

**Capabilities:**
- Real-time KPI streaming (metrics per order, segment, region)
- Adaptive threshold monitoring
- Historical KPI retention
- Client subscription management

---

### 3.9 Monitoring Dashboard (Stretch Goal)
**Responsibility:** Visual monitoring and manual intervention interface  
**Technology:** Streamlit, Plotly, Pandas  
**Features:**
- Real-time KPI visualization (charts, gauges)
- Deviation alerts (color-coded severity)
- Agent decision logs (searchable, filterable)
- Order tracking with status updates
- Manual agent triggering (for testing)
- RAG knowledge base management

**Views:**
- Dashboard (KPI summary, alerts, stats)
- Orders (search, filter, drill-down)
- Agents (execution logs, decision trails)
- Knowledge Base (add/edit policies)
- Settings (thresholds, configuration)

---

### 3.10 Logging & Monitoring
**Responsibility:** Audit trail, error tracking, performance metrics  
**Technology:** Python logging, ELK Stack (optional), Prometheus  
**Logs:**
- All KPI calculations with timestamps
- Deviation events with severity & context
- Agent triggers, decisions, and outputs
- API requests/responses with latency
- Streaming KPI updates
- User actions (Streamlit dashboard)

---

## 4. Tech Stack Justification

### Core Stack
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

### Stretch Goal Stack
| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Streaming KPI** | Kafka + Zookeeper | Distributed event streaming; scales to high-throughput |
| **Real-time WebSocket** | FastAPI WebSocket | Native async support; lightweight real-time |
| **RAG Vector DB** | Chroma (Embeddings) | Lightweight, in-process; Pinecone (cloud) as alternative |
| **RAG Embeddings** | OpenAI Embeddings API | High-quality semantic search; integrated with LangChain |
| **Monitoring Dashboard** | Streamlit + Plotly | Rapid development; interactive visualizations |
| **Persistence** | PostgreSQL | ACID compliance; good for structured agent data |
| **Message Queue** | Redis (optional) | In-memory queue for event handling; Kafka for scale |

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

### Assumptions (Core)
1. **Data Quality** - Kaggle dataset is representative of real retail order flows
2. **Simulated Resolutions** - Refund/reschedule are simulated, not real transactions
3. **No Authentication** - Open API for Garage demo (add OAuth in production)

### Stretch Goal Assumptions
1. **Kafka Availability** - Kafka cluster available for streaming (can use in-memory queue for MVP)
2. **Vector DB Setup** - Chroma or Pinecone available (can use in-memory embeddings)
3. **PostgreSQL** - Database available for persistence (optional, SQLite fallback)
4. **Streamlit Environment** - Development environment for Streamlit UI

### Limitations (Core)
1. **ML Models** - Using heuristics for delay prediction (can train real ML model)
2. **Single Data Source** - Only CSV input (extend with APIs later)
3. **Limited Agent Memory** - Agent context is basic without RAG

### Stretch Goal Limitations
1. **RAG Knowledge Scope** - Limited to documents provided (can expand with web scraping)
2. **Multi-Agent Coordination** - Agents don't communicate between decisions (v2 feature)
3. **Streaming Latency** - KPI updates depend on Kafka processing time
4. **Streamlit Scalability** - UI designed for single concurrent user (move to React/Vue for scale)

---

## 7. Implementation Scope

### Core Features (MVP)
- ✅ Data loading & preprocessing
- ✅ KPI calculation (synchronous)
- ✅ Deviation detection (rule-based)
- ✅ Single AI agent (OpenAI)
- ✅ REST API
- ✅ Docker setup

### Stretch Goals (Implementation Target)
- 🎯 Multi-agent system (shipment, customer, payment, escalation)
- 🎯 Lightweight RAG knowledge base for agent context
- 🎯 Streaming KPI updates (Kafka + WebSocket)
- 🎯 Streamlit UI for monitoring & interaction
- 🎯 PostgreSQL for persistent data & audit logs
- 🎯 Conversation history & multi-turn agent memory
- 🎯 GitHub Actions CI/CD pipeline

### Future Extensions (v2+)
- [ ] ML-based delay prediction (XGBoost/LightGBM)
- [ ] Email/SMS integration for customer communication
- [ ] Metrics dashboard (Prometheus + Grafana)
- [ ] Process Mining integration (Celonis platform)
- [ ] Advanced RL agent for optimization
- [ ] Multi-tenant architecture
- [ ] Mobile app for monitoring
- [ ] ERP/WMS system integrations
- [ ] Multi-region deployment
- [ ] Advanced agent reasoning (o1, Claude 3)

---

## 8. Project Structure (Core + Stretch Goals)

```
fulfillment_ai/
├── ARCHITECTURE.md          # This document
├── README.md                # Getting started guide
├── requirements.txt         # Python dependencies
├── requirements-streaming.txt # Optional: Kafka, Streamlit
├── Dockerfile               # Container image
├── docker-compose.yml       # Local dev setup
├── docker-compose-full.yml  # Full setup with Kafka, PostgreSQL, Redis
├── .gitignore               # Git ignore rules
├── .env.example             # Environment template
│
├── src/
│   ├── __init__.py
│   ├── api.py               # FastAPI app (core + WebSocket endpoints)
│   ├── config.py            # Config & env vars
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── loader.py        # CSV loading logic
│   │   └── preprocessor.py  # Data cleaning & feature engineering
│   │
│   ├── kpi/
│   │   ├── __init__.py
│   │   ├── calculator.py    # KPI computation (sync)
│   │   ├── calculator_async.py # Async KPI calculation
│   │   ├── definitions.py   # KPI specs/thresholds
│   │   └── streamer.py      # Streaming KPI updates (STRETCH GOAL)
│   │
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── deviation.py     # Deviation detection logic
│   │   ├── threshold.py     # Threshold rules
│   │   └── event_publisher.py # Kafka event publishing
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── orchestrator.py  # Multi-agent coordinator (STRETCH GOAL)
│   │   ├── prompts.py       # LLM prompts with RAG context
│   │   ├── handlers/
│   │   │   ├── base_agent.py      # Base agent class
│   │   │   ├── shipment.py        # Shipment agent
│   │   │   ├── customer.py        # Customer service agent
│   │   │   ├── refund.py          # Refund agent
│   │   │   └── escalation.py      # Escalation agent
│   │   └── state_manager.py # Conversation history/memory
│   │
│   ├── rag/                 # RAG Knowledge Base (STRETCH GOAL)
│   │   ├── __init__.py
│   │   ├── knowledge_base.py # Vector store & embeddings
│   │   ├── document_loader.py # Load policies, templates
│   │   ├── retriever.py     # RAG retrieval logic
│   │   └── updater.py       # Update knowledge base
│   │
│   ├── streaming/           # Streaming & Real-time (STRETCH GOAL)
│   │   ├── __init__.py
│   │   ├── kafka_producer.py # Kafka producer for KPI events
│   │   ├── kafka_consumer.py # Kafka consumer for KPI updates
│   │   ├── scheduler.py     # Periodic KPI scheduler
│   │   └── websocket_manager.py # WebSocket connection management
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py       # Pydantic models
│   │   └── database.py      # SQLAlchemy DB models (PostgreSQL)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logger.py        # Logging configuration
│       └── cache.py         # Caching utilities
│
├── ui/                      # Streamlit Dashboard (STRETCH GOAL)
│   ├── __init__.py
│   ├── app.py               # Main Streamlit app
│   ├── pages/
│   │   ├── dashboard.py     # KPI dashboard
│   │   ├── orders.py        # Order search & tracking
│   │   ├── agents.py        # Agent logs & triggers
│   │   ├── knowledge_base.py # RAG KB management
│   │   └── settings.py      # Configuration UI
│   └── components/
│       ├── charts.py        # Visualization components
│       └── tables.py        # Data table components
│
├── tests/
│   ├── __init__.py
│   ├── test_data.py
│   ├── test_kpi.py
│   ├── test_detection.py
│   ├── test_agent.py
│   ├── test_api.py
│   ├── test_rag.py          # RAG module tests
│   ├── test_streaming.py    # Streaming module tests
│   └── fixtures/            # Test fixtures and mocks
│
├── data/
│   ├── raw/                 # Original CSV files
│   ├── processed/           # Preprocessed data
│   └── knowledge/           # RAG knowledge documents
│
├── logs/
│   └── app.log              # Application logs
│
├── docs/
│   ├── setup.md             # Detailed setup
│   ├── setup-streaming.md   # Kafka & streaming setup
│   ├── api_examples.md      # API usage examples
│   ├── kpi_definitions.md   # KPI specifications
│   ├── agent_design.md      # Multi-agent architecture
│   └── rag_guide.md         # RAG knowledge base guide
│
└── config/
    ├── kafka/               # Kafka configuration files
    │   └── topics.yaml      # KPI topic definitions
    ├── rag/                 # RAG configuration
    │   └── policies.yaml    # Policy templates
    └── agents/              # Agent configuration
        └── agents.yaml      # Agent role definitions
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

## 11. Stretch Goal Design Decisions

### Streaming & Real-Time KPI
- **Kafka vs Redis:** Kafka for scalability and durability; Redis as fallback for simplicity
- **Update Frequency:** Configurable (default: 5-minute intervals)
- **WebSocket Broadcasting:** Selective updates (only connected clients receive streams)

### Multi-Agent System
- **Agent Router:** LangChain's function calling for intelligent agent selection
- **Fallback Strategy:** Escalation agent for unhandled cases
- **Agent Specialization:** Each agent has specific prompts and allowed actions

### RAG Knowledge Base
- **Vector Store:** Chroma (development) → Pinecone (production)
- **Embedding Model:** OpenAI's text-embedding-3-small
- **Update Strategy:** Manual + automated ingestion of new policies
- **Retrieval:** Top-5 relevant documents per agent query

### Streamlit Dashboard
- **Responsiveness:** Real-time KPI updates via WebSocket
- **User Actions:** Manual agent triggering, threshold adjustment
- **Data Refresh:** Configurable auto-refresh intervals
- **Multi-page:** Modular pages for different admin views

---

## 12. Open Questions / Next Steps

### Core Implementation
1. **Which KPIs matter most** for the demo? (Delay prediction vs. segment risk?)
2. **How detailed should agent responses** be? (Simple email draft vs. multi-turn conversation?)
3. **Threshold values** - What constitute "high risk"? (70% delay probability? X days late?)
4. **Data enrichment** - Generate synthetic delivery dates or use CSV as-is?

### Stretch Goals
5. **Kafka Setup** - Use Docker Kafka or assume existing cluster?
6. **Vector DB** - Start with Chroma in-memory or Pinecone cloud?
7. **Agent Knowledge** - What policies/documents should be in RAG KB?
8. **Dashboard Features** - Priority features for Streamlit MVP?
9. **Multi-Agent Routing** - How to determine which agent to use?

---

**Document Version:** 2.0 (Updated with Stretch Goals)  
**Last Updated:** 2026-02-14  
**Author:** scriperdj  
**Status:** Ready for implementation (Core + Stretch Goals)
