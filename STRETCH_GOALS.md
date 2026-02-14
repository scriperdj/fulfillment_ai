# Stretch Goals Implementation Guide

**fulfillment_ai** has been enhanced to support the stretch goals from the Celonis challenge. This document describes what has been added and how to implement each stretch goal.

---

## 🎯 Stretch Goals Summary

The challenge mentions four optional stretch goals:
1. **Simulate streaming-based KPI updates** (via scheduler or Kafka)
2. **Add multi-agent system** (e.g., shipment agent, payment agent)
3. **Incorporate a lightweight RAG-based knowledge base** for the agent
4. **Add a simple UI** for monitoring and interaction

**All four are now scaffolded and ready for implementation!**

---

## 1. Streaming-Based KPI Updates (Kafka)

### What's Included
- **Kafka Producer** (`src/streaming/kafka_producer.py`) - Publishes KPI events
- **Kafka Consumer** (skeleton in codebase) - Subscribes to KPI streams
- **WebSocket Manager** (`src/streaming/websocket_manager.py`) - Real-time client updates
- **Kafka Topics Config** (`config/kafka/topics.yaml`) - Topic definitions

### How to Implement
1. **Install Kafka** (via docker-compose-full.yml):
   ```bash
   docker-compose -f docker-compose-full.yml up kafka zookeeper
   ```

2. **Implement KPI Producer** in `src/streaming/kafka_producer.py`:
   ```python
   # Connect to Kafka
   # Publish KPI metrics when calculated
   # Include timestamp, metric name, value, threshold
   ```

3. **Implement KPI Consumer** (new file):
   ```python
   # Subscribe to Kafka topics
   # Update in-memory cache
   # Trigger WebSocket broadcasts
   ```

4. **Add WebSocket Endpoint** in `src/api.py`:
   ```python
   @app.websocket("/ws/kpi")
   async def websocket_kpi(websocket: WebSocket):
       # Stream real-time KPI updates
   ```

5. **Configure KPI Scheduler** (`src/kpi/streamer.py`):
   - Use APScheduler to trigger periodic KPI calculations
   - Publish results to Kafka
   - Coordinate with consumer for updates

### Benefits
- Real-time KPI monitoring (no polling needed)
- Scalable event streaming (Kafka handles high throughput)
- Client subscriptions via WebSocket
- Audit trail of all KPI changes

---

## 2. Multi-Agent System

### What's Included
- **Base Agent Class** (`src/agent/handlers/base_agent.py`) - Abstract interface
- **Agent Types** (scaffolds for: shipment, customer, refund, escalation)
- **Agent Orchestrator** (`src/agent/orchestrator.py`) - Router & coordinator
- **Agent Configuration** (`config/agents/agents.yaml`) - Definitions & routing rules
- **Agent State Manager** (skeleton) - Conversation history & memory

### Agents to Implement
1. **Shipment Agent** - Handles delivery rescheduling, carrier contact
2. **Customer Service Agent** - Drafts communications, manages compensation
3. **Refund Agent** - Evaluates refund eligibility, simulates processing
4. **Escalation Agent** - Routes complex cases to human review

### How to Implement
1. **Create Agent Classes** in `src/agent/handlers/`:
   ```python
   from src.agent.handlers.base_agent import BaseAgent
   
   class ShipmentAgent(BaseAgent):
       async def handle(self, context):
           # Use RAG KB for policies
           # Call OpenAI with agent-specific prompts
           # Return structured resolution
   ```

2. **Implement Agent Router** in `src/agent/orchestrator.py`:
   ```python
   async def route_to_agent(self, deviation):
       # Match deviation to appropriate agent
       # Use rules from agents.yaml
       # Fallback to escalation agent
   ```

3. **Add Multi-Turn Conversation** in `src/agent/state_manager.py`:
   ```python
   # Store conversation history per agent
   # Include context retrieval from RAG
   # Support follow-up questions
   ```

