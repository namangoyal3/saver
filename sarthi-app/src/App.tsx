import { useEffect } from 'react';
import { useSarthi } from './store/useSarthi';
import Onboarding from './components/Onboarding';
import Discovery from './components/Discovery';
import Dashboard from './components/Dashboard';
import GoalDetail from './components/GoalDetail';
import RouteView from './components/RouteView';
import UnlocksView from './components/UnlocksView';
import ReasoningLog from './components/ReasoningLog';
import Architecture from './components/Architecture';
import AskSarthi from './components/AskSarthi';
import { ReplanOverlay, LogExpenseFab } from './components/ReplanOverlay';

const TABS = [
  { id: 'dashboard', label: 'Dashboard', ic: '◎' },
  { id: 'route', label: 'Pool', ic: '◈' },
  { id: 'unlocks', label: 'Unlocks', ic: '🛡' },
  { id: 'ask', label: 'Ask', ic: '✦' },
] as const;

function BottomNav() {
  const { tab, setTab, screen } = useSarthi();
  if (screen === 'onboarding' || screen === 'discovery') return null;
  return (
    <nav className="bottomnav" aria-label="Main navigation">
      {TABS.map((t) => (
        <button
          key={t.id}
          className={tab === t.id ? 'on' : ''}
          aria-current={tab === t.id ? 'page' : undefined}
          onClick={() => setTab(t.id)}
        >
          <span className="ic" aria-hidden>
            {t.ic}
          </span>
          {t.label}
        </button>
      ))}
    </nav>
  );
}

function Screen() {
  const { screen } = useSarthi();
  switch (screen) {
    case 'onboarding':
      return <Onboarding />;
    case 'discovery':
      return <Discovery />;
    case 'goal':
      return <GoalDetail />;
    case 'route':
      return <RouteView />;
    case 'unlocks':
      return <UnlocksView />;
    case 'architecture':
      return <Architecture />;
    case 'ask':
      return <AskSarthi />;
    case 'dashboard':
    case 'reasoning':
    default:
      return <Dashboard />;
  }
}

export default function App() {
  const { init, loading, error, driver, screen, replanning, go } = useSarthi();

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className="shell">
      <div className="device">
        <header className="topbar">
          <div>
            <div className="brand">
              Sarthi<b>.</b>
            </div>
            <div className="sub">
              {driver ? `${driver.name} · ${driver.city}` : 'Financial co-pilot'}
            </div>
          </div>
          <div className="spacer" />
          {driver && screen !== 'onboarding' && (
            <button
              className="chip"
              onClick={() => go('architecture')}
              aria-label="View agent architecture"
            >
              ⚙ Agent
            </button>
          )}
        </header>

        {loading && (
          <main className="center-stack">
            <div className="spinner" />
            <p className="muted-p">Loading the synthetic dataset…</p>
          </main>
        )}

        {error && (
          <main className="center-stack">
            <h1 className="lede">Could not load data</h1>
            <p className="note">{error}</p>
            <p className="muted-p">
              Ensure the CSVs are in <code>public/data/</code> and reload.
            </p>
          </main>
        )}

        {!loading && !error && <Screen />}

        {screen === 'reasoning' && <ReasoningLog />}
        {replanning && <ReplanOverlay />}
        <LogExpenseFab />
        <BottomNav />
      </div>
    </div>
  );
}
