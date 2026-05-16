import { useSarthi } from '../store/useSarthi';
import type { Driver } from '../data/types';

const personaClass = (p: Driver['persona']) =>
  p === 'firefighter' ? 'ff' : p === 'grower' ? 'gr' : 'st';

export default function Onboarding() {
  const { ds, pickDriver } = useSarthi();
  if (!ds) return null;
  const drivers = [...ds.drivers].sort((a, b) =>
    a.driver_id === 'drv_siti_sg_10' ? -1 : b.driver_id === 'drv_siti_sg_10' ? 1 : 0,
  );

  return (
    <main className="center-stack" aria-labelledby="ob-h">
      <p className="chip" style={{ alignSelf: 'flex-start' }}>
        Inside the Grab Driver app
      </p>
      <h1 className="lede" id="ob-h">
        Your money has a <span className="g">co-pilot</span> now.
      </h1>
      <p className="muted-p">
        Sarthi reads your earnings and spending, sets goals that fit your life,
        then shows you the exact extra hours that fund them — and unlocks
        family cover and cheaper credit as you go. Pick a driver to link.
      </p>

      <div className="section-label">Link a driver account</div>
      {drivers.map((d) => (
        <button
          key={d.driver_id}
          className="card driver-card"
          onClick={() => pickDriver(d.driver_id)}
        >
          <span className={`avatar ${personaClass(d.persona)}`}>
            {d.name.split(' ').map((w) => w[0]).join('').slice(0, 2)}
          </span>
          <span className="driver-meta">
            <b>{d.name}</b>
            <span>
              {d.city} · {d.vehicle} · age {d.age} ·{' '}
              {d.dependents} dependent{d.dependents === 1 ? '' : 's'}
            </span>
          </span>
          <span className={`persona-tag ${d.persona}`}>{d.persona}</span>
        </button>
      ))}

      <p className="note">
        Synthetic data only. No live Grab production data. Sarthi never moves
        money — it prepares decisions; you confirm.
      </p>
    </main>
  );
}
