<rpg-method>
# Fulfillment AI - Product Requirements Document
## AI-Driven Retail Fulfillment Risk Detection & Autonomous Resolution

This PRD follows the Repository Planning Graph (RPG) methodology. It is structured for `task-master parse-prd` to generate a dependency-aware task graph from the ARCHITECTURE.md specification.
</rpg-method>

---

<overview>

## Problem Statement

Retail fulfillment operations lack proactive visibility into delivery delays. Issues are detected reactively — after a customer complains or a shipment misses its SLA — resulting in costly interventions, poor customer experience, and cascading operational failures. There is no unified system that predicts delays before they happen, monitors operational KPIs in real time, and autonomously triggers corrective actions.

## Target Users

- **Operations Managers**: Need real-time visibility into fulfillment health, delay predictions, and KPI dashboards to make informed decisions.
- **Customer Service Teams**: Need automated first-response for at-risk orders (proactive notifications, refund processing) before customers escalate.
- **Engineering/ML Teams**: Need an extensible platform to add new models, agents, data sources, and KPIs without rearchitecting the system.
- **Demo/Portfolio Audience**: This is a portfolio project demonstrating end-to-end ML + AI agent orchestration in a realistic retail fulfillment domain.

## Success Metrics

- ML model achieves >= 0.65 ROC-AUC on the Kaggle test set for delay prediction
- Batch CSV upload returns predictions for 10K+ rows within 60 seconds via Airflow DAG
- Streaming pipeline processes micro-batches (15s / 1K messages) with end-to-end latency under 30 seconds
- Multi-agent system triggers appropriate specialist agent(s) for >= 90% of critical deviations
- RAG retrieval returns relevant policy documents with cosine similarity >= 0.7 for agent queries
- All services start successfully via a single `docker-compose up` command

</overview>

---

<functional-decomposition>

## Capability Tree

### Capability: Project Foundation
Core infrastructure, configuration, logging, and database models that all other modules depend on.

#### Feature: Project configuration and environment management
- **Description**: Centralized configuration loading from environment variables and `.env` files for database URLs, Kafka brokers, model paths, API keys, and thresholds.
- **Inputs**: `.env` file, environment variables
- **Outputs**: Config object accessible by all modules
- **Behavior**: Load env vars at startup, validate required keys exist, provide typed accessors with defaults for optional values.

#### Feature: Structured logging
- **Description**: JSON-structured logging utility used across all modules for consistent audit trails.
- **Inputs**: Log level, message, contextual metadata (order_id, batch_job_id, etc.)
- **Outputs**: Structured JSON log entries to stdout
- **Behavior**: Format logs with timestamp, module name, level, and structured context fields. Support correlation IDs for request tracing.

#### Feature: PostgreSQL database models and connection management
- **Description**: SQLAlchemy ORM models for batch_jobs, predictions, deviations, and agent_responses tables, plus connection pool management.
- **Inputs**: Database URL from config
- **Outputs**: ORM models, session factory, migration scripts
- **Behavior**: Define four core tables with FK chain (batch_jobs → predictions → deviations → agent_responses). Provide async session management for FastAPI and sync sessions for Airflow tasks. Include Alembic migrations.

#### Feature: Database initialization and seeding
- **Description**: Script to create database tables and seed initial data if needed.
- **Inputs**: Database connection, ORM models
- **Outputs**: Initialized database schema
- **Behavior**: Run CREATE TABLE IF NOT EXISTS for all models. Idempotent — safe to run multiple times.

---

### Capability: ML Model Training
Jupyter notebook-based pipeline to train a binary classifier for delivery delay prediction using the Kaggle Customer Analytics dataset.

#### Feature: Exploratory data analysis (EDA)
- **Description**: Analyze the Kaggle dataset (10,999 rows, 12 columns) for distributions, correlations, class balance, and feature importance.
- **Inputs**: Raw Kaggle CSV (`data/raw/ecommerce_shipping.csv`)
- **Outputs**: Visualization plots, statistical summaries, documented findings in notebook markdown cells
- **Behavior**: Generate histograms for all features, correlation heatmap, class balance bar chart (Reached.on.Time_Y.N), and identify any data quality issues (nulls, outliers).

#### Feature: Feature engineering and preprocessing pipeline
- **Description**: Build a scikit-learn preprocessing pipeline that encodes categoricals and scales numerics, matching the 10 model input features.
- **Inputs**: Raw DataFrame with 12 columns
- **Outputs**: Transformed feature matrix (10 features), fitted preprocessing pipeline object
- **Behavior**: OneHot or Label encode `Warehouse_block`, `Mode_of_Shipment`, `Product_importance`, `Gender`. Pass through numeric features. Export fitted pipeline as `models/preprocessor.joblib`.

#### Feature: Model selection and training
- **Description**: Train and compare multiple classifiers (LogisticRegression, RandomForest, XGBoost, LightGBM) using cross-validation, then select the best.
- **Inputs**: Preprocessed feature matrix, target labels, 80/20 train/test split
- **Outputs**: Trained best model, comparison table of all models
- **Behavior**: 5-fold stratified cross-validation for each model. Compare by ROC-AUC, F1, Precision, Recall. Select best model by ROC-AUC.

#### Feature: Model evaluation and export
- **Description**: Evaluate the best model on the held-out test set and export artifacts.
- **Inputs**: Best trained model, test set
- **Outputs**: `models/delay_classifier.joblib`, `models/preprocessor.joblib`, `models/model_metadata.json` (metrics, feature names, threshold)
- **Behavior**: Generate confusion matrix, ROC curve, classification report. Serialize model + preprocessor via joblib. Write metadata JSON with accuracy, ROC-AUC, F1, optimal threshold, feature list, and training timestamp.

---

### Capability: ML Inference Service
Load trained model artifacts and run predictions on new enriched order data.

#### Feature: Model loading and initialization
- **Description**: Load `delay_classifier.joblib` and `preprocessor.joblib` into memory once at startup for fast inference.
- **Inputs**: File paths to model artifacts from config
- **Outputs**: In-memory model and preprocessor objects
- **Behavior**: Load on FastAPI lifespan startup and Airflow worker initialization. Validate model metadata matches expected feature set. Raise clear error if artifacts missing.

#### Feature: Single-order prediction
- **Description**: Accept a single order JSON, preprocess it, and return the delay probability and severity classification.
- **Inputs**: JSON object with enriched order fields (10 model features + metadata)
- **Outputs**: `{ delay_probability: float, severity: str, order_id: str }`
- **Behavior**: Extract 10 features, apply preprocessor transform, run `model.predict_proba()`, classify severity (critical >0.7, warning >0.5, info >0.3, none <=0.3). Return synchronously.

#### Feature: Batch prediction
- **Description**: Accept a DataFrame of orders, run vectorized inference, and return predictions for all rows.
- **Inputs**: Pandas DataFrame with enriched order columns
- **Outputs**: DataFrame with added `delay_probability` and `severity` columns
- **Behavior**: Vectorized preprocessing + `model.predict_proba()` on entire DataFrame. Much faster than row-by-row. Used by both batch CSV and streaming micro-batch paths.

---

### Capability: Data Ingestion and Validation
Handle CSV upload for batch processing and validate enriched order schema for both batch and streaming inputs.

#### Feature: CSV file upload and batch job creation
- **Description**: Accept CSV file via API, save to disk, create a `batch_jobs` record in Postgres with status `pending`, and return a `batch_job_id`.
- **Inputs**: Multipart CSV file upload via POST `/predict/batch`
- **Outputs**: `{ batch_job_id: UUID }` response, CSV saved to disk, batch_jobs row created
- **Behavior**: Validate file is CSV, save to `data/uploads/{batch_job_id}.csv`, insert batch_jobs row (status=pending, row_count from CSV), return batch_job_id immediately (async processing).

#### Feature: Schema validation for enriched order data
- **Description**: Validate that input data (CSV rows or Kafka messages) conform to the 18-field enriched schema.
- **Inputs**: DataFrame or dict with order fields
- **Outputs**: Validation result (pass/fail) + list of errors
- **Behavior**: Check required fields exist (order_id, warehouse_block, mode_of_shipment, customer_care_calls, customer_rating, cost_of_product, prior_purchases, product_importance, gender, discount_offered, weight_in_gms). Validate types and value ranges. Allow nullable fields (ship_date, delivery_date for in-transit orders). Return detailed error list for invalid rows.

#### Feature: Batch job status tracking
- **Description**: Track and expose batch job lifecycle (pending → processing → completed → failed).
- **Inputs**: batch_job_id
- **Outputs**: Status object with progress, timestamps, error messages
- **Behavior**: Update status in Postgres as processing progresses. Expose via GET `/batch/{id}/status`. On failure, store error_message and set status=failed.

---

### Capability: Feature Engineering (Transform Layer)
Convert enriched upstream order data into the 10 features expected by the ML model.

#### Feature: Feature extraction from enriched schema
- **Description**: Extract the 10 model features from the 18-field enriched input schema, applying the same encoding used during training.
- **Inputs**: Enriched order data (DataFrame or dict with 18 fields)
- **Outputs**: Feature vector (10 features) ready for model inference, plus passthrough of raw fields for KPI calculations
- **Behavior**: Select `warehouse_block`, `mode_of_shipment`, `customer_care_calls`, `customer_rating`, `cost_of_product`, `prior_purchases`, `product_importance`, `gender`, `discount_offered`, `weight_in_gms`. Apply loaded `preprocessor.joblib` transform. Keep raw date/status fields separate for KPI engine.

