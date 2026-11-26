/**
 * عميل بديل متوافق مع واجهة OpenAI، بالشكل نفسه الذي يصدّره عميل Manus:
 * LlmClient (chat, models) وmessageText وmapLimit.
 * العنوان من LLM_BASE_URL (مثال: http://127.0.0.1:3001/v1) والمفتاح من LLM_API_KEY.
 * لا يطبع المفتاح أبدًا.
 */
const BASE = String(process.env.LLM_BASE_URL || '').replace(/\/+$/, '')
const KEY = process.env.LLM_API_KEY || ''

export class LlmClient {
  constructor({ timeoutMs = 300000, maxRetries = 3 } = {}) {
    this.timeoutMs = timeoutMs
    this.maxRetries = maxRetries
  }
  async #req(path, body) {
    let last
    for (let i = 0; i <= this.maxRetries; i++) {
      try {
        const r = await fetch(`${BASE}${path}`, {
          method: body ? 'POST' : 'GET',
          headers: { 'content-type': 'application/json', authorization: `Bearer ${KEY}` },
          body: body ? JSON.stringify(body) : undefined,
          signal: AbortSignal.timeout(this.timeoutMs),
        })
        const text = await r.text()
        if (r.ok) return JSON.parse(text)
        const e = new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`)
        e.fatal = r.status === 401 || r.status === 403 || r.status === 400
        if (e.fatal) throw e
        last = e
      } catch (e) {
        if (e.fatal) throw e
        last = e
      }
      await new Promise((res) => setTimeout(res, 1000 * 2 ** i))
    }
    throw last
  }
  chat(body) { return this.#req('/chat/completions', body) }
  models() { return this.#req('/models') }
}

export function messageText(resp) {
  const c = resp?.choices?.[0]?.message?.content
  if (Array.isArray(c)) return c.map((p) => p.text || '').join('')
  return c ?? null
}

export async function mapLimit(items, limit, fn) {
  const out = new Array(items.length)
  let next = 0
  const worker = async () => {
    while (next < items.length) {
      const i = next++
      out[i] = await fn(items[i], i)
    }
  }
  await Promise.all(Array.from({ length: Math.max(1, Math.min(limit, items.length)) }, worker))
  return out
}
