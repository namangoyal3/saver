import { useState, useRef, useEffect } from 'react';
import { useSarthi } from '../store/useSarthi';
import { answer } from '../agent/ask';
import { narrate, llmEnabled, setKey, getKey } from '../agent/llm';

const SUGGESTIONS = [
  'How long am I okay?',
  'Where does my money go?',
  'Should I opt in to CPF?',
  'How do I fund my insurance goal?',
];

export default function AskSarthi() {
  const { ds, driver, state, chat, pushChat } = useSarthi();
  const [q, setQ] = useState('');
  const [keyOpen, setKeyOpen] = useState(false);
  const [keyVal, setKeyVal] = useState(getKey());
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  if (!ds || !driver || !state) return null;

  const send = async (text: string) => {
    if (!text.trim()) return;
    pushChat({ role: 'me', text });
    setQ('');
    const a = answer(text, ds, driver, state);
    const narrated = await narrate(a.text, `Driver ${driver.name}`);
    pushChat({
      role: 'ai',
      text: narrated.text,
      source: `${a.source} · ${narrated.source}`,
    });
  };

  return (
    <>
      <main className="scroll" aria-label="Ask Sarthi" style={{ paddingBottom: 16 }}>
        <div className="topbar" style={{ position: 'static', border: 'none', padding: '4px 2px 8px' }}>
          <div>
            <div className="section-label" style={{ margin: 0 }}>
              Ask Sarthi
            </div>
            <div className="topbar sub" style={{ padding: 0 }}>
              {llmEnabled() ? 'LLM narration on' : 'deterministic · grounded'}
            </div>
          </div>
          <div className="spacer" />
          <button className="chip" onClick={() => setKeyOpen((o) => !o)}>
            {llmEnabled() ? 'LLM ✓' : 'Add LLM key'}
          </button>
        </div>

        {keyOpen && (
          <section className="card">
            <div className="section-label" style={{ marginTop: 0 }}>
              Optional — Anthropic key (demo only, stored locally)
            </div>
            <div className="edit-field">
              <input
                type="password"
                placeholder="sk-ant-…"
                value={keyVal}
                onChange={(e) => setKeyVal(e.target.value)}
              />
              <button
                className="btn go"
                onClick={() => {
                  setKey(keyVal);
                  setKeyOpen(false);
                }}
              >
                Save
              </button>
            </div>
            <p className="note">
              Off by default. The deterministic engine stays the grounding
              authority — the model only rephrases, it never adds a number.
            </p>
          </section>
        )}

        <div className="chat">
          {chat.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              {m.text}
              {m.source && <span className="src">{m.source}</span>}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className="suggest">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => void send(s)}>
              {s}
            </button>
          ))}
        </div>
      </main>

      <form
        className="compose"
        onSubmit={(e) => {
          e.preventDefault();
          void send(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask about your money…"
          aria-label="Ask Sarthi a question"
        />
        <button className="send" aria-label="Send" type="submit">
          ↑
        </button>
      </form>
    </>
  );
}
