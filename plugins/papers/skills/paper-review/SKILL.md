---
name: paper-review
description: "Multi-agent academic paper review system. Use this skill whenever the user asks to review, critique, improve, or get feedback on an academic paper, manuscript, preprint, or draft. Triggers include: 'review my paper', 'critique this manuscript', 'find weaknesses in my paper', 'help me improve this draft', 'simulate peer review', 'what would reviewers say', 'prepare for submission', any mention of reviewing a .tex or .pdf paper, or requests to check a paper's theory, experiments, writing quality, or positioning before submission. Also triggers when the user wants to iteratively refine a paper through multiple review rounds. Works with LaTeX source (.tex files) or PDF. Supports venue-specific review rubrics (NeurIPS, ICML, ICLR, COLT, AAAI, JMLR, Nature, Science, PNAS, etc.)."
---

# Paper Review Skill

A multi-agent iterative paper review system that simulates rigorous peer review, synthesises actionable feedback, and (with human approval) implements improvements.

## Overview

This skill spawns parallel specialist review agents, a synthesis agent, a devil's advocate, and a verification agent, orchestrated across up to 5 human-gated iterations. The goal is to surface real issues a reviewer would raise, not to produce generic praise.

## Quick reference: agent roster

| Agent | Role | Phase |
|-------|------|-------|
| Theory | Proof correctness, assumptions, logical gaps | 1 |
| Experiments | Methodology, baselines, statistics, reproducibility | 1 |
| Writing | Clarity, structure, flow, redundancy | 1 |
| Positioning | Related work, novelty claims, overclaims, literature gaps | 1 |
| Consistency | Abstract/intro/conclusion alignment, figures vs text | 1 |
| Devil's Advocate | Strongest possible objection to main claim | 1 |
| Synthesis | Reconciles reviews, ranks changes, flags disagreements | 2 |
| Implementation | Applies approved changes, produces diffs | 4 |
| Verification | Checks changes are correct and introduced no new issues | 5 |

## Workflow

Before starting, read the relevant reference files:
- `references/review-rubrics.md`: venue-specific rubrics and scoring criteria
- `references/agent-prompts.md`: detailed prompts for each specialist agent
- `references/output-schemas.md`: JSON schemas for all structured outputs

### Step 0: Setup

1. **Identify the paper.** The user provides a `.tex` file, a directory of `.tex` files or a `.pdf`. For LaTeX, find the main file by looking for `\documentclass`. For PDF, note that implementation (Phase 4) requires LaTeX source. If the input is a scan-only or born-digital PDF, or a non-arXiv journal PDF, first run `papers:academic-pdf-to-mkd` to produce a clean `…-fulltext.md` with figures/tables for the review agents.

2. **Identify the venue.** Ask which venue or type of venue the user is targeting. Look up its current reviewer guidelines or review form on the web, and use its review dimensions, scoring scales and recommendation labels. Do not supply these from memory, as scales and wording change from year to year. If no current form can be found, use the venue's entry in `references/review-rubrics.md` for its review priorities, choose a simple scale and tell the user the scales are generic. If no venue is specified, use the generic entry in that file. Pass the resulting dimensions, scales and recommendation labels to every agent as the venue rubric.

3. **Check for reference papers.** Ask whether the user has local PDFs of key cited papers in a directory. If so, note the path. If not, the positioning agent will search for key references itself. It may read full text only from open copies: arXiv or open access. For any other paper, including any subscription paper, use the title, abstract and short quotes, and never read the full text. A connected alphaXiv MCP server provides an optional route for arXiv papers through `discover_papers`, `get_paper_content`, `answer_pdf_queries` and `read_files_from_github_repository` (locate them with ToolSearch `alphaxiv`). It is not required.

4. **Set iteration counter** to 1.

5. **Tell the user the cost and wait for a go-ahead.** Before Phase 1, state how many rounds you plan and how many agents each round uses: six reviewers and one synthesis agent, plus an implementation agent and a verification agent in rounds that reach Phases 4 and 5. Wait for the user to say go ahead in chat. A full run uses a large share of a usage allowance.

### Phase 1: Parallel Specialist Reviews

Spawn all six review agents concurrently as subagents. Each agent receives:
- The full paper text
- The venue rubric
- Its specific review prompt (from `references/agent-prompts.md`)
- Any available reference papers (local or retrieved)

Each agent outputs a **structured JSON review** (schema in `references/output-schemas.md`). The review includes:
- Scores for each dimension in the venue's form, using that venue's scales
- A list of findings, each tagged with severity (critical / major / minor / style)
- Specific locations in the paper (section, paragraph, equation, figure number)
- Suggested remedies
- Confidence level per finding

**The Positioning Agent** uses web search. When an alphaXiv MCP server is connected, its tools are an optional route for arXiv papers (locate them with ToolSearch `alphaxiv`). It reads full text only from open copies (arXiv or open access), and for any other paper it uses the title, abstract and short quotes:
- Finds and retrieves open copies of cited papers. For arXiv papers it uses `get_paper_content` (a report optimised for LLMs) or `answer_pdf_queries` (targeted questions about one PDF, with pages to cite directly) if alphaXiv is connected, and otherwise web search
- Surfaces potentially missing references the authors should cite: `discover_papers` (ranked prior-art / related-work discovery from keywords + a semantic description); else web search
- Checks novelty claims against the retrieved text, for example through `answer_pdf_queries` where available, not from memory. If only an abstract is available, it says that the check rests on the abstract
- Checks whether the related work section fairly represents cited work
- Reports on any relevant concurrent/subsequent work found
- When a claim hinges on a cited paper's *implementation*, inspect its repo with `read_files_from_github_repository`

