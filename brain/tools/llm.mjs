#!/usr/bin/env node
/**
 * عميل النموذج المدمج في Manus (بلا مفاتيح خارجية).
 * الأوامر:
 *   models                                   — عرض الكتالوج الحي مع الأسعار
 *   single --prompt "..." | --prompt-file F  — نداء واحد (خيارات: --system --schema --out --max-tokens --model)
 *   batch  --input F --template "..."        — نداءات متتابعة (خيارات: --workers --schema --out --system --model)
 * يُشغَّل عبر: bash tools/llm.sh <الأمر> ...
 */
import { pathToFileURL } from 'node:url'
import { readFile, writeFile } from 'node:fs/promises'

const SKILL = '/home/ubuntu/skills/builtin-llm-models'
const { LlmClient, messageText, mapLimit } = await import(pathToFileURL(`${SKILL}/lib/llm.mjs`).href)

const argv = process.argv.slice(2)
const cmd = argv[0]
const has = (n) => argv.includes(`--${n}`)
const arg = (n, d = null) => {
  const i = argv.indexOf(`--${n}`)
  if (i === -1) return d
  const v = argv[i + 1]
  return v === undefined || v.startsWith('--') ? true : v
}

const MODEL = String(arg('model', 'gpt-5-mini'))
const isGemini = MODEL.startsWith('gemini')
const llm = new LlmClient({ timeoutMs: 300000, maxRetries: 3 })

/** يحترم قواعد كل عائلة: Gemini يستخدم max_tokens، وGPT يستخدم max_completion_tokens. */
/** يحترم قواعد كل عائلة: Gemini يستخدم max_tokens، وGPT يستخدم max_completion_tokens.
 *  وحدّ أدنى للرموز، لأن النماذج التي «تفكّر» تستهلك الرموز قبل الناتج فيصير فارغاً. */
function budget(body, n) {
  const want = Number(n) || 0
  if (isGemini) {
    body.max_tokens = Math.max(want, 1024)
    const eff = arg('reasoning-effort')
    if (typeof eff === 'string') body.reasoning_effort = eff
  } else {
    body.max_completion_tokens = Math.max(want, 2500)
    const eff = arg('reasoning-effort')
    body.reasoning = { effort: typeof eff === 'string' ? eff : 'minimal' }
  }
  return body
}

async function loadSchema() {
  const p = arg('schema')
  if (!p || typeof p !== 'string') return null
  const s = JSON.parse(await readFile(p, 'utf-8'))
  return { type: 'json_schema', json_schema: { name: String(arg('schema-name', 'out')), strict: true, schema: s } }
}

function fatalReport(e) {
  const fatal = e && e.fatal ? ' (خطأ قاطع — لا تُعاد المحاولة)' : ''
  console.error(`✘ فشل النداء${fatal}: ${e && e.message ? e.message : e}`)
}

if (cmd === 'models') {
  const list = await llm.models()
  const rows = (list.data || list).map((m) => ({
    id: m.id,
    in: m.pricing?.input_per_1m_usd,
    out: m.pricing?.output_per_1m_usd,
    thinking: m.capabilities?.thinking_param || '—',
  }))
  console.log(JSON.stringify(rows, null, 1))
} else if (cmd === 'single') {
  const sys = arg('system')
  let prompt = arg('prompt')
  const pf = arg('prompt-file')
  if (typeof pf === 'string') prompt = await readFile(pf, 'utf-8')
  if (!prompt || prompt === true) {
    console.error('✘ يلزم --prompt أو --prompt-file')
    process.exit(2)
  }
  const messages = []
  if (sys && typeof sys === 'string') messages.push({ role: 'system', content: sys })
  messages.push({ role: 'user', content: prompt })
  const body = budget({ model: MODEL, messages }, arg('max-tokens'))
  const schema = await loadSchema()
  if (schema) body.response_format = schema
  try {
    const resp = await llm.chat(body)
    const text = messageText(resp)
    if (text === null || text === undefined) {
      console.error('✘ ناتج فارغ (استُهلكت الرموز قبل الناتج) — ارفع --max-tokens')
      process.exit(1)
    }
    const out = arg('out')
    if (typeof out === 'string') {
      await writeFile(out, text, 'utf-8')
      console.error(`✔ كُتب الناتج في ${out} · رموز: ${resp.usage?.prompt_tokens || '?'}/${resp.usage?.completion_tokens || '?'}`)
    } else {
      console.log(text)
    }
  } catch (e) {
    fatalReport(e)
    process.exit(1)
  }
} else if (cmd === 'batch') {
  const input = arg('input')
  const template = String(arg('template', '{input}'))
  const sys = arg('system')
  if (typeof input !== 'string') {
    console.error('✘ يلزم --input')
    process.exit(2)
  }
  const raw = await readFile(input, 'utf-8')
  const items = raw.trim().startsWith('[')
    ? JSON.parse(raw)
    : raw.split('\n').map((l) => l.trim()).filter(Boolean)
  const schema = await loadSchema()
  const workers = Number(arg('workers', 6))
  let fatal = null
  const results = await mapLimit(items, workers, async (item) => {
    if (fatal) return { input: item, output: null, error: 'تُخطّي بعد خطأ قاطع' }
    const messages = []
    if (sys && typeof sys === 'string') messages.push({ role: 'system', content: sys })
    messages.push({ role: 'user', content: template.replace('{input}', typeof item === 'string' ? item : JSON.stringify(item)) })
    const body = budget({ model: MODEL, messages }, arg('max-tokens'))
    if (schema) body.response_format = schema
    try {
      const resp = await llm.chat(body)
      const text = messageText(resp)
      if (text === null || text === undefined) {
        return { input: item, output: null, usage: resp.usage, error: 'ناتج فارغ — ارفع --max-tokens' }
      }
      return { input: item, output: text, usage: resp.usage, error: null }
    } catch (e) {
      if (e && e.fatal) fatal = e
      return { input: item, output: null, error: e && e.message ? e.message : String(e) }
    }
  })
  const lines = results.map((r, i) => JSON.stringify({ index: i, ...r }))
  const out = arg('out')
  if (typeof out === 'string') await writeFile(out, lines.join('\n') + '\n', 'utf-8')
  else console.log(lines.join('\n'))
  const ok = results.filter((r) => !r.error).length
  console.error(`✔ اكتمل: ${ok}/${results.length} ناجح · النموذج: ${MODEL}`)
  if (fatal) {
    fatalReport(fatal)
    process.exit(1)
  }
} else {
  console.error('الاستخدام: models | single --prompt … | batch --input … --template …')
  process.exit(2)
}
