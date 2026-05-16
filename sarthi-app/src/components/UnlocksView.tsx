import { useSarthi } from '../store/useSarthi';

export default function UnlocksView() {
  const { state, driver } = useSarthi();
  if (!state || !driver) return null;

  return (
    <main className="scroll" aria-labelledby="uv-h">
      <p className="chip" style={{ alignSelf: 'flex-start' }}>
        Step 5 — what your goals unlock
      </p>
      <h1 className="lede" id="uv-h">
        Meet your goals, <span className="g">unlock</span> protection.
      </h1>
      <p className="muted-p">
        The pitch to {driver.name.split(' ')[0]}: earn more, hit your goals, and
        these open up. Sarthi never charges you — premiums and repayments go
        straight to the Grab partner, money stays in the ecosystem.
      </p>

      {state.unlocks.map((u) => (
        <section
          key={u.key}
          className={`card unlock ${u.unlocked ? '' : 'locked'}`}
        >
          <span className="u-ic">{u.unlocked ? u.icon : '🔒'}</span>
          <div className="u-c">
            <b>{u.title}</b>
            <p>{u.detail}</p>
            <div className={`u-state ${u.unlocked ? 'on' : 'off'}`}>
              {u.unlocked
                ? '✓ Unlocked — ready to activate'
                : `Locked · needs: ${u.requirement}`}
            </div>
          </div>
        </section>
      ))}

      <p className="note">
        This is the answer to "why would Grab trust us with their money": Sarthi
        does not custody money. It grows ride earnings (Grab revenue) and GXS
        engagement, and routes protection to Grab partners. Incentives aligned.
      </p>
    </main>
  );
}
