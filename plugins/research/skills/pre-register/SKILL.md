---
name: pre-register
description: "Idea triage and pre-registration gate for research. Use this skill BEFORE investing time or compute in a research idea, experiment, or project direction, to decide honestly whether it is worth doing and to commit to predictions before piloting. Triggers include: 'is this idea worth doing', 'should I pursue this', 'pre-register this', 'before I run this experiment', 'what would make this interesting', 'frame this research question', 'help me decide if this is interesting', 'pre-mortem this', 'I have a new research idea', 'is this worth the compute', 'commit my predictions', or any moment of deciding whether a hypothesis/experiment deserves real effort. Especially for computational experiments (RL, ML, numerical) where a cheap pilot is possible. Encodes the rule: ask 'is this interesting?' not just 'is this publishable?', and pre-register before piloting."
---

# Pre-Registration & Idea Triage Skill

A gate you pass an idea through *before* spending time or compute on it. It forces
three honest commitments (what would make the result interesting, what the cheapest
decisive test is, and what you predict will happen) and then issues a triage verdict.

## Why this exists

The design is based on one finding from the AI-co-scientist literature and one working assumption:

1. **"Novel-sounding" ≠ good.** In the Ideation-Execution Gap study (Si et al. 2025,
   arXiv 2506.20803), LLM-generated ideas scored higher than human experts' ideas at the
   idea stage on novelty, excitement, effectiveness and overall, and **lost that advantage
   once executed**: their scores fell by 1–2 points on a 1–10 scale, significantly more
   than the human ideas' scores. After execution the human ideas scored higher on all four;
   the difference was not significant with each of the 43 projects as the unit, and was
   significant on every metric but novelty with each review as the unit. For the
   machine-generated ideas, excitement before execution correlated negatively with
   excitement after it (Pearson r = -0.32, with no significance reported); the other
   correlations were weak or near zero. How exciting an idea sounds before it is run is no
   guide to how it executes.
2. **Working assumption: idea-stage review skips the things that kill ideas**: missing
   baselines, missing ablations, resource infeasibility and the likely null result. We assume
   these mostly become apparent only during execution, so the skill asks for them beforehand.

So this skill refuses to let you (or the assistant) fall in love with an un-executed idea.
It does not score novelty. It forces the execution-proxies and a pre-registered prediction,
and it redefines "interesting" as something that *survives* execution.

## The core principle

> **An idea is interesting if its most-likely outcome, including the null result,
> would be worth knowing.** If the idea is only worth anything when it *works*, it is
> fragile; if even the boring outcome teaches you something, it is robust.

This is the operational form of "is this interesting?" not "is this publishable?". A good
research bet pays off across outcomes, not just on success.

## When to use / not use

- **Use** at the birth of an idea, before any meaningful compute or multi-day effort; when
  choosing between competing directions; when an idea *feels* exciting (that is exactly when
  to be suspicious); before launching an HPC sweep.
- **Don't use** for routine engineering, for ideas already mid-execution (use `convergence-check`
  instead), or as a substitute for actually running the cheap pilot it prescribes.

## Workflow

The assistant drafts each step and presents it; the human owns the judgments. Do not skip
the human gate at Step 4.

