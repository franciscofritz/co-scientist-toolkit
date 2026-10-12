# Verdict rubric

Verdicts are products of **reading and reasoning, not keyword matching** — "semantics over grep". A verifier must build a model of what a claim asserts, read the source that would support it, and judge whether the source actually asserts the same thing.

## Per-claim verdicts (verifier stage)

| Verdict | Meaning |
|---|---|
| `verified` | Claim is supported by an archived primary source. Quote the supporting sentence. |
| `verified-secondary` | Supported only by a secondary source. Flag for primary-source upgrade. |
| `unsourced` | No archived source supports it and none is inferable. |
| `contradicted` | An archived source says something different. Quote both. |
| `misattributed` | Claim says "Source X says Y" but Y is not in X. Quote both locations. |
| `quote-mismatch` | A quoted string in the claim is not verbatim in any source (paraphrase passed as a quote). |
| `prescription-detected` | Use only when the run's guidance asks for a prescription sweep. The sentence tells an actor what to do rather than stating a fact. Propose a rewrite as a factual observation. Judge the meaning: a quoted source may legitimately contain "should/must". |

## Source-tier verdicts (skeptic stage)

| Tier | Meaning |
|---|---|
| `primary` | The originating entity's own artefact (vendor blog, model card, paper, repo, docs, regulator filing). |
| `secondary` | A reproduction or report of a primary that exists elsewhere. Upgrade if possible. |
| `reaction-coverage` | Trade press / commentary. Mood evidence only, never a factual source. |
| `none` | No source cited. |
| `not-applicable` | Claim is internal logic / synthesis, not an external fact. |

## Fix-plan priority order

1. Contradictions (highest)
2. Misattributions and quote-mismatches
3. Prescriptions (when the run asks for a sweep)
4. Unsourced claims
5. Secondary-source upgrades / reaction-coverage reliance (lowest)

When the fix-plan holds only low-priority items or none, the deliverable is clean enough to ship.
