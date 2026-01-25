# Product Requirements Document (PRD): Agentic Backend Transformation

## 1. Overview
**Project Name:** Nex-Agentic-Core
**Based on:** Nex Backend (Voice-First AI Infrastructure)
**New Core Tech:** Graphiti (Knowledge Graph Framework), Neo4j, Milvus

This project aims to evolve the existing Nex Backend from a stateless conversational router into a stateful **Agentic Backend**. By integrating **Graphiti** backed by **Neo4j**, the system will autonomously build a dynamic knowledge graph of user interactions, enabling the AI to "remember" facts, preferences, and historical context across sessions. **Milvus** will be retained and optimized for high‑scale static vector retrieval, ensuring the system can handle 10k concurrent users and 10k Requests Per Second (RPS).

## 2. Problem Statement
The current architecture uses Redis for short‑term conversation state and Milvus for standard vector storage. However, standard RAG (Retrieval‑Augmented Generation) struggles with changing relationships and evolving user details (e.g., "I moved from New York to London"). The backend lacks a mechanism to model specific "facts" about the user ("triplets" like *User → Loves → Adidas*) effectively over time.

## 3. Goals & Objectives
1. **Agentic Memory:** Enable the backend to automatically extract and store user details (facts) from conversations using Graphiti's episodic memory.
2. **Hybrid Architecture:** Implement a dual‑memory system:
   * **Dynamic Memory (Graphiti + Neo4j):** For evolving user contexts, temporal facts, and relationships.
   * **Static Memory (Milvus):** For high‑speed retrieval of fixed documents/embeddings (legacy Nex capability).
3. **High Scalability:** Support **10,000 RPS** and **10,000 Concurrent Users** through asynchronous ingestion pipelines and database clustering.
4. **API Compatibility:** Maintain the existing `WebSocket` and `FastAPI` interface contracts so frontend clients require zero changes.

## 4. Technical Architecture

### 4.1. High‑Level Stack Changes
| Component | Current Implementation | New Agentic Implementation |
| :--- | :--- | :--- |
| **API Layer** | FastAPI + WebSocket | FastAPI + WebSocket (Unchanged) |
| **Orchestrator** | Linear Python Logic | LangChain/LangGraph + Graphiti |
| **Graph Storage** | N/A | **Neo4j** (via Graphiti) |
| **Vector Storage** | Milvus | **Milvus** (Static Data) + **Neo4j** (Graph Embeddings) |
| **Short‑term Memory**| Redis | Redis (Buffer) + Graphiti Episodes |

### 4.2. Data Flow (The "Agentic Loop")
1. **Ingest (Real‑time):**
   * User audio/text arrives via WebSocket `/ws`.
   * Redis caches the immediate "Turn" (short‑term context).
2. **Retrieval (Hybrid):**
   * **Graph Query:** The system queries Graphiti (Neo4j) for facts related to the current query (e.g., *Who is the user? What do they like?*) using hybrid search (Semantic + BM25 + Graph).
   * **Vector Query:** Parallel query to Milvus for relevant static documentation or policy data.
   * **Context Assembly:** Retrieved facts and vectors are injected into the LLM system prompt.
3. **Response:**
   * LLM generates a response, streamed back via WebSocket.
4. **Memory Consolidation (Async Background Process):**
   * The conversation turn is packaged as a Graphiti **Episode**.
   * Graphiti processes the episode, extracting nodes/edges (e.g., `(User)-[HAS_GOAL]->(Build Scalable Backend)`) and updates Neo4j asynchronously to prevent latency on the chat thread.

## 5. Functional Requirements

### 5.1. Memory & Knowledge Graph (Graphiti)
* **Initialization:** The backend must initialize the `Graphiti` client with the `Neo4jDriver` on startup.
* **Episodic Ingestion:** Every completed conversation turn (User + AI response) must be added to the graph via `graphiti.add_episode()`. This must extract entities and relationships automatically.
* **Temporal Awareness:** The system must utilize Graphiti's bi‑temporal data model to handle contradictory facts (e.g., updating the user's current location while remembering the old one).
* **Custom Schema:** Define specific Pydantic models for `User` and `Preference` nodes to ensure structured data extraction.

