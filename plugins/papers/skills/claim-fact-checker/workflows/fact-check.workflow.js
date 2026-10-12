export const meta = {
  name: 'claim-fact-check',
  description: 'Fan-out fact-check: extract the non-obvious factual claims from a deliverable, then run one isolated verifier per claim against the archived sources plus a source-quality skeptic, and synthesize a findings + fix-plan pair. Works on reviews of a paper and on any document checked against a folder of sources.',
  phases: [
    { title: 'Extract', detail: 'one extractor per target deliverable → claim list' },
    { title: 'Verify', detail: 'per claim: verifier reads the source, then a source skeptic — isolated context each' },
    { title: 'Synthesize', detail: 'merge verdicts into findings + fix-plan markdown' },
  ],
}

// ---------------------------------------------------------------------------
// args (passed by the caller after it has resolved paths on disk):
//   {
//     label:       string  — human label for this run (repo + entry)
//     domain:      'paper-review' | 'document'
//     targets:     string[] — ABSOLUTE paths to the deliverable file(s) that make claims
//     sources:     string[] — ABSOLUTE paths to the archived source files to verify against
//     primaryRule: 'strict' | 'moderate' | 'quote-verbatim'
//     guidance:    string   — domain-specific notes folded into every prompt
//     verdictsPath: string, ABSOLUTE path to references/verdicts.md (subagents cannot resolve relative paths)
//   }
// The workflow reads nothing from disk itself — subagents read the paths with their Read tool.
// It RETURNS { summary, counts, factcheckMd, fixplanMd } and the caller writes the two files
// (so the run never depends on a subagent's write permissions or path resolution).
// ---------------------------------------------------------------------------

const cfg = args || {}
const targets = cfg.targets || []
const sources = cfg.sources || []
if (!targets.length) { return { error: 'No targets passed in args.targets', summary: 'nothing to check' } }
const verdictsPath = cfg.verdictsPath
if (!verdictsPath) { return { error: 'No args.verdictsPath: pass the absolute path of references/verdicts.md', summary: 'nothing to check' } }

const sourceList = sources.length ? sources.map(s => `- ${s}`).join('\n') : '(no archived sources passed — every claim will be unsourced unless inferable)'
const ruleText = {
  strict: 'Primary sources ONLY. A vendor/lab/author/regulator own artefact is primary; trade press is reaction-coverage, never a factual source. Flag any claim resting on secondary or laundered press.',
  moderate: 'Prefer primary sources; secondary sources are acceptable if clearly the best available, but flag them for upgrade.',
  'quote-verbatim': 'Treat exactness as load-bearing: any quoted text in a claim must appear VERBATIM in an archived source. Paraphrase passed off as a quote is a defect.',
}[cfg.primaryRule || 'strict']

const DOMAIN_FRAMING = {
  'paper-review': 'The deliverable is a review of an academic paper. The archived sources are the paper itself (fulltext, figures, tables). A claim is verified when the review accurately reflects what the paper actually says/shows. Watch for: the review attributing a finding the paper does not make, overstating effect sizes, or mis-describing a figure/table.',
  'document': 'The deliverable is a document that makes factual claims. The archived sources are the files the user named. A claim is verified when a source actually asserts the same thing. Watch for: numbers, dates and attributions that differ from the source, quotes that are not verbatim, and characterisations that overstate the source.',
}[cfg.domain] || ''

const framing = `${DOMAIN_FRAMING}\n\nVerdict rubric: read ${verdictsPath} for the meaning of each verdict and source tier.\n\nSource-quality rule: ${ruleText}\n${cfg.guidance ? '\nExtra guidance: ' + cfg.guidance : ''}`

const CLAIMS_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['claims'],
  properties: {
    claims: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['text', 'location', 'sourceHint', 'kind'],
        properties: {
          text: { type: 'string', description: 'verbatim claim sentence from the deliverable' },
          location: { type: 'string', description: 'section heading or approx line' },
          sourceHint: { type: 'string', description: 'which archived source (by filename) should support this, or "none apparent"' },
          kind: { type: 'string', enum: ['fact', 'quote', 'attribution', 'number-or-date', 'characterisation'] },
        },
      },
    },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'supportingSource', 'supportingQuote', 'reasoning'],
  properties: {
    verdict: { type: 'string', enum: ['verified', 'verified-secondary', 'unsourced', 'contradicted', 'misattributed', 'quote-mismatch', 'prescription-detected'] },
    supportingSource: { type: 'string', description: 'archived source path that supports it, or "none"' },
    supportingQuote: { type: 'string', description: 'verbatim quote from the source that supports/contradicts the claim, or ""' },
    reasoning: { type: 'string', description: 'why claim and source match or diverge — reasoning, not keyword match' },
  },
}

