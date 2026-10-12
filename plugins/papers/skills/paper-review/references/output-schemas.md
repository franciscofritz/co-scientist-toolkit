# Output Schemas

JSON schemas for all agent outputs. Every agent MUST conform to these schemas. The synthesis agent depends on consistent structure to do its job.

---

## ReviewOutput (Theory, Experiments, Writing, Consistency agents)

```json
{
  "agent": "theory | experiments | writing | positioning | consistency",
  "paper_title": "string",
  "venue": "string",
  "rubric_source": "URL of the venue form or guidelines used, or 'fallback: references/review-rubrics.md', or 'generic'",
  "iteration": 1,
  "scores": {
    "<dimension name from the venue's form>": {
      "score": "value on that venue's scale for this dimension (a number or a label, as the form defines it)",
      "justification": "Brief justification for the score"
    }
  },
  "findings": [
    {
      "id": "T-001",
      "severity": "critical | major | minor | style",
      "confidence": "high | medium | low",
      "location": {
        "section": "string (e.g., '3.2')",
        "element": "string (e.g., 'Theorem 3', 'Figure 2', 'paragraph 4')",
        "detail": "string (e.g., 'line 4 of the induction step')"
      },
      "description": "Precise description of the issue",
      "evidence": "Why this is an issue (cite specific text, equations, etc.)",
      "suggested_fix": "How to fix it, or null if unclear",
      "affects_claims": ["list of main claims this finding impacts"]
    }
  ],
  "summary": "2-3 sentence overall assessment from this agent's perspective"
}
```

### ID conventions

Each agent uses a prefix for finding IDs:
- Theory: `T-001`, `T-002`, ...
- Experiments: `E-001`, `E-002`, ...
- Writing: `W-001`, `W-002`, ...
- Positioning: `P-001`, `P-002`, ...
- Consistency: `C-001`, `C-002`, ...

---

## PositioningReviewOutput (extends ReviewOutput)

The positioning agent adds a `references_found` field:

```json
{
  "...all ReviewOutput fields...": "",
  "references_found": [
    {
      "title": "Paper title",
      "authors": "Author names",
      "year": 2024,
      "url": "URL where the paper was found",
      "venue": "Where it was published (if known)",
      "relevance": "Brief description of how this relates to the reviewed paper",
      "should_cite": true,
      "citation_location": "Where in the paper this should be cited (e.g., 'Related work, §2.1')",
      "impact_on_claims": "Does this affect any novelty claims? How?"
    }
  ]
}
```

---

## DevilsAdvocateOutput

```json
{
  "agent": "devils_advocate",
  "paper_title": "string",
  "iteration": 1,
  "core_claim": "The paper's main thesis, stated precisely",
  "objection": {
    "summary": "One-sentence summary of the objection",
    "detailed_argument": "Full multi-paragraph argument developing the objection",
    "key_points": [
      "Numbered list of the argument's main points"
    ]
  },
  "evidence": {
    "from_paper": "Evidence from within the paper that supports the objection",
    "from_literature": "Evidence from other work (if applicable)",
    "from_first_principles": "Logical/mathematical arguments"
  },
  "rebuttal_needed": {
    "minimum": "The minimum the authors must do to address this",
    "ideal": "What would fully resolve the objection"
  },
  "damage_level": "fatal | severe | significant | minor",
  "confidence": "high | medium | low"
}
```

---

## SynthesisOutput

```json
{
  "agent": "synthesis",
  "paper_title": "string",
  "venue": "string",
  "rubric_source": "URL of the venue form or guidelines used, or 'fallback: references/review-rubrics.md', or 'generic'",
  "iteration": 1,
  "mock_review": {
    "summary_of_contributions": "string",
    "strengths": [
      {
        "id": "S-1",
        "description": "string"
      }
    ],
    "weaknesses": [
      {
        "id": "WK-1",
        "severity": "critical | major | minor",
        "description": "string",
        "source_findings": ["T-001", "E-003"]
      }
    ],
    "questions_for_authors": [
      "string"
    ],
    "scores": {
      "<dimension name from the venue's form>": "value on that venue's scale, a number or a label as the form defines it"
    },
    "recommendation": "string: one label taken verbatim from the chosen venue's recommendation scale",
    "markdown_text": "Full review as a markdown string"
  },
  "change_list": [
    {
      "id": "CH-001",
      "rank": 1,
      "severity": "critical | major | minor | style",
      "confidence": "high | medium | low",
      "description": "What needs to change",
      "rationale": "Why this matters",
      "location": {
        "section": "string",
        "element": "string"
      },
      "source_findings": ["T-001", "C-003"],
      "suggested_implementation": "Specific suggestion for how to make the change",
      "dependencies": ["CH-003"],
      "status": "pending"
    }
  ],
  "unresolved_conflicts": [
    {
      "id": "UC-001",
      "description": "What the conflict is",
      "side_a": {
        "agent": "writing",
        "finding_id": "W-005",
        "position": "Section 4 is too verbose"
      },
      "side_b": {
        "agent": "theory",
        "finding_id": "T-012",
        "position": "Section 4 needs more proof detail"
      },
      "synthesis_recommendation": "What the synthesis agent thinks, if anything"
    }
  ],
  "devils_advocate_section": {
    "objection_summary": "string",
    "damage_level": "string",
    "implications_for_revision": "How this should affect the revision strategy"
  },
  "overall_assessment": {
    "key_strengths": "string",
    "key_issues": "string",
    "revision_feasibility": "Can the major issues be fixed in a revision? How much work?",
    "honest_assessment": "Frank assessment of the paper's chances at the target venue"
  }
}
```

---

## ImplementationLog

```json
{
  "iteration": 1,
  "changes_implemented": [
    {
      "change_id": "CH-001",
      "status": "implemented | skipped | partial",
      "files_modified": ["main.tex"],
      "description": "What was done",
      "diff_summary": "Human-readable description of the change"
    }
  ],
  "compilation": {
    "status": "pass | fail | not_tested",
    "errors": [],
    "warnings": []
  }
}
```

---

## VerificationReport

```json
{
  "iteration": 1,
  "verification_results": [
    {
      "change_id": "CH-001",
      "status": "pass | fail | partial",
      "notes": "Details on what was checked and any issues"
    }
  ],
  "unapproved_changes": [
    {
      "location": "string",
      "description": "What changed that wasn't approved"
    }
  ],
  "new_issues": [
    {
      "severity": "critical | major | minor",
      "description": "A new issue introduced by the changes",
      "location": "string"
    }
  ],
  "compilation_status": {
    "status": "pass | fail | not_tested",
    "details": "string"
  },
  "overall": "pass | fail | needs_attention"
}
```

---

## Notes on schema usage

- All agents MUST return valid JSON. No markdown wrapping, no code fences in the output.
- The `iteration` field tracks which review cycle this output belongs to.
- Finding IDs are globally unique within an iteration (prefixed by agent).
- `scores` maps the chosen venue's dimension names to values on its scales. Include overall and confidence entries if the form has them. Do not use another venue's names or scales. If no form could be found, use the fallback or generic dimensions and say so in `rubric_source`.
- `recommendation` is a string containing one label from the chosen venue's recommendation scale. Copy the label exactly as it appears in the form.
- The synthesis agent's `change_list` items reference finding IDs via `source_findings`.
- The implementation and verification agents reference change IDs from the synthesis output.