---

### Capability: KPI Calculation Engine
Compute operational KPIs from predictions and historical data using 30-day rolling windows.

#### Feature: Per-order KPI computation
- **Description**: Calculate per-order metrics: Predicted Delivery Delay (delay_probability) and Fulfillment Gap (shipped but likely to miss window).
- **Inputs**: Prediction result (delay_probability, severity), order metadata (order_status)
- **Outputs**: Per-order KPI dict with delay_probability and fulfillment_gap flag
- **Behavior**: Fulfillment Gap = True when `order_status == 'shipped'` AND `delay_probability > threshold`. Threshold from config.

#### Feature: Running average KPI computation (30-day rolling)
- **Description**: Compute aggregate KPIs from historical predictions: Segment Risk Score, On-Time Delivery Rate, High-Risk Order Count.
- **Inputs**: Current predictions DataFrame, PostgreSQL predictions table (30-day window)
- **Outputs**: Aggregated KPI dict grouped by segment (warehouse_block, mode_of_shipment, product_importance)
- **Behavior**: Query `SELECT * FROM predictions WHERE created_at > NOW() - INTERVAL '30 days'`. Compute: avg delay_probability per segment (Segment Risk Score), % below threshold per segment (On-Time Delivery Rate), count above threshold (High-Risk Order Count). Merge with current batch predictions.

#### Feature: KPI dashboard data endpoint
- **Description**: Provide current KPI values via API for dashboard consumption.
- **Inputs**: GET `/kpi/dashboard` request
- **Outputs**: JSON with all running average KPIs and recent per-order KPIs
- **Behavior**: Query latest aggregate KPIs from Postgres. Return formatted response with segment breakdowns and trend data.

---

### Capability: Risk Detection and Deviation Engine
Identify orders that require intervention based on ML predictions and KPI breaches.

#### Feature: Threshold-based deviation detection
- **Description**: Classify predictions into severity levels and generate deviation records for orders exceeding warning threshold.
- **Inputs**: Prediction results with delay_probability and order context
- **Outputs**: List of deviation records (severity, reason, order context)
- **Behavior**: Apply thresholds: critical (>0.7), warning (>0.5), info (>0.3). Generate deviation record with severity, reason text, prediction_id FK. Store in Postgres deviations table.

#### Feature: KPI breach detection
- **Description**: Detect when segment-level KPIs breach acceptable thresholds (e.g., segment risk score spike, on-time rate drop).
- **Inputs**: Current KPI values, historical baselines
- **Outputs**: Additional deviation events for KPI breaches
- **Behavior**: Compare current segment KPIs against configurable thresholds. Generate deviation events when segment risk exceeds baseline by configurable margin. Combine with per-order deviations.

#### Feature: Deviation event publishing
- **Description**: Publish critical/warning deviations to Kafka `deviation-events` topic for agent consumption.
- **Inputs**: Deviation records with severity >= warning
- **Outputs**: Messages published to `deviation-events` Kafka topic
- **Behavior**: Serialize deviation + full order context to JSON. Publish to Kafka with order_id as message key (ensures ordering per order). Only publish severity >= warning (configurable).

---

### Capability: Unified Processing Pipeline
Orchestrate the full transform → inference → KPI → deviation flow as a single atomic job, shared by batch and streaming paths.

#### Feature: Pipeline orchestrator
- **Description**: Execute the four-step processing pipeline as a single function call, usable by both Airflow batch and streaming DAGs.
- **Inputs**: DataFrame of enriched orders (from CSV or Kafka micro-batch), source label ('batch' or 'streaming'), optional batch_job_id
- **Outputs**: Predictions stored in Postgres, deviations stored in Postgres, critical deviations published to Kafka
- **Behavior**: Call feature engineering → ML inference → store predictions → KPI computation → deviation detection → store deviations → publish deviation events. Single transaction boundary for DB writes. Return summary (prediction count, deviation count, severity breakdown).

---

### Capability: Kafka Event Infrastructure
Event streaming setup using Redpanda (Kafka-compatible) for fulfillment events and deviation routing.

#### Feature: Kafka topic management and producer/consumer utilities
- **Description**: Utility module for Kafka producer and consumer setup, topic creation, and message serialization.
- **Inputs**: Kafka broker URL from config, topic names
- **Outputs**: Producer and consumer instances, topic management functions
- **Behavior**: Create topics (`fulfillment-events`, `deviation-events`) if they don't exist. Provide async producer with JSON serialization. Provide consumer group management. Handle connection retries.

#### Feature: Kafka producer simulator
- **Description**: Standalone service that generates synthetic enriched order events and publishes them to `fulfillment-events` topic at configurable intervals.
- **Inputs**: Configuration (event rate, warehouse distribution, shipment mode distribution)
- **Outputs**: Enriched order events published to `fulfillment-events` topic
- **Behavior**: Generate realistic enriched order data matching the 18-field schema. Randomize fields within realistic distributions (warehouse blocks A-E, shipment modes Ship/Flight/Road, etc.). Simulate upstream system data (OMS, WMS, TMS, CRM, PIM, Pricing). Configurable events-per-second rate. Run as continuous Docker service.

---

### Capability: Airflow Orchestration
Three Airflow 3.x DAGs managing batch processing, streaming consumption, and agent orchestration.

#### Feature: Batch processing DAG
- **Description**: Airflow DAG triggered by API when a CSV is uploaded. Loads CSV, runs unified pipeline, updates batch job status.
- **Inputs**: `batch_job_id` passed as DAG run config
- **Outputs**: Predictions and deviations stored in Postgres, batch_job status updated to completed/failed
- **Behavior**: Task 1: Load CSV by batch_job_id path. Task 2: Validate schema. Task 3: Run unified processing pipeline. Task 4: Update batch_job status. Error handling: set status=failed with error_message on any task failure.

#### Feature: Streaming DAG with Kafka consumer trigger
- **Description**: Airflow DAG using Kafka consumer trigger on `fulfillment-events`. Collects micro-batches and runs unified pipeline.
- **Inputs**: Messages from `fulfillment-events` Kafka topic
- **Outputs**: Predictions and deviations in Postgres, deviation events to Kafka
- **Behavior**: Kafka trigger collects messages until 15 seconds elapsed OR 1,000 messages buffered. Deserialize messages into DataFrame. Run unified pipeline on micro-batch. Bulk insert predictions/deviations. Publish critical deviations to `deviation-events`.

#### Feature: Agent orchestration DAG
- **Description**: Airflow DAG using Kafka consumer trigger on `deviation-events`. Triggers multi-agent orchestrator for each deviation.
- **Inputs**: Messages from `deviation-events` Kafka topic
- **Outputs**: Agent responses stored in Postgres and ingested into RAG
- **Behavior**: Deserialize deviation event. Call multi-agent orchestrator with deviation context. Store agent response in Postgres. Ingest resolution into RAG knowledge base.

---

### Capability: RAG Knowledge Base
Vector-based knowledge retrieval system using Chroma and OpenAI embeddings for agent decision support.

#### Feature: Policy document ingestion (static, at startup)
- **Description**: Load and embed policy/SLA markdown documents from `knowledge_base/` directory into Chroma at application startup.
- **Inputs**: Markdown files from `knowledge_base/policies/`, `knowledge_base/slas/`, `knowledge_base/templates/`
- **Outputs**: Embedded document chunks stored in Chroma (persisted to `data/chroma_db/`)
- **Behavior**: Use LangChain TextSplitter to chunk documents. Embed with OpenAI `text-embedding-3-small`. Store in Chroma with metadata (category, agent_type, source_file). Skip if Chroma already populated (idempotent startup).

#### Feature: Policy document creation
- **Description**: Create the actual policy/SLA markdown documents that agents will reference for decision-making.
- **Inputs**: Domain knowledge about shipping, refunds, escalation, and communication policies
- **Outputs**: Markdown files in `knowledge_base/` directory structure
- **Behavior**: Create shipping_policy.md (mode upgrade rules, weight limits, carrier selection), refund_policy.md (eligibility, compensation tiers), escalation_criteria.md (when to escalate, priority levels), communication_guidelines.md (tone, templates), carrier_slas.md (delivery time guarantees), warehouse_slas.md (processing times).

#### Feature: Historical resolution ingestion (runtime)
- **Description**: After every agent resolution, embed and store the decision in Chroma for future agent reference.
- **Inputs**: Agent response (action, details, order context, severity)
- **Outputs**: New document in Chroma with resolution metadata
- **Behavior**: Format resolution as text document with order context + decision + outcome. Embed and store with metadata (agent_type, severity, warehouse, shipment_mode). Enables "How did we handle a similar delay before?" queries.

#### Feature: Knowledge retrieval (pre-execution and on-demand)
- **Description**: Retrieve relevant knowledge for agent context — both automatically before agent calls and as an agent tool during reasoning.
- **Inputs**: Query string (constructed from deviation context or agent request), optional metadata filters (agent_type)
- **Outputs**: Top-5 relevant document chunks with similarity scores
- **Behavior**: Pre-execution: orchestrator constructs query from deviation context, retrieves top-5 filtered by agent_type, injects into agent prompt. On-demand: agents call `search_knowledge_base(query)` tool during multi-turn reasoning.

