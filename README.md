# Saver — Driver & Partner Financial Wellness Coach

An agentic financial wellness companion for Grab driver-partners and delivery-partners. Saver ingests a partner's earnings, spending, and obligations, then proactively nudges them toward personalized savings, debt, and emergency-fund goals — with conversational reasoning they can interrogate in their own language.

**Live Demo:** [https://saver-web-production.up.railway.app/](https://saver-web-production.up.railway.app/)

---

## The Problem

~1.3M Grab driver/delivery partners across SEA live with structural income volatility:

- **Earnings vary 30-60% week-to-week** — no monthly salary, no 13th-month pay
- **No employer benefits** — illness = zero income; no CPF, no insurance provided
- **Financial blind spot** — fuel, platform fees, food, and remittances blur into a payout that feels smaller than expected
- **Generic advice doesn't fit** — personal finance apps assume monthly salaries and retirement accounts, not weekly payouts and motorbike repairs
- **One bad week breaks them** — no emergency buffer means a hospital visit triggers high-cost borrowing

**Saver solves this** by reasoning across a partner's transactions, Grab earnings telemetry, and goals to deliver personalized, proactive, compliant financial coaching — in their language — within regulator-acceptable boundaries.

---

## The Agent's Toolkit

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent Runtime** | [LangGraph](https://github.com/langchain-ai/langgraph) | Typed, auditable state graph for supervisor + specialist agent orchestration |
| **LLM** | NVIDIA Nemotron (free) / Groq Llama 3.3 / Anthropic Claude | Multi-provider with auto-detection; tool-use-capable frontier models |
| **Tool Layer** | 9 typed Python functions with Pydantic schemas | Deterministic contracts for financial data — LLM never generates numbers |
| **Data Store** | SQLite | Transactions, earnings, goals, trips (mirrors Postgres schemas from PRD) |
| **Web Framework** | FastAPI + Jinja2 + Tailwind CSS | Server-rendered dashboard with async AI insights |
| **Input Guardrails** | Regex NER + keyword classifier | PII redaction (NRIC/KTP/phone) + scope check (blocks regulated advice) |
| **Output Guardrails** | Numeric grounding validator + scope classifier | Every number must trace to a tool output; investment advice auto-blocked |
| **CLI** | Rich (Python) | Interactive terminal chat with reasoning trace display |
| **Testing** | pytest (32 tests) | Tools, guardrails, agent integration, authorization checks |
| **Deployment** | Railway | Auto-seeds data on startup, single-container deployment |

---

## Agent Logic & Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE BRAIN (LLM)                               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph State Graph                       │  │
│  │                                                                │  │
│  │   USER INPUT                                                   │  │
│  │       │                                                        │  │
│  │       ▼                                                        │  │
│  │   ┌──────────────┐     ┌──────────────────────────────────┐   │  │
│  │   │ INPUT GUARD   │────►│  SUPERVISOR (LLM Reasoning)      │   │  │
│  │   │ • PII redact  │     │  • Classifies intent             │   │  │
│  │   │ • Scope check │     │  • Plans tool calls              │   │  │
│  │   └──────────────┘     │  • Routes to specialist          │   │  │
│  │         │ blocked      │  • Composes final response       │   │  │
│  │         ▼              └──────┬──────────┬────────────────┘   │  │
│  │   ┌──────────┐               │          │                     │  │
│  │   │ REFUSAL  │          ┌────▼───┐ ┌───▼────┐                │  │
│  │   │ (polite) │          │ANALYST │ │PLANNER │                │  │
│  │   └──────────┘          │ node   │ │ node   │                │  │
│  │                         └───┬────┘ └───┬────┘                │  │
│  │                             │          │                      │  │
│  │                         ┌───▼──────────▼───┐                 │  │
│  │                         │   OUTPUT GUARD    │                 │  │
│  │                         │ • Numeric ground  │                 │  │
│  │                         │ • Scope validate  │                 │  │
│  │                         └────────┬──────────┘                │  │
│  │                                  ▼                            │  │
│  │                            RESPONSE + TRACE                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────────┐    ┌──────────────────────────────────┐
│    THE TOOLS (APIs)  │    │      THE MEMORY (State)           │
│                      │    │                                    │
│ get_expense_breakdown│    │  SQLite Database                   │
│ get_income_summary   │    │  ├── users (profile, market)      │
│ get_grab_earnings    │    │  ├── transactions (90 days)       │
│ get_grab_trip_summary│    │  ├── grab_earnings (daily)        │
│ forecast_cashflow    │    │  ├── goals (savings targets)      │
│ simulate_goal        │    │  └── (session state in-memory)    │
│ list_goals           │    │                                    │
│ create_goal          │    │  Conversation History              │
│ update_goal          │    │  └── Last 20 messages per session  │
└─────────────────────┘    └──────────────────────────────────┘
```

### How the Agent Reasons

1. **User sends message** → Input Guard redacts PII, checks if question is in-scope
2. **Supervisor plans** → LLM classifies intent (spend analysis? forecast? goal? out-of-scope?) and selects tools
3. **Specialist executes** → Analyst or Planner node calls typed Python tools against SQLite
4. **Supervisor composes** → LLM synthesizes tool outputs into a warm, grounded response
5. **Output Guard validates** → Every number checked against tool outputs; regulated advice blocked
6. **Response delivered** → With full reasoning trace available via `/trace` or trace toggle

---

## Sample Reasoning Log

This is a real trace from the agent processing "Kenapa saldo saya habis cepat minggu ini?" ("Why is my balance gone so fast this week?") for Budi, a delivery partner in Jakarta:

```
turn_id: 7f3e...  |  user: budi-001  |  lang: id
────────────────────────────────────────────────────────

[Step 1] supervisor.plan                              (1380 ms)
  Intent: describe_spend
  Plan: Call get_expense_breakdown + get_grab_trip_summary
  Reasoning: User asks about balance depletion → need spending
  breakdown and trip data to correlate spending with work activity.

[Step 2] analyst.tool_call                            (1 ms)
  Tool: get_expense_breakdown(window_days=7)
  Result: total=718,984 IDR
    ├── remittance:  266,193 (37.0%)
    ├── groceries:   187,639 (26.1%)
    ├── fuel:        120,458 (16.8%)
    ├── food_on_road: 86,749 (12.1%)
    ├── other:        35,389 (4.9%)
    └── data_top_up:  22,555 (3.1%)

[Step 3] analyst.tool_call                            (2 ms)
  Tool: get_grab_trip_summary(window_days=7)
  Result: trips=92, hours=48.8h, fuel_ratio=8%
  Observation: High trip count but low fuel ratio — fuel
  spending increase may be due to price changes, not more driving.

[Step 4] supervisor.compose                           (7281 ms)
  Synthesizing: expense breakdown + trip correlation
  Language: Bahasa Indonesia (user preference)
  Grounding: All numbers from Steps 2-3, no fabricated figures
  Tone: Warm, non-judgmental, actionable

[Step 5] output_guard.validate                        (< 1 ms)
  Faithfulness: PASS (all numerics trace to tool outputs)
  Scope: PASS (no regulated advice given)
  Tone: PASS (non-judgmental)

FINAL RESPONSE (id):
  "Halo Budi! Minggu ini pengeluaranmu ~Rp718.984 — naik dari
  rata-rata minggu sebelumnya. Penyebab utama: transfer uang
  (37%), belanja (26.1%), dan bensin (16.8%). Mau saya bantu
  buat rencana tabungan dari sisa pendapatanmu?"

Total latency: 8,664 ms  |  Cost: ~$0.007
```

This log demonstrates: **intent classification → specialist routing → grounded tool calls → observation/correlation → composition with citation → guardrail verification → localized response with actionable next step.**

---

## Assumptions & Guardrails

### Assumptions

1. **Mock data throughout** — 90-day synthetic earnings, transactions, and trips for 2 personas (Budi in Jakarta, Siti in Singapore). No live Grab/GXS data.
2. **Self-contained** — runs locally with `python -m saver web` or deployed on Railway. No external dependencies beyond the LLM API.
3. **Users are consented, 21+, in-market** — the prototype assumes SG/ID markets with full data consent.
4. **Cold-start users have 30+ days of history** — the forecast tool requires historical data.

### Guardrails — How We Prevent Hallucination & Rogue Actions

| Threat | Guardrail | Implementation |
|--------|-----------|----------------|
| **Hallucinated financial numbers** | Numeric grounding validator | Every number in the response is checked against tool outputs. Ungrounded numbers are stripped. LLMs never generate monetary figures — they come only from typed tool functions. |
| **Regulated advice** (investments, insurance, tax) | Scope classifier + prompt constraints | Input guard blocks keywords (crypto, stock, invest, tax). Output guard catches if LLM accidentally produces advice-shaped text. Refused with polite handoff to licensed advisor. |
| **PII leakage** | Pre-LLM PII redaction | Regex patterns for NRIC (Singapore), KTP (Indonesia), phone numbers, and account numbers. Redacted before the message reaches the LLM. |
| **Unauthorized actions** | User ownership checks | `update_goal()` requires `user_id` match. Goal creation requires explicit confirmation. No money movement without user action. |
| **Prompt injection** | Input sanitization + structured output | User input is cleaned before entering the prompt. Tool outputs are rendered with delimiters. System prompt explicitly forbids treating tool output as instructions. |
| **Moralizing / shaming** | Tone enforcement | System prompt: "NEVER moralize or judge the user's spending. Be warm, supportive, and non-judgmental." |
| **Model drift** | Multi-provider fallback | NVIDIA → Groq → Anthropic auto-detection. If one provider fails, others are available. |

### What Saver Does NOT Do (Hard-Coded Boundaries)

- Give specific investment recommendations or securities advice
- Recommend specific insurance or credit products
- File taxes or provide tax advice
- Execute money movement without explicit user confirmation
- Replace a licensed financial advisor

---

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/namangoyal3/saver.git
cd saver
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. Configure LLM provider (pick ONE)
cp .env.example .env

# Option A: NVIDIA (free) — get key from https://build.nvidia.com
echo "NVIDIA_API_KEY=nvapi-xxxxx" >> .env

# Option B: Groq (free) — get key from https://console.groq.com
echo "GROQ_API_KEY=gsk_xxxxx" >> .env

# 3. Seed synthetic data (90 days for 2 personas)
python -m saver seed

# 4a. Web dashboard (recommended)
python -m saver web                 # http://localhost:8000

# 4b. Or use the CLI
python -m saver chat --user budi    # Jakarta delivery partner (Bahasa)
python -m saver chat --user siti    # Singapore ride-hail driver (English)
```

## Demo Personas

| Persona | Market | Type | Currency | Earnings | Language |
|---------|--------|------|----------|----------|----------|
| **Budi** | Indonesia | Delivery | IDR | 4.5M-7M/month | Bahasa Indonesia |
| **Siti** | Singapore | Ride-hail | SGD | 3.8K-5.2K/month | English |

90 days of synthetic transactions, Grab earnings, and trip data are generated for each persona with realistic patterns: day-of-week seasonality, rest days, weekly/monthly obligations, occasional bad days, and expense spikes.

## Web Dashboard

The web dashboard provides a full end-to-end experience:

- **Login** — Select persona (Budi or Siti)
- **Dashboard** — AI-powered "Saver Says" insights + financial snapshot (income, expenses, Grab earnings, trips, forecast chart, goals with progress bars, week-over-week deltas)
- **Chat** — Conversational AI with markdown rendering, typing indicators, suggestion chips, and reasoning trace toggle
- **Goals** — Create savings goals, simulate feasibility with historical data, track progress

Mobile-responsive (tested at 375px, 768px, 1280px).

## Tests

```bash
python -m pytest tests/ -v    # 32 tests — tools, guardrails, agent integration, auth
```

## Project Structure

```
saver/
├── saver/
│   ├── __main__.py            # python -m saver entrypoint
│   ├── cli.py                 # Rich-powered interactive CLI
│   ├── models.py              # Pydantic schemas (PRD §15)
│   ├── agents/
│   │   ├── supervisor.py      # LangGraph state graph + orchestration
│   │   ├── llm_config.py      # Multi-provider LLM setup
│   │   ├── prompts.py         # System prompts + refusal templates
│   │   └── tool_registry.py   # Tool functions + LLM schemas
│   ├── tools/
│   │   ├── transactions.py    # get_expense_breakdown, get_income_summary
│   │   ├── grab_earnings.py   # get_grab_earnings, get_grab_trip_summary
│   │   ├── forecast.py        # forecast_cashflow, simulate_goal
│   │   └── goals.py           # list_goals, create_goal, update_goal
│   ├── guardrails/
│   │   ├── input_guard.py     # PII regex + scope keywords
│   │   └── output_guard.py    # Numeric grounding + advice detection
│   ├── data/
│   │   ├── db.py              # SQLite schema + helpers
│   │   └── seed.py            # Synthetic data generator (Budi + Siti)
│   └── web/
│       ├── app.py             # FastAPI web application + AI insights API
│       └── templates/         # Jinja2 HTML templates
├── tests/                     # 32 tests (tools, guardrails, auth, integration)
├── data/saver.db              # Generated SQLite database
└── pyproject.toml
```

## Who Benefits

1. **Gig Economy Workers** — Get tailored financial coaching designed for weekly payouts, variable income, and no employer benefits. Move from reactive cash management to proactive financial resilience.

2. **Customers/Users** — Benefit from intelligent, proactive, and deeply personalized financial tools that address their specific needs, not generic one-size-fits-all advice.

3. **Financial Service Providers (GXS/Grab)** — Differentiated product that drives engagement, deepens trust, and creates a pathway to additional financial products (savings, insurance, credit) — all within regulatory boundaries.

## Compliance

- Designed per MAS FEAT/Veritas principles: Fairness, Ethics, Accountability, Transparency
- PDPA-aware: PII redacted before LLM, data residency considerations
- Scope-limited: generic education + budgeting only, regulated advice → licensed advisor handoff
