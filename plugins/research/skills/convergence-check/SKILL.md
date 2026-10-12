---
name: convergence-check
description: "Diagnose whether an iterative research or writing loop is genuinely converging or spinning in place. Use this skill when you have iterated several times (on a paper, an experiment, an abstract, a proof, a model) and want an honest read on whether to keep going, stop, or change the question. Triggers include: 'am I going in circles', 'are we converging', 'this is the third time I've reframed this', 'critique keeps finding new problems', 'whack-a-mole', 'should I stop iterating', 'is the data the bottleneck', 'we keep rewriting the abstract', 'each review round finds different issues', or any sense of being stuck in a revise-and-resubmit loop with yourself. Pairs with the paper-review skill, if installed (analyses its outputs across rounds) and the pre-register skill (which prevents the loop in the first place)."
---

# Convergence Check Skill

A diagnostic for iterative loops. It answers one question honestly: **are you converging
(refining the same issue toward done) or escalating (discovering new kinds of problems each
round, which means the question or setup is wrong)?**

## Why this exists

Healthy critique-and-revise loops *converge*: round 2 finds finer-grained versions of round
1's issues; round 3 polishes those. The dangerous pattern looks like progress but isn't:

- **Critique escalation**: each round finds problems *orthogonal* to the last. That is not
  refinement; it is whack-a-mole on a fundamentally wrong setup.
- **Reframing on unchanged data**: the abstract gets rewritten around the same experiments
  again and again. Two framings on the same data is normal; **three means the data isn't
  carrying a strong enough claim for any framing**, and the question, not the wording, is
  the bottleneck. (Strong results constrain the framing; weak results admit many.)
- **Motivation drift**: each revision moves toward defensibility/cleanliness and away from
  the seed observation that started the project.

The instinct under sunk cost is to find a new framing for existing experiments rather than
rethink the setup. This skill exists to make that pattern *visible* before it consumes weeks.

## When to use

After ~2+ rounds of any of: paper-review iterations, abstract redrafts, proof-repair
attempts, experiment-reframings, plan revisions. Use it *instead of* launching another
revision when you suspect you're looping.

## Inputs

Any of:
- A directory or set of files holding successive critique rounds (e.g. `paper-review`
  outputs, reviewer notes, draft abstracts over time).
- A git/draft history of the abstract or claim.
- The user simply recounting the rounds verbally; the assistant reconstructs the map.

## Workflow

### Step 1: Build the round-over-round issue map
Lay out, per round: the main issues raised and the framing/claim in force. Produce a table:

| Round | Framing / main claim | Issues raised | Data changed since last round? |
|---|---|---|---|

### Step 2: Apply the three diagnostics
1. **Escalation vs convergence.** For each round, classify its issues against the previous
   round: are they *finer-grained versions of the same issues* (converging) or *new kinds of
   issues* (escalating)? A loop where round N's problems are orthogonal to round N−1's is
   escalating.
2. **Reframing count on unchanged data.** Count how many distinct framings have been applied
   to the *same* underlying results. **≥3 with no new data → the data is the bottleneck.**
3. **Motivation drift.** Compare the current framing to the original seed observation. Write
   the sentence: *"This version still captures the original motivation by ___."* If you can't
   complete it honestly, the plan has drifted.

### Step 3: Deliver the verdict with evidence
State one verdict, and **quote the specific rounds as evidence** (not vibes):

- **CONVERGING**: issues are narrowing; keep going, you're close. Name the 1–2 remaining items.
- **ESCALATING**: new kinds of problems each round. **Stop revising.** The underlying
  question/setup is likely wrong; revisit it, don't polish it.
- **REFRAMING-ON-WEAK-DATA**: ≥3 framings, unchanged data. The data isn't speaking strongly
  enough. The move is to *run a different experiment or strengthen the result*, not to reword.
- **DRIFTED**: the work has wandered from its seed motivation. Re-anchor or consciously
  accept the new direction.

### Step 4: If stopping, offer paths (don't just say "stop")
When the verdict is ESCALATING / REFRAMING / DRIFTED, present 2–3 concrete options and let
the user choose:
- **(a) Descope**: a smaller, narrower claim the current data *does* support strongly.
- **(b) Pivot**: a different question on the same setup/data.
- **(c) Step back**: stop optimising for paper-shaped output; write up what's durably useful
  (a method, a negative result, a clean tool) and possibly return later.

Name what the work has *already* produced that is durably useful regardless of the verdict:
a stopped paper is not wasted work, and saying so plainly is part of the honest read.

Once the user decides, execute that path cleanly. Do not keep trying to rescue the previous
direction.

## Important principles

- **Be specific, not vibes-based.** Useful: "rounds 1–3 each raised orthogonal issues:
  baselines, then framing, then a proof gap; that's escalation." Not useful: "I'm uncertain
  this is working."
- **Name the failure mode, show the evidence, propose the alternative.** All three, every time.
- **"Here's revision v4" is the worst move when the right move is "stop".** If the honest read
  is that the loop is not converging, say so instead of proposing another iteration.
- **A stop is a legitimate research outcome.** Converging on "this question is wrong" early is
  a win, not a failure; it returns weeks of life.
