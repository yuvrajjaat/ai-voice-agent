"""
Riverwood AI Voice Agent - Backend Server
An AI-powered voice agent for Riverwood Projects real estate CRM.
"""

import os
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Riverwood AI Voice Agent")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory conversation store (keyed by session ID)
conversations: dict[str, list[dict]] = {}

SYSTEM_PROMPT = """You are a warm, professional AI voice agent for Riverwood Projects LLP, a next-generation real estate development company.

## About Riverwood
- Riverwood Projects LLP develops plotted townships under Deen Dayal Jan Awas Yojana (DDJAY).
- Flagship project: **Riverwood Estate** in Sector 7, Kharkhauda — a 25-acre residential township.
- Located near the upcoming IMT Kharkhauda industrial hub anchored by Maruti Suzuki.
- Philosophy: "Building Foundations and Creating Long-Term Relationships."

## Current Construction Update (March 2026)
- Phase 1 plots: Road construction is 85% complete.
- Boundary wall construction has begun on the eastern perimeter.
- Water supply pipeline installation is underway.
- Electricity infrastructure planning is in final approval stage.
- Green belt and park area landscaping will begin next month.
- Site office is fully operational for customer visits.

## Your Behavior
- Greet the customer warmly by name if provided.
- You can speak in Hindi or English based on what the customer prefers. If unsure, start in English and offer Hindi.
- Share construction progress updates naturally and conversationally.
- Ask if the customer would like to schedule a site visit.
- If they want to visit, ask for their preferred date and time, then confirm.
- Be helpful about payment schedules, project timelines, and amenities.
- Keep responses concise (2-4 sentences) since this is a voice conversation.
- Sound human-like — use natural fillers occasionally like "So," or "Actually," or "By the way."
- Always end with a question or next step to keep the conversation going.
- If the customer speaks Hindi, respond in Hindi (use Romanized Hindi so TTS can handle it).

## Key Project Details
- Plot sizes: 50 sq yard, 100 sq yard, 150 sq yard, 200 sq yard
- Starting price: ₹12 lakh for 50 sq yard plots
- Payment plan: 30% booking amount, rest in 12 monthly installments
- Registry and possession expected: Q4 2026
- Amenities: Parks, wide roads, water supply, electricity, security gate, community center
- RERA registered project
- Contact: 8572070707
"""


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    message = body.get("message", "")
    session_id = body.get("session_id", "default")
    customer_name = body.get("customer_name", "")

    # Initialize conversation if new session
    if session_id not in conversations:
        system = SYSTEM_PROMPT
        if customer_name:
            system += f"\n\nThe customer's name is {customer_name}."
        conversations[session_id] = [{"role": "system", "content": system}]

    # Add user message
    conversations[session_id].append({"role": "user", "content": message})

    # Keep conversation manageable (last 20 messages + system)
    messages = [conversations[session_id][0]] + conversations[session_id][-20:]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )

    assistant_message = response.choices[0].message.content

    # Store assistant response
    conversations[session_id].append(
        {"role": "assistant", "content": assistant_message}
    )

    return JSONResponse(
        {
            "response": assistant_message,
            "session_id": session_id,
            "turn_count": len(conversations[session_id]) - 1,
        }
    )


@app.post("/api/start-call")
async def start_call(request: Request):
    """Simulate an outbound call — agent initiates the conversation."""
    body = await request.json()
    session_id = body.get("session_id", f"call-{datetime.now().timestamp()}")
    customer_name = body.get("customer_name", "Customer")
    language = body.get("language", "english")

    system = SYSTEM_PROMPT + f"\n\nThe customer's name is {customer_name}."
    if language == "hindi":
        system += "\nThe customer prefers Hindi. Respond in Romanized Hindi."

    conversations[session_id] = [{"role": "system", "content": system}]

    # Agent initiates
    init_prompt = f"You are calling {customer_name} to share a construction progress update about Riverwood Estate. Start the call with a warm greeting and introduce yourself. Keep it natural and brief."

    conversations[session_id].append({"role": "user", "content": init_prompt})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversations[session_id],
        temperature=0.7,
        max_tokens=200,
    )

    greeting = response.choices[0].message.content
    # Replace the init prompt with a system-level note so it doesn't confuse further turns
    conversations[session_id].pop()
    conversations[session_id].append({"role": "assistant", "content": greeting})

    return JSONResponse(
        {
            "response": greeting,
            "session_id": session_id,
        }
    )


@app.get("/api/history/{session_id}")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    if session_id not in conversations:
        return JSONResponse({"messages": []})

    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in conversations[session_id]
        if m["role"] != "system"
    ]
    return JSONResponse({"messages": messages})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
