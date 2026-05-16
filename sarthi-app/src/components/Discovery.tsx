import { useState } from 'react';
import { useSarthi } from '../store/useSarthi';
import type { ChosenGoal } from '../agent/supervisor';
import { sgd } from '../agent/tools';

interface Draft {
  on: boolean;
  name: string;
  target: number;
  editing: boolean;
}

export default function Discovery() {
  const { driver, proposed, ds, confirmGoals } = useSarthi();
  const [drafts, setDrafts] = useState<Record<string, Draft>>(() =>
    Object.fromEntries(
      proposed.map((p) => [
        p.goal_key,
        { on: p.category === 'safety', name: p.name, target: p.target, editing: false },
      ]),
    ),
  );
  if (!driver || !ds) return null;

  const set = (k: string, patch: Partial<Draft>) =>
    setDrafts((d) => ({ ...d, [k]: { ...d[k], ...patch } }));

  const chosenCount = Object.values(drafts).filter((d) => d.on).length;

  const confirm = () => {
    const chosen: ChosenGoal[] = proposed
      .filter((p) => drafts[p.goal_key]?.on)
      .map((p) => {
        const d = drafts[p.goal_key];
        const existing = p.existingGoalId
          ? ds.goals.find((g) => g.goal_id === p.existingGoalId)
          : undefined;
        return {
          goal_id: p.existingGoalId ?? `goal_${driver.driver_id}_${p.goal_key}`,
          name: d.name,
          target: d.target,
          current: existing?.current_amount ?? 0,
        };
      });
    confirmGoals(chosen);
  };

  return (
    <main className="scroll" aria-labelledby="dc-h">
      <p className="chip" style={{ alignSelf: 'flex-start' }}>
        Step 1 — the agent analysed {driver.name.split(' ')[0]}'s data
      </p>
      <h1 className="lede" id="dc-h">
        Goals Sarthi <span className="g">predicted</span> for you.
      </h1>
      <p className="muted-p">
        Synthesised from your income, spending pattern, debt and family. Keep,
        edit the target, or skip — you decide before anything is tracked.
      </p>

      {proposed.map((p) => {
        const d = drafts[p.goal_key];
        if (!d) return null;
        return (
          <div
            key={p.goal_key}
            className={`card proposed ${d.on ? 'picked' : ''}`}
          >
            <div className="pp-top">
              <div>
                <h4>{d.name}</h4>
                <span className="chip" style={{ marginTop: 6, display: 'inline-block' }}>
                  {p.category} · {p.horizon}
                  {p.existingGoalId ? ' · already active' : ' · new'}
                </span>
              </div>
              <button
                className="check"
                aria-label={d.on ? 'Deselect goal' : 'Select goal'}
                aria-pressed={d.on}
                onClick={() => set(p.goal_key, { on: !d.on })}
              >
                ✓
              </button>
            </div>

            <p className="why">{p.why}</p>

            {d.editing ? (
              <div className="edit-field">
                <label htmlFor={`t-${p.goal_key}`}>Target amount (S$)</label>
                <input
                  id={`t-${p.goal_key}`}
                  type="number"
                  value={d.target}
                  onChange={(e) =>
                    set(p.goal_key, { target: Number(e.target.value) })
                  }
                />
                <button
                  className="link-edit"
                  onClick={() => set(p.goal_key, { editing: false })}
                >
                  Done
                </button>
              </div>
            ) : (
              <div className="nums">
                <div>
                  Target
                  <b>{sgd(d.target)}</b>
                </div>
                <div>
                  Suggested / month
                  <b>{sgd(p.monthly)}</b>
                </div>
                <button
                  className="link-edit"
                  onClick={() => set(p.goal_key, { editing: true, on: true })}
                >
                  Edit target
                </button>
              </div>
            )}
          </div>
        );
      })}

      <button
        className="btn go block"
        disabled={chosenCount === 0}
        style={{ opacity: chosenCount === 0 ? 0.5 : 1, marginTop: 6 }}
        onClick={confirm}
      >
        Track {chosenCount} goal{chosenCount === 1 ? '' : 's'} → build my plan
      </button>
      <p className="note">
        Sarthi recommends a product only when it fits. It will tell you not to
        take one. Nothing here moves money.
      </p>
    </main>
  );
}