#### Feature: Admin knowledge ingestion API
- **Description**: Allow adding new policy documents via API without redeployment.
- **Inputs**: POST `/knowledge/ingest` with content and category
- **Outputs**: Document chunked, embedded, and stored in Chroma
- **Behavior**: Accept content string + category metadata. Chunk, embed, store. Return confirmation with document count.

---

### Capability: Multi-Agent Orchestrator
LLM-based routing system that dispatches deviations to specialized agents for autonomous resolution.

#### Feature: LLM-based deviation router (orchestrator)
- **Description**: Analyze deviation context using an LLM and decide which specialist agent(s) to invoke via function calling.
- **Inputs**: Deviation event (order context, prediction, severity, KPI data)
- **Outputs**: List of agent invocations with routing rationale
- **Behavior**: System prompt describes available agents and their capabilities. LLM uses function calling to select one or more agents (e.g., reschedule shipment AND notify customer). Pass deviation context + retrieved RAG knowledge to selected agents. Aggregate results from all invoked agents.

#### Feature: Shipment agent
- **Description**: Specialist agent for shipping-related resolutions — rescheduling, mode upgrades, warehouse transfers.
- **Inputs**: Deviation context, retrieved shipping policies/SLAs from RAG
- **Outputs**: `{ agent_type: "shipment", action: str, details: dict, conversation_history: list }`
- **Behavior**: System prompt loaded with shipping domain knowledge from RAG. Tools: `reschedule_shipment()`, `check_carrier_status()`, `transfer_warehouse()`. Multi-turn reasoning: analyze → decide → execute tool → evaluate result → conclude. All tools execute simulated business logic.

#### Feature: Customer service agent
- **Description**: Specialist agent for customer communication — emails, notifications, interaction logging.
- **Inputs**: Deviation context, retrieved communication guidelines from RAG
- **Outputs**: `{ agent_type: "customer", action: str, details: dict, conversation_history: list }`
- **Behavior**: System prompt with tone rules and templates from RAG. Tools: `draft_email()`, `send_notification()`, `log_interaction()`. Drafts contextual, empathetic communications based on deviation severity and order details.

#### Feature: Payment/refund agent
- **Description**: Specialist agent for refund eligibility, compensation, and credit issuance.
- **Inputs**: Deviation context, retrieved refund policies from RAG
- **Outputs**: `{ agent_type: "payment", action: str, details: dict, conversation_history: list }`
- **Behavior**: System prompt with refund policy tiers from RAG. Tools: `check_refund_eligibility()`, `issue_refund()`, `apply_credit()`. Follows policy rules for discount-modified refund terms.

#### Feature: Escalation agent
- **Description**: Specialist agent for human escalation — ticket creation, priority assignment, routing.
- **Inputs**: Deviation context, retrieved escalation criteria from RAG
- **Outputs**: `{ agent_type: "escalation", action: str, details: dict, conversation_history: list }`
- **Behavior**: System prompt with escalation priority rules from RAG. Tools: `create_ticket()`, `assign_human()`, `flag_priority()`. Escalates when automated resolution is insufficient or severity exceeds agent authority.

#### Feature: Agent tool implementations (simulated)
- **Description**: Implement all agent tools as real Python functions with simulated business logic.
- **Inputs**: Tool-specific parameters (order_id, amounts, messages, etc.)
- **Outputs**: Structured tool results that agents reason over
- **Behavior**: Each tool is a real function call returning structured JSON. No actual carrier APIs, payment gateways, or email servers. Returns realistic simulated responses (e.g., new tracking ID, refund confirmation number, ticket ID).

#### Feature: Agent response storage and RAG ingestion
- **Description**: Store agent responses in Postgres and ingest into RAG for future reference.
- **Inputs**: Completed agent response (action, details, conversation_history)
- **Outputs**: Row in agent_responses table, new document in Chroma
- **Behavior**: Insert into agent_responses with deviation_id FK. Format resolution as text document. Embed and store in Chroma. Dual-store pattern: Postgres for structured queries, Chroma for semantic retrieval.

---

### Capability: REST API Layer
FastAPI application exposing all system functionality via HTTP endpoints.

#### Feature: Health check and system status
- **Description**: Basic health endpoint and system readiness check.
- **Inputs**: GET `/health`
- **Outputs**: `{ status: "healthy", model_loaded: bool, db_connected: bool, kafka_connected: bool }`
- **Behavior**: Verify model is loaded, DB is reachable, Kafka is connected. Return component-level health.

#### Feature: Single prediction endpoint
- **Description**: Synchronous single-order prediction via POST `/predict`.
- **Inputs**: JSON body with enriched order fields
- **Outputs**: `{ order_id, delay_probability, severity, features_used }`
- **Behavior**: Validate input schema, run feature extraction, call model inference, return prediction immediately.

#### Feature: Batch prediction endpoint
- **Description**: Async batch prediction via POST `/predict/batch` (CSV upload).
- **Inputs**: Multipart CSV file
- **Outputs**: `{ batch_job_id: UUID }` (processing happens asynchronously via Airflow)
- **Behavior**: Save CSV, create batch_jobs record, trigger Airflow batch DAG, return batch_job_id immediately.

#### Feature: Batch results endpoints
- **Description**: Query batch processing results via GET endpoints.
- **Inputs**: GET `/batch/{id}/status`, `/batch/{id}/predictions`, `/batch/{id}/deviations`, `/batch/{id}/agent-responses`
- **Outputs**: JSON arrays of predictions, deviations, or agent responses for the batch
- **Behavior**: Query Postgres by batch_job_id FK. Return paginated results. 404 if batch_job_id not found.

#### Feature: Deviation listing endpoint
- **Description**: List recent deviations with filtering.
- **Inputs**: GET `/deviations` with optional query params (severity, time range, order_id)
- **Outputs**: Paginated list of deviation records
- **Behavior**: Query deviations table with filters. Default to last 24 hours if no time range specified.

#### Feature: Manual agent trigger endpoint
- **Description**: Manually trigger agent orchestration on a specific deviation.
- **Inputs**: POST `/trigger-agent` with deviation_id or order_id
- **Outputs**: `{ status: "triggered", deviation_id, agent_dag_run_id }`
- **Behavior**: Look up deviation, trigger Airflow agent DAG with deviation context, return confirmation.

#### Feature: Order detail endpoint
- **Description**: Full order view with predictions, deviations, and agent actions.
- **Inputs**: GET `/orders/{id}`
- **Outputs**: Combined view of all predictions, deviations, and agent responses for an order
- **Behavior**: Join predictions → deviations → agent_responses by order_id. Return complete order lifecycle.

#### Feature: Knowledge base API endpoints
- **Description**: Endpoints for RAG knowledge base management.
- **Inputs**: POST `/knowledge/ingest` (add document), POST `/knowledge/search` (query)
- **Outputs**: Ingestion confirmation or search results with similarity scores
- **Behavior**: Ingest: chunk, embed, store in Chroma. Search: embed query, similarity search, return top results.

---

### Capability: Docker Compose Infrastructure
Containerized deployment of all services via Docker Compose.

#### Feature: Docker Compose service definitions
- **Description**: Define all services (API, Redpanda, Airflow, Postgres, stream-producer) in docker-compose.yml.
- **Inputs**: Dockerfiles for custom services, official images for infrastructure
- **Outputs**: Running multi-container environment via `docker-compose up`
- **Behavior**: Services: api (FastAPI, port 8000), redpanda (Kafka, port 9092), airflow-webserver (port 8080), airflow-scheduler, postgres (port 5432), stream-producer. Shared network. Volume mounts for models, data, DAGs.

#### Feature: Custom Dockerfiles
- **Description**: Dockerfiles for the FastAPI API service and Kafka producer simulator.
- **Inputs**: Python application code, requirements.txt
- **Outputs**: Docker images for api and stream-producer services
- **Behavior**: Multi-stage builds. Install dependencies, copy source, configure entrypoints. API starts uvicorn. Producer runs simulator script.

#### Feature: Environment configuration
- **Description**: `.env.example` template and docker-compose environment variable passthrough.
- **Inputs**: Template with all required environment variables
- **Outputs**: `.env.example` file documenting all config
- **Behavior**: Document all env vars: DATABASE_URL, KAFKA_BROKER, OPENAI_API_KEY, MODEL_PATH, thresholds. Docker Compose reads from `.env` file.

---

### Capability: Streamlit Monitoring Dashboard (Stretch Goal)
Visual monitoring interface for operational KPIs, deviations, and agent activity.

#### Feature: KPI dashboard view
- **Description**: Real-time KPI visualization with charts and gauges.
- **Inputs**: KPI data from GET `/kpi/dashboard` API
- **Outputs**: Interactive Plotly charts showing segment risk scores, on-time rates, high-risk counts
- **Behavior**: Auto-refresh on configurable interval. Color-coded severity indicators. Segment breakdown charts.

#### Feature: Deviation alerts view
- **Description**: Live feed of deviation alerts with filtering and drill-down.
- **Inputs**: Deviation data from GET `/deviations` API
- **Outputs**: Color-coded alert list with severity, order details, and agent response status
- **Behavior**: Filter by severity, time range. Click to see full deviation + agent response details.

