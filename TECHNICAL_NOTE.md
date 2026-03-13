# Riverwood AI Voice Agent — Technical Note

## Architecture Overview

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser     │────▶│  FastAPI      │────▶│  OpenAI GPT  │
│  (Frontend)   │◀────│  (Backend)    │◀────│  (LLM)       │
└──────────────┘     └──────────────┘     └──────────────┘
  │         ▲
  │ Web Speech API
  ▼         │
┌──────────────┐
│  Voice I/O   │
│  (STT + TTS) │
└──────────────┘
```

### Components
1. **Frontend**: Single-page HTML/JS app with call simulation UI
2. **Speech-to-Text**: Browser Web Speech API (Chrome) for voice input
3. **LLM Engine**: OpenAI GPT-4o-mini for contextual response generation
4. **Text-to-Speech**: Browser SpeechSynthesis API for voice output
5. **Backend**: FastAPI server with conversation memory per session
6. **Context System**: System prompt with Riverwood project details + rolling conversation window

### Conversation Flow
1. Agent initiates call → GPT generates personalized greeting
2. User responds via voice (mic) or text
3. Backend appends to session history → GPT generates contextual reply
4. Response spoken aloud via TTS + displayed in chat UI

---

## Infrastructure Design: 1000 Calls/Morning

### Architecture for Scale

```
┌────────────┐     ┌──────────────┐     ┌──────────────┐
│  Campaign   │────▶│  Task Queue   │────▶│  Worker Pool  │
│  Scheduler  │     │  (Redis/SQS)  │     │  (50 workers) │
└────────────┘     └──────────────┘     └──────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                   ▼                   ▼
                   ┌────────────┐     ┌────────────┐     ┌────────────┐
                   │  Twilio     │     │  OpenAI    │     │  ElevenLabs│
                   │  Voice API  │     │  GPT API   │     │  TTS API   │
                   └────────────┘     └────────────┘     └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │  CRM DB     │
                   │  (Postgres) │
                   └────────────┘
```

### Design

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Telephony | Twilio Programmable Voice | Handles concurrent outbound calls, supports webhooks |
| Orchestration | VAPI or custom FastAPI | Manages call flow, handles Twilio webhooks |
| LLM | OpenAI GPT-4o-mini | Low latency, cost-effective for conversations |
| TTS | ElevenLabs Turbo v2 | Human-like voice, Hindi support, streaming |
| STT | Deepgram Nova-2 | Real-time streaming transcription, low latency |
| Queue | Redis + Celery (or AWS SQS) | Distribute calls across workers, handle retries |
| Database | PostgreSQL | Store call logs, transcripts, customer responses |
| Scheduling | Cron job / Airflow | Trigger morning campaign at configured time |

### Scaling Strategy
- **50 concurrent workers** to handle 1000 calls in ~1 hour (avg 3 min/call)
- **Rate limiting** on Twilio (configure CPS — calls per second)
- **Retry logic** for busy/no-answer with exponential backoff
- **Priority queue** for high-value customers first
- **Circuit breaker** on API failures to prevent cascade

### Estimated Cost per 1000 Calls

| Service | Unit Cost | Usage per Call | Cost (1000 calls) |
|---------|-----------|---------------|-------------------|
| Twilio Voice (outbound, India) | ₹0.50/min | ~3 min | ₹1,500 |
| OpenAI GPT-4o-mini | $0.15/1M input + $0.60/1M output | ~800 tokens | ₹50 (~$0.60) |
| ElevenLabs TTS | $0.18/1K chars | ~500 chars | ₹750 (~$9) |
| Deepgram STT | $0.0043/min | ~2 min | ₹360 (~$4.30) |
| Infrastructure (server) | ~₹5,000/month | — | ₹170/day |

**Total estimated cost: ₹2,830 per 1000 calls (~₹2.83 per call)**

### Optimizations
- Cache common responses to reduce LLM calls
- Use ElevenLabs voice cloning for a consistent brand voice
- Batch API calls where possible
- Use Twilio's AMD (Answering Machine Detection) to skip voicemails
- Store call outcomes in CRM for analytics and follow-up scheduling