4. **Update API** to support multi-agent:
   ```python
   @app.post("/trigger-agent")
   async def trigger_agent(order_id: str, deviation_id: str):
       # Route to appropriate agent
       # Track conversation history
       # Return response with audit trail
   ```

### Agent Routing Rules
See `config/agents/agents.yaml` for examples:
- Route delivery delays → Shipment Agent
- Route fulfillment gaps → Customer Service Agent
- Route refunds → Refund Agent
- Route complex cases → Escalation Agent

---

## 3. RAG Knowledge Base

### What's Included
- **Knowledge Base Module** (`src/rag/knowledge_base.py`) - Vector store interface
- **Document Loader** (skeleton) - Load policies, templates, FAQs
- **Retriever** (skeleton) - Semantic search via embeddings
- **RAG Config** (`config/rag/policies.yaml`) - Policy templates

### Knowledge Types to Include
1. **Company Policies**
   - Refund policy (conditions, amounts, timelines)
   - Warranty policy (coverage, claims process)
   - Shipping policy (transit times, exceptions)
   - Return policy (conditions, procedures)

2. **Historical Agent Responses**
   - Example resolutions for common scenarios
   - Customer communication templates
   - Decision logs for learning

3. **Regulatory & Compliance**
   - Data protection (GDPR, CCPA)
   - Consumer protection laws
   - Industry standards

### How to Implement
1. **Set Up Vector Store** (`src/rag/knowledge_base.py`):
   ```python
   from chromadb import Client
   
   # Initialize Chroma (dev) or Pinecone (prod)
   # Configure embedding model (OpenAI embeddings)
   ```

2. **Load Initial Knowledge**:
   ```python
   kb = KnowledgeBase()
   kb.add_policy("refund", """
       Refund Eligibility:
       - Full refund within 30 days
       - 50% refund 30-60 days
       - No refund after 60 days
   """)
   ```

3. **Implement Retrieval** (`src/rag/retriever.py`):
   ```python
   # Convert query to embedding
   # Search vector DB for similar documents
   # Return top-k with similarity scores
   ```

4. **Integrate with Agents**:
   ```python
   # In agent prompts, include retrieved context
   # "Based on our refund policy: {retrieved_policy}"
   # Update KB with new decisions
   ```

5. **Add Management API**:
   ```python
   @app.post("/kb/add-document")
   async def add_knowledge(doc: Document):
       # Add new policy or learning
       # Embed and store in vector DB
   ```

---

## 4. Streamlit Dashboard (Monitoring UI)

### What's Included
- **Main App** (`ui/app.py`) - Navigation & layout
- **Dashboard Page** (`ui/pages/dashboard.py`) - KPI visualization
- **Orders Page** (`ui/pages/orders.py`) - Search & tracking
- **Agents Page** (`ui/pages/agents.py`) - Execution logs
- **Knowledge Base Page** (`ui/pages/knowledge_base.py`) - KB management
- **Settings Page** (`ui/pages/settings.py`) - Configuration
- **Dockerfile.streamlit** - Containerized dashboard

### Dashboard Features to Implement
1. **KPI Dashboard**
   - Real-time KPI cards (on-time %, avg delay, etc.)
   - Trend charts (time series)
   - Deviation alerts (color-coded severity)
   - Risk heatmap by segment/region

2. **Orders View**
   - Search by order ID
   - Filter by status, risk level, date range
   - Drill-down to order details
   - View associated deviations & agent responses

3. **Agents View**
   - Agent execution logs (searchable, filterable)
   - Decision trails (full conversation history)
   - Manual agent triggering (for testing)
   - Agent performance stats

4. **Knowledge Base View**
   - Browse documents by category
   - Search knowledge base
   - Edit/add policies
   - Upload new documents

5. **Settings View**
   - Adjust KPI thresholds
   - Configure agent settings
   - Manage Kafka topics
   - View system health

### How to Implement
1. **Set Up Streamlit**:
   ```bash
   pip install streamlit plotly
   streamlit run ui/app.py
   ```

