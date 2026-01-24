# NEX Backend — Voice-First Cognitive System (v1.3)

NEX is a **voice-first, belief-driven cognitive system** designed for low-latency, stateful conversations. It utilizes **LiveKit** for real-time audio transport and **Gemini 1.5/2.5** for high-reasoning cognitive orchestration.

---

## 🚀 System Architecture

NEX distinguishes between two intelligence paths to optimize for both speed and depth:

1.  **Fast Path (Real-time Conversation)**:
    *   Direct audio streaming via LiveKit.
    *   Immediate response generation for simple turns.
    *   No mandatory RAG overhead.
2.  **Deep Path (Conditional Cognition)**:
    *   Triggered when historical context or personalization is required.
    *   Performs **Selective Memory Retrieval (RAG)** using Milvus.
    *   Analyzes **Belief State** to resolve ambiguities before acting.

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Real-time Audio** | LiveKit (WebRTC) |
| **Cognitive Brain** | Gemini 1.5 Flash / 2.5 Flash |
| **Vector Memory** | Milvus (Standalone) |
| **Backend Framework** | FastAPI |
| **Dependency Management** | Poetry |
| **Containerization** | Docker + Docker Compose |

---

## 📂 Project Structure

```text
app/
├── main.py             # FastAPI entrypoint & REST endpoints
├── agent.py            # LiveKit Voice Agent implementation
├── nex_agent_llm.py    # Custom LLM wrapper for Nex-specific logic
├── orchestrator.py     # Cognitive Orchestration Engine (The "Thinker")
├── llm_runtime.py      # Gemini integration (Thought & Token generation)
├── memory_engine.py    # Selective RAG logic & Milvus interface
├── cognition.py        # Pydantic models for Belief & Intent
├── livekit_token.py    # JWT generation for LiveKit rooms
└── ... (Utilities)
```

---

## ⚡ Getting Started

### 1. Environment Setup
Create a `.env` file in the root directory:

```env
GOOGLE_API_KEY="your-gemini-api-key"
LIVEKIT_URL="http://localhost:7880"
LIVEKIT_API_KEY="devkey"
LIVEKIT_API_SECRET="secretkey"
```

### 2. Run with Docker (Infrastructure Only)
To start the necessary infrastructure (LiveKit Server, Milvus, Redis):

```bash
docker compose up -d
```

### 3. Run the Backend Locally
Install dependencies and start the FastAPI server:

```bash
poetry install
poetry run uvicorn app.main:app --reload
```

---

## 🧠 Core Concepts

### Belief State Model
Every turn is analyzed to produce a **Belief Object**:
- **Confidence**: 0.0–1.0.
- **Ambiguities**: List of unresolved points.
- **Assumptions**: What the system is "guessing" to keep the flow.
- **Requires Context**: Boolean trigger for memory retrieval.

### Selective Memory Retrieval (RAG)
Unlike traditional RAG systems, NEX **does not** query the database on every turn. The **Memory Retrieval Gate** analyzes the intent:
- **Fast Path**: Simple greetings or acknowledgments skip the DB.
- **Deep Path**: References to the past or complex planning trigger a Milvus query.

---

## 🧪 Testing

We provide a specialized test script to verify the core endpoints (Token & Chat):

```bash
poetry run python test_nex_endpoints.py
```

**What it tests:**
- ✅ **LiveKit Auth**: Generates a valid JWT for room joining.
- ✅ **Cognitive Chat**: Sends a message and measures the **latency** and **conciseness** of the belief-driven response.

---

## 📡 API Endpoints

- `POST /livekit/token`: Generate a token to join a voice room.
- `POST /chat/text`: Secondary text-based entry point to the cognitive engine.
- `WebSocket /ws`: Legacy/Secondary WebSocket interface.

---

## 🌐 Production Deployment

For deployment at `umashriventures.com`, we recommend the following subdomain structure:

| Component | Subdomain | Purpose |
| :--- | :--- | :--- |
| **Frontend** | `nex.umashriventures.com` | User Interface |
| **Backend API** | `api.nex.umashriventures.com` | FastAPI endpoints, Token generation, Text chat |
| **LiveKit Server** | `livekit.nex.umashriventures.com` | WebRTC signaling and data transport |

### Deployment Requirements
1.  **SSL/TLS**: All subdomains MUST have valid SSL certificates. LiveKit requires HTTPS/WSS for browser-side WebRTC.
2.  **Reverse Proxy**: Use Nginx or Traefik to route traffic:
    *   `api.nex.umashriventures.com` -> `nex-api:8000`
    *   `livekit.nex.umashriventures.com` -> `livekit-server:7880`
3.  **Ports**: Ensure the following ports are open on your firewall for LiveKit:
    *   `TCP: 7880, 7881` (Signaling)
    *   `UDP: 50000-60000` (WebRTC Media)

---

## 🛡 Security & Deployment
- **Platform**: Designed for AWS ECS.
- **Security**: AES-256 for stored transcripts, user-isolated memory nodes.
- **Performance**: Targets <1.5s total voice turn latency.