const SKEPTIC_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['sourceTier', 'concern'],
  properties: {
    sourceTier: { type: 'string', enum: ['primary', 'secondary', 'reaction-coverage', 'none', 'not-applicable'] },
    concern: { type: 'string', description: 'one line: is the cited source actually the originating artefact, or laundered? "" if fine' },
  },
}

// ---- Phase 1: extract claims (fan out per target deliverable) -------------
phase('Extract')
const perTarget = await parallel(targets.map(t => () =>
  agent(
    `You are a claims extractor. Read the deliverable at:\n${t}\n\n${framing}\n\n` +
    `List every NON-OBVIOUS factual claim it makes — facts, quotes, attributions, numbers/dates, and characterisations of a source. ` +
    `Skip throat-clearing and obvious framing. For each, name the archived source (by filename) that should support it. Archived sources available:\n${sourceList}`,
    { label: `extract:${t.split('/').pop()}`, phase: 'Extract', schema: CLAIMS_SCHEMA }
  ).then(r => (r && r.claims ? r.claims.map(c => ({ ...c, target: t })) : []))
))
const claims = perTarget.filter(Boolean).flat()
log(`Extracted ${claims.length} claims across ${targets.length} deliverable(s)`)
if (!claims.length) { return { summary: 'No checkable claims found', counts: {}, factcheckMd: '', fixplanMd: '' } }

// ---- Phase 2: verify each claim in isolation, then skeptic-audit source ----
// Pipeline (no barrier): a claim can be at the skeptic stage while another is still verifying.
const verified = await pipeline(claims,
  (c) => agent(
    `You are a single-claim verifier. Verify EXACTLY ONE claim against the archived sources. Read only what you need.\n\n` +
    `Claim: "${c.text}"\nFrom: ${c.target} (${c.location})\nSuggested source: ${c.sourceHint}\n\n` +
    `Archived sources you may read:\n${sourceList}\n\n${framing}\n\n` +
    `Semantics over grep: build a model of what the claim asserts, read the source that would support it, and reason about whether the source actually asserts the same thing. Do not verify on keyword overlap alone. Quote the supporting (or contradicting) sentence verbatim.`,
    { label: `verify:${(c.kind)}`, phase: 'Verify', schema: VERDICT_SCHEMA }
  ).then(v => ({ ...c, ...v })),
  (v) => agent(
    `You are a source-quality skeptic. The claim "${v.text}" was judged "${v.verdict}" citing source "${v.supportingSource}". ` +
    `Read that source and decide its tier under this rule:\n${ruleText}\n\n` +
    `Default skeptical: if you cannot confirm it is the originating artefact, do not call it primary.`,
    { label: `skeptic`, phase: 'Verify', schema: SKEPTIC_SCHEMA }
  ).then(s => ({ ...v, ...s }))
)
const checked = verified.filter(Boolean)

// ---- counts ----
const counts = {}
checked.forEach(c => { counts[c.verdict] = (counts[c.verdict] || 0) + 1 })
const flagged = checked.filter(c =>
  ['unsourced', 'contradicted', 'misattributed', 'quote-mismatch', 'prescription-detected'].includes(c.verdict) ||
  c.sourceTier === 'reaction-coverage' || c.verdict === 'verified-secondary')

// ---- Phase 3: synthesize findings + fix-plan ------------------------------
phase('Synthesize')
const synth = await agent(
  `You are the findings synthesizer. Below is the JSON array of verified claims for "${cfg.label}". ` +
  `Produce TWO markdown documents.\n\n` +
  `1) FINDINGS: a summary verdict-count table, then findings grouped by target file, each with the verbatim claim, location, verdict, supporting source + quote, and one-line reasoning.\n` +
  `2) FIX-PLAN: action items ordered by priority — contradictions first, then misattributions/quote-mismatches, then prescriptions, then unsourced, then secondary-source upgrades. Each item: file, location, current text, issue, proposed action.\n\n` +
  `Return them separated by the exact delimiter line "===FIXPLAN===" (findings before it, fix-plan after).\n\n` +
  `Verified claims JSON:\n${JSON.stringify(checked, null, 1)}`,
  { label: 'synthesize', phase: 'Synthesize' }
)
const [factcheckMd, fixplanMd] = String(synth).split('===FIXPLAN===')

return {
  summary: `${checked.length} claims checked for ${cfg.label}: ${flagged.length} flagged. ${Object.entries(counts).map(([k, v]) => `${k}=${v}`).join(', ')}`,
  counts,
  flaggedCount: flagged.length,
  factcheckMd: (factcheckMd || '').trim(),
  fixplanMd: (fixplanMd || '').trim(),
}
