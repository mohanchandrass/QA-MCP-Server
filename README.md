# Knowledge-Powered Q&A and Action Bot (MCP)

**Author:** Mohan Chandra S S  
**GitHub:** https://github.com/mohanchandrass/QA-MCP-Server

---

## Overview

This project implements a **Knowledge-Powered Q&A and Action Bot** using the **Model Context Protocol (MCP)**.

The system is designed to:
- Answer user queries using a configurable knowledge base
- Resolve user intent deterministically from configuration
- Allow an LLM (Gemini) to handle the majority of conversations
- Escalate to a human agent only when required
- Trigger actions (e.g., ticket creation) in a controlled, auditable manner
- Support instant industry switching by swapping configuration files only

All **decision-making logic is configuration-driven**, while the **LLM is strictly limited to language generation**. This ensures enterprise safety, predictability, and auditability.

---

## Architecture Summary

The system consists of **two decoupled components**:

### 1. MCP Server (Dockerized)
- Exposes MCP resources:
  - `knowledge://search`
  - `config://persona`
  - `config://intents`
  - `config://actions`
- Resolves intent using deterministic rules (no LLM)
- Executes actions only when explicitly invoked by the client
- Stateless and reproducible

### 2. MCP Client (LLM-Integrated)
- Queries MCP resources
- Uses Gemini for natural language generation
- Enforces escalation and sampling policies from configuration
- Explicitly triggers MCP action tools
- Emits full trace logs for observability

### High-Level Flow

```
User
 └─> MCP Client (LLM + Policy Enforcement)
      ├─> MCP Resource: knowledge://search
      ├─> MCP Tool: resolve_intent
      ├─> Decision Logic (from actions.yaml)
      └─> MCP Tool: create_ticket (if required)
           └─> MCP Server
```

---

## Repository Structure

```
qa-mcp/
├── mcp-client/
│   ├── qa_mcp_client.py
│   ├── requirements.txt
│   └── tests/
└── mcp-server/
    ├── qa_mcp_server.py
    ├── Dockerfile
    ├── requirements.txt
    ├── config/
    │   ├── persona.yaml
    │   ├── intents.yaml
    │   └── actions.yaml
    └── data/
        └── knowledge.json
```

---

## Execution Guide (Copy–Paste Ready)

### Prerequisites
- Python 3.11+
- Docker
- Gemini API Key

---

### Step 0: Navigate to Project Root

```bash
cd qa-mcp
```

All subsequent commands assume you start from this directory.

---

### Step 1: Install MCP Client Dependencies (Required)

```bash
cd mcp-client
pip install -r requirements.txt
```

**Why this is required**
- Enables Gemini API integration
- Enables MCP client ↔ server communication

---

### Step 2: Set LLM API Key

```bash
export GEMINI_API_KEY=your_api_key_here
```

- This key is used **only by the MCP client**
- The MCP server does **not** require an LLM key

---

### Step 3: Run the MCP Server

Return to the project root:

```bash
cd ..
```

#### Option A: Run via Docker (Recommended)

Navigate to server directory:

```bash
cd mcp-server
```

Build the Docker image:

```bash
docker build -t qa-mcp-server .
```

Run the server with mounted resources:

```bash
docker run -p 8000:8000 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/data:/app/data \
  qa-mcp-server
```

**Why resource mounting is mandatory**
- `/app/config` → persona, intents, actions (industry behavior)
- `/app/data` → knowledge base
- Enables hot-swappable industry configuration without rebuilding the image

Server endpoints:
```
MCP Endpoint:  http://localhost:8000/mcp
Health Check: http://localhost:8000/health
```

---

#### Option B: Run via Python (Local Development)

```bash
cd mcp-server
pip install -r requirements.txt
python qa_mcp_server.py
```

Ensure the following directories exist:
```
mcp-server/config/
mcp-server/data/
```

---

### Step 4: Run the MCP Client

Open a **new terminal**:

```bash
cd qa-mcp/mcp-client
python qa_mcp_client.py
```

You can now interact with the system via the terminal.

---

## Runtime Flow (After Startup)

### MCP Server Loads
- Persona configuration
- Intent taxonomy
- Action and escalation policies
- Knowledge base

### MCP Client Workflow
1. Reads MCP resources (`/knowledge`, `/persona`, `/intents`, `/actions`)
2. Sends user queries
3. Uses Gemini to generate responses
4. Enforces escalation rules deterministically
5. Triggers MCP action tools when required

---

## Configuration-Driven Design

### Industry Switching

Industry behavior is controlled entirely via configuration files:
- `persona.yaml` → industry, tone, search behavior
- `intents.yaml` → intent taxonomy and triggers
- `actions.yaml` → escalation, sampling, and action policy

To switch industries (e.g., banking → healthcare):
- Replace configuration files only
- No code changes required

---

## Decision Logic (Escalation)

### Core Principle
The **LLM never decides escalation**.
All escalation decisions are **deterministic and configuration-driven**.

### Escalation Triggers
Escalation occurs when **any** of the following are true:

1. **Explicit User Request**
   - Phrases such as:
     - "talk to an agent"
     - "connect me to a human"
     - "raise a ticket"

2. **High-Severity Intent**
   - Example: billing issues
   - Severity defined in `intents.yaml`

3. **Low Confidence / Fallback**
   - Intent resolution confidence is `fallback`

4. **Repeated Failure (Sampling Logic)**
   - User repeats the issue beyond configured thresholds

All thresholds and rules are defined in `actions.yaml`.

### What Happens on Escalation
1. Client detects escalation condition
2. Client explicitly calls MCP tool:
   ```
   create_ticket
   ```
3. MCP server executes the action
4. Session ends (enterprise-standard behavior)
5. Full trace log is emitted

---

## Role of the LLM

The LLM is used **only** for:
- Natural language generation
- Persona-based tone and formatting
- Explaining known solutions from the knowledge base

The LLM **cannot**:
- Escalate on its own
- Execute actions
- Override policy
- Access internal logic

This guarantees safety, predictability, and auditability.

---

## Observability & Trace Logs

Every interaction emits a structured trace including:
- Knowledge search latency
- Intent resolution latency
- LLM API latency
- Action execution latency
- Escalation decision
- Confidence level

### Example Trace
```json
{
  "intent": {
    "intent": "billing",
    "severity": "high",
    "confidence": "high"
  },
  "action_taken": "create_ticket",
  "timings_ms": {
    "knowledge_search": 8.2,
    "intent_resolution": 6.9,
    "llm_api_call": 3200.5,
    "action_execution": 5.1,
    "total": 3225.4
  }
}
```

---

## Output Examples

**Screenshot 1: Normal Knowledge Resolution Output**

*(Insert output image here)*

**Screenshot 2: Escalation and Ticket Creation Output**

*(Insert output image here)*

---

## Why This Design Works

- LLM handles most cases → fast, conversational support
- Deterministic fallback → guaranteed escalation when needed
- Config-only industry switching → scalable and reusable
- MCP-native integration → clean separation of concerns
- Enterprise-safe → no hidden logic, no hallucinated actions

---

## Summary

This system demonstrates a **production-grade MCP architecture** where:
- Knowledge, intent, and actions are fully externalized
- LLMs enhance UX without compromising control
- Escalation is predictable and auditable
- Industry behavior is configurable, not hardcoded

The solution fully satisfies the **Knowledge-Powered Q&A and Action Bot hackathon requirements**.