#### Feature: Agent activity view
- **Description**: Searchable log of agent executions with decision trails.
- **Inputs**: Agent response data from API
- **Outputs**: Filterable table of agent actions with conversation history viewer
- **Behavior**: Show agent_type, action, timestamp, order context. Expand to view full multi-turn conversation history.

#### Feature: Order search and tracking view
- **Description**: Search orders by ID and view full lifecycle with prediction scores.
- **Inputs**: Order ID search, GET `/orders/{id}` API
- **Outputs**: Order detail page with prediction, deviations, and agent actions timeline
- **Behavior**: Search bar, result display with prediction probability gauge, deviation history, agent action timeline.

</functional-decomposition>

---

<structural-decomposition>

## Repository Structure

```
fulfillment_ai/
├── src/
│   ├── config/                  # Maps to: Project Foundation
│   │   ├── settings.py          # Environment config loader
│   │   └── __init__.py
│   ├── db/                      # Maps to: Project Foundation (DB)
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── session.py           # Connection pool and session management
│   │   ├── init_db.py           # Database initialization script
│   │   └── __init__.py
│   ├── ml/                      # Maps to: ML Inference Service
│   │   ├── model_loader.py      # Model loading and initialization
│   │   ├── inference.py         # Single and batch prediction
│   │   └── __init__.py
│   ├── ingestion/               # Maps to: Data Ingestion and Validation
│   │   ├── csv_handler.py       # CSV upload, save, batch job creation
│   │   ├── schema_validator.py  # Enriched schema validation
│   │   └── __init__.py
│   ├── features/                # Maps to: Feature Engineering
│   │   ├── transform.py         # Feature extraction from enriched schema
│   │   └── __init__.py
│   ├── kpi/                     # Maps to: KPI Calculation Engine
│   │   ├── calculator.py        # Per-order and running average KPIs
│   │   └── __init__.py
│   ├── detection/               # Maps to: Risk Detection and Deviation Engine
│   │   ├── deviation_detector.py # Threshold + KPI breach detection
│   │   ├── publisher.py         # Kafka deviation event publishing
│   │   └── __init__.py
│   ├── pipeline/                # Maps to: Unified Processing Pipeline
│   │   ├── processor.py         # Orchestrate transform→inference→KPI→deviation
│   │   └── __init__.py
│   ├── kafka/                   # Maps to: Kafka Event Infrastructure
│   │   ├── client.py            # Producer/consumer utilities, topic management
│   │   ├── producer_simulator.py # Synthetic event generator
│   │   └── __init__.py
│   ├── agents/                  # Maps to: Multi-Agent Orchestrator
│   │   ├── orchestrator.py      # LLM-based deviation router
│   │   ├── shipment_agent.py    # Shipping specialist
│   │   ├── customer_agent.py    # Customer service specialist
│   │   ├── payment_agent.py     # Payment/refund specialist
│   │   ├── escalation_agent.py  # Escalation specialist
│   │   ├── tools.py             # Simulated agent tool implementations
│   │   └── __init__.py
│   ├── rag/                     # Maps to: RAG Knowledge Base
│   │   ├── ingestion.py         # Document chunking, embedding, storage
│   │   ├── retrieval.py         # Similarity search and retrieval
│   │   └── __init__.py
│   ├── api/                     # Maps to: REST API Layer
│   │   ├── app.py               # FastAPI app with lifespan
│   │   ├── routes/
│   │   │   ├── health.py        # Health check
│   │   │   ├── predict.py       # Single and batch prediction
│   │   │   ├── batch.py         # Batch results queries
│   │   │   ├── deviations.py    # Deviation listing
│   │   │   ├── agents.py        # Manual trigger and agent responses
│   │   │   ├── orders.py        # Order detail
│   │   │   ├── kpi.py           # KPI dashboard data
│   │   │   └── knowledge.py     # RAG admin endpoints
│   │   └── __init__.py
│   └── logging/                 # Maps to: Project Foundation (Logging)
│       ├── logger.py            # Structured JSON logger
│       └── __init__.py
├── dags/                        # Maps to: Airflow Orchestration
│   ├── batch_processing_dag.py  # Batch DAG
│   ├── streaming_dag.py         # Streaming Kafka consumer DAG
│   └── agent_orchestration_dag.py # Agent DAG
├── notebooks/                   # Maps to: ML Model Training
│   └── model_training.ipynb     # EDA + training + evaluation + export
├── models/                      # ML artifacts (output of training)
│   ├── delay_classifier.joblib
│   ├── preprocessor.joblib
│   └── model_metadata.json
├── knowledge_base/              # Maps to: RAG Knowledge Base (static docs)
│   ├── policies/
│   │   ├── shipping_policy.md
│   │   ├── refund_policy.md
│   │   ├── escalation_criteria.md
│   │   └── communication_guidelines.md
│   ├── slas/
│   │   ├── carrier_slas.md
│   │   └── warehouse_slas.md
│   └── templates/
│       ├── apology_email.md
│       └── refund_confirmation.md
├── data/
│   ├── raw/                     # Kaggle dataset
│   ├── uploads/                 # CSV uploads (batch)
│   └── chroma_db/               # Persisted vector DB
├── dashboard/                   # Maps to: Streamlit Dashboard (stretch)
│   └── app.py
├── tests/
│   ├── test_config.py
│   ├── test_db_models.py
│   ├── test_inference.py
│   ├── test_ingestion.py
│   ├── test_features.py
│   ├── test_kpi.py
│   ├── test_detection.py
│   ├── test_pipeline.py
│   ├── test_kafka.py
│   ├── test_agents.py
│   ├── test_rag.py
│   └── test_api.py
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.producer
├── requirements.txt
├── .env.example
└── alembic/                     # Database migrations
    └── versions/
```

## Module Definitions

### Module: src/config
- **Maps to capability**: Project Foundation
- **Responsibility**: Centralized configuration from environment variables
- **Exports**:
  - `Settings` - Pydantic settings class with typed config values
  - `get_settings()` - Cached settings accessor

### Module: src/db
- **Maps to capability**: Project Foundation (DB)
- **Responsibility**: ORM models, connection management, initialization
- **Exports**:
  - `BatchJob`, `Prediction`, `Deviation`, `AgentResponse` - ORM models
  - `get_session()` - Async session dependency for FastAPI
  - `get_sync_session()` - Sync session for Airflow tasks
  - `init_db()` - Schema creation function

### Module: src/logging
- **Maps to capability**: Project Foundation (Logging)
- **Responsibility**: Structured JSON logging
- **Exports**:
  - `get_logger(name)` - Returns configured logger for a module

### Module: src/ml
- **Maps to capability**: ML Inference Service
- **Responsibility**: Model loading and prediction
- **Exports**:
  - `load_model()` - Load model artifacts into memory
  - `predict_single(order_data)` - Single prediction
  - `predict_batch(df)` - Batch prediction on DataFrame

### Module: src/ingestion
- **Maps to capability**: Data Ingestion and Validation
- **Responsibility**: CSV handling and schema validation
- **Exports**:
  - `save_csv_and_create_job(file)` - Save CSV, create batch job record
  - `validate_schema(data)` - Validate enriched order schema

### Module: src/features
- **Maps to capability**: Feature Engineering
- **Responsibility**: Transform enriched data to model features
- **Exports**:
  - `extract_features(df)` - Extract and preprocess 10 model features

### Module: src/kpi
- **Maps to capability**: KPI Calculation Engine
- **Responsibility**: Compute per-order and running average KPIs
- **Exports**:
  - `compute_order_kpis(predictions_df)` - Per-order KPIs
  - `compute_running_kpis(session)` - 30-day rolling aggregate KPIs

### Module: src/detection
- **Maps to capability**: Risk Detection and Deviation Engine
- **Responsibility**: Detect deviations, publish to Kafka
- **Exports**:
  - `detect_deviations(predictions_df, kpis)` - Generate deviation records
  - `publish_deviations(deviations, kafka_producer)` - Publish to Kafka topic

### Module: src/pipeline
- **Maps to capability**: Unified Processing Pipeline
- **Responsibility**: Orchestrate full processing flow
- **Exports**:
  - `run_pipeline(df, source, batch_job_id, session, kafka_producer)` - Full pipeline execution

### Module: src/kafka
- **Maps to capability**: Kafka Event Infrastructure
- **Responsibility**: Kafka client utilities and event simulation
- **Exports**:
  - `get_producer()` - Async Kafka producer
  - `get_consumer(topic, group_id)` - Kafka consumer
  - `ensure_topics()` - Create topics if not exist

### Module: src/agents
- **Maps to capability**: Multi-Agent Orchestrator
- **Responsibility**: LLM-based agent routing and specialist agents
- **Exports**:
  - `orchestrate(deviation_event)` - Route deviation to agents
  - `ShipmentAgent`, `CustomerAgent`, `PaymentAgent`, `EscalationAgent` - Specialist classes

### Module: src/rag
- **Maps to capability**: RAG Knowledge Base
- **Responsibility**: Document ingestion and retrieval
- **Exports**:
  - `ingest_documents(docs_path)` - Bulk ingest from directory
  - `ingest_resolution(agent_response)` - Ingest single resolution
  - `retrieve(query, agent_type, top_k)` - Similarity search

### Module: src/api
- **Maps to capability**: REST API Layer
- **Responsibility**: FastAPI application with all HTTP endpoints
- **Exports**:
  - `app` - FastAPI application instance

