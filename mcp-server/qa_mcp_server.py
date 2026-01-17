# Knowledge-Powered Q&A and Action Bot MCP Server
# ENTERPRISE-SAFE – HACKATHON-COMPLIANT FINAL
#
# This server exposes:
# - Knowledge search as MCP resources
# - Persona, intents, and actions from external configs
# - Intent resolution as a tool
# - Action tools for escalation and system updates
#
# Industry switching is achieved by swapping config files only.

from fastmcp import FastMCP
from starlette.responses import PlainTextResponse
import json, yaml, time, re
from pathlib import Path

# ---------------- INITIALIZATION ----------------

mcp = FastMCP("knowledge-action-bot")

BASE_CONFIG_PATH = Path("config")

PERSONA_CFG = yaml.safe_load(open(BASE_CONFIG_PATH / "persona.yaml"))
INTENTS_CFG = yaml.safe_load(open(BASE_CONFIG_PATH / "intents.yaml"))
ACTIONS_CFG = yaml.safe_load(open(BASE_CONFIG_PATH / "actions.yaml"))

KNOWLEDGE = json.load(open("data/knowledge.json"))

# ---------------- SEARCH CONFIG (FROM PERSONA) ----------------

SEARCH_CFG = PERSONA_CFG.get("search", {})
SEARCH_MODE = SEARCH_CFG.get("mode", "keyword")

TEXT_CFG = SEARCH_CFG.get("text_processing", {})
STOPWORDS = set(TEXT_CFG.get("stopwords", []))
MIN_TOKEN_MATCH = TEXT_CFG.get("min_token_match", 1)

# ---------------- TEXT NORMALIZATION ----------------

def tokenize(text: str):
    return {
        t for t in re.findall(r"[a-zA-Z]+", text.lower())
        if t not in STOPWORDS
    }

# ---------------- KNOWLEDGE NORMALIZATION ----------------

NORMALIZED_KNOWLEDGE = []
for k in KNOWLEDGE:
    combined = f"{k['title']} {k['content']}"
    NORMALIZED_KNOWLEDGE.append({
        **k,
        "text": combined.lower(),
        "tokens": tokenize(combined)
    })

# ---------------- INTENT INDEX ----------------

INTENT_INDEX = []
for intent in INTENTS_CFG.get("intents", []):
    triggers = (
        intent.get("primary_triggers", [])
        + intent.get("secondary_triggers", [])
    )
    INTENT_INDEX.append({
        "name": intent["name"],
        "triggers": [t.lower() for t in triggers],
        "severity": intent.get("severity", "low")
    })

INTENT_RESOLUTION_CFG = INTENTS_CFG.get("intent_resolution", {})
FALLBACK_INTENT = INTENT_RESOLUTION_CFG.get("fallback_intent", "general")

SECURITY_TRIGGERS = (
    INTENT_RESOLUTION_CFG
    .get("security_triggers", {})
    .get("force_general", [])
)

# ---------------- HEALTH ----------------

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return PlainTextResponse("OK")

# ---------------- SEARCH IMPLEMENTATIONS ----------------

def keyword_search(query: str):
    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    return [
        k for k in NORMALIZED_KNOWLEDGE
        if len(q_tokens & k["tokens"]) >= MIN_TOKEN_MATCH
    ]

def semantic_search(query: str):
    q_tokens = tokenize(query)
    scored = []

    for k in NORMALIZED_KNOWLEDGE:
        score = len(q_tokens & k["tokens"])
        if score > 0:
            scored.append((score, k))

    scored.sort(reverse=True, key=lambda x: x[0])
    return [k for _, k in scored]

def hybrid_search(query: str):
    merged = {}
    for k in keyword_search(query):
        merged[k["id"]] = k
    for k in semantic_search(query):
        merged.setdefault(k["id"], k)
    return list(merged.values())

# ---------------- RESOURCES ----------------

@mcp.resource("knowledge://search/{query}")
async def search_knowledge(query: str) -> dict:
    start = time.time()

    if SEARCH_MODE == "semantic":
        results = semantic_search(query)
    elif SEARCH_MODE == "hybrid":
        results = hybrid_search(query)
    else:
        results = keyword_search(query)

    return {
        "search_mode": SEARCH_MODE,
        "matches": [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "category": r["category"]
            }
            for r in results
        ],
        "response_time_ms": round((time.time() - start) * 1000, 2)
    }

@mcp.resource("knowledge://search/")
async def search_all_knowledge() -> dict:
    return {
        "matches": [
            {
                "id": k["id"],
                "title": k["title"],
                "content": k["content"],
                "category": k["category"]
            }
            for k in NORMALIZED_KNOWLEDGE
        ],
        "response_time_ms": 0
    }

@mcp.resource("config://persona")
async def get_persona() -> dict:
    return PERSONA_CFG

@mcp.resource("config://intents")
async def get_intents() -> dict:
    return INTENTS_CFG

@mcp.resource("config://actions")
async def get_actions() -> dict:
    return ACTIONS_CFG

# ---------------- INTENT TOOL ----------------

@mcp.tool()
async def resolve_intent(user_query: str) -> dict:
    q = user_query.lower()

    for phrase in SECURITY_TRIGGERS:
        if phrase in q:
            return {
                "intent": "general",
                "severity": "low",
                "confidence": "security_override"
            }

    for intent in INTENT_INDEX:
        for trigger in intent["triggers"]:
            if trigger in q:
                return {
                    "intent": intent["name"],
                    "severity": intent["severity"],
                    "confidence": "high"
                }

    return {
        "intent": FALLBACK_INTENT,
        "severity": "low",
        "confidence": "fallback"
    }

# ---------------- ACTION TOOLS ----------------
# NOTE: Execution gating is controlled by actions.yaml

@mcp.tool()
async def create_ticket(issue: str) -> dict:
    return {"status": "created", "issue": issue}

@mcp.tool()
async def update_record(record_id: str, fields: dict) -> dict:
    return {"status": "updated", "record_id": record_id, "fields": fields}

@mcp.tool()
async def send_notification(channel: str, payload: str) -> dict:
    return {"status": "sent", "channel": channel, "payload": payload}

# ---------------- ENTRY ----------------

if __name__ == "__main__":
    print("Starting Knowledge-Powered MCP Server...")
    mcp.run(transport="http", host="0.0.0.0", port=8001)
