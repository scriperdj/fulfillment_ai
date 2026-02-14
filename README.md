# fulfillment_ai

**Autonomous AI-driven system for proactive detection and resolution of retail fulfillment operational issues.**

Built for Celonis Garage Technical Challenge.

## 🎯 Overview

fulfillment_ai combines **process monitoring** (KPI tracking), **risk detection** (ML/heuristics), and **autonomous AI agents** (LLM-driven resolution) to proactively prevent delivery delays and optimize fulfillment operations.

### Key Features
- ✅ Real-time KPI monitoring (delivery delays, segment risk, fulfillment gaps)
- ✅ Proactive deviation detection (predict issues before they happen)
- ✅ Autonomous AI agents (OpenAI + LangChain for resolution)
- ✅ REST API for triggering and monitoring
- ✅ Dockerized, cloud-native architecture

---

## 📋 Requirements

- Python 3.10+
- Docker & Docker Compose (for containerized setup)
- OpenAI API Key (for agent integration)
- Kaggle Customer Analytics Dataset (CSV)

---

## 🚀 Quick Start

### Local Development

**1. Clone & Setup**
```bash
git clone https://github.com/scriperdj/fulfillment_ai.git
cd fulfillment_ai

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
```

**2. Configure Environment**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

**3. Download Dataset**
```bash
# Download Customer Analytics Dataset from Kaggle
# Place CSV in: data/raw/

# See docs/setup.md for detailed instructions
```

**4. Run API Server**
```bash
uvicorn src.api:app --reload
```

API will be available at: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

**5. Test System**
```bash
pytest tests/ -v
```

---

### Docker Deployment

```bash
# Build image
docker build -t fulfillment_ai:latest .

# Run with compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

API will be available at: `http://localhost:8000`

---

## 📚 Project Structure

```
fulfillment_ai/
├── ARCHITECTURE.md          # System design & diagrams
├── README.md                # This file
├── requirements.txt         # Dependencies
├── Dockerfile               # Container image
├── docker-compose.yml       # Local dev setup
│
├── src/
│   ├── api.py               # FastAPI application
│   ├── config.py            # Configuration
│   ├── data/                # Data loading & preprocessing
│   ├── kpi/                 # KPI calculation logic
│   ├── detection/           # Deviation detection
│   ├── agent/               # AI agent orchestration
│   └── models/              # Data models & schemas
│
├── tests/                   # Unit & integration tests
├── data/                    # Data files (raw & processed)
├── logs/                    # Application logs
└── docs/                    # Additional documentation
```

---

## 🔌 API Endpoints

### Health & Diagnostics
```
GET  /health              System health check
GET  /status              Detailed status info
```

### KPI & Data
```
POST /kpi/compute         Trigger KPI calculation
GET  /kpi/dashboard       View current KPI values
GET  /kpi/history         KPI historical data
```

### Deviation Detection
```
POST /detect-deviation    Run deviation detection
GET  /deviations          List recent deviations
GET  /deviations/{id}     Deviation details
```

### Agent & Resolution
```
POST /trigger-agent       Trigger agent on deviation
GET  /agent-response/{id} Fetch agent resolution output
POST /agent/reset         Reset agent state
```

### Orders
```
GET  /orders              List orders (paginated)
GET  /orders/{id}         Order details + KPI info
POST /orders/bulk-upload  Bulk upload orders
```

### Full API docs available at: `http://localhost:8000/docs`

---

## 🏗️ Architecture

See **ARCHITECTURE.md** for:
- System diagrams
- Component descriptions
- Tech stack justification
- Deployment details
- Assumptions & limitations
- Future extensions

---

## 📖 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design & diagrams
- **[docs/setup.md](docs/setup.md)** - Detailed setup instructions
- **[docs/api_examples.md](docs/api_examples.md)** - API usage examples
- **[docs/kpi_definitions.md](docs/kpi_definitions.md)** - KPI specifications

---

## 🧪 Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test:
```bash
pytest tests/test_kpi.py -v
```

With coverage:
```bash
pytest tests/ --cov=src --cov-report=html
```

---

## 🔐 Configuration

Environment variables (see `.env.example`):
```env
# Required
OPENAI_API_KEY=sk-...

# Optional
LOG_LEVEL=INFO
DATA_PATH=./data/raw
CACHE_TTL=3600
AGENT_TIMEOUT=30
```

---

## 🚧 Development Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make changes & test**
   ```bash
   pytest tests/
   ```

3. **Commit & push**
   ```bash
   git add .
   git commit -m "feat: add my feature"
   git push origin feat/my-feature
   ```

4. **Create Pull Request**
   - Reference issue if applicable
   - Ensure tests pass

---

## 📊 Example Usage

### 1. Load Data & Compute KPIs
```bash
curl -X POST http://localhost:8000/kpi/compute
```

### 2. View KPI Dashboard
```bash
curl http://localhost:8000/kpi/dashboard
```

### 3. Run Deviation Detection
```bash
curl -X POST http://localhost:8000/detect-deviation
```

### 4. Trigger Agent on High-Risk Order
```bash
curl -X POST http://localhost:8000/trigger-agent \
  -H "Content-Type: application/json" \
  -d '{"order_id": "ORDER_123", "risk_reason": "High delay probability"}'
```

### 5. Get Agent Response
```bash
curl http://localhost:8000/agent-response/response_123
```

---

## 🐛 Known Issues

- None yet (this is v1.0)

---

## 🔮 Future Work

**Short-term:**
- [ ] Multi-agent system (shipment, customer, payment agents)
- [ ] Streamlit UI dashboard
- [ ] PostgreSQL backend for persistence
- [ ] GitHub Actions CI/CD

**Medium-term:**
- [ ] ML-based delay prediction model
- [ ] Kafka-based real-time KPI streaming
- [ ] RAG knowledge base for agent context
- [ ] Email/SMS integration

**Long-term:**
- [ ] Celonis platform integration
- [ ] Advanced RL-based optimization
- [ ] Multi-tenant architecture
- [ ] ERP/WMS system integrations

---

## 💡 Tips & Best Practices

1. **Start with heuristics** - Get the system working before adding ML
2. **Simulate everything** - Refunds, shipment updates, etc. are simulated
3. **Clear assumptions** - Document what you're mocking vs. implementing
4. **Modular design** - Each component should be independently testable
5. **Log decisions** - Agent decisions should be fully auditable

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feat/my-feature`
3. Make changes & add tests
4. Commit: `git commit -am 'Add my feature'`
5. Push: `git push origin feat/my-feature`
6. Create Pull Request

---

## 📞 Support

- **Documentation:** See [docs/](docs/) directory
- **Issues:** GitHub Issues (coming soon)
- **Questions:** Open a discussion

---

## 📄 License

(Add your license here)

---

**Built with ❤️ for Celonis Garage**

Last Updated: 2026-02-14
