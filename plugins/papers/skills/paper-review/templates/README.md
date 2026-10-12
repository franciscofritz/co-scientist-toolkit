# Single-pass review lenses

Optional structured templates for a focused, one-shot review. Use one for a single review in a
specific register. They complement the full multi-agent workflow in `../SKILL.md`.

Adapted (MIT) from Dominik Lukeš's `paper-reviewer-skill`
(https://github.com/techczech/dominiks-agent-skills).

| Template | Use for |
|---|---|
| `quick-read.md` | 10–20 min triage: TL;DR, key findings, "should I read deeper?" |
| `methods-deep-dive.md` | Reproducibility + rigour: design, power, data/code availability |
| `statistical-critique.md` | Critique of statistical methods and interpretation: forking paths, power, multiple comparisons, "what I'd have done differently" |
| `claims-audit-and-press.md` | Probity audit: every load-bearing claim checked verbatim against the evidence, plus press/news representation |

Use the claims audit with `papers:claim-fact-checker`: first identify the claims on which the
argument depends, then assign one verifier to each claim.

## YAML header

Each template starts with a YAML header. Set `{REVIEWER}` to the model that wrote the review and
fill the other `{PLACEHOLDERS}`. Use the template's body structure. The header is optional and
can be changed freely.

## Deliberately not included

`critical-review.md` from the source skill uses a claims/evidence/validity/rating/verdict
structure that overlaps with the mock-review output already produced here by the multi-agent
synthesis agent.
