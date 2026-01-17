# Knowledge-Powered Q&A and Action Bot MCP Client (Gemini)
# ENTERPRISE-SAFE – FINAL (HACKATHON-COMPLIANT, OBSERVABLE)

import asyncio
import os
import json
import time
from fastmcp import Client
from google import genai
from google.genai import types

MCP_SERVER_URL = "http://localhost:8001/mcp"
MAX_HISTORY_TURNS = 4  # aligns with conversation.max_history_turns


# ---------------- HELPERS ----------------

def read_resource_json(resource_result):
    if not resource_result:
        return {}
    item = resource_result[0]
    return json.loads(item.text) if hasattr(item, "text") else {}


def extract_knowledge_matches(resource_result):
    if not resource_result:
        return []
    item = resource_result[0]
    if hasattr(item, "text"):
        return json.loads(item.text).get("matches", [])
    return []


def select_fallback_knowledge(all_kb, intent_name):
    for k in all_kb:
        if k.get("category") == intent_name:
            return [k]
    return []


def is_explicit_escalation(user_query, persona_cfg):
    indicators = (
        persona_cfg.get("escalation_phrases", {})
        .get("user_request_indicators", [])
    )
    q = user_query.lower()
    return any(p in q for p in indicators)


# ---------------- MAIN ----------------

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    gemini = genai.Client(api_key=api_key)
    mcp = Client(MCP_SERVER_URL)

    print("🚀 Knowledge MCP Client started")
    print("Type 'exit', 'quit', or 'done' to end the session.\n")

    conversation_history = []

    async with mcp:
        await mcp.initialize()

        persona = read_resource_json(await mcp.read_resource("config://persona"))

        while True:
            user_query = input("User: ").strip()

            if not user_query:
                print("Please enter a query.\n")
                continue

            if user_query.lower() in {"exit", "quit", "done"}:
                print("Session ended.")
                break

            trace = {
                "persona_loaded": True,
                "timings_ms": {}
            }

            overall_start = time.time()

            # ---------- Explicit Escalation ----------
            if is_explicit_escalation(user_query, persona):
                action_start = time.time()

                await mcp.call_tool(
                    "create_ticket",
                    {"issue": user_query}
                )

                trace["timings_ms"]["action_execution"] = round(
                    (time.time() - action_start) * 1000, 2
                )

                print("\nAssistant:")
                print(
                    "Your request has been escalated to a support representative. "
                    "This session will now end."
                )

                trace["action_taken"] = "create_ticket"
                trace["session_ended"] = True
                trace["timings_ms"]["total"] = round(
                    (time.time() - overall_start) * 1000, 2
                )

                print("\n[TRACE]")
                print(json.dumps(trace, indent=2))
                print("-" * 60)
                break  # enterprise-standard behavior

            # ---------- Knowledge Search ----------
            ks_start = time.time()
            kb_res = await mcp.read_resource(f"knowledge://search/{user_query}")
            knowledge = extract_knowledge_matches(kb_res)
            trace["knowledge_matches"] = len(knowledge)
            trace["timings_ms"]["knowledge_search"] = round(
                (time.time() - ks_start) * 1000, 2
            )

            kb_all = extract_knowledge_matches(
                await mcp.read_resource("knowledge://search/")
            )

            # ---------- Intent Resolution ----------
            ir_start = time.time()
            intent = json.loads(
                (await mcp.call_tool(
                    "resolve_intent",
                    {"user_query": user_query}
                )).content[0].text
            )
            trace["intent"] = intent
            trace["confidence"] = intent.get("confidence", "unknown")
            trace["timings_ms"]["intent_resolution"] = round(
                (time.time() - ir_start) * 1000, 2
            )

            # ---------- Knowledge Fallback ----------
            if not knowledge:
                knowledge = select_fallback_knowledge(
                    kb_all, intent["intent"]
                )
                trace["fallback_used"] = True
            else:
                trace["fallback_used"] = False

            # ---------- Update Conversation History ----------
            conversation_history.append({"role": "user", "text": user_query})
            conversation_history = conversation_history[-MAX_HISTORY_TURNS:]

            # ---------- Build Prompt ----------
            prompt = (
                "You are an enterprise support assistant.\n\n"
                f"Persona Configuration:\n{json.dumps(persona, indent=2)}\n\n"
                f"Relevant Knowledge:\n{json.dumps(knowledge, indent=2)}\n\n"
                "Conversation Context:\n"
            )

            for turn in conversation_history:
                prompt += f"{turn['role'].upper()}: {turn['text']}\n"

            # ---------- LLM Call ----------
            llm_start = time.time()
            response = await gemini.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=prompt)]
                    )
                ]
            )
            trace["timings_ms"]["llm_api_call"] = round(
                (time.time() - llm_start) * 1000, 2
            )

            assistant_reply = response.text.strip()
            conversation_history.append(
                {"role": "model", "text": assistant_reply}
            )

            print("\nAssistant:")
            print(assistant_reply)

            trace["action_taken"] = False
            trace["timings_ms"]["total"] = round(
                (time.time() - overall_start) * 1000, 2
            )

            print("\n[TRACE]")
            print(json.dumps(trace, indent=2))
            print("-" * 60)


# ---------------- ENTRY ----------------

if __name__ == "__main__":
    asyncio.run(main())
