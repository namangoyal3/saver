# Sarthi — Agent Logic & Architecture

Deliverable (b): a visual breakdown of the **brain** (reasoning engine), the
**tools** (functions over the data) and the **memory** (state).

```
                         ┌───────────────────────────────────────────┐
                         │  REQUEST  or  SHOCK SIGNAL                  │
                         │  (driver opens app / logs a S$400 repair)  │
                         └─────────────────────┬─────────────────────-┘
                                               ▼
┌──────────────────────────────  BRAIN  ──────────────────────────────────┐
│                                                                          │
│   ┌────────────┐  plans + routes + composes + phrases                    │
│   │ Supervisor │───────────────┬───────────────┬───────────────┐        │
│   └────────────┘               ▼               ▼               ▼        │
│   Expense Analyst   Cashflow Forecaster   Goal Tracker   Action Planner  │
│   (categorise,      (runway under         (per-goal      (rank actions,  │
│    anomalies)        stress)               badge)         match product) │
│                                                                          │
│   Optional LLM seam: rephrases composed text. NEVER introduces a number. │
└─────────────────────────────────┬────────────────────────────────────────┘
                                   ▼  every call appended to the reasoning trace
┌──────────────────────────────  TOOLS  ──────────────────────────────────┐
│  income_summary()      expense_breakdown()   forecast_cashflow()         │
│  detect_anomaly()      predict_goals()       goal_tracker()              │
│  plan_actions()        match_product()       allocate_surplus()          │
│  check_unlocks()       cpf_project()                                     │
│  Typed, deterministic. Every output is a figure from a CSV row.          │
└─────────────────────────────────┬────────────────────────────────────────┘
                                   ▼  reads
┌──────────────────────────────  DATA  ───────────────────────────────────┐
│  expense_dump/   drivers, transactions, monthly_summary, goals,          │
│                  category_analytics, recurring_obligations               │
│  sg_opportunity/ zone_demand_grid, driver_shift_log, goal_action_link    │
│  Synthetic, reconciled. Structured tables — NOT a vector DB (the data    │
│  is bounded and exact, so a vector store would be the wrong choice).     │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────  MEMORY  ──────────────────────────────────┐
│  Dashboard state (working memory, re-emitted on every re-plan)           │
│  Decision history (goals selected/edited, shocks logged)                 │
│  Conversation history (Ask Sarthi turns)            — Zustand store      │
└──────────────────────────────────────────────────────────────────────────┘
```

## The agent turn (same path for a question or a shock)

1. **Input guard** — scope check + redact identifiers. Out-of-scope (tax,
   legal, investment advice) → refusal with a qualified-source pointer.
2. **Supervisor plans** — which sub-agents and tools are needed.
3. **Sub-agents execute** — each calls typed tools; every call + result is
   appended to the reasoning trace.
4. **Compose** — supervisor assembles `dashboard_state` + plain-language reply.
5. **Output guard** — verify every figure traces to a tool result; verify
   scope.
6. **Emit** — `dashboard_state` + reasoning trace returned; UI is a pure
   render of that state.

## Shock re-plan (signature interaction)

```
log expense ─► supervisor re-runs ─► forecast_cashflow (runway ↓)
            ─► goal_tracker (badge → At risk / Protected)
            ─► plan_actions + match_product (FlexiLoan bridge)
            ─► compose red hero ─► 1.3s overlay ─► dashboard re-renders
```

Mapping to production: the deterministic supervisor here is a
**LangGraph state machine**; each sub-agent is a node; the typed tools are
Python functions; the data layer is structured tables. The prototype keeps
this self-contained so the demo cannot break on stage.
