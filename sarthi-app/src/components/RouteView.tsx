import { useSarthi } from '../store/useSarthi';
import { sgd } from '../agent/tools';

export default function RouteView() {
  const { state, driver } = useSarthi();
  if (!state || !driver) return null;
  const a = state.allocation;

  return (
    <main className="scroll" aria-labelledby="rv-h">
      <p className="chip" style={{ alignSelf: 'flex-start' }}>
        Step 4 — route the surplus
      </p>
      <h1 className="lede" id="rv-h">
        Where your <span className="g">spare money</span> goes.
      </h1>
      {!a || a.slices.length === 0 ? (
        <section className="card">
          <p className="goal-sub">
            No surplus to route this week — every dollar is committed to
            essentials and your goal contributions. Sarthi will not invent
            spare cash.
          </p>
        </section>
      ) : (
        <>
          <p className="muted-p">
            You have <b>{sgd(a.surplus)}</b> notionally spare this week. Sarthi
            splits it by your <b>{driver.persona}</b> risk profile — liquidity
            first, then yield, then a small invested slice. It prepares the
            split; you confirm each move.
          </p>
          <section className="card">
            {a.slices.map((s) => (
              <div className="alloc-row" key={s.product}>
                <span className="alloc-ic">{s.icon}</span>
                <span className="alloc-meta">
                  <b>{s.product}</b>
                  <span>{s.why}</span>
                </span>
                <span className="alloc-amt">{sgd(s.amount)}</span>
              </div>
            ))}
          </section>
          <button className="btn go block">Prepare these moves</button>
          <p className="note">
            Money stays inside the Grab / GXS ecosystem. Sarthi never holds or
            transfers it — that is why it can be trusted with the decision but
            not the cash.
          </p>
        </>
      )}
    </main>
  );
}