**The Devil's Advocate Agent** has a special mandate:
- Its sole job is to construct the strongest possible objection to the paper's main thesis
- It should assume the role of an adversarial but intellectually honest reviewer
- It must articulate what evidence or argument would be needed to defeat its objection

### Phase 2: Synthesis

A single synthesis agent receives all six reviews and produces:

1. **Conflict resolution**: Where reviewers disagree, the synthesis agent adjudicates or flags for human decision
2. **Ranked change list**: Every suggested change, deduplicated and ranked by:
   - Severity: critical > major > minor > style
   - Confidence: high > medium > low
   - Dependency: changes that unblock other changes come first
3. **Mock review summary**: A formal review in the style of the target venue, including:
   - Summary of contributions
   - Strengths (numbered)
   - Weaknesses (numbered, with severity tags)
   - Questions for the authors
   - Scores for each dimension in the venue's form, using that venue's scales (including overall score and confidence if the form has them)
   - Recommendation: one label from the venue's recommendation scale

Output format: structured JSON (see `references/output-schemas.md`) plus a rendered markdown summary for human reading.

### Phase 3: Human Gate (STOP HERE)

Present to the user:
1. The mock review summary (rendered as markdown)
2. The ranked change list
3. Any unresolved reviewer disagreements
4. The devil's advocate objection

The user then:
- Approves, rejects, or modifies each change item
- Resolves any flagged disagreements
- Responds to the devil's advocate objection (this may inform which changes to prioritise)
- Decides whether to proceed to implementation

**Do not proceed to Phase 4 without explicit user approval.**

### Phase 4: Implementation

If the user has provided LaTeX source:

1. Spawn an implementation agent that receives:
   - The original paper source
   - The approved change list only
   - The venue rubric (for style conventions)

2. The agent applies changes and produces:
   - Modified `.tex` file(s)
   - A human-readable diff summary (not just `git diff`, but a narrative of what changed and why)
   - A checklist mapping each approved change to where it was implemented

If the paper is PDF-only, skip automated implementation. Instead, produce a detailed change specification document the user can implement manually.

### Phase 5: Verification

A verification agent receives:
- The original paper
- The modified paper
- The approved change list
- The implementation checklist

It checks:
- Every approved change was actually implemented
- No approved change was incorrectly implemented
- No unapproved changes were introduced
- The changes didn't introduce new inconsistencies (e.g., a modified claim in §3 now contradicts §5)
- LaTeX compiles without errors (if source is available, run `pdflatex` or `latexmk`)

Output: a short verification report with pass/fail per change item and any new issues found.

### Iteration

After Phase 5, present the verification report and ask the user whether to:
- **Iterate**: Return to Phase 1 with the modified paper (increment iteration counter)
- **Stop**: The user is satisfied

Maximum 5 iterations. By iteration 3, if the review is still surfacing critical issues, flag this to the user; it may indicate a structural problem that line edits won't fix.

## Configuration

The user can customise:
- **Venue**: determines the review form (dimensions, scales and recommendation labels) and review style. Use the review priorities in `references/review-rubrics.md` as a fallback.
- **Focus areas**: Optionally disable agents that aren't relevant (e.g., skip experiments agent for a pure theory paper)
- **Severity threshold**: Optionally suppress style-level findings to reduce noise
- **Reference directory**: Path to local PDFs of cited papers
- **LaTeX build command**: Default `latexmk -pdf`, overridable

## Optional review lenses (single-pass templates)

For a focused review by one reviewer, use the structures in `templates/`: `quick-read` (10–20 min triage), `methods-deep-dive` (reproducibility and rigour), `statistical-critique` (forking paths, power and multiple comparisons), or `claims-audit-and-press` (an audit of every claim central to the argument against the evidence, plus its representation in press/news). See `templates/README.md`. The claims audit can be used with `papers:claim-fact-checker`. Adapted under MIT (see `LICENSE`) from Dominik Lukeš's paper-reviewer-skill.

## Hand-offs to other skills

- **Input (Step 0):** for a scan-only, born-digital or non-arXiv PDF, run `papers:academic-pdf-to-mkd` first to produce a clean `…-fulltext.md` with figures/tables for the agents.
- **Verify (post-synthesis):** check each claim central to the argument against the paper using the per-claim agents in `papers:claim-fact-checker`. Use `papers:reference-verifier` to confirm that the bibliography's references exist and DOIs resolve.

## Important principles

- **Be adversarial, not hostile.** The point is to find real issues before reviewers do. Generic praise wastes the user's time.
- **Cite specific locations.** "The proof of Theorem 3 has a gap in the induction step" is useful. "Some proofs could be tightened" is not.
- **Respect authorial voice.** The implementation agent preserves the author's writing style. It changes content, not voice.
- **Structured output is non-negotiable.** Every agent outputs JSON conforming to the schemas. This enables the synthesis agent to actually work rather than parsing free text.
- **The human gate is sacred.** Never auto-implement changes. The user is the domain expert.
