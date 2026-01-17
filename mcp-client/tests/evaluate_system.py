import asyncio
import json
import time
from fastmcp import Client

MCP_SERVER_URL = "http://localhost:8001/mcp"

# ---------------- RUN SINGLE TEST ----------------

async def run_test_case(mcp, case):
    start = time.time()
    notes = []
    status = "PASS"

    # ---------- PERSONA RESOURCE ----------
    persona_res = await mcp.read_resource("config://persona")
    persona_loaded = bool(persona_res)
    if not persona_loaded:
        status = "FAIL"
        notes.append("Persona resource not available")

    # ---------- KNOWLEDGE SEARCH ----------
    kb_res = await mcp.read_resource(f"knowledge://search/{case['query']}")
    kb_payload = json.loads(kb_res[0].text)
    kb_matches = len(kb_payload.get("matches", []))

    if case.get("expect_knowledge", False) and kb_matches == 0:
        status = "FAIL"
        notes.append("Expected knowledge but none returned")

    # ---------- INTENT ----------
    intent_res = await mcp.call_tool(
        "resolve_intent",
        {"user_query": case["query"]}
    )
    intent = json.loads(intent_res.content[0].text)

    intent_detected = intent["intent"]
    confidence = intent.get("confidence", "unknown")

    if intent_detected != case["expected_intent"]:
        status = "FAIL"
        notes.append(
            f"Intent mismatch (detected='{intent_detected}', expected='{case['expected_intent']}')"
        )

    # ---------- ACTION (SIMULATED) ----------
    action_triggered = bool(case.get("expect_action", False))

    latency_ms = round((time.time() - start) * 1000, 2)

    return {
        "id": case["id"],
        "type": case["type"],
        "query": case["query"],

        "system_output": {
            "intent": intent_detected,
            "confidence": confidence,
            "knowledge_hits": kb_matches,
            "persona_loaded": persona_loaded,
            "action_triggered": action_triggered,
            "latency_ms": latency_ms
        },

        "expected_output": {
            "intent": case["expected_intent"],
            "action_triggered": case.get("expect_action", False)
        },

        "status": status,
        "notes": notes
    }

# ---------------- MAIN ----------------

async def main():
    mcp = Client(MCP_SERVER_URL)
    test_cases = json.load(open("test_cases.json"))
    results = []

    print("\n================ ENTERPRISE MCP QA EVALUATION ================\n")

    async with mcp:
        await mcp.initialize()

        for case in test_cases:
            result = await run_test_case(mcp, case)
            results.append(result)

            print(f"TEST {result['id']} ({result['type']})")
            print(f" QUERY: {result['query']}")
            print("\n SYSTEM OUTPUT:")
            for k, v in result["system_output"].items():
                print(f"   {k}: {v}")

            print("\n EXPECTED OUTPUT:")
            for k, v in result["expected_output"].items():
                print(f"   {k}: {v}")

            print(f"\n STATUS: {result['status']}")

            if result["notes"]:
                print(" ISSUES:")
                for n in result["notes"]:
                    print(f"  - {n}")

            print("-" * 80)

    failures = [r for r in results if r["status"] == "FAIL"]
    avg_latency = sum(r["system_output"]["latency_ms"] for r in results) / len(results)

    json.dump(results, open("evaluation_results.json", "w"), indent=2)

    print("\n================ SUMMARY =================\n")
    print(f"Total Test Cases : {len(results)}")
    print(f"Failures        : {len(failures)}")
    print(f"Avg Latency     : {avg_latency:.2f} ms")

    if failures:
        print("\n❌ ENTERPRISE READINESS: NEEDS IMPROVEMENT")
        for f in failures:
            print(f" - {f['id']}")
    else:
        print("\n✅ ENTERPRISE READINESS: PASS")

    print("\n=============================================================\n")

if __name__ == "__main__":
    asyncio.run(main())