### Step 0: Capture the seed honestly
Record, in the user's own words:
- **The seed observation / motivation**: what actually sparked this? (Quote it; you will
  check later that the plan hasn't drifted from it.)
- **The idea** in one or two sentences.
- **The claimed payoff**: what the user hopes is true.

Watch for the *motivation-drift* failure mode: if subsequent steps optimise for theoretical
cleanliness or defensibility and away from the seed observation, name it.

### Step 1: The "interesting" test (interesting / boring / dead)
For the idea, write three concrete outcomes *and what each would teach*:
- **Interesting outcome**: the hoped-for result. State it as a falsifiable claim with a
  rough magnitude, not "X helps".
- **Boring / null outcome**: the most likely mundane result (no effect, known effect
  reproduced). **Then answer the load-bearing question: would this null result still be
  worth knowing?** If yes → robust idea. If no → fragile idea; flag it.
- **Dead outcome**: the result that would kill the direction entirely.

If you cannot state a null result whose knowing is worthwhile, the idea is fragile and the
verdict should reflect that.

### Step 2: The execution-proxy gate
No idea is "rankable" until all four are concrete (these are exactly what idea-stage review
skips):
1. **Cheapest decisive experiment**: the smallest run that would meaningfully update your
   belief. Prefer minutes on a laptop or a single small job over a big sweep.
2. **The baselines / ablations a hostile reviewer would demand**: name them now. If the
   idea has no fair baseline, that is a finding.
3. **The most likely null result** (carried from Step 1), and how you'd detect it.
4. **Cost**: rough compute/time on the available hardware (e.g. a laptop locally vs a
   cluster job). If the cheapest decisive test is expensive, that itself is a triage signal.

**Prior-art grounding (do it here, and keep it about feasibility, not novelty-scoring).** If the alphaXiv MCP tools are
connected, locate them via ToolSearch `alphaxiv` and use `discover_papers`. Spend one query
checking whether the cheapest decisive experiment, or a close variant, has already been run.
If it has, the decisive result may already exist. Read it with `get_paper_content` /
`answer_pdf_queries`, or from an open copy on arXiv or the publisher's open-access page,
instead of spending compute. For a subscription paper, use only its title, abstract and short
quotes. Use the closest prior work to refine the hostile-reviewer baselines in item 2.
Both purposes concern feasibility and base the gate on what is actually known. Do not score
the idea's novelty (see Important principles). If alphaXiv is unconnected, use a quick web
search.

### Step 3: Pre-registration commitment
Before any pilot:
- **Predicted result**: commit, in writing, to what you expect (direction + rough
  magnitude). A well-scaled prediction sounds neither trivial ("above chance") nor grandiose
  ("recovers a major theoretical optimum"). If you can't write one that avoids both, the
  question is mis-scaled; say so.
- **Decision rule**: "if the pilot shows X, I proceed; if Y, I stop." Fixed *now*, not
  after seeing data.
- **Garden-of-forking-paths guard**: list every threshold / magnitude / hyperparameter /
  experimental cell you'll choose, and for each ask: *was this selected because it produces
  the cleanest result (i.e. on the dependent variable)?* If yes, either re-select on
  theoretical grounds or pre-commit the choice transparently. Hidden selection is the trap.
- **Abstract-first check**: draft the one-sentence finding now. If it reads "we find X,
  where X = [the cleanest result from a sweep]", there is a pre-registration problem.
- **Confirmatory versus exploratory**: name the comparisons that are confirmatory. Those,
  with their decision rule, are frozen now. Anything chosen after looking at the relevant
  results is exploratory and is reported as exploratory, never as a preregistered test.

### Step 4: Triage verdict (HUMAN GATE)
Present the assembled pre-registration and recommend one verdict, with reasons:
- **PURSUE**: robust (null is worth knowing), cheapest test is affordable, prediction is
  well-scaled. Proceed to the cheap pilot.
- **DESCOPE**: promising but over-scoped; narrow to the single cheapest decisive test first.
- **SHELVE**: interesting but not now; record it as a lead with its pre-registration intact.
- **KILL**: fragile (only valuable if it works), or no fair baseline, or mis-scaled. Say so
  plainly; do not soften a kill into a reframe.

The human accepts, overrides, or revises. The assistant must be willing to recommend KILL;
honest dissent is the point, not compliant encouragement.

### Step 5: Save the artifact
On a PURSUE/DESCOPE/SHELVE verdict, save the pre-registration (template below) to:
- **Default:** `./pre-registrations/YYYY-MM-DD-<slug>.md` in the current project directory,
  so it lives with the work.
- **Optionally** (ask the user), save a copy or a link wherever the user keeps project notes.

The saved prediction + decision rule is what later makes "did reality match the bet?"
answerable, converting iteration from "find a flattering framing" into "test the bet".

## Output format: the pre-registration template

```markdown
# Pre-registration: <idea title>
Date: YYYY-MM-DD · Project: <name> · Verdict: PURSUE | DESCOPE | SHELVE | KILL

## Seed observation (what sparked this)
<quoted, in the user's words>

## The idea
<1–2 sentences>

## Outcomes
- Interesting: <falsifiable claim + rough magnitude>
- Boring/null: <most likely result>; worth knowing? YES/NO because <...>
- Dead: <what would kill the direction>

## Execution proxies
1. Cheapest decisive experiment: <...>
2. Hostile-reviewer baselines/ablations: <...>
3. Most likely null result + how detected: <...>
4. Cost (local / cluster): <...>

## Pre-registered prediction
- Predicted result (direction + magnitude): <...>
- Decision rule: if <X> proceed; if <Y> stop.
- Confirmatory comparisons (frozen): <...>
- Forking-paths guard: <choices + whether any are DV-selected>
- One-sentence finding (drafted before running): <...>

## Verdict & reasoning
<PURSUE/DESCOPE/SHELVE/KILL + why>

## Deviations (append-only, dated)
<YYYY-MM-DD: what changed from the frozen plan, why, and whether it was decided before or after seeing the relevant results. Failed attempts go here too.>
```

## Important principles

- **Do not score novelty or excitement.** In that study, scores before execution predicted scores after it weakly or not at all, and negatively for the excitement of machine-generated ideas.
  Score robustness (does the null teach you something?) and feasibility (is the cheap test
  affordable?).
- **Be willing to KILL.** "Yes, here's how to make it work" is the wrong move when the
  honest read is "this only matters if it works". Recommend the kill.
- **One reframe, then run.** If the idea is being reframed rather than tested, stop reframing
  and execute the cheapest decisive experiment. (If you're already past this point and
  looping, switch to the `convergence-check` skill.)
- **Pre-register before piloting, never after.** A prediction written after seeing data is
  not a prediction.
- **Deviations are recorded, never edited in.** When the work departs from the frozen
  prediction, comparison or decision rule, append a dated entry under `## Deviations` and
  leave the original commitments untouched. Report failed attempts alongside the one that
  worked.
- **The human owns "interesting".** The assistant assembles the evidence and recommends; the
  researcher decides what is worth their life. Never overrule that, but never flatter it either.
