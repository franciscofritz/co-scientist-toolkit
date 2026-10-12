# Methods Deep Dive Template

Use this template for detailed methodological analysis focused on reproducibility and rigor.

---

## YAML Header Template

```yaml
---
type: review
review_style: methods-deep-dive
paper_title: "{FULL_TITLE}"
reviewed_date: "{YYYY-MM-DDTHH:MM:SSZ}"
reviewer: "{REVIEWER}"
status: completed
duration_minutes: {MINUTES}
tags:
  - "methodology"
  - "reproducibility"
  - "{specific-method-tag}"
---
```

Replace all `{PLACEHOLDERS}` with actual values.

---

# Methods Deep Dive: {PAPER_TITLE}

**Paper**: {Full Citation}
**Reviewed**: {Date}

---

## Methods Summary

<!-- High-level overview of methodology (1-2 paragraphs) -->


---

## Study Design

### Type

<!-- RCT, observational, meta-analysis, qualitative, mixed methods, etc. -->
<!-- Justify whether the design is appropriate for the research question -->


### Population

<!-- Who was studied? -->
<!-- Include: target population, sampling frame, inclusion/exclusion criteria -->


### Intervention/Exposure

<!-- What was manipulated or measured? -->
<!-- For experiments: describe intervention in detail -->
<!-- For observational: describe exposure and how it was assessed -->


### Outcomes

<!-- What was measured? -->
<!-- Primary and secondary outcomes -->
<!-- Measurement instruments and validation -->


### Sample Size and Power

<!-- How many participants? -->
<!-- Was a power analysis conducted? -->
<!-- Is the sample size adequate for the analyses? -->


---

## Data Collection

### Instruments/Measures

<!-- How was data collected? -->
<!-- Describe: surveys, interviews, observations, sensors, etc. -->
<!-- Reliability and validity of measures -->


### Procedure

<!-- Step-by-step data collection process -->
<!-- Timeline -->
<!-- Setting (lab, field, online, etc.) -->


### Quality Control

<!-- How did they ensure data quality? -->
<!-- Examples: pilot testing, inter-rater reliability, validation checks -->


---

## Analysis Plan

### Pre-registration

<!-- Was the analysis pre-registered? -->
<!-- If yes, did they follow the plan? Any deviations? -->
<!-- If no, are there signs of p-hacking or forking paths? -->


### Statistical Methods

<!-- What analyses were performed? -->
<!-- List all major analyses -->
<!-- Are the methods appropriate for the data and research questions? -->


### Software/Tools

<!-- What software was used? -->
<!-- Specific packages/libraries -->
<!-- Versions reported? -->


### Assumptions

<!-- What statistical assumptions are required? -->
<!-- Were they tested? -->
<!-- What happens if they're violated? -->


---

## Reproducibility Assessment

### Data Availability

<!-- Can I access the data? -->
<!-- Public repository? Upon request? Not available? -->
<!-- File formats? Documentation? -->


### Code Availability

<!-- Can I access the analysis code? -->
<!-- GitHub? Supplement? Upon request? Not available? -->
<!-- Is it documented? Commented? -->


### Documentation Quality

<!-- How well is the method documented? -->
<!-- Could I replicate this study based on the paper alone? -->
<!-- What information is missing? -->


### Reproducibility Score

<!-- Overall reproducibility assessment -->
- **Data**: Available/Upon Request/Not Available
- **Code**: Available/Upon Request/Not Available
- **Documentation**: Excellent/Good/Adequate/Poor
- **Overall**: High/Medium/Low


---

## Methodological Strengths

<!-- What did they do well methodologically? -->
<!-- Examples:
- Strong design for causal inference
- Adequate sample size with power analysis
- Pre-registered analysis plan
- Multiple robustness checks
- Validated measurement instruments
- Clear documentation
-->

-
-


---

## Methodological Weaknesses

<!-- What could be improved? -->
<!-- Examples:
- Underpowered
- Missing control groups
- Convenience sampling
- No pre-registration
- Unclear procedures
- Missing robustness checks
-->

-
-


---

## Alternative Approaches

<!-- What else could have been done? -->
<!-- Suggest specific methodological alternatives -->
<!-- Explain trade-offs -->


---

## Replication Notes

<!-- If I wanted to replicate or extend this study... -->
<!-- What would I need? -->
<!-- What would I do differently? -->
<!-- What challenges would I face? -->


---

## Review Metadata

**Review Style**: Methods-focused deep dive
**Focus**: Reproducibility and methodological rigor
**Depth**: Comprehensive
**Audience**: Researchers interested in methods and replication
