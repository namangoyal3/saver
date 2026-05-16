# Sarthi — Financial co-pilot for Grab driver-partners

An agentic AI financial wellness co-pilot, embedded as a feature inside the
Grab Driver app. Sarthi closes one loop end to end:

> **predict the goals → fund them with smarter rides → route the surplus into
> GXS → unlock family protection and cheaper credit.**

This repository is the **functional frontend prototype** (hackathon
deliverable a). It runs self-contained in the browser against the synthetic
dataset — no backend, no live Grab data.

---

## The Problem

Singapore's full-time gig workers earn a median ~S$1,500–2,500/month with
**irregular income, thin credit files, and no employer safety net**. The
financial product shelf already exists (GXS Bank, FlexiLoan, Boost Pocket,
Invest) — what is missing is an **intelligent layer that decides which
product, when, and why**, and proves its reasoning.

Sarthi addresses the specific pains:

1. **"How long am I okay?"** — income volatility with no buffer.
2. **Goals that never get funded** — no link between the goal and the next
   shift.
3. **Money sitting idle or going to informal credit** — no orchestration of
   the GXS shelf.
4. **The irreversible CPF opt-in** (Platform Workers Act) — a one-way decision
   with no personalised guidance.

## The Closed Loop (what the demo shows)

| Step | Screen | What the agent does |
|---|---|---|
| 1 Profile + spend ingest | Onboarding | Reads `drivers.csv` + `monthly_summary` + `category_analytics` + `recurring_obligations`. |
| 2 Predict goals | Discovery | `predict_goals()` synthesises personalised goals from the driver's real income, deficit months, debt and dependents. The driver **selects / edits / proceeds**. |
| 3 Fund by earning | Dashboard → Goal detail | `goal_tracker()` + `plan_actions()` turn each goal's weekly gap into the exact earning windows that cover it (from `goal_action_link` + `zone_demand_grid`). Goal-driven, **not** a demand heatmap — Sarthi does not duplicate RideGuide. |
| 4 Route the surplus | Pool | `allocate_surplus()` splits notional surplus across **GXS Bank / Boost Pocket / Invest** by persona risk profile. |
| 5 Unlock protection | Unlocks | `check_unlocks()` turns goal progress into **partner family health insurance** and a **lower FlexiLoan rate**. |

Plus the signature interactions: a live **Reasoning Log**, a **shock re-plan**
(log a S$400 bike repair → the dashboard recomputes), and the **CPF opt-in**
trade-off model.

### Why Grab can trust this with their money

Sarthi never custodies or moves money. It prepares decisions; the driver
confirms. Increased earnings are Grab revenue, surplus flows into GXS
(Grab/Singtel's own bank), and protection routes to Grab partners. Incentives
are aligned — Sarthi is trusted with the **decision**, not the cash.

---

## The Agent's Toolkit (tech stack)

| Layer | Choice | Why |
|---|---|---|
| UI | React 19 + TypeScript + Vite | Component tree mirrors the Frontend Spec; self-contained. |
| State / memory | Zustand store | Dashboard state, decision history, conversation history. |
| Data | Papa Parse over bundled CSVs | Synthetic `expense_dump` + `sg_opportunity`, SG-only slice. |
| Brain | Deterministic supervisor + sub-agents (`src/agent/`) | Default, demo-safe, fully grounded. |
| Optional LLM | Anthropic Haiku via browser fetch (`src/agent/llm.ts`) | OFF by default. Only **rephrases** grounded text — never adds a number. |

In production this maps to a **LangGraph supervisor** with the same typed
tools; here the agent runs in a self-contained form so the live demo never
depends on a network call. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Assumptions & Guardrails (anti-hallucination, anti-rogue-action)

| Risk | Guardrail | Where |
|---|---|---|
| Inventing a number | Every figure comes from a typed tool over a CSV row; the output guard step asserts traceability before emit. | `supervisor.ts` (output_guard) |
| Answering out of scope | Input guard refuses tax / legal / investment-advice and points to a qualified source. | `agent/ask.ts` |
| Taking an irreversible action | Sarthi never executes a draw, transfer or CPF opt-in — it prepares; the driver confirms. | UI copy + no mutation paths |
| Pushing an unsuitable product | `match_product()` is need-driven and can return "no product". | `agent/tools.ts` |
| Silent state change | Every re-plan shows the animation and emits a fresh, viewable reasoning trace. | `ReplanOverlay` + `ReasoningLog` |
| LLM drift | The model is given pre-computed figures and instructed never to alter them; deterministic phrasing is the always-correct fallback. | `agent/llm.ts` |

**Assumptions:** synthetic data only; `notional_available_sgd` uses the
dataset's flat 12%-of-net surplus proxy; the demand grid is a typical-week
pattern; the CPF rates are illustrative pending CPF fields in the dataset.

---

## Run it

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # production bundle (~81 KB gzipped JS)
```

Data lives in `public/data/` (SG-only slice, prepared from
`../expense_dump` and `../sg_opportunity`). Demo persona: **Siti Rahman**
(Singapore, firefighter, age 45, 2 dependents) — first in the driver list.

Deliverables: this prototype (a), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
(b), [`docs/REASONING_LOG.md`](docs/REASONING_LOG.md) (c), this README (d).
