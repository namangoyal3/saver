import { useSarthi } from '../store/useSarthi';
import { goalStatus, cpfProject, incomeSummary, sgd, sgd1 } from '../agent/tools';

interface ParsedWindow {
  when: string;
  zone: string;
  rate: string;
  surge: string;
}

function parseWindows(raw: string): ParsedWindow[] {
  if (!raw) return [];
  return raw
    .split(';')
    .map((w) => w.trim())
    .filter(Boolean)
    .slice(0, 4)
    .map((w) => {
      const m = w.match(
        /^(\w+ \d+:\d+)\s+(.+?)\s+\(~?(S\$[\d.]+\/hr),?\s*x?([\d.]+)?\)?/,
      );
      if (!m) return { when: w, zone: '', rate: '', surge: '' };
      return {
        when: m[1],
        zone: m[2],
        rate: m[3],
        surge: m[4] ? `${m[4]}×` : '',
      };
    });
}

export default function GoalDetail() {
  const { ds, driver, state, focusGoalId, go } = useSarthi();
  if (!ds || !driver || !state) return null;
  const goal =
    state.goals.find((g) => g.goal_id === focusGoalId) ?? state.goals[0];
  if (!goal) return null;
  const link = goalStatus(ds, goal.goal_id);
  const windows = parseWindows(link?.recommended_windows ?? '');
  const eligibleCpf = driver.age >= 31; // born before 1995
  const inc = incomeSummary(ds, driver.driver_id);
  const cpf = cpfProject(inc.avgMonthlyNet, eligibleCpf);

  return (
    <main className="scroll" aria-labelledby="gd-h">
      <button
        className="link-edit"
        onClick={() => go('dashboard')}
        style={{ alignSelf: 'flex-start' }}
      >
        ← Dashboard
      </button>
      <h1 className="lede" id="gd-h">
        {goal.name}
      </h1>
      <section className="card">
        <div className="kv">
          <span>Funded</span>
          <b>
            {sgd(goal.current)} / {sgd(goal.target)} (
            {Math.round((goal.current / Math.max(goal.target, 1)) * 100)}%)
          </b>
        </div>
        <div className="kv">
          <span>Weekly need</span>
          <b>{sgd1(goal.weeklyNeed)}</b>
        </div>
        <div className="kv">
          <span>This week</span>
          <b style={{ color: goal.gap > 0 ? 'var(--amber)' : 'var(--grab-dark)' }}>
            {goal.gap > 0 ? `${sgd1(goal.gap)} short` : 'covered'}
          </b>
        </div>
        <div className="kv">
          <span>Extra hours to close</span>
          <b>{link ? `${link.extra_hours_needed.toFixed(1)} h` : '—'}</b>
        </div>
      </section>

      <div className="section-label">
        Earn it — windows that fund this goal
      </div>
      <p className="note">
        Not "drive where it's surging". Sarthi starts from this goal's gap and
        points to the windows in your preferred zones that cover it.
      </p>
      <section className="card">
        {windows.length === 0 && (
          <p className="goal-sub">
            On track — no extra window needed this week.
          </p>
        )}
        {windows.map((w, i) => (
          <div className="window-row" key={i}>
            <span className="wr-when">{w.when}</span>
            <span className="wr-zone">
              {w.zone}
              <span>{w.surge && `surge ${w.surge}`}</span>
            </span>
            <span className="wr-rate">{w.rate}</span>
          </div>
        ))}
      </section>

      {eligibleCpf && /insurance|emergency|buffer|smoothing/i.test(goal.name) && (
        <>
          <div className="section-label">
            The CPF opt-in — Sarthi's signature decision
          </div>
          <section className="card">
            <p className="why" style={{ marginBottom: 8 }}>
              You were born before 1995, so you can opt in to higher CPF. It is
              <b> irreversible</b>. Sarthi models it; you decide.
            </p>
            <div className="kv">
              <span>Take-home now</span>
              <b>{sgd(cpf.before)}/mo</b>
            </div>
            <div className="kv">
              <span>Take-home if opted in</span>
              <b>{sgd(cpf.after)}/mo</b>
            </div>
            <div className="kv">
              <span>Operator match (free)</span>
              <b style={{ color: 'var(--grab-dark)' }}>
                +{sgd(cpf.operatorContribution)}/mo
              </b>
            </div>
            <div className="kv">
              <span>Into retirement / housing</span>
              <b style={{ color: 'var(--grab-dark)' }}>
                {sgd(cpf.retirementGain)}/mo
              </b>
            </div>
            <p className="note" style={{ marginTop: 10 }}>
              Sarthi will not opt you in. It prepares the trade-off; you confirm
              with CPF directly.
            </p>
          </section>
        </>
      )}
    </main>
  );
}
