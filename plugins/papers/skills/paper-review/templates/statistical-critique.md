# Statistical Critique Template

Use this template for a critical review of a paper's statistical methods, study design and interpretation.

Draws on themes from Andrew Gelman's published critiques (forking paths, power, multiple comparisons); not written or endorsed by him.

---

## YAML Header Template

```yaml
---
type: review
review_style: statistical-critique
paper_title: "{FULL_TITLE}"
reviewed_date: "{YYYY-MM-DDTHH:MM:SSZ}"
reviewer: "{REVIEWER}"
status: completed
duration_minutes: {MINUTES}
tags:
  - "experimental-design"
  - "statistical-methods"
  - "{add-relevant-tags}"
---
```

Replace all `{PLACEHOLDERS}` with actual values.

---

# Statistical Critique: {PAPER_TITLE}

**Paper**: {Authors}. ({Year}). {Title}. *{Journal}*, {Volume}({Issue}), {Pages}. DOI: {doi}

**Reviewed**: {Date}
**Reviewer**: {REVIEWER}

---

## Executive Summary

<!-- 2-3 paragraph overview of the paper and your main critique. -->
<!-- What did they do, what did they find, and what's your quick take? -->


---

## What They Did

<!-- Describe the study design, methods, and approach in plain language -->
<!-- Focus on:
- Research question
- Study design (RCT, observational, etc.)
- Sample and participants
- Intervention or exposure
- Outcomes measured
- Analysis approach
-->


---

## What They Found

<!-- Summarize key findings without editorializing -->
<!-- Use their numbers and claims, but present them clearly -->
<!-- Bullet points or paragraphs, depending on complexity -->


---

## What I Think

### The Good

<!-- What the paper does well -->
<!-- Examples:
- Strong experimental design choices
- Appropriate statistical methods
- Clear presentation
- Novel approach
- Adequate sample size
- Pre-registration
-->


### The Bad

<!-- Significant flaws and questionable decisions -->
<!-- Examples:
- Questionable design choices
- Missing control groups
- Inadequate power
- Statistical issues
- Over-interpretation
- Missing robustness checks
-->


### The Ugly

<!-- Serious methodological or interpretative problems, if any -->
<!-- Reserve this for major issues that undermine the work -->


---

## Statistical and Methodological Critique

### Design Issues

<!-- Critique of experimental design -->
<!-- Examples:
- Is the design appropriate for the research question?
- Are there confounds or alternative explanations?
- How were participants assigned to conditions?
- Were there selection biases?
-->


### Analysis Concerns

<!-- Statistical analysis issues -->
<!-- Examples:
- Are the statistical methods appropriate?
- Were assumptions tested?
- Are there multiple comparison issues?
- Is the power adequate?
- Are effect sizes reported?
- Are confidence intervals reasonable?
-->


### Missing Analyses

<!-- What should have been done but wasn't -->
<!-- Examples:
- Robustness checks
- Sensitivity analyses
- Subgroup analyses
- Alternative specifications
- Heterogeneity analyses
-->


### Interpretive Issues

<!-- Over-claiming, under-claiming, or misinterpretation -->
<!-- Examples:
- Do the claims match the evidence?
- Are causal claims justified by the design?
- Are limitations acknowledged?
- Is the generalizability claimed appropriate?
-->


---

## What I Would Have Done Differently

<!-- Concrete alternative approaches -->
<!-- Be specific about design, analysis, or presentation choices -->
<!-- Example format:
Instead of X, I would have done Y because Z.
-->


---

## What This Means

<!-- Implications for the field, practice, and future research -->
<!-- Examples:
- How does this change what we know?
- What are the practical implications?
- What questions remain unanswered?
- What should future research do?
-->


---

## Bottom Line

<!-- Final assessment in 2-3 sentences -->
<!-- Is this work credible? Important? Flawed? Salvageable? -->


---

## Questions for the Authors

<!-- Specific questions you'd ask in a review or discussion -->
<!-- Frame as genuine questions, not rhetorical attacks -->
<!-- Examples:
- Why did you choose X over Y?
- Have you considered alternative explanation Z?
- Can you provide more detail on...?
-->

1.
2.
3.

---

## Review Metadata

**Review Style**: Critical statistical review
**Focus**: Statistical methods, experimental design, interpretation
**Depth**: Comprehensive
**Audience**: Researchers and methodologists

---

## Notes on This Style of Review

**Characteristics**:
- Skeptical but constructive
- Focus on design and statistical choices
- Question assumptions explicitly
- Suggest concrete alternatives
- Direct about weaknesses
- Acknowledge genuine strengths
- "What I Would Have Done" thinking

**Common Themes**:
- Statistical significance vs practical significance
- Power and sample size issues
- Multiple comparisons
- Causal inference from observational data
- Over-interpretation
- Missing robustness checks
- Forking paths and researcher degrees of freedom

**Tone**:
- Direct and honest
- Critical but not cruel
- Constructive
- Pedagogical (explain why things matter)