### Module: dags/
- **Maps to capability**: Airflow Orchestration
- **Responsibility**: Airflow DAG definitions
- **Files**: `batch_processing_dag.py`, `streaming_dag.py`, `agent_orchestration_dag.py`

### Module: dashboard/
- **Maps to capability**: Streamlit Dashboard (stretch)
- **Responsibility**: Monitoring UI
- **Files**: `app.py`

</structural-decomposition>

---

<dependency-graph>

## Dependency Chain

### Foundation Layer (Phase 0)
No dependencies — these are built first.

- **src/config (settings)**: Provides centralized configuration for all modules. No dependencies.
- **src/logging (logger)**: Provides structured logging. No dependencies.
- **src/db (models, session, init_db)**: Provides ORM models and database connectivity. Depends on [src/config].

### ML Training Layer (Phase 1)
Can be built in parallel with Foundation — only needs raw Kaggle data.

- **notebooks/model_training.ipynb**: Trains ML model, exports artifacts. Depends on [raw Kaggle dataset]. No code dependency on Foundation, but outputs (`models/*.joblib`) are consumed by later phases.

### Core Processing Layer (Phase 2)
Depends on Foundation + trained model artifacts.

- **src/ml (inference)**: Model loading and prediction. Depends on [src/config, src/logging, model artifacts from Phase 1].
- **src/ingestion (csv_handler, schema_validator)**: Data ingestion and validation. Depends on [src/config, src/logging, src/db].
- **src/features (transform)**: Feature engineering. Depends on [src/config, src/logging, model artifacts from Phase 1 (preprocessor.joblib)].

### KPI and Detection Layer (Phase 3)
Depends on Core Processing.

- **src/kpi (calculator)**: KPI computation. Depends on [src/db, src/config, src/logging].
- **src/detection (deviation_detector)**: Deviation detection. Depends on [src/config, src/logging, src/kpi].

### Event Infrastructure Layer (Phase 4)
Can be built in parallel with Phase 2-3 — only needs config.

- **src/kafka (client)**: Kafka producer/consumer utilities. Depends on [src/config, src/logging].
- **src/detection (publisher)**: Deviation event publishing. Depends on [src/kafka, src/detection].

### Pipeline Integration Layer (Phase 5)
Unifies all processing components.

- **src/pipeline (processor)**: Unified processing pipeline. Depends on [src/features, src/ml, src/kpi, src/detection, src/db, src/kafka].

### Knowledge and Agent Layer (Phase 6)
Depends on Pipeline + Kafka + DB for deviation handling.

- **knowledge_base/ (policy documents)**: Static policy/SLA markdown files. No code dependencies.
- **src/rag (ingestion, retrieval)**: RAG knowledge base. Depends on [src/config, src/logging, knowledge_base/ documents].
- **src/agents (orchestrator, specialists, tools)**: Multi-agent system. Depends on [src/config, src/logging, src/db, src/rag].

### API Layer (Phase 7)
Exposes all functionality via HTTP.

- **src/api (app, routes)**: FastAPI application. Depends on [src/ml, src/ingestion, src/pipeline, src/kpi, src/detection, src/db, src/rag, src/agents].

### Orchestration Layer (Phase 8)
Airflow DAGs that wire everything together.

- **dags/batch_processing_dag.py**: Batch DAG. Depends on [src/pipeline, src/db, src/ingestion].
- **dags/streaming_dag.py**: Streaming DAG. Depends on [src/pipeline, src/kafka, src/db].
- **dags/agent_orchestration_dag.py**: Agent DAG. Depends on [src/agents, src/kafka, src/db, src/rag].
- **src/kafka (producer_simulator)**: Kafka event simulator. Depends on [src/kafka (client), src/config].

### Infrastructure Layer (Phase 9)
Docker Compose and deployment.

- **docker-compose.yml**: Service definitions. Depends on [all modules — packages everything].
- **Dockerfile, Dockerfile.producer**: Container images. Depends on [src/api, src/kafka].
- **.env.example**: Environment template. Depends on [src/config].

### Stretch Layer (Phase 10)
Optional dashboard.

- **dashboard/app.py**: Streamlit dashboard. Depends on [src/api (REST endpoints available)].

</dependency-graph>

---

<implementation-roadmap>

## Development Phases

### Phase 0: Project Foundation
**Goal**: Establish configuration, logging, database models, and project scaffolding that all other modules depend on.

**Entry Criteria**: Clean repository with ARCHITECTURE.md and basic file structure.

**Tasks**:
- [ ] Implement project configuration module (`src/config/settings.py`) (depends on: none)
  - Acceptance criteria: Pydantic Settings class loads DATABASE_URL, KAFKA_BROKER, OPENAI_API_KEY, MODEL_PATH, threshold values from env vars with sensible defaults
  - Test strategy: Unit test config loading with env overrides, test missing required vars raise errors

- [ ] Implement structured logging module (`src/logging/logger.py`) (depends on: none)
  - Acceptance criteria: JSON-formatted log output with timestamp, module, level, and context fields; correlation ID support
  - Test strategy: Unit test log format, context injection, log level filtering

- [ ] Implement PostgreSQL ORM models (`src/db/models.py`) (depends on: config)
  - Acceptance criteria: SQLAlchemy models for batch_jobs, predictions, deviations, agent_responses with correct FK chain, column types, and indexes
  - Test strategy: Unit test model creation, FK constraints, test with in-memory SQLite

- [ ] Implement database session management (`src/db/session.py`) (depends on: config, models)
  - Acceptance criteria: Async session factory for FastAPI, sync session for Airflow, connection pool configuration
  - Test strategy: Integration test session creation, connection pooling

- [ ] Implement database initialization script (`src/db/init_db.py`) (depends on: models, session)
  - Acceptance criteria: Creates all tables idempotently; safe to run multiple times
  - Test strategy: Test create, then re-create without errors

- [ ] Create requirements.txt with all project dependencies (depends on: none)
  - Acceptance criteria: All required packages pinned (fastapi, uvicorn, sqlalchemy, pandas, scikit-learn, xgboost, joblib, kafka-python, langchain, chromadb, openai, streamlit, plotly, apache-airflow, pydantic-settings, alembic, pytest)
  - Test strategy: `pip install -r requirements.txt` succeeds

**Exit Criteria**: Config loads from env, logger produces structured JSON, DB models create tables, all foundation tests pass.

**Delivers**: Other modules can import config, logger, and DB models without errors.

---

### Phase 1: ML Model Training
**Goal**: Train and export the delay prediction model with evaluation metrics.

**Entry Criteria**: Raw Kaggle dataset available in `data/raw/`.

**Tasks**:
- [ ] Download and place Kaggle dataset (`data/raw/ecommerce_shipping.csv`) (depends on: none)
  - Acceptance criteria: CSV file with 10,999 rows and 12 columns present in data/raw/
  - Test strategy: Verify file existence, row count, column names

- [ ] Implement EDA section in notebook (`notebooks/model_training.ipynb`) (depends on: Kaggle dataset)
  - Acceptance criteria: Distribution plots for all features, correlation heatmap, class balance analysis, data quality summary
  - Test strategy: Notebook runs end-to-end without errors; visual inspection of outputs

- [ ] Implement feature engineering and preprocessing pipeline in notebook (depends on: EDA)
  - Acceptance criteria: Scikit-learn Pipeline with categorical encoding, numeric passthrough for 10 features, exports `models/preprocessor.joblib`
  - Test strategy: Preprocessor transforms sample data without errors; output shape matches expected 10 features

- [ ] Implement model training and selection in notebook (depends on: preprocessing)
  - Acceptance criteria: 4+ models compared via 5-fold CV, comparison table with ROC-AUC/F1/Precision/Recall, best model selected
  - Test strategy: All models train without errors; best model ROC-AUC >= 0.65

- [ ] Implement evaluation and export in notebook (depends on: model training)
  - Acceptance criteria: Confusion matrix, ROC curve, classification report generated. `models/delay_classifier.joblib`, `models/preprocessor.joblib`, `models/model_metadata.json` exported
  - Test strategy: All artifact files exist and are loadable; metadata JSON has expected keys

**Exit Criteria**: Model artifacts in `models/` directory, ROC-AUC >= 0.65, all metrics documented in metadata JSON.

**Delivers**: Trained model ready for inference by downstream modules.

---

### Phase 2: Core Processing Components
**Goal**: Build the feature engineering, ML inference, and data ingestion modules.

**Entry Criteria**: Phase 0 (Foundation) complete, Phase 1 (Model Training) complete (artifacts available).

**Tasks**:
- [ ] Implement model loading and initialization (`src/ml/model_loader.py`) (depends on: config, logging, model artifacts)
  - Acceptance criteria: Loads delay_classifier.joblib and preprocessor.joblib into memory; validates feature list matches metadata; raises clear error if artifacts missing
  - Test strategy: Unit test loading with valid/invalid paths; test feature validation

- [ ] Implement single-order prediction (`src/ml/inference.py`) (depends on: model_loader)
  - Acceptance criteria: Accepts dict with order fields, returns {delay_probability, severity, order_id}; severity thresholds: critical>0.7, warning>0.5, info>0.3
  - Test strategy: Unit test with known inputs, verify probability range [0,1], verify severity classification

