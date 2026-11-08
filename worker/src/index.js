// Gilded Ace "Ask the Floor" proxy: keeps the Gemini key server-side.
// Only relays generateContent for allowed models, from allowed origins, with size caps and a per-visitor rate limit.
const ALLOWED_ORIGINS = ['https://deeps45.github.io', 'http://localhost:8765'];
const ALLOWED_MODELS = ['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-3.1-flash-lite'];
const MAX_BODY = 200_000;      // bytes: system prompt + facts + short chat history
const MAX_OUTPUT_TOKENS = 1000;

const cors = origin => ({
  'Access-Control-Allow-Origin': origin,
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Max-Age': '86400',
  'Vary': 'Origin',
});
const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json', ...(origin ? cors(origin) : {}) } });

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const ok = ALLOWED_ORIGINS.includes(origin);
    if (req.method === 'OPTIONS') return ok ? new Response(null, { status: 204, headers: cors(origin) }) : new Response(null, { status: 403 });
    if (req.method === 'GET') return json({ service: 'gilded-ace-ask', ok: true }, 200, ok ? origin : null);
    if (req.method !== 'POST') return json({ error: { message: 'method not allowed' } }, 405, ok ? origin : null);
    if (!ok) return json({ error: { message: 'origin not allowed' } }, 403, null);

    const ip = req.headers.get('CF-Connecting-IP') || 'unknown';
    if (env.LIMITER) {
      const { success } = await env.LIMITER.limit({ key: ip });
      if (!success) return json({ error: { message: 'Too many questions in a minute. Please wait a moment.' } }, 429, origin);
    }
    const raw = await req.text();
    if (raw.length > MAX_BODY) return json({ error: { message: 'request too large' } }, 413, origin);
    let body; try { body = JSON.parse(raw); } catch { return json({ error: { message: 'invalid JSON' } }, 400, origin); }

    const model = body.model;
    if (!ALLOWED_MODELS.includes(model)) return json({ error: { message: 'model not allowed' } }, 400, origin);
    const payload = body.request || {};
    // Only pass through the fields the dashboard uses, and cap output length.
    const clean = {
      systemInstruction: payload.systemInstruction,
      contents: payload.contents,
      tools: payload.tools,
      generationConfig: { temperature: 0.2, ...(payload.generationConfig || {}), maxOutputTokens: Math.min(MAX_OUTPUT_TOKENS, (payload.generationConfig || {}).maxOutputTokens || MAX_OUTPUT_TOKENS) },
    };
    let r;
    try {
      r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
        body: JSON.stringify(clean),
        signal: AbortSignal.timeout(25_000),  // fail fast so the page can retry with a fallback model
      });
    } catch (e) {
      return json({ error: { message: 'upstream timeout' } }, 504, origin);
    }
    const text = await r.text();
    return new Response(text, { status: r.status, headers: { 'Content-Type': 'application/json', ...cors(origin) } });
  },
};
