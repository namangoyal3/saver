import { useSarthi } from '../store/useSarthi';
import { sgd } from '../agent/tools';
import type { DashboardGoal } from '../data/types';

const badgeClass = (b: DashboardGoal['badge']) =>
  b === 'On track'
    ? 'ontrack'
    : b === 'Ready'
      ? 'ready'
      : b === 'At risk'
        ? 'atrisk'
        : b === 'Protected'
          ? 'protected'
          : 'tapped';

export default function Dashboard() {
  const { state, driver, go, openGoal, setTab } = useSarthi();
  if (!state || !driver) return null;
  const { hero, runway, goals, actions } = state;
  const runwayPct = Math.min(
    100,
    Math.max(6, (runway.days / 60) * 100),
  );

  return (
    <main className="scroll" aria-label="Sarthi dashboard">
      {/* 1 — Hero: what matters right now */}
      <section
        className={`card hero ${hero.tone === 'green' ? '' : hero.tone}`}
        aria-labelledby="hero-h"
      >
        <div className="hero-top">
          <span className="hero-icon">{hero.icon}</span>
          <span className="section-label" style={{ margin: 0 }}>
            What matters now
          </span>
        </div>
        <div className="hero-title" id="hero-h">
          {hero.title}
        </div>
        <div className="hero-body">{hero.body}</div>
        <button className="hero-trace" onClick={() => go('reasoning')}>
          See how Sarthi reasoned →
        </button>
      </section>

      {/* 2 — Cash runway: how long am I okay */}
      <div className="section-label">Cash runway</div>
      <section className={`card runway ${runway.stressed ? 'stressed' : ''}`}>
        <div className="metric">
          {runway.days} <small>days okay if work slows</small>
        </div>
        <div className="runway-bar">
          <div className="runway-fill" style={{ width: `${runwayPct}%` }} />
        </div>
        <div className="comfort">
          Balance {sgd(runway.balance)} · comfort line {sgd(runway.comfortLine)}{' '}
          · stressed to 55% income
        </div>
      </section>

      {/* 3 — Goals strip: am I making progress */}
      <div className="section-label">Goals</div>
      {goals.map((g) => (
        <button
          key={g.goal_id}
          className="card goal"
          style={{ textAlign: 'left' }}
          onClick={() => openGoal(g.goal_id)}
        >
          <div className="goal-row">
            <span className="goal-name">{g.name}</span>
            <span className={`badge ${badgeClass(g.badge)}`}>{g.badge}</span>
          </div>
          <div className="progress">
            <i
              style={{
                width: `${Math.min(100, (g.current / Math.max(g.target, 1)) * 100)}%`,
              }}
            />
          </div>
          <div className="goal-sub">
            {sgd(g.current)} of {sgd(g.target)} ·{' '}
            {g.gap > 0
              ? `S$${g.gap.toFixed(0)} short this week`
              : `weekly need S$${g.weeklyNeed.toFixed(0)}`}
          </div>
        </button>
      ))}

      {/* 4 — This week: what should I do */}
      <div className="section-label">This week</div>
      {actions.map((a) => (
        <section
          key={a.id}
          className={`card action ${a.primary ? 'primary' : ''}`}
        >
          <p
            className="action-text"
            dangerouslySetInnerHTML={{ __html: a.text }}
          />
          <div className="btn-row">
            <button
              className="btn go"
              onClick={() =>
                a.link === 'route'
                  ? setTab('route')
                  : a.link === 'goal'
                    ? openGoal(goals[0]?.goal_id ?? '')
                    : undefined
              }
            >
              {a.buttons[0]}
            </button>
            <button className="btn ghost">{a.buttons[1]}</button>
          </div>
        </section>
      ))}

      {/* 5 — Ask Sarthi: dig deeper */}
      <button
        className="card ask-bar"
        style={{ marginTop: 4 }}
        onClick={() => setTab('ask')}
      >
        <span className="dot">✦</span>
        <span className="q">Ask Sarthi anything about your money…</span>
        <span aria-hidden>→</span>
      </button>
    </main>
  );
}