- [ ] Implement batch prediction (`src/ml/inference.py`) (depends on: model_loader)
  - Acceptance criteria: Accepts DataFrame, returns DataFrame with delay_probability and severity columns; vectorized inference
  - Test strategy: Test with 1, 100, 10000 row DataFrames; verify output shape matches input

- [ ] Implement schema validation (`src/ingestion/schema_validator.py`) (depends on: config, logging)
  - Acceptance criteria: Validates 18-field enriched schema; returns pass/fail + error list; allows nullable fields (ship_date, delivery_date)
  - Test strategy: Test valid data, missing fields, wrong types, null handling

- [ ] Implement CSV handler and batch job creation (`src/ingestion/csv_handler.py`) (depends on: config, logging, db models)
  - Acceptance criteria: Saves CSV to data/uploads/{id}.csv, creates batch_jobs row (status=pending), returns batch_job_id
  - Test strategy: Test upload, file save, DB record creation, duplicate handling

- [ ] Implement feature extraction from enriched schema (`src/features/transform.py`) (depends on: config, logging, preprocessor.joblib)
  - Acceptance criteria: Extracts 10 features from 18-field input; applies preprocessor.joblib transform; passes through raw fields
  - Test strategy: Test with valid enriched data; verify output has 10 features; verify raw fields preserved

**Exit Criteria**: Single and batch predictions work with loaded model, CSV uploads create batch jobs, schema validation catches errors.

**Delivers**: Working ML inference and data ingestion — can predict on new order data.

---

### Phase 3: KPI and Deviation Detection
**Goal**: Build KPI computation and deviation detection logic.

**Entry Criteria**: Phase 2 (Core Processing) complete.

**Tasks**:
- [ ] Implement per-order KPI computation (`src/kpi/calculator.py`) (depends on: db, config, logging)
  - Acceptance criteria: Computes delay_probability (pass-through) and fulfillment_gap flag per order
  - Test strategy: Test with various order_status + probability combinations; verify gap detection logic

- [ ] Implement running average KPIs with 30-day rolling window (`src/kpi/calculator.py`) (depends on: db, config)
  - Acceptance criteria: Queries predictions table for 30-day window; computes segment risk score, on-time rate, high-risk count grouped by warehouse/shipment/importance
  - Test strategy: Seed test DB with known predictions; verify aggregate calculations match expected values

- [ ] Implement threshold-based deviation detection (`src/detection/deviation_detector.py`) (depends on: config, logging, kpi)
  - Acceptance criteria: Generates deviation records with correct severity (critical>0.7, warning>0.5, info>0.3); stores in Postgres deviations table
  - Test strategy: Test with predictions at various thresholds; verify severity assignment and DB storage

- [ ] Implement KPI breach detection (`src/detection/deviation_detector.py`) (depends on: kpi, config)
  - Acceptance criteria: Detects segment-level KPI breaches when metrics exceed configurable thresholds
  - Test strategy: Test with known KPI values crossing thresholds; verify deviation generation

**Exit Criteria**: Per-order and aggregate KPIs computed correctly, deviations generated at correct thresholds.

**Delivers**: Risk scoring and deviation detection — system can identify at-risk orders.

---

### Phase 4: Kafka Event Infrastructure
**Goal**: Set up Kafka client utilities and deviation event publishing.

**Entry Criteria**: Phase 0 (Foundation) complete.

**Tasks**:
- [ ] Implement Kafka client utilities (`src/kafka/client.py`) (depends on: config, logging)
  - Acceptance criteria: Async producer with JSON serialization, consumer with group management, topic creation (fulfillment-events, deviation-events), connection retry logic
  - Test strategy: Integration test with Redpanda container; test produce/consume round-trip; test topic creation

- [ ] Implement deviation event publisher (`src/detection/publisher.py`) (depends on: kafka client, detection)
  - Acceptance criteria: Serializes deviation + order context to JSON; publishes to deviation-events topic with order_id as key; only publishes severity >= warning
  - Test strategy: Test serialization format; test publish with mock producer; test severity filtering

- [ ] Implement Kafka producer simulator (`src/kafka/producer_simulator.py`) (depends on: kafka client, config)
  - Acceptance criteria: Generates realistic enriched order events matching 18-field schema; configurable rate; realistic distributions for warehouse blocks, shipment modes, etc.
  - Test strategy: Test event schema validity; test configurable rate; test distribution randomness

**Exit Criteria**: Can produce and consume Kafka messages, deviation events publish correctly, simulator generates realistic events.

**Delivers**: Event streaming infrastructure ready for Airflow DAGs.

---

### Phase 5: Unified Processing Pipeline
**Goal**: Wire together all processing components into a single orchestrated pipeline.

**Entry Criteria**: Phase 2 (Core Processing), Phase 3 (KPI/Detection), Phase 4 (Kafka) complete.

**Tasks**:
- [ ] Implement pipeline orchestrator (`src/pipeline/processor.py`) (depends on: features, ml, kpi, detection, db, kafka)
  - Acceptance criteria: `run_pipeline(df, source, batch_job_id, session, kafka_producer)` executes transform → inference → store predictions → KPI → deviation → store deviations → publish. Returns summary with counts.
  - Test strategy: Integration test with sample data; verify all DB records created; verify Kafka events published; test error handling (partial failure)

- [ ] Test end-to-end pipeline with batch data (depends on: pipeline orchestrator)
  - Acceptance criteria: CSV data flows through entire pipeline; predictions, deviations stored; critical deviations published to Kafka
  - Test strategy: Load sample CSV, run pipeline, verify all outputs in DB and Kafka

**Exit Criteria**: Single function call processes data through all stages, all outputs correctly stored.

**Delivers**: Core processing capability — same code usable by both batch and streaming paths.

---

### Phase 6: RAG Knowledge Base and Policy Documents
**Goal**: Build the RAG system with policy documents for agent decision support.

**Entry Criteria**: Phase 0 (Foundation) complete.

**Tasks**:
- [ ] Create policy and SLA documents (`knowledge_base/`) (depends on: none)
  - Acceptance criteria: shipping_policy.md, refund_policy.md, escalation_criteria.md, communication_guidelines.md, carrier_slas.md, warehouse_slas.md, apology_email.md, refund_confirmation.md — all with realistic, detailed content
  - Test strategy: Documents are parseable markdown; content covers scenarios agents will encounter

- [ ] Implement document ingestion pipeline (`src/rag/ingestion.py`) (depends on: config, logging)
  - Acceptance criteria: Chunks markdown docs with LangChain TextSplitter; embeds with OpenAI text-embedding-3-small; stores in Chroma with metadata (category, agent_type); persists to data/chroma_db/; idempotent startup
  - Test strategy: Test chunking, embedding dimensions, Chroma storage; test idempotent re-ingestion

- [ ] Implement historical resolution ingestion (`src/rag/ingestion.py`) (depends on: document ingestion)
  - Acceptance criteria: Accepts agent response, formats as text document, embeds, stores in Chroma with metadata (agent_type, severity, warehouse, shipment_mode)
  - Test strategy: Test with sample agent response; verify stored in Chroma with correct metadata

- [ ] Implement knowledge retrieval (`src/rag/retrieval.py`) (depends on: document ingestion)
  - Acceptance criteria: `retrieve(query, agent_type, top_k=5)` returns relevant document chunks with similarity scores; supports metadata filtering by agent_type
  - Test strategy: Ingest known documents, query with related terms, verify relevance; test agent_type filtering

**Exit Criteria**: Policy documents ingested into Chroma, retrieval returns relevant results for agent queries.

**Delivers**: Knowledge base ready for agent consumption.

---

### Phase 7: Multi-Agent Orchestration System
**Goal**: Build the LLM-based multi-agent system with four specialist agents and simulated tools.

**Entry Criteria**: Phase 6 (RAG) complete, Phase 3 (Detection) complete, Phase 0 (DB) complete.

**Tasks**:
- [ ] Implement simulated agent tools (`src/agents/tools.py`) (depends on: config, logging)
  - Acceptance criteria: All 12 tools implemented as Python functions with simulated logic: reschedule_shipment(), check_carrier_status(), transfer_warehouse(), draft_email(), send_notification(), log_interaction(), check_refund_eligibility(), issue_refund(), apply_credit(), create_ticket(), assign_human(), flag_priority(). Each returns structured JSON.
  - Test strategy: Unit test each tool with sample inputs; verify structured output format

- [ ] Implement Shipment Agent (`src/agents/shipment_agent.py`) (depends on: tools, rag retrieval, config)
  - Acceptance criteria: LangChain agent with shipping system prompt, RAG-retrieved policies injected, access to shipment tools (reschedule, carrier status, transfer). Multi-turn reasoning.
  - Test strategy: Test with sample deviation; verify tool calls; verify RAG context injection; verify structured response

- [ ] Implement Customer Service Agent (`src/agents/customer_agent.py`) (depends on: tools, rag retrieval, config)
  - Acceptance criteria: LangChain agent with communication guidelines from RAG, access to customer tools (draft email, notification, log interaction). Contextual, empathetic tone.
  - Test strategy: Test with sample deviation; verify communication tone; verify structured response

- [ ] Implement Payment/Refund Agent (`src/agents/payment_agent.py`) (depends on: tools, rag retrieval, config)
  - Acceptance criteria: LangChain agent with refund policies from RAG, access to payment tools (eligibility, refund, credit). Follows policy tiers.
  - Test strategy: Test with sample deviation including discount context; verify policy-compliant decisions

