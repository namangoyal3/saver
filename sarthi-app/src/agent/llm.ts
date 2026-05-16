// Optional LLM seam. In production a large language model sits behind the
// supervisor to plan, route and phrase explanations. Here it is OPTIONAL and
// OFF by default: the deterministic engine is the grounding authority so the
// live demo never depends on a network call. If the user pastes an Anthropic
// key in Settings, goal narratives are rephrased by the model — but the
// numbers still come only from the typed tools (output guard).

const KEY = 'sarthi_anthropic_key';

export const getKey = (): string => localStorage.getItem(KEY) ?? '';
export const setKey = (k: string): void =>
  k ? localStorage.setItem(KEY, k) : localStorage.removeItem(KEY);
export const llmEnabled = (): boolean => getKey().length > 10;

// Rephrase a grounded fact into warmer plain language. The model is told it
// MUST NOT introduce numbers — every figure is passed in already computed.
export async function narrate(
  grounded: string,
  context: string,
): Promise<{ text: string; source: 'llm' | 'deterministic' }> {
  if (!llmEnabled()) return { text: grounded, source: 'deterministic' };
  try {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': getKey(),
        'anthropic-version': '2023-06-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 160,
        system:
          'You are Sarthi, a financial co-pilot for a Grab driver. Rephrase the given grounded fact in one warm, plain sentence. NEVER add, change or invent any number — use only the figures given. No jargon.',
        messages: [
          { role: 'user', content: `Context: ${context}\nFact: ${grounded}` },
        ],
      }),
    });
    if (!res.ok) throw new Error(String(res.status));
    const data = await res.json();
    const text: string = data?.content?.[0]?.text?.trim();
    if (!text) throw new Error('empty');
    return { text, source: 'llm' };
  } catch {
    // Graceful degradation — the deterministic phrasing is always correct.
    return { text: grounded, source: 'deterministic' };
  }
}
