# Knowledge-Powered Q&A and Action Bot MCP Server
# ENTERPRISE-SAFE – FINAL

from fastmcp import FastMCP
from starlette.responses import PlainTextResponse
import json, yaml, time

# ---------------- INITIALIZATION ----------------

mcp = FastMCP("knowledge-action-bot")

CONFIG = yaml.safe_load(open("config/industry.yaml"))
KNOWLEDGE = json.load(open("data/knowledge.json"))

# Normalize knowledge once (performance)
NORMALIZED_KNOWLEDGE = [
    {
        **k,
        "text": f"{k['title']} {k['content']}".lower()
    }
    for k in KNOWLEDGE
]

# Pre-index intents (deterministic, no actions here)
INTENT_INDEX = []
for intent in CONFIG["intents"]:
    triggers = []
    triggers.extend(intent.get("primary_triggers", []))
    triggers.extend(intent.get("secondary_triggers", []))

    INTENT_INDEX.append({
        "name": intent["name"],
        "categories": intent.get("categories", []),
        "triggers": [t.lower() for t in triggers],
        "severity": intent.get("severity", "low")
    })

FALLBACK_INTENT = CONFIG.get("intent_resolution", {}).get(
    "fallback_intent", "general"
)

# ---------------- HEALTH CHECK ----------------

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return PlainTextResponse("OK")

# ---------------- RESOURCES ----------------

@mcp.resource("knowledge://search/{query}")
async def search_knowledge(query: str) -> dict:
    """Fast keyword-based knowledge search"""
    start = time.time()
    q = query.lower()

    results = [
        k for k in NORMALIZED_KNOWLEDGE
        if q in k["text"]
    ]

    duration_ms = round((time.time() - start) * 1000, 2)

    return {
        "matches": [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"],
                "category": r["category"]
            }
            for r in results
        ],
        "response_time_ms": duration_ms
    }

@mcp.resource("config://persona")
async def get_persona() -> dict:
    return CONFIG["persona"]

@mcp.resource("config://intents")
async def get_intents() -> dict:
    return CONFIG["intents"]

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


# ---------------- INTENT RESOLUTION ----------------

@mcp.tool()
async def resolve_intent(user_query: str) -> dict:
    """
    Deterministic intent resolution.
    NO actions are decided here.
    """
    q = user_query.lower()

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

@mcp.tool()
async def create_ticket(issue: str) -> dict:
    return {
        "status": "created",
        "message": f"Support ticket created for issue: {issue}"
    }

@mcp.tool()
async def update_record(record_id: str, fields: dict) -> dict:
    return {
        "status": "updated",
        "record_id": record_id,
        "fields": fields
    }

@mcp.tool()
async def send_notification(channel: str, payload: str) -> dict:
    return {
        "status": "sent",
        "channel": channel,
        "payload": payload
    }

# ---------------- SERVER ENTRY ----------------

if __name__ == "__main__":
    print("Starting Knowledge-Powered MCP Server...")
    mcp.run(transport="http", host="0.0.0.0", port=8001)
