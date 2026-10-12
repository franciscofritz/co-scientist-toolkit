# Block: `timeline`

A vertical chronology of events with timestamps, titles, body text, optional tags, and optional follow-up checklists.

**Group:** diagram · **Default packaging:** `static` · **Markdown fields:** `events[].body`

## When To Use

When the section's value is *the order things happened*: incident timelines, project history, decision logs, release notes, audit trails, study schedules, workshop run-of-show. Use the timeline block over a regular bullet list whenever the dates carry meaning the reader should be able to scan.

For temporal slide content (e.g. a deck), don't use this block — use the deck's slide layout instead. The timeline block is for in-document narrative.

## Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | no | Section title above the list. |
| `events` | array of event objects | yes | Rendered top-to-bottom in order. |
| `events[].date` | string | yes | Display string. The compiler does not parse it. |
| `events[].title` | string | yes | Short headline for the event. |
| `events[].body` *(markdown)* | string | no | Renders to `bodyHtml`. |
| `events[].tag` | string | no | Short pill displayed alongside the date. |
| `events[].status` | enum: `info`, `success`, `warning`, `danger` | no | Tints the marker. Default `info`. |
| `events[].followUps` | array of string | no | Renders as a checklist beneath the body. |

## Example

```yaml
- type: timeline
  data:
    title: "Incident timeline · auth-svc 2026-04-12"
    events:
      - date: "08:42"
        title: "First failed login spike detected"
        body: "Grafana fired auth-svc-error-rate-warn. On-call paged."
        status: warning
        tag: "P2"
      - date: "08:55"
        title: "Root cause identified"
        body: "Token validator was pinned to a removed JWKS endpoint after the rotation at 08:30."
        status: danger
        followUps:
          - "Re-check JWKS rotation runbook"
          - "Add canary on validator config drift"
      - date: "09:14"
        title: "Mitigated"
        body: "Rolled forward to validator v2.18 with the new JWKS URL."
        status: success
```

## Rendering

Vertical line on the left, event nodes as filled circles tinted by `status`, date in a small caps label, title as bold text, body flowing beneath. Tags render as a small inline pill. Follow-ups render as `<ul>` with checkbox-style markers. The block has no JavaScript by default — it stays static and prints cleanly.
