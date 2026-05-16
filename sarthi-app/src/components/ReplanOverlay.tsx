import { useState } from 'react';
import { useSarthi } from '../store/useSarthi';

const STEPS = [
  'Expense Analyst recategorising…',
  'Cashflow Forecaster recomputing runway…',
  'Goal Tracker rebalancing pockets…',
  'Action Planner drafting the bridge…',
];

export function ReplanOverlay() {
  return (
    <div className="replan" role="status" aria-live="polite">
      <div className="spinner" />
      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} style={{ animationDelay: `${i * 280}ms` }}>
            {s}
          </span>
        ))}
      </div>
    </div>
  );
}

const SHOCKS = [
  { category: 'bike repair', amount: 400 },
  { category: 'medical bill', amount: 220 },
  { category: 'phone replacement', amount: 310 },
];

export function LogExpenseFab() {
  const { replan, screen } = useSarthi();
  const [open, setOpen] = useState(false);
  if (screen !== 'dashboard') return null;

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Log an unexpected expense"
        style={{
          position: 'absolute',
          right: 16,
          bottom: 88,
          width: 52,
          height: 52,
          borderRadius: 999,
          background: 'var(--ink)',
          color: '#fff',
          fontSize: 22,
          boxShadow: 'var(--shadow-pop)',
          zIndex: 20,
        }}
      >
        +
      </button>
      {open && (
        <div
          className="card"
          style={{
            position: 'absolute',
            right: 16,
            bottom: 150,
            zIndex: 21,
            width: 240,
            boxShadow: 'var(--shadow-pop)',
          }}
        >
          <div className="section-label" style={{ marginTop: 0 }}>
            Log a shock — watch Sarthi re-plan
          </div>
          {SHOCKS.map((s) => (
            <button
              key={s.category}
              className="btn block"
              style={{ marginTop: 8 }}
              onClick={() => {
                setOpen(false);
                void replan({ type: 'user_reported', ...s });
              }}
            >
              S${s.amount} {s.category}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