- [ ] Implement Escalation Agent (`src/agents/escalation_agent.py`) (depends on: tools, rag retrieval, config)
  - Acceptance criteria: LangChain agent with escalation criteria from RAG, access to escalation tools (ticket, assign, priority). Escalates when automated resolution insufficient.
  - Test strategy: Test with high-severity deviation; verify escalation triggers correctly

- [ ] Implement LLM-based orchestrator/router (`src/agents/orchestrator.py`) (depends on: all specialist agents, rag retrieval, config, db)
  - Acceptance criteria: Receives deviation event, uses LLM function calling to select agent(s), passes context + RAG knowledge, aggregates results, stores in Postgres agent_responses, ingests into RAG
  - Test strategy: Test routing logic with various deviation types; verify multi-agent invocation; verify DB storage and RAG ingestion

**Exit Criteria**: Orchestrator routes deviations to appropriate agents, agents reason with RAG context and execute tools, responses stored in DB and RAG.

**Delivers**: Autonomous resolution capability — system can handle deviations end-to-end.

---

### Phase 8: REST API Layer
**Goal**: Expose all system functionality via FastAPI HTTP endpoints.

**Entry Criteria**: Phase 5 (Pipeline), Phase 7 (Agents), Phase 6 (RAG) complete.

**Tasks**:
- [ ] Implement FastAPI app with lifespan events (`src/api/app.py`) (depends on: config, db, ml, rag)
  - Acceptance criteria: App startup loads model, initializes DB, ingests policy documents into RAG. Shutdown gracefully closes connections. CORS configured. Swagger docs auto-generated.
  - Test strategy: Test app startup/shutdown; verify model loaded; verify DB initialized

- [ ] Implement health check endpoint (`src/api/routes/health.py`) (depends on: app)
  - Acceptance criteria: GET /health returns component-level health (model, DB, Kafka connectivity)
  - Test strategy: Test healthy state; test degraded state (DB down); verify response format

- [ ] Implement single prediction endpoint (`src/api/routes/predict.py`) (depends on: app, ml inference, ingestion validation)
  - Acceptance criteria: POST /predict accepts JSON, validates schema, returns prediction synchronously
  - Test strategy: Test with valid/invalid input; verify response format; test edge cases

- [ ] Implement batch prediction endpoint (`src/api/routes/predict.py`) (depends on: app, ingestion csv_handler)
  - Acceptance criteria: POST /predict/batch accepts CSV upload, returns batch_job_id, triggers Airflow DAG asynchronously
  - Test strategy: Test upload with valid/invalid CSV; verify batch_job creation; verify async return

- [ ] Implement batch results endpoints (`src/api/routes/batch.py`) (depends on: app, db)
  - Acceptance criteria: GET /batch/{id}/status, /predictions, /deviations, /agent-responses return correct data; 404 for unknown IDs
  - Test strategy: Seed DB with test data; verify each endpoint returns correct filtered results

- [ ] Implement deviation listing endpoint (`src/api/routes/deviations.py`) (depends on: app, db)
  - Acceptance criteria: GET /deviations with severity/time_range/order_id filters; paginated; default last 24h
  - Test strategy: Test with various filters; verify pagination; test empty results

- [ ] Implement manual agent trigger endpoint (`src/api/routes/agents.py`) (depends on: app, agents orchestrator)
  - Acceptance criteria: POST /trigger-agent accepts deviation_id, triggers agent DAG, returns confirmation
  - Test strategy: Test with valid/invalid deviation_id; verify trigger execution

- [ ] Implement order detail endpoint (`src/api/routes/orders.py`) (depends on: app, db)
  - Acceptance criteria: GET /orders/{id} returns joined predictions + deviations + agent_responses
  - Test strategy: Seed DB with full order lifecycle; verify all data joined correctly

- [ ] Implement KPI dashboard endpoint (`src/api/routes/kpi.py`) (depends on: app, kpi calculator)
  - Acceptance criteria: GET /kpi/dashboard returns running average KPIs with segment breakdowns
  - Test strategy: Seed DB with predictions; verify aggregate calculations match

- [ ] Implement knowledge base endpoints (`src/api/routes/knowledge.py`) (depends on: app, rag)
  - Acceptance criteria: POST /knowledge/ingest adds document; POST /knowledge/search returns results with scores
  - Test strategy: Test ingest + search round-trip; verify similarity scores

**Exit Criteria**: All 15 API endpoints functional, Swagger documentation complete, all API tests pass.

**Delivers**: Full HTTP interface to the system.

---

### Phase 9: Airflow DAGs and Orchestration
**Goal**: Create three Airflow DAGs for batch, streaming, and agent orchestration.

**Entry Criteria**: Phase 5 (Pipeline), Phase 4 (Kafka), Phase 7 (Agents) complete.

**Tasks**:
- [ ] Implement Batch Processing DAG (`dags/batch_processing_dag.py`) (depends on: pipeline, db, ingestion)
  - Acceptance criteria: Triggered with batch_job_id config; loads CSV → validates → runs pipeline → updates batch_job status. Error handling sets status=failed.
  - Test strategy: Trigger with test batch_job_id; verify predictions in DB; verify status transitions

- [ ] Implement Streaming DAG with Kafka trigger (`dags/streaming_dag.py`) (depends on: pipeline, kafka, db)
  - Acceptance criteria: Kafka consumer trigger on fulfillment-events; collects micro-batch (15s/1K max); deserializes → runs pipeline → deviations to Kafka
  - Test strategy: Publish test events to Kafka; verify micro-batch processing; verify pipeline output

- [ ] Implement Agent Orchestration DAG (`dags/agent_orchestration_dag.py`) (depends on: agents, kafka, db, rag)
  - Acceptance criteria: Kafka consumer trigger on deviation-events; deserializes deviation → calls orchestrator → stores response in DB → ingests into RAG
  - Test strategy: Publish test deviation to Kafka; verify agent execution; verify DB and RAG storage

**Exit Criteria**: All three DAGs visible in Airflow UI, batch DAG processes CSV, streaming DAG handles Kafka events, agent DAG triggers orchestrator.

**Delivers**: Full orchestration — automated processing and agent triggering.

---

### Phase 10: Docker Compose and Deployment
**Goal**: Containerize all services for single-command deployment.

**Entry Criteria**: All core phases (0-9) complete.

**Tasks**:
- [ ] Create Dockerfile for FastAPI service (depends on: api module)
  - Acceptance criteria: Multi-stage build; installs deps, copies source, runs uvicorn on port 8000
  - Test strategy: `docker build` succeeds; container starts and /health returns 200

- [ ] Create Dockerfile for Kafka producer simulator (depends on: kafka producer_simulator)
  - Acceptance criteria: Runs producer_simulator.py as entrypoint; configurable via env vars
  - Test strategy: Container starts and publishes events to Kafka

- [ ] Create docker-compose.yml with all services (depends on: Dockerfiles, all modules)
  - Acceptance criteria: Services: api (8000), redpanda (9092), airflow-webserver (8080), airflow-scheduler, postgres (5432), stream-producer. Shared network. Volume mounts for models, data, DAGs. Health checks.
  - Test strategy: `docker-compose up` starts all services; each service is healthy

- [ ] Create .env.example with all environment variables (depends on: config module)
  - Acceptance criteria: Documents every env var with descriptions and example values
  - Test strategy: Copy to .env, fill in values, docker-compose up succeeds

**Exit Criteria**: `docker-compose up -d` starts all services, API accessible on :8000, Airflow UI on :8080, Kafka on :9092.

**Delivers**: One-command deployment of entire system.

---

### Phase 11: Streamlit Dashboard (Stretch Goal)
**Goal**: Build visual monitoring interface.

**Entry Criteria**: Phase 8 (API) complete and accessible.

**Tasks**:
- [ ] Implement KPI dashboard view (`dashboard/app.py`) (depends on: API /kpi/dashboard endpoint)
  - Acceptance criteria: Plotly charts for segment risk scores, on-time delivery rates, high-risk counts; auto-refresh
  - Test strategy: Visual verification with seeded data; charts render without errors

- [ ] Implement deviation alerts view (depends on: API /deviations endpoint)
  - Acceptance criteria: Color-coded alert list; severity filtering; drill-down to agent response
  - Test strategy: Visual verification; filter interactions work

- [ ] Implement agent activity view (depends on: API agent response endpoints)
  - Acceptance criteria: Filterable table of agent actions; conversation history viewer
  - Test strategy: Visual verification; expand/collapse conversation works

- [ ] Implement order search and tracking view (depends on: API /orders/{id} endpoint)
  - Acceptance criteria: Search by order ID; prediction gauge; deviation timeline; agent action log
  - Test strategy: Search returns correct order; all sections populate

- [ ] Add Streamlit to docker-compose (depends on: all dashboard views)
  - Acceptance criteria: streamlit service on port 8501; connects to API service
  - Test strategy: Dashboard accessible at :8501; data loads from API

**Exit Criteria**: Dashboard accessible at :8501 with all four views functional.

**Delivers**: Visual monitoring and manual intervention interface.

</implementation-roadmap>

---

<test-strategy>

## Test Pyramid

```
        /\
       /E2E\       ← 10% (Docker Compose integration, full pipeline flow)
      /------\
     /Integration\ ← 30% (Module interactions, DB queries, Kafka round-trips)
    /------------\
   /  Unit Tests  \ ← 60% (Fast, isolated, deterministic)
  /----------------\
```

