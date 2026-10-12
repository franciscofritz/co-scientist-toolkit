# Block: `slider`

Live parameter controls that recompute one or more outputs in real time.

**Group:** interactive · **Default packaging:** `interactive` · **Markdown fields:** `description`

## When To Use

When the section explains a value that depends on a few parameters and readers will benefit from feeling the relationship by sliding: animation easing, pricing tiers, latency budgets, retry policies, image compression tradeoffs. The slider block is for *exploratory understanding*, not for production calculators.

For a single value with no parameters, just write the number. For complex models with many inputs, use a real spreadsheet — the slider block is best with two to four parameters.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the controls. |
| `description` *(markdown)* | string | no | Short explanatory paragraph above the controls. Renders to `descriptionHtml`. |
| `parameters` | array of parameter objects | yes | At least one. |
| `parameters[].name` | string | yes | JavaScript-safe identifier used in `outputs[].compute`. |
| `parameters[].label` | string | yes | Display label. |
| `parameters[].min` | number | yes | Slider minimum. |
| `parameters[].max` | number | yes | Slider maximum. |
| `parameters[].step` | number | no | Default `(max-min)/100`. |
| `parameters[].default` | number | yes | Initial value. |
| `parameters[].unit` | string | no | Suffix shown next to the value. |
| `outputs` | array of output objects | yes | At least one. |
| `outputs[].label` | string | yes | Output label. |
| `outputs[].compute` | string | yes | JavaScript expression evaluated with parameter names in scope. Returns a number or string. |
| `outputs[].format` | string | no | Output format: `number`, `integer`, `percent`, `currency`, `text`. Default `number`. |
| `outputs[].unit` | string | no | Suffix appended after formatting. |
| `outputs[].decimals` | integer | no | Decimal places for numeric formats. Default 2. |

## Example

```yaml
- type: slider
  packaging: interactive
  data:
    title: "Base64 inflation"
    description: |
      Base64 encoding adds roughly 33% overhead. Slide the raw size to see the
      effect on the packaged HTML.
    parameters:
      - { name: rawMb,   label: "Raw asset size", min: 1, max: 50, step: 1, default: 10, unit: "MB" }
      - { name: extraMb, label: "Other content",  min: 0, max: 20, step: 1, default: 2,  unit: "MB" }
    outputs:
      - { label: "Encoded size",   compute: "rawMb * 1.33 + extraMb", format: number, decimals: 1, unit: "MB" }
      - { label: "Inflation cost", compute: "(rawMb * 0.33)",          format: number, decimals: 1, unit: "MB" }
```

## Rendering

A small panel with one row per parameter (label + range input + live readout) and an output row showing each output's label and computed value. Outputs update on every input event. Disabled when `packaging: static`, where the block renders parameter defaults and computed values as a static table instead.

## Compute Expression Safety

Expressions are evaluated with `new Function` inside the renderer. Authors are trusted with their own document, but treat the `compute` field the same way you treat the `custom` block's `js` field: don't evaluate untrusted input through it. The audit script flags slider blocks alongside `custom` blocks in its concentration report.
