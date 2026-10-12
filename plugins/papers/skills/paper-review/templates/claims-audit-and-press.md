# Claims Audit & Press Representation Template

Use this template for a *probity-focused* review that holds the paper to its
own evidence. The job is to evaluate (a) whether every load-bearing claim in
the title, abstract, discussion, and conclusions is warranted by the actual
data the paper presents, and (b) how faithfully press releases, news
coverage, and other downstream summaries represent the paper.

This is the template to reach for when a paper's policy or popular footprint
matters more than its technical contribution — when citations are doing real
work in the world and you want to know whether they should be.

Hold the paper to the highest standard of scientific probity. Be specific:
quote the claim, point to the supporting data, and say where the gap is.

---

## YAML Header Template

```yaml
---
type: review
review_style: claims-audit-and-press
paper_title: "{FULL_TITLE}"
reviewed_date: "{YYYY-MM-DDTHH:MM:SSZ}"
reviewer: "{REVIEWER}"
status: completed
duration_minutes: {MINUTES}
press_sources_reviewed:
  - title: "{Press headline / article title}"
    outlet: "{outlet name}"
    url: "{URL}"
    date: "{YYYY-MM-DD}"
    type: "press-release | news | podcast | blog | social"
tags:
  - "claims-audit"
  - "press-representation"
  - "probity"
  - "{topic-tag}"
---
```

---

# Claims Audit & Press Representation: {PAPER_TITLE}

**Paper**: {Full Citation}
**Reviewed**: {Date}
**Press sources reviewed**: {N items — see frontmatter for list}

---

## 1. What the paper actually shows

<!-- 2-3 paragraphs. Reconstruct the actual evidence base from Methods and
Results, not from the Abstract or Discussion. Be precise about: sample size,
effect sizes, confidence intervals, the population studied, the conditions
under which effects appeared, and the specific manipulations performed.

This section is the yardstick everything else is measured against. -->

---

## 2. Title — claim audit

> "{exact title}"

<!-- For each substantive noun phrase or verb in the title, assess:
- Is it supported by the data? Where exactly?
- Is the scope of the title broader than the data warrants?
- Are quantifiers honest? (e.g. "can", "may", "X-fold", "first")
- Does the title obscure the population, setting, or condition?

Output: one bullet per claim, with a verdict (warranted / partially warranted /
overreach / misleading) and the specific evidence. -->

| Claim in title | Verdict | Evidence / gap |
|---|---|---|
| | | |
| | | |

---

## 3. Abstract — claim audit

<!-- Quote each major claim from the abstract verbatim, then audit it against
the actual data. Pay particular attention to:
- The first sentence (typically frames the contribution)
- Numeric claims ("X% improvement", "N participants", "P < 0.001")
- Conclusions sentences ("Our findings suggest…", "These results show…")
- Implication / call-to-action sentences

Be specific about which Result section, which Figure, which Table, which
Supplementary Section the claim does or does not rest on. -->

### Claim A: "{quote}"

- **Where the paper supports it**: {Figure / Table / Section}
- **Where it falls short**: {gap, if any}
- **Verdict**: {warranted | partially warranted | overreach | misleading}

### Claim B: "{quote}"

- ...

### Claim C: "{quote}"

- ...

---

## 4. Discussion — claim audit

<!-- The Discussion is where overreach most often lives. Look for:
- Causal claims from observational / correlational evidence
- Generalisation beyond the studied population, setting, or conditions
- "Real-world implications" sections that introduce new claims not supported
  by the actual experiments
- Speculative mechanisms presented as established
- Selective citation of supporting prior work; omission of competing evidence

For each major claim in the Discussion, evaluate whether it is licensed by the
study's design and results. -->

### Claim 1: {brief paraphrase}

- **Strength of support**: {strong / partial / speculative / unsupported}
- **What would be needed**: {what additional evidence would license this claim?}

### Claim 2: ...

---

## 5. Conclusions — claim audit

<!-- The Conclusions are the take-home message that citations will carry. Audit:
- Does it accurately summarise the actual findings, or does it dress them up?
- Does it import claims from the Discussion that are themselves speculative?
- Does it suggest policy, deployment, or normative recommendations that exceed
  the study's authority?
- Does it acknowledge the limitations that the rest of the paper flagged? -->

