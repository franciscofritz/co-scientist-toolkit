# claim-fact-checker

A fact-checking workflow for Claude Code. It extracts a list of claims from a deliverable and checks them against archived sources, using one verifier subagent per claim in an isolated context and, for each claim, a second agent that assesses the quality of its source. It produces a findings file and a fix-plan file without editing the deliverable. Each verifier starts with a clean context, so the quality of a check does not depend on the document's length. Coverage depends on extraction: a claim the extractor misses is not checked.

## Targets (presets)

| Preset | Deliverable | Verified against |
|---|---|---|
| `paper-review` | a review of one paper, named by the user | the `papers:academic-pdf-to-mkd` output for that paper (`{paper_id}-fulltext.md`, `figures/`, `tables/`), plus the `source/` folder from `papers:arxiv-fetcher` if it fetched the paper |
| `document` | any document the user names | a folder of sources the user names |

## Layout

- `SKILL.md`: when to use the skill, how to run it, and cost.
- `workflows/fact-check.workflow.js`: the code that runs the workflow: extraction, then a verifier and a source-quality check for each claim, then synthesis.
- `presets/*.json`: source and strictness settings for each target type.
- `references/verdicts.md`: the criteria for each verdict.

## Use

Ask Claude to fact-check a review or document and name the sources folder. Claude resolves the target and source paths, tells you how many claims and agents the run involves, and waits for your go-ahead. It then calls

`Workflow({ scriptPath: "${CLAUDE_SKILL_DIR}/workflows/fact-check.workflow.js", args })`

with `args` containing `label`, `domain`, `targets`, `sources`, `primaryRule`, `guidance` and `verdictsPath`. `verdictsPath` is the absolute path of `references/verdicts.md`, where the workflow's subagents read the verdict criteria. The workflow returns the findings and fix-plan Markdown, which Claude writes beside the deliverable.