2. **Implement Dashboard Page** (`ui/pages/dashboard.py`):
   ```python
   import streamlit as st
   import plotly.express as px
   
   # Fetch KPI data from API
   # Display metrics cards
   # Create trend charts
   # Show recent deviations
   ```

3. **Implement Orders Page** (`ui/pages/orders.py`):
   ```python
   # Order search form
   # Results table with filtering
   # Click to view details
   # Show associated agents/responses
   ```

4. **Implement Agents Page** (`ui/pages/agents.py`):
   ```python
   # Agent execution history
   # Filter by agent type, status, date
   # View conversation logs
   # Manual trigger buttons
   ```

5. **Add WebSocket Integration**:
   ```python
   # Connect to /ws/kpi endpoint
   # Receive real-time KPI updates
   # Auto-refresh charts without polling
   ```

6. **Run Full Stack**:
   ```bash
   docker-compose -f docker-compose-full.yml up
   # API: http://localhost:8000
   # Dashboard: http://localhost:8501
   ```

---

## Implementation Roadmap

### Phase 1: Multi-Agent System (Core)
- [ ] Implement base agent classes
- [ ] Create agent routing logic
- [ ] Add conversation history
- [ ] Test with OpenAI

### Phase 2: RAG Knowledge Base
- [ ] Set up vector store (Chroma)
- [ ] Load initial policies
- [ ] Implement semantic search
- [ ] Integrate with agents

### Phase 3: Streaming KPI Updates
- [ ] Implement Kafka producer/consumer
- [ ] Add WebSocket endpoint
- [ ] Implement APScheduler
- [ ] Test real-time updates

### Phase 4: Streamlit Dashboard
- [ ] Implement dashboard pages
- [ ] Connect to API endpoints
- [ ] Add WebSocket integration
- [ ] Deploy with Docker

### Phase 5: Integration & Testing
- [ ] End-to-end testing
- [ ] Load testing
- [ ] Performance optimization
- [ ] Documentation

---

## Environment Configuration

### Core Environment (.env)
```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
LOG_LEVEL=INFO
```

### Stretch Goal Environment
```env
# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# RAG
CHROMA_DB_PATH=./data/chroma
EMBEDDING_MODEL=text-embedding-3-small

# Streamlit
STREAMLIT_SERVER_PORT=8501
API_URL=http://localhost:8000
```

---

## Deployment

### Local Development (All Components)
```bash
docker-compose -f docker-compose-full.yml up
```

Services:
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- PostgreSQL: localhost:5432
- Kafka: localhost:9092
- Redis: localhost:6379

### Production Deployment
- Replace Chroma with Pinecone or Weaviate
- Use managed Kafka (AWS MSK, Confluent Cloud)
- Use cloud PostgreSQL (RDS, Cloud SQL)
- Deploy dashboard separately (Kubernetes)

---

## Testing

### Unit Tests (for each component)
```bash
pytest tests/test_agent.py -v
pytest tests/test_rag.py -v
pytest tests/test_streaming.py -v
```

### Integration Tests
```bash
pytest tests/ -v --integration
```

### Load Testing (Kafka + WebSocket)
```bash
# Use Apache JMeter or custom Python script
```

---

## Tips for Success

1. **Start with Core**: Implement base agent system first
2. **Test Early**: Test each component independently
3. **Use Mocking**: Mock OpenAI calls for development
4. **Incremental Deployment**: Deploy each stretch goal separately
5. **Monitor Performance**: Use Prometheus for metrics
6. **Document Decisions**: Keep ARCHITECTURE.md updated

---

## Resources

- **FastAPI WebSocket**: https://fastapi.tiangolo.com/advanced/websockets/
- **LangChain Agents**: https://python.langchain.com/docs/modules/agents/
- **Chroma Vector DB**: https://docs.trychroma.com/
- **Kafka with Python**: https://kafka-python.readthedocs.io/
- **Streamlit**: https://docs.streamlit.io/

---

**Document Version:** 1.0  
**Last Updated:** 2026-02-14  
**Status:** Ready for implementation
