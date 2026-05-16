import { useSarthi } from '../store/useSarthi';

export default function ReasoningLog() {
  const { state, go } = useSarthi();
  if (!state) return null;

  return (
    <div className="sheet-wrap" role="dialog" aria-label="Reasoning log">
      <div className="sheet-scrim" onClick={() => go('dashboard')} />
      <div className="sheet">
        <div className="sheet-head">
          <b>Reasoning log</b>
          <button
            className="x"
            aria-label="Close"
            onClick={() => go('dashboard')}
          >
            ✕
          </button>
        </div>
        <div className="sheet-body">
          <p className="note">
            Every step Sarthi took for this recommendation. Each figure traces
            to a typed tool over your data — the agent does not invent numbers.
          </p>
          {state.reasoning.map((s) => (
            <div
              key={s.step}
              className={`trace-step ${s.kind}`}
              style={{ animationDelay: `${s.step * 70}ms` }}
            >
              <span className="trace-n">{s.step}</span>
              <div className="trace-c">
                <span className="act">{s.text}</span>
                <span className="tool">{s.tool}()</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
