# NEX-Agentic-Core (v2.0)

NEX is a **stateful, agentic cognitive backend** designed for persistent, high‑intelligence conversations. It integrates **Graphiti** and **Neo4j** to build a dynamic knowledge graph of user interactions, enabling "forever memory."

---

## 🚀 Agentic Architecture

NEX combines two memory paths to optimize for scale and intelligence:

1.  **Dynamic Memory (Episodic Graph)**:
    *   Powered by **Graphiti** + **Neo4j**.
    *   Automatically extracts facts, identities, and relationships.
    *   Handles temporal updates (e.g., "I moved to London").
2.  **Static Memory (Vector RAG)**:
    *   Powered by **Milvus**.
    *   High‑speed retrieval of fixed documents and global knowledge.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Cognitive Brain** | Gemini 1.5 Flash / 2.5 Flash |
| **Knowledge Graph** | Neo4j (via Graphiti) |
| **Vector Memory** | Milvus (Standalone) |
| **Backend Framework** | FastAPI (HTTP Only) |
| **Infrastructure** | Docker + Docker Compose |

---

## 📂 Project Structure

```text
app/
├── main.py             # FastAPI entrypoint & REST endpoints
├── orchestrator.py     # Agentic Orchestration Engine (The "Thinker")
├── memory_engine.py    # Hybrid Retrieval logic (Graph + Vector)
├── memory_graph.py     # Graphiti & Neo4j integration
├── llm_runtime.py      # Gemini integration (Thought & Token generation)
├── cognition.py        # Pydantic models for Belief & Intent
└── ... (Utilities)
```

---

## ⚡ Getting Started

### 1. Environment Setup
Create a `.env` file:

```env
GOOGLE_API_KEY="your-gemini-api-key"
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"
```

### 2. Start Infrastructure
Launch Neo4j, Milvus, and Redis:

```bash
docker compose up -d
```

### 3. Run the Agentic Core
```bash
poetry install
poetry run uvicorn app.main:app --reload
```

---

## 📡 API Specifications

- **`POST /chat/text`**: Primary entry point. Ingests transcript, retrieves hybrid memory, generates response, and async-consololidates the turn into the graph.
- **`POST /memory/search`**: Debug endpoint to view the knowledge graph and search context for a user.
- **`GET /health`**: Verifies connectivity to Neo4j, Milvus, and Redis.

---

## 🧠 Cognitive Concepts

### Selective Memory Retrieval
NEX analyzes the **Intent** and **Belief State** of every message.
- **Fast Path**: Simple chat skips DB retrieval.
- **Deep Path**: Temporal or identity-based queries trigger a hybrid Graph + Vector search.

### Async Consolidation
Every conversation turn is transformed into a Graphiti **Episode** and ingested into Neo4j as a background task, ensuring 0ms latency impact on the user response.

---

## 🛡 Security & Scalability
- **Scalability**: Designed for 10k RPS via distributed Milvus and Neo4j clustering.
- **Security**: AES-256 for stored graph data; user-isolated nodes.
