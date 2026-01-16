# Knowledge-Powered Q&A and Action Bot MCP Client (Gemini)
# ENTERPRISE-SAFE – FINAL

import asyncio
import os
import json
from fastmcp import Client
from google import genai
from google.genai import types

MCP_SERVER_URL = "http://localhost:8001/mcp"

HUMAN_KEYWORDS = {
    "human", "agent", "representative",
    "real person", "talk to someone",
    "create ticket", "raise a ticket",
    "contact support"
}


def user_requested_human(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in HUMAN_KEYWORDS)


def extract_contents(resource):
    """Safely extract MCP resource contents"""
    if hasattr(resource, "contents") and resource.contents:
        return resource.contents
    return []

def read_resource_json(resource_result):
    """
    FastMCP resources return a list of TextResourceContents.
    This safely extracts JSON from the first item.
    """
    if not resource_result:
        return {}
    item = resource_result[0]
    if hasattr(item, "text"):
        return json.loads(item.text)
    return {}

def extract_knowledge_matches(resource_result):
    if not resource_result:
        return []
    item = resource_result[0]
    if hasattr(item, "text"):
        payload = json.loads(item.text)
        return payload.get("matches", [])
    return []

def select_fallback_knowledge(all_kb, intent_name):
    """
    Client-side fallback selection.
    Uses intent category to select generic guidance.
    """
    for item in all_kb:
        if item.get("category") == intent_name:
            return [item]
    return []




async def main():
    user_query = input("Enter your query: ").strip()
    if not user_query:
        print("Empty query.")
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    gemini = genai.Client(api_key=api_key)
    mcp = Client(MCP_SERVER_URL)
    trace = {}

    async with mcp:
        await mcp.initialize()

        # -------- Persona (RESOURCE) --------
        persona_res = await mcp.read_resource("config://persona")
        persona = read_resource_json(persona_res)
        trace["persona"] = persona

        # -------- Knowledge (RESOURCE) --------
        kb_res = await mcp.read_resource(f"knowledge://search/{user_query}")
        knowledge = extract_knowledge_matches(kb_res)
        trace["knowledge_matches"] = len(knowledge)

        # -------- Load Full Knowledge Base (for fallback) --------
        kb_all_res = await mcp.read_resource("knowledge://search/")
        kb_all = extract_knowledge_matches(kb_all_res)
        trace["kb_total"] = len(kb_all)


        # -------- Intent (TOOL) --------
        intent_res = await mcp.call_tool(
            "resolve_intent",
            {"user_query": user_query}
        )
        intent = json.loads(intent_res.content[0].text)
        trace["intent"] = intent

        if not knowledge:
            knowledge = select_fallback_knowledge(kb_all, intent["intent"])
            trace["fallback_used"] = True
        else:
            trace["fallback_used"] = False


    
        # -------- LLM Response (Gemini-Compatible) --------

        system_prompt = (
            f"You are a {persona['tone']} support assistant. "
            f"Respond in a {persona['verbosity']} and {persona['style']} manner. "
            "Provide direct, actionable guidance. "
            "Do not mention internal systems, confidence levels, or escalation logic."
        )

        response = await gemini.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=system_prompt)]
                ),
                types.Content(
                    role="user",
                    parts=[types.Part(text=f"Context:\n{knowledge}")]
                ),
                types.Content(
                    role="user",
                    parts=[types.Part(text=user_query)]
                )
            ]
        )


        print("\n🟢 Final Answer")
        print(response.text.strip())

        # -------- Action Policy (STRICT) --------
        action_taken = False

        if user_requested_human(user_query):
            if intent["severity"] in ("medium", "high"):
                await mcp.call_tool(
                    "create_ticket",
                    {"issue": user_query}
                )
                action_taken = True

        trace["action_taken"] = action_taken

        # -------- Internal Trace (DEV ONLY) --------
        print("\n🔍 TRACE LOG (internal)")
        print(json.dumps(trace, indent=2))


if __name__ == "__main__":
    print("🚀 Starting Knowledge MCP Client (Gemini)...")
    asyncio.run(main())