### 5.2. Vector Search (Milvus)
* **Role Definition:** Milvus will remain the primary store for broad, unstructured knowledge base data (e.g., company manuals, global knowledge) which does not require the complex relationship mapping of the user graph.
* **Integration:** The backend agent will classify queries; if a query requires static knowledge, it routes to Milvus; if it requires personal context, it routes to Graphiti.

### 5.3. Scalability (10k RPS Strategy)
* **Concurrency Settings:** Set the `SEMAPHORE_LIMIT` environment variable in Graphiti to a value >10 (e.g., 50‑100) to allow high‑throughput ingestion without hitting LLM rate limits, or implement a queue‑based buffer.
* **Read/Write Separation:**
   * **Reads (Retrieval):** Must be sub‑200ms. Graphiti's hybrid retrieval is optimized for this.
   * **Writes (Ingestion):** Must be decoupled from the response loop. Use Python `asyncio` tasks or Celery (already optional in Nex) to offload `add_episode` calls.
* **Infrastructure:**
   * **Neo4j:** Deploy as a Causal Cluster (Leader/Follower) to handle read scaling.
   * **Milvus:** Deploy in Distributed Mode (query nodes vs. data nodes).

## 6. API Specifications
*Existing endpoints remain, logic upgrades:*

* **`GET /ws` (WebSocket)**
  * **Input:** Streaming Audio/Text.
  * **Process:**
    1. Identify User via JWT.
    2. **NEW:** Execute `graphiti.search()` for user context.
    3. Generate LLM response.
    4. **NEW:** Dispatch async task → `graphiti.add_episode()`.
  * **Output:** Streamed Audio/Text (unchanged).

* **`GET /health`**
  * **Update:** Must now check connectivity to Neo4j in addition to Redis and Milvus.

* **`POST /memory/search` (New Internal/Debug Endpoint)**
  * Allows developers to query the graph directly to verify facts stored about a user.
  * **Input:** `query` (string), `user_id`.
  * **Output:** JSON graph data (nodes/edges).

## 7. Implementation Plan

### Phase 1: Infrastructure Upgrade
* Modify `docker-compose.yml` to include the Neo4j container.
```yaml
neo4j:
  image: neo4j:5.26
  ports:
    - "7474:7474"
    - "7687:7687"
  environment:
    - NEO4J_AUTH=neo4j/password
```
* Ensure Milvus service remains configured as per Nex standards.

### Phase 2: Dependency Integration
* Add `graphiti-core` to `pyproject.toml` or `requirements.txt`.
* If using specific LLMs (e.g., OpenAI or Anthropic), install the relevant extras (e.g., `graphiti-core[anthropic]`).

### Phase 3: Backend Logic Refactor
* Instantiate the Neo4j Driver within `app/main.py` or a new `app/services/memory.py` module.
```python
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver

driver = Neo4jDriver(uri="bolt://neo4j:7687", auth=("neo4j", "password"))
graphiti = Graphiti(graph_driver=driver)
```
* Inject the `graphiti` instance into the WebSocket message handler logic.

### Phase 4: Load Testing & Telemetry
* Configure Graphiti telemetry (or disable via `GRAPHITI_TELEMETRY_ENABLED=false` for privacy).
* Simulate 10k users using a load testing tool (e.g., Locust) hitting the WebSocket endpoint.
* Monitor Neo4j memory usage and `SEMAPHORE_LIMIT` bottlenecks.

## 8. Requirements for LLMs
* **Structured Output:** Graphiti relies on LLMs that support Structured Output (OpenAI/Gemini) for accurate schema generation. Ensure the LLM Service in Nex is configured to use a compatible model (e.g., GPT‑4o, Gemini 1.5).

## 9. Success Metrics
* **Recall Accuracy:** The system correctly retrieves a user fact stated 10 turns ago.
* **Latency:** Added latency for Context Retrieval < 200ms.
* **Throughput:** System handles 10k RPS without 429 errors or connection drops.