### Conclusion-level claims

- [ ] Each conclusion-level claim is traceable to a specific result in the paper.
- [ ] The conclusions correctly transmit the scope and conditions of the findings.
- [ ] The conclusions acknowledge — or at least do not contradict — the
      paper's own Limitations section.
- [ ] Policy / deployment / normative implications, where present, are licensed
      by the evidence rather than by the authors' opinion.

Per-claim audit:

### Claim 1: "{quote}"

- ...

---

## 6. Press release — representation audit

<!-- Press releases are typically written by the institution's communications
office, sometimes with author input, sometimes not. They are designed to
maximise pickup, not accuracy. Compare every load-bearing claim in the press
release against (a) what the paper actually shows, and (b) what the abstract
claims.

Track three failure modes:
1. **Inflation**: stronger claim in PR than in paper.
2. **Scope creep**: PR generalises the finding beyond the studied setting.
3. **Causal slippage**: correlational findings stated as causal.

If no press release exists for this paper, skip this section. -->

**Press release**: {URL} ({outlet}, {date})

### Headline / lede claim audit

| Claim in PR | Claim in paper | Verdict | Notes |
|---|---|---|---|
| | | | |
| | | | |

### Quotes from authors

<!-- Direct quotes from the authors in the press release sometimes go beyond
the paper's own claims. Audit any such quotes against the paper's evidence
base. -->

---

## 7. News coverage — representation audit

<!-- Survey the news coverage you can find. For each substantive article,
assess how it represents the paper. Common failure modes:
- Headlines that promise causation where the paper found correlation
- Loss of the "in a controlled / preliminary setting" qualifier
- Conflation with adjacent findings from other research
- Editorial framing that the paper does not support

If a podcast or video interview was a major distribution channel, treat it
similarly. -->

**Coverage reviewed** (also listed in YAML frontmatter):

1. **{Outlet} — {headline}** ({date}, {URL})
   - Representation accuracy: {high / mixed / low}
   - Specific issues: ...

2. **{Outlet} — {headline}** ({date}, {URL})
   - ...

### Cross-cutting patterns in the coverage

<!-- What do the press representations share? Where do they collectively
amplify a particular interpretation? Where do they collectively miss the same
caveats? -->

---

## 8. Social-media / influencer representation

<!-- Optional. Many papers reach the public primarily through Twitter / X
threads, LinkedIn posts, or YouTube explainers from named influencers. If the
paper has had significant social pickup, sample the most-shared threads and
note whether they represent it accurately.

This is not about adversarial readings — it is about whether the *typical*
reader of the social discourse comes away with an accurate understanding of
what the paper actually established. -->

---

## 9. What the paper does *not* claim — and how representations sometimes import claims anyway

<!-- A subtler representation failure: claims that are absent from the paper
get attributed to it by press coverage or downstream citation, often by
implication or by neighbouring framing.

List any such phantom claims you encountered. -->

- ...
- ...

---

## 10. Summary scorecard

| Surface | Probity verdict | Notes |
|---|---|---|
| Title | {warranted / partial / overreach / misleading} | |
| Abstract | {…} | |
| Discussion | {…} | |
| Conclusions | {…} | |
| Press release | {…} | |
| News coverage | {…} | |
| Social media | {…} | |

**Overall probity verdict**: {high / mostly accurate with caveats / mixed / problematic / misleading}

---

## 11. Citing this paper responsibly

<!-- Given the audit above, write a 2-3 sentence statement of what *can* be
cited from this paper and under what qualifications, and what should *not* be
cited from it. This is the most useful section for downstream readers. -->

**Cite this paper for**: ...

**Do not cite this paper for**: ...

**Always include the caveat that**: ...

---

## 12. What an honest version of the paper would look like

<!-- If the authors had been maximally probity-focused throughout, what would
they have published differently? This is a useful counterfactual because it
makes the audit constructive rather than merely critical. -->

- Title: ...
- Abstract: ...
- Discussion: ...
- Conclusions: ...
- Press release: ...

---

## Review Metadata

**Review Style**: Claims audit + press representation
**Focus**: Probity — what does the evidence actually license?
**Depth**: Methods + Discussion + Conclusions read end-to-end; press release and ≥3 news items reviewed
**Audience**: Readers who need to know whether — and how — to cite this paper
