import { useSarthi } from '../store/useSarthi';

const TOOLS = [
  'income_summary',
  'expense_breakdown',
  'forecast_cashflow',
  'detect_anomaly',
  'predict_goals',
  'goal_tracker',
  'plan_actions',
  'match_product',
  'allocate_surplus',
  'check_unlocks',
  'cpf_project',
];

export default function Architecture() {
  const { go } = useSarthi();
  return (
    <main className="scroll arch" aria-labelledby="ar-h">
      <button
        className="link-edit"
        onClick={() => go('dashboard')}
        style={{ alignSelf: 'flex-start' }}
      >
        ← Dashboard
      </button>
      <h1 className="lede" id="ar-h">
        Agent <span className="g">architecture</span>
      </h1>
      <p className="muted-p">
        Supervisor agent with typed tools. The brain plans and phrases; the
        tools compute and ground; the memory holds state. Every figure is
        traceable — that is the anti-hallucination guarantee.
      </p>

      <div className="layer brain">
        <div className="lyr-t">Brain — reasoning engine</div>
        <div className="pill-grid">
          <span className="pill">Supervisor</span>
          <span className="pill">Expense Analyst</span>
          <span className="pill">Cashflow Forecaster</span>
          <span className="pill">Goal Tracker</span>
          <span className="pill">Action Planner</span>
        </div>
        <p className="goal-sub" style={{ marginTop: 8 }}>
          Deterministic by default (demo-safe, sandboxed). Optional LLM seam
          rephrases narratives — it never introduces a number (output guard).
        </p>
      </div>
      <div className="flowline">▼ calls typed tools ▼</div>
      <div className="layer tools">
        <div className="lyr-t">Tools — functions over the dataset</div>
        <div className="pill-grid">
          {TOOLS.map((t) => (
            <span className="pill mono" key={t}>
              {t}()
            </span>
          ))}
        </div>
        <p className="goal-sub" style={{ marginTop: 8 }}>
          Source: expense_dump (84k txns, drivers, goals) + sg_opportunity
          (zone demand grid, shift log, goal-action link). Synthetic, reconciled.
        </p>
      </div>
      <div className="flowline">▼ reads / writes ▼</div>
      <div className="layer memory">
        <div className="lyr-t">Memory — state management</div>
        <div className="pill-grid">
          <span className="pill">Dashboard state (working)</span>
          <span className="pill">Decision history</span>
          <span className="pill">Conversation history</span>
        </div>
        <p className="goal-sub" style={{ marginTop: 8 }}>
          Structured typed tables, not a vector DB — the driver's financial data
          is bounded and exact, so a vector store would be wrong here.
        </p>
      </div>

      <div className="section-label">Guardrails</div>
      <section className="card">
        {[
          ['Inventing a number', 'Output guard rejects any figure not from a tool result.'],
          ['Out of scope', 'Input guard refuses tax / legal / investment advice.'],
          ['Irreversible action', 'Never executes a draw, transfer or CPF opt-in — prepares only.'],
          ['Unsuitable product', 'match_product is need-driven; can return "no product".'],
          ['Silent change', 'Every re-plan shows the animation and a fresh viewable trace.'],
        ].map(([k, v]) => (
          <div className="kv" key={k}>
            <span>{k}</span>
            <b style={{ maxWidth: 200, textAlign: 'right', fontWeight: 600 }}>
              {v}
            </b>
          </div>
        ))}
      </section>
    </main>
  );
}