## Coverage Requirements
- Line coverage: 80% minimum
- Branch coverage: 70% minimum
- Function coverage: 85% minimum
- Critical paths (pipeline, inference, detection): 90% minimum

## Critical Test Scenarios

### ML Inference
**Happy path**:
- Load model artifacts, predict on valid order → returns probability [0,1] and correct severity
- Batch predict on 1K rows → all get predictions, output shape matches input

**Edge cases**:
- Order at exact threshold boundaries (0.3, 0.5, 0.7) → verify correct severity classification
- Missing optional fields (ship_date null) → prediction still succeeds
- All-categorical inputs at each category level

**Error cases**:
- Model artifact files missing → clear error message, not crash
- Input with wrong column names → schema validation catches it
- Input with wrong data types → validation error

### Unified Processing Pipeline
**Happy path**:
- 100-row DataFrame → all predictions stored, deviations detected, Kafka events published

**Edge cases**:
- Empty DataFrame → no errors, returns zero counts
- Single-row DataFrame → processes correctly
- All predictions below threshold → no deviations generated
- All predictions above critical threshold → all become deviations

**Error cases**:
- Database connection failure mid-pipeline → transaction rollback, no partial data
- Kafka publish failure → deviations still stored in DB (Kafka failure non-fatal for DB)

### Multi-Agent System
**Happy path**:
- Critical deviation → orchestrator selects appropriate agent → agent reasons with RAG context → executes tool → stores response

**Edge cases**:
- Deviation requiring multiple agents → orchestrator invokes both, aggregates results
- Agent tool returns unexpected result → agent adapts reasoning

**Error cases**:
- OpenAI API rate limit → graceful retry or error response
- RAG returns no relevant documents → agent still makes reasonable decision

### KPI Engine
**Integration points**:
- KPI computation queries 30-day window correctly → verify SQL date filtering
- Running averages update as new predictions arrive → verify incremental accuracy
- Segment breakdown matches manual calculation on known data

## Test Generation Guidelines
- Use pytest with fixtures for DB sessions, Kafka producers, model objects
- Mock external services (OpenAI API, Kafka broker) in unit tests
- Use testcontainers for integration tests (Postgres, Redpanda)
- Each module has a corresponding `tests/test_{module}.py`
- Use factory fixtures for generating test order data matching enriched schema
- Parametrize threshold boundary tests

</test-strategy>

---

<architecture>

## System Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| ML Training | scikit-learn, XGBoost, LightGBM, Pandas | Train delay classifier on Kaggle dataset |
| ML Serving | joblib, FastAPI | Load model, run inference |
| Data Processing | Pandas, NumPy | Tabular data transformation |
| API | FastAPI | REST endpoints with Swagger docs |
| Orchestration | Apache Airflow 3.x | Batch, streaming, agent DAGs |
| Event Streaming | Redpanda (Kafka-compatible) | Event routing (fulfillment-events, deviation-events) |
| Database | PostgreSQL | System of record (shared with Airflow metadata) |
| AI Agents | OpenAI API, LangChain | Multi-agent orchestration with function calling |
| RAG Vector DB | Chroma, OpenAI text-embedding-3-small | Policy/SLA retrieval for agents |
| Dashboard | Streamlit, Plotly | Monitoring UI (stretch goal) |

## Data Models

```sql
batch_jobs (id UUID PK, filename, status, row_count, created_at, completed_at, error_message)
    ↓ batch_job_id
predictions (id UUID PK, batch_job_id FK, source, order_id, delay_probability, severity, features_json JSONB, created_at)
    ↓ prediction_id
deviations (id UUID PK, prediction_id FK, batch_job_id FK, severity, reason, status, created_at)
    ↓ deviation_id
agent_responses (id UUID PK, deviation_id FK, agent_type, action, details_json JSONB, conversation_history JSONB, created_at)
```

## Technology Stack

**Decision: Redpanda over Apache Kafka**
- **Rationale**: Kafka API-compatible with single C++ binary — no Zookeeper, no JVM, lower memory. Same client libraries work unchanged.
- **Trade-offs**: Less ecosystem maturity than Apache Kafka; fewer managed cloud offerings.
- **Alternatives considered**: Apache Kafka (heavier, needs Zookeeper), RabbitMQ (different protocol), Redis Streams (less durable).

**Decision: Airflow 3.x as unified orchestrator**
- **Rationale**: Native Kafka consumer triggers, DAG visualization, built-in retry/alerting. Eliminates standalone consumer services.
- **Trade-offs**: Airflow overhead for simple tasks; learning curve for DAG development.
- **Alternatives considered**: Celery + custom consumers (more code to maintain), Prefect (less mature Kafka support).

**Decision: Chroma for RAG vector DB**
- **Rationale**: In-process, persists to disk, zero external dependencies. Sufficient for demo scale.
- **Trade-offs**: Not horizontally scalable; single-process only.
- **Alternatives considered**: Pinecone (external dependency), Weaviate (heavier), pgvector (ties to Postgres).

**Decision: Multi-agent over single agent**
- **Rationale**: Prompt specialization, tool isolation, clean audit trails, independent iteration per agent type.
- **Trade-offs**: More complex orchestration; higher LLM API costs (multiple calls per deviation).
- **Alternatives considered**: Single agent with all tools (context dilution, riskier tool access).

</architecture>

---

<risks>

## Technical Risks

**Risk**: OpenAI API rate limits or costs during agent orchestration
- **Impact**: High — agents cannot function without LLM
- **Likelihood**: Medium
- **Mitigation**: Implement retry with exponential backoff; cache common routing decisions; use gpt-4o-mini for orchestrator routing, gpt-4o for specialist agents
- **Fallback**: Rule-based routing fallback when LLM unavailable

**Risk**: Airflow 3.x Kafka trigger maturity
- **Impact**: Medium — streaming DAG may need custom implementation
- **Likelihood**: Medium
- **Mitigation**: Prototype Kafka trigger early in Phase 4; fallback to custom consumer task if trigger insufficient
- **Fallback**: Use Airflow sensor-based polling or standalone Kafka consumer service

**Risk**: ML model accuracy limited by Kaggle dataset quality
- **Impact**: Low — this is a demo project, not production
- **Likelihood**: High (dataset is known to have limited predictive power)
- **Mitigation**: Focus on pipeline architecture quality over model accuracy; document limitations clearly
- **Fallback**: Use fixed thresholds if model performance too low

## Dependency Risks

**Risk**: Redpanda Docker image compatibility issues across platforms (ARM vs x86)
- **Impact**: Medium — blocks local development on Apple Silicon
- **Likelihood**: Low
- **Mitigation**: Test on both platforms early; use platform-specific image tags if needed
- **Fallback**: Switch to Apache Kafka with docker-compose or use kafka-python mock

**Risk**: Chroma + OpenAI embedding API dependency for RAG
- **Impact**: Medium — RAG non-functional without embeddings API
- **Likelihood**: Low
- **Mitigation**: Use local embedding model (sentence-transformers) as fallback
- **Fallback**: Pre-compute and cache embeddings; use keyword search fallback

## Scope Risks

**Risk**: Multi-agent system complexity exceeds time budget
- **Impact**: High — core feature of the project
- **Likelihood**: Medium
- **Mitigation**: Start with simple rule-based routing, upgrade to LLM routing incrementally; implement one agent fully, then replicate pattern for others
- **Fallback**: Deliver 2 agents (Shipment + Customer) instead of 4

**Risk**: Airflow DAG complexity with 3 DAGs + Kafka triggers
- **Impact**: Medium — orchestration is central to architecture
- **Likelihood**: Medium
- **Mitigation**: Build simplest DAG (batch) first; add streaming and agent DAGs incrementally
- **Fallback**: Run pipeline directly from API without Airflow for MVP demo

</risks>

---

<appendix>

## References
- [Customer Analytics Kaggle Dataset](https://www.kaggle.com/datasets/prachi13/customer-analytics)
- [Apache Airflow 3.x Documentation](https://airflow.apache.org/docs/)
- [Redpanda Documentation](https://docs.redpanda.com/)
- [LangChain Agents Documentation](https://python.langchain.com/docs/modules/agents/)
- [Chroma Vector DB Documentation](https://docs.trychroma.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Glossary
- **Deviation**: An order or segment-level event that breaches risk thresholds and may require intervention
- **Enriched Schema**: The 18-field unified data format combining data from all simulated upstream systems
- **Micro-batch**: A small batch of streaming messages (15s window or 1K messages) processed together for efficiency
- **Running Average KPI**: Aggregate metric computed over a 30-day rolling window from the predictions table
- **Fulfillment Gap**: An order that has shipped but has high predicted delay probability (likely to miss delivery window)
- **RAG (Retrieval-Augmented Generation)**: Technique of retrieving relevant documents and injecting them into LLM prompts for grounded decision-making

## Open Questions
- Should Airflow DAGs communicate with the FastAPI service via HTTP or import pipeline code directly?
- What is the optimal micro-batch window size (currently 15s) — should it be tunable per deployment?
- Should agent conversation history be stored as full JSON or summarized for RAG ingestion?
- Should the Streamlit dashboard poll the API or use WebSocket for real-time updates?
- What monitoring/alerting should be built into Airflow DAGs vs handled externally?

</appendix>
