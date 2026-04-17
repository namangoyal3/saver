# Saver — Driver & Partner Financial Wellness Coach

An agentic financial wellness companion for Grab driver-partners and delivery-partners. Saver ingests earnings and spending data, explains where money is going, forecasts cashflow, and helps partners build savings goals — all grounded in real data, never hallucinated.

## Architecture

```
                        ┌──────────────────────────────────────┐
  User (CLI)            │            LangGraph                  │
    │                   │                                       │
    ▼                   │  input_guard ──► supervisor_plan      │
  InputGuard ──────────►│                    │                  │
  (PII redact,          │        ┌───────────┼──────────┐      │
   scope check)         │        ▼           ▼          │      │
                        │    analyst      planner       │      │
                        │    (txn,grab,   (forecast,    │      │
                        │     expense)     goals)       │      │
                        │        │           │          │      │
                        │        └─────┬─────┘          │      │
                        │              ▼                │      │
                        │      supervisor_compose       │      │
                        │              │                │      │
                        │        output_guard           │      │
                        │        (grounding,            │      │
                        │         scope check)          │      │
                        └──────────────────────────────────────┘
                                       │
                                       ▼
                              Tools (SQLite) ◄── Synthetic Data
```

- **Supervisor** routes intent to Analyst (spend/income analysis) or Planner (goals/forecast)
- **9 typed tools** with Pydantic schemas: expense breakdown, income summary, Grab earnings, trip summary, cashflow forecast, goal simulation, goal CRUD
- **Input guardrails**: PII redaction (NRIC, KTP, phone, accounts), scope check (blocks investment/tax/legal advice)
- **Output guardrails**: numeric grounding (every number must come from a tool), scope validation
- **Multi-provider LLM**: NVIDIA (free), Groq (free), or Anthropic — auto-detected from API keys

## Quick Start

```bash
# 1. Clone and install
cd saver
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. Configure LLM provider (pick ONE)
cp .env.example .env

# Option A: NVIDIA (free) — get key from https://build.nvidia.com
echo "NVIDIA_API_KEY=nvapi-xxxxx" >> .env

# Option B: Groq (free) — get key from https://console.groq.com
echo "GROQ_API_KEY=gsk_xxxxx" >> .env

# Option C: Anthropic
echo "ANTHROPIC_API_KEY=sk-ant-xxxxx" >> .env

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
| **Budi** | Indonesia | Delivery | IDR | 4.5M-7M/month | Bahasa |
| **Siti** | Singapore | Ride-hail | SGD | 3.8K-5.2K/month | English |

90 days of synthetic transactions, Grab earnings, and trip data are generated for each persona with realistic patterns: day-of-week seasonality, rest days, weekly/monthly obligations, occasional bad days, and expense spikes.

## Example Conversations

```
You> Where did my money go this week?
Saver> Your total spending was IDR 718,984. Top categories: fuel (38%), food (22%)...

You> How much did I earn from Grab last month?
Saver> Gross: SGD 4,278. After fees (SGD 984) and incentives (SGD 42), net: SGD 3,336.

You> Can I save 3 million rupiah in 6 months?
Saver> That needs IDR 115,473/week. Your surplus is IDR 148,925 — tight but doable...

You> What's my cashflow forecast?
Saver> Next 2 weeks: balance may dip around Apr 22. High-risk dates: [dates]...

You> Should I buy Bitcoin?
Saver> I focus on budgeting and savings — for investment advice, please see a licensed advisor.
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/trace` | Show full reasoning trace (tools called, latency, guardrail results) |
| `/help` | Show help with example questions |
| `/seed` | Re-generate synthetic data |
| `/quit` | Exit |

## Web Dashboard

The web dashboard provides a full end-to-end experience:

- **Login** — Select persona (Budi or Siti)
- **Dashboard** — Financial snapshot: income, expenses, Grab earnings, trips, forecast chart, goals
- **Chat** — AI chat with typing indicators, suggestion chips, reasoning trace toggle
- **Goals** — Create goals, simulate feasibility, track progress with visual bars

The dashboard is mobile-responsive (tested at 375px, 768px, 1280px viewports).

## Tests

```bash
python -m pytest tests/ -v    # 31 tests — tools, guardrails, agent integration
```

## Project Structure

```
saver/
├── saver/
│   ├── __main__.py            # python -m saver entrypoint
│   ├── cli.py                 # Rich-powered interactive CLI
│   ├── models.py              # Pydantic schemas (PRD §15)
│   ├── agents/
│   │   └── supervisor.py      # LangGraph agent graph
│   ├── tools/
│   │   ├── transactions.py    # get_expense_breakdown, get_income_summary
│   │   ├── grab_earnings.py   # get_grab_earnings, get_grab_trip_summary
│   │   ├── forecast.py        # forecast_cashflow, simulate_goal
│   │   └── goals.py           # list_goals, create_goal, update_goal
│   ├── guardrails/
│   │   ├── input_guard.py     # PII regex + scope keywords
│   │   └── output_guard.py    # Numeric grounding + advice detection
│   ├── data/
│   │   ├── db.py              # SQLite schema (mirrors PRD §15.1)
│   │   └── seed.py            # Synthetic data generator (Budi + Siti)
│   └── web/
│       ├── app.py             # FastAPI web application
│       └── templates/         # Jinja2 HTML templates (login, dashboard, chat, goals)
├── tests/
│   ├── test_tools.py          # Tool function tests
│   ├── test_guardrails.py     # Guardrail tests
│   └── test_agent_integration.py  # Agent node tests (no LLM)
├── data/saver.db              # Generated SQLite database
└── pyproject.toml
```

## Guardrails

| Layer | What it does | Implementation |
|-------|-------------|----------------|
| **PII Redaction** | Removes NRIC, KTP, phone, account numbers before LLM | Regex patterns in `input_guard.py` |
| **Scope Check** | Blocks investment/tax/legal advice requests | Keyword matching with educational override |
| **Numeric Grounding** | Ensures every number in reply traces to a tool output | Post-LLM validator in `output_guard.py` |
| **Advice Detection** | Catches if LLM accidentally gives regulated advice | Pattern matching on output |
| **Non-judgmental Tone** | System prompt enforces warm, supportive language | Prompt engineering |

## Compliance Notes

- Saver is NOT a licensed financial advisor
- All financial figures come from tool outputs, never LLM generation
- Out-of-scope requests (investments, insurance, tax, legal) are refused with handoff to licensed advisors
- PII is redacted before reaching the LLM
- Designed per MAS FEAT/Veritas principles: Fairness, Ethics, Accountability, Transparency
