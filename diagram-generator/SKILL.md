---
name: diagram-generator
description: "Renders plain-text ASCII diagrams (flowcharts, sequence diagrams, trees and hierarchies) from JSON using a bundled Python script that computes layout, spacing and arrow routing. Use when the user asks to draw, sketch or diagram a process, architecture, service interaction, directory tree or org chart as text for a README, code comment, ticket or terminal."
---

# ASCII Diagrams

## Activation Contract

Use this skill when the user asks to represent a flow, interaction, architecture, tree, or hierarchy as plain text, ASCII, or monospaced content for terminals, documentation, or comments.

## Hard Rules

- Always generate the diagram with `render_diagram.py`; never write or correct the final diagram characters manually.
- Preserve the renderer output exactly inside a code block.
- Check that no text is truncated and every connection points to the correct destination.
- If the result is not readable, change the JSON and render it again.
- Do not create a persistent file unless the user requests one; use stdin or a temporary file.

## Decision Gates

| Need | Type |
| --- | --- |
| Process, algorithm, pipeline, decision, or directed architecture | `flowchart` |
| Ordered messages between actors or services | `sequence` |
| Folders, organization chart, taxonomy, or hierarchy | `tree` |
| Ambiguous architecture with boxes and arrows | `flowchart` |

## Execution Steps

1. Read `references/schema.md` and choose the diagram type.
2. Build valid JSON with concise labels and every required connection.
3. Resolve `render_diagram.py` from the directory containing this `SKILL.md`, not from the user's current working directory.
4. Run the script with the available Python launcher (`python`, with `python3` as a fallback), preferably sending JSON through stdin with `-`.
5. Inspect the output; if crossings are confusing or labels are too long, adjust the JSON and run it again.
6. If the user requested a file, use `-o PATH` and report the created path.

## Output Contract

Return the rendered ASCII unchanged inside a code block. Add a brief note only when a relevant limitation exists or a file was created.

## References

- [Schemas and limitations](references/schema.md) — JSON formats for `flowchart`, `sequence`, and `tree`.
