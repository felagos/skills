# Input schemas for ASCII diagrams

Use these formats with `render_diagram.py`. The script calculates widths, padding, spacing, lifelines, and routing; do not edit the rendered ASCII manually.

## Flowchart

```json
{
  "type": "flowchart",
  "nodes": [
    {"id": "A", "label": "Start"},
    {"id": "B", "label": "Is it valid?", "shape": "diamond"},
    {"id": "C", "label": "Process"}
  ],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C", "label": "yes"}
  ]
}
```

- `id` identifies nodes within `edges`; it must be short and unique.
- `label` is the visible text and supports automatic line wrapping.
- `shape` accepts `box` (default) or `diamond`.
- Keep diamond labels on one line, ideally under 20 characters.
- `edges[].label` is optional.
- Node order affects the order within each layer. Connections that skip layers are routed through a side channel.

## Sequence

```json
{
  "type": "sequence",
  "participants": ["Client", "API", "Database"],
  "messages": [
    {"from": "Client", "to": "API", "label": "POST /login", "style": "solid"},
    {"from": "API", "to": "Database", "label": "SELECT user", "style": "solid"},
    {"from": "Database", "to": "API", "label": "row found", "style": "dashed"},
    {"from": "API", "to": "Client", "label": "200 OK", "style": "dashed"}
  ]
}
```

- `participants` defines the horizontal order.
- `messages` is processed in temporal order, from top to bottom.
- Use `solid` for calls and `dashed` for responses.
- Width is recalculated to fit the longest label, including messages between non-adjacent participants.
- A call where `from == to` is displayed as an inline note rather than a classic loop.

## Tree

```json
{
  "type": "tree",
  "root": {
    "label": "src/",
    "children": [
      {
        "label": "components/",
        "children": [
          {"label": "Button.tsx"},
          {"label": "Header.tsx"}
        ]
      },
      {"label": "index.ts"}
    ]
  }
}
```

Each node requires `label`; `children` is optional. The renderer calculates indentation and connectors recursively.

## Limitations

- Flowcharts with many crossing branches may be correct but not compact. Split them into subdiagrams if readability suffers.
- Diamonds work best with short, single-line labels.
- Sequence self-calls are rendered as inline notes.
