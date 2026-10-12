# Block: `live-template`

A template with named variables and editable inputs that re-render the output as the reader types.

**Group:** interactive · **Default packaging:** `interactive` · **Markdown fields:** `description`

## When To Use

When the section explains a template — a prompt, a config snippet, a meeting agenda, an email format — and readers will benefit from seeing it filled with their own values. Excellent for prompt-engineering pages, onboarding docs that include letter or message templates, and decision documents that include "fill in the blank" slot lists.

For complex calculation, use `slider`. For purely displayed examples, use `tabbed-code`. The `live-template` block sits between them: text-shaped output, free-form inputs.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the controls. |
| `description` *(markdown)* | string | no | Short paragraph above the inputs. Renders to `descriptionHtml`. |
| `template` | string | yes | The template body. Variable slots are written as `{name}` (or `{{name}}`); the renderer accepts both. |
| `variables` | array of variable objects | yes | At least one. |
| `variables[].name` | string | yes | Must match a slot in `template`. |
| `variables[].label` | string | yes | Display label for the input. |
| `variables[].default` | string | yes | Initial value. |
| `variables[].kind` | enum: `text`, `multiline`, `select` | no | Default `text`. |
| `variables[].options` | array of string | conditional | Required when `kind` is `select`. |
| `variables[].placeholder` | string | no | Input placeholder. |
| `outputFormat` | enum: `text`, `markdown`, `code` | no | Default `text`. `code` renders the output in a monospace block; `markdown` renders the output as Markdown. |

## Example

```yaml
- type: live-template
  packaging: interactive
  data:
    title: "Stand-up message template"
    description: "Edit any field and the message updates live."
    template: |
      Hi {team}, quick stand-up:
      • Yesterday: {yesterday}
      • Today: {today}
      • Blockers: {blockers}
    variables:
      - { name: team,      label: "Team",       default: "growth", kind: text }
      - { name: yesterday, label: "Yesterday",  default: "shipped the dashboard skeleton", kind: multiline }
      - { name: today,     label: "Today",      default: "wire up search filters",          kind: multiline }
      - { name: blockers,  label: "Blockers",   default: "none", kind: text }
    outputFormat: text
```

## Rendering

A two-column layout on wide viewports (inputs on the left, rendered output on the right) and stacked on narrow ones. Each input is a real form control with `<label>` association. The output panel updates on every input event. A "Copy" button copies the current rendered output to the clipboard.

When `packaging: static`, the block renders the template filled with the default variable values, with no inputs.
