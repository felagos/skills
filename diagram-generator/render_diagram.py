#!/usr/bin/env python3
"""
render_diagram.py — Render ASCII diagrams (flowchart, sequence, tree) from a
JSON description, calculating widths, padding, columns, and spacing
mathematically rather than by hand.

Usage:
    python render_diagram.py input.json
    python render_diagram.py input.json -o output.txt
    echo '{...}' | python render_diagram.py -

See references/schema.md (or SKILL.md) for the input format of each diagram
type: "flowchart", "sequence", and "tree".
"""

import sys
import json
import argparse
import textwrap

# ---------------------------------------------------------------------------
# Sparse canvas utilities
# ---------------------------------------------------------------------------

class Canvas:
    """Sparse character canvas.

    Draws at arbitrary (row, column) coordinates without precomputing the
    total size and merges crossing lines with the correct box-drawing
    characters (┼, ├, ┤, etc.) instead of overwriting them blindly.
    """

    # Merge table for intersecting line strokes.
    MERGE = {
        frozenset(['│', '─']): '┼',
        frozenset(['│', '┌']): '├',
        frozenset(['│', '┐']): '┤',
        frozenset(['│', '└']): '├',
        frozenset(['│', '┘']): '┤',
        frozenset(['─', '┌']): '┬',
        frozenset(['─', '┐']): '┬',
        frozenset(['─', '└']): '┴',
        frozenset(['─', '┘']): '┴',
    }

    def __init__(self):
        self.cells = {}

    def set(self, r, c, ch, merge=False):
        if ch == ' ':
            return
        if merge and (r, c) in self.cells:
            existing = self.cells[(r, c)]
            if existing != ch:
                key = frozenset([existing, ch])
                ch = self.MERGE.get(key, ch)
        self.cells[(r, c)] = ch

    def text(self, r, c, s):
        for i, ch in enumerate(s):
            self.set(r, c + i, ch)

    def h_line(self, r, c1, c2, ch='─', merge=True):
        for c in range(min(c1, c2), max(c1, c2) + 1):
            self.set(r, c, ch, merge=merge)

    def v_line(self, r1, r2, c, ch='│', merge=True):
        for r in range(min(r1, r2), max(r1, r2) + 1):
            self.set(r, c, ch, merge=merge)

    def render(self):
        if not self.cells:
            return ""
        max_r = max(r for r, c in self.cells)
        max_c = max(c for r, c in self.cells)
        lines = []
        for r in range(max_r + 1):
            row_chars = [self.cells.get((r, c), ' ') for c in range(max_c + 1)]
            lines.append(''.join(row_chars).rstrip())
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Box calculation (word wrapping and computed padding, never hand-tuned)
# ---------------------------------------------------------------------------

def wrap_label(label, max_width=22):
    """Wrap text by words when it exceeds max_width.

    Returns the wrapped lines and content width.
    """
    label = str(label)
    if not label:
        return [""], 0
    wrapped = textwrap.wrap(label, width=max_width) or [""]
    content_width = max(len(line) for line in wrapped)
    return wrapped, content_width


def box_dimensions(label, shape='box', max_width=22, padding=1):
    """Calculate wrapped lines and the exact box size for the given padding."""
    lines, content_width = wrap_label(label, max_width=max_width)
    inner_width = content_width + 2 * padding
    total_width = inner_width + 2  # left and right borders
    total_height = len(lines) + 2  # top and bottom borders
    return {
        'lines': lines,
        'content_width': content_width,
        'inner_width': inner_width,
        'width': total_width,
        'height': total_height,
    }


def draw_box(canvas, top, left, dims, shape='box'):
    """Draw a box and return geometry metadata for arrow routing."""
    lines = dims['lines']
    inner_width = dims['inner_width']
    width = dims['width']
    height = dims['height']

    if shape == 'diamond':
        # Size the diamond from the actual width of its single-line label.
        text = lines[0] if lines else ""
        inner = f" {text} "
        w = len(inner)
        r = top
        canvas.text(r, left + 1, "_" * w)
        canvas.text(r + 1, left, "/" + inner + "\\")
        canvas.text(r + 2, left, "\\" + ("_" * w) + "/")
        return {
            'top': top, 'bottom': top + 2, 'left': left, 'right': left + w + 2,
            'center_col': left + (w + 2) // 2,
            'height': 3,
        }

    # Standard rectangular box.
    canvas.text(top, left, "┌" + ("─" * inner_width) + "┐")
    for i, line in enumerate(lines):
        padded = line.center(inner_width)
        canvas.text(top + 1 + i, left, "│" + padded + "│")
    canvas.text(top + height - 1, left, "└" + ("─" * inner_width) + "┘")
    return {
        'top': top, 'bottom': top + height - 1, 'left': left, 'right': left + width - 1,
        'center_col': left + width // 2,
        'height': height,
    }


# ---------------------------------------------------------------------------
# FLOWCHART: topological layering and orthogonal edge routing
# ---------------------------------------------------------------------------

def compute_layers(nodes, edges):
    """Assign each node to a layer using the longest path from a root.

    This is a simplified Sugiyama-style topological layering. Cycles fall
    back to breadth-first traversal from the first node for deterministic
    output.
    """
    node_ids = [n['id'] for n in nodes]
    preds = {nid: [] for nid in node_ids}
    succs = {nid: [] for nid in node_ids}
    for e in edges:
        succs[e['from']].append(e['to'])
        preds[e['to']].append(e['from'])

    indegree = {nid: len(preds[nid]) for nid in node_ids}
    layer = {}
    queue = [nid for nid in node_ids if indegree[nid] == 0] or [node_ids[0]]
    for nid in queue:
        layer[nid] = 0

    processed = set(queue)
    # Kahn's algorithm with layer recalculation: max(predecessors) + 1.
    from collections import deque
    dq = deque(queue)
    visits = {nid: 0 for nid in node_ids}
    while dq:
        u = dq.popleft()
        for v in succs[u]:
            layer[v] = max(layer.get(v, 0), layer[u] + 1)
            visits[v] += 1
            if visits[v] >= len(preds[v]):
                if v not in processed:
                    processed.add(v)
                    dq.append(v)

    # Place unreachable nodes (cycles or isolated nodes) below the current
    # maximum layer so the diagram remains readable.
    max_layer = max(layer.values()) if layer else 0
    for nid in node_ids:
        if nid not in layer:
            max_layer += 1
            layer[nid] = max_layer

    layers = {}
    for nid in node_ids:
        layers.setdefault(layer[nid], []).append(nid)
    # Preserve original appearance order within each layer.
    order_index = {nid: i for i, nid in enumerate(node_ids)}
    for l in layers:
        layers[l].sort(key=lambda nid: order_index[nid])
    return layers


def render_flowchart(data):
    nodes = data['nodes']
    edges = data.get('edges', [])
    node_by_id = {n['id']: n for n in nodes}
    layers = compute_layers(nodes, edges)

    canvas = Canvas()
    H_SPACING = 4   # minimum horizontal spacing between boxes in a layer
    V_SPACING = 4   # connector band height between layers: one blank row
                     # plus up to two crossing lanes

    # Track predecessors so simple one-parent-to-one-child chains can share a
    # vertical axis instead of always being left-aligned.
    preds_map = {n['id']: [] for n in nodes}
    for e in edges:
        preds_map[e['to']].append(e['from'])

    geom = {}  # id -> geometry of the rendered box
    row_cursor = 0

    for layer_idx in sorted(layers.keys()):
        ids_in_layer = layers[layer_idx]
        dims_list = []
        for nid in ids_in_layer:
            node = node_by_id[nid]
            dims = box_dimensions(node.get('label', nid), shape=node.get('shape', 'box'))
            dims_list.append(dims)

        # Center a single node with one parent under that parent to avoid
        # unnecessary zigzags. Otherwise, arrange nodes in a row using the
        # minimum H_SPACING value.
        col_cursor = 10
        row_geoms = []
        single_aligned = (
            len(ids_in_layer) == 1
            and len(preds_map[ids_in_layer[0]]) == 1
            and preds_map[ids_in_layer[0]][0] in geom
        )
        if single_aligned:
            parent_center = geom[preds_map[ids_in_layer[0]][0]]['center_col']
            width = dims_list[0]['width']
            col_cursor = max(2, parent_center - width // 2)

        for nid, dims in zip(ids_in_layer, dims_list):
            node = node_by_id[nid]
            g = draw_box(canvas, row_cursor, col_cursor, dims, shape=node.get('shape', 'box'))
            geom[nid] = g
            width_used = (g['right'] - g['left'] + 1)
            col_cursor += width_used + H_SPACING
            row_geoms.append(g)

        layer_height = max(g['height'] for g in row_geoms)
        row_cursor += layer_height

        # Leave room for the connector band before the next layer.
        if layer_idx != max(layers.keys()):
            row_cursor += V_SPACING

    # --- Edge routing ---------------------------------------------------
    # Group edges by source layer and assign non-overlapping horizontal lanes
    # by detecting collisions between column ranges.
    layer_of = {}
    for l, ids_ in layers.items():
        for nid in ids_:
            layer_of[nid] = l

    adjacent_edges = [e for e in edges if layer_of[e['to']] - layer_of[e['from']] == 1]
    skip_edges = [e for e in edges if layer_of[e['to']] - layer_of[e['from']] != 1]

    # Edges that skip layers cannot cross intermediate boxes, so route them
    # through a vertical side channel beyond every rendered box.
    if skip_edges:
        max_right = max(g['right'] for g in geom.values())
        side_col = max_right + 3
        for i, e in enumerate(skip_edges):
            channel = side_col + i * 2
            sg, tg = geom[e['from']], geom[e['to']]
            mid_row_out = sg['top'] + sg['height'] // 2
            mid_row_in = tg['top'] + tg['height'] // 2
            canvas.h_line(mid_row_out, sg['right'] + 1, channel)
            canvas.v_line(mid_row_out, mid_row_in, channel)
            canvas.h_line(mid_row_in, channel, tg['right'] + 1)
            canvas.set(mid_row_in, tg['right'] + 1, '◀')
            if e.get('label'):
                canvas.text(mid_row_out - 1, channel - len(e['label']) // 2, e['label'])

    edges_by_source_layer = {}
    for e in adjacent_edges:
        l = layer_of[e['from']]
        edges_by_source_layer.setdefault(l, []).append(e)

    for layer_idx, edge_list in edges_by_source_layer.items():
        ids_in_layer = layers[layer_idx]
        top_of_band = geom[ids_in_layer[0]]['bottom'] + 2
        # Assign each edge to the first lane whose [min, max] column range
        # does not overlap an edge already placed there.
        lane_ranges = []  # list of (c1, c2) ranges for each lane
        assigned_lane = []
        for e in edge_list:
            sc = geom[e['from']]['center_col']
            tc = geom[e['to']]['center_col']
            c1, c2 = min(sc, tc), max(sc, tc)
            placed = False
            for li, ranges in enumerate(lane_ranges):
                if all(c2 < r1 - 1 or c1 > r2 + 1 for (r1, r2) in ranges):
                    ranges.append((c1, c2))
                    assigned_lane.append(li)
                    placed = True
                    break
            if not placed:
                lane_ranges.append([(c1, c2)])
                assigned_lane.append(len(lane_ranges) - 1)

        band_height = len(lane_ranges)

        for e, lane in zip(edge_list, assigned_lane):
            sc = geom[e['from']]['center_col']
            tc = geom[e['to']]['center_col']
            sbottom = geom[e['from']]['bottom']
            ttop = geom[e['to']]['top']
            bend_row = top_of_band + lane
            below_band = top_of_band + band_height

            canvas.v_line(sbottom + 1, bend_row - 1, sc)
            if sc == tc:
                canvas.v_line(bend_row, ttop - 1, tc)
            else:
                canvas.h_line(bend_row, sc, tc)
                # Use direction-aware corners rather than a generic plus sign.
                canvas.set(bend_row, sc, '└' if tc > sc else '┘')
                canvas.set(bend_row, tc, '┐' if tc > sc else '┌')
                canvas.v_line(below_band, ttop - 1, tc)
                if below_band > bend_row + 1:
                    canvas.v_line(bend_row + 1, below_band, tc)
            canvas.set(ttop - 1, tc, '▼')

            label = e.get('label')
            if label:
                if sc != tc:
                    # Center the label inside the horizontal segment so it
                    # cannot collide with a box.
                    c1, c2 = sorted((sc, tc))
                    lc = (c1 + c2) // 2
                    canvas.text(bend_row, lc - len(label) // 2, f" {label} ")
                else:
                    canvas.text(bend_row, sc + 2, label)

    return canvas.render()


# ---------------------------------------------------------------------------
# SEQUENCE: iteratively size participant columns until every message fits,
# including messages that skip participants.
# ---------------------------------------------------------------------------

def render_sequence(data):
    participants = data['participants']
    messages = data.get('messages', [])
    idx_of = {p: i for i, p in enumerate(participants)}

    gap = 3
    MAX_GAP = 80
    while True:
        widths = [max(len(p), 4) for p in participants]
        centers = []
        cursor = 2
        for w in widths:
            centers.append(cursor + w // 2)
            cursor += w + gap
        ok = True
        for m in messages:
            i, j = idx_of[m['from']], idx_of[m['to']]
            if i == j:
                continue
            span = abs(centers[j] - centers[i])
            needed = len(m.get('label', '')) + 4
            if span < needed:
                ok = False
                break
        if ok or gap >= MAX_GAP:
            break
        gap += 2

    canvas = Canvas()
    row = 0
    # Center participant names above their lifelines.
    for p, w, c in zip(participants, widths, centers):
        canvas.text(row, c - len(p) // 2, p)
    row += 1
    lifeline_top = row
    row += 1

    def draw_lifelines_row(r):
        for c in centers:
            canvas.set(r, c, '│')

    draw_lifelines_row(row - 1)

    for m in messages:
        i, j = idx_of[m['from']], idx_of[m['to']]
        style = m.get('style', 'solid')
        label = m.get('label', '')
        ci, cj = centers[i], centers[j]

        if i == j:
            # Render a self-message as an inline note instead of a full loop.
            canvas.text(row, ci + 2, f"(self: {label})" if label else "(self)")
            draw_lifelines_row(row)
            row += 1
            continue

        dash = '- ' if style == 'dashed' else '-'
        line_char = '-'
        c1, c2 = min(ci, cj), max(ci, cj)
        line = [' '] * (c2 - c1 + 1)
        for k in range(len(line)):
            line[k] = line_char if style == 'solid' else ('-' if k % 2 == 0 else ' ')
        # Center the label within the segment.
        if label:
            start = max(0, (len(line) - len(label)) // 2)
            for k, ch in enumerate(label):
                if start + k < len(line):
                    line[start + k] = ch
        text = ''.join(line)
        canvas.text(row, c1, text)
        # Point the arrowhead toward the destination.
        canvas.set(row, cj, '>' if cj > ci else '<')
        canvas.set(row, ci, '|')
        canvas.set(row, cj, '>' if cj > ci else '<')
        row += 1
        draw_lifelines_row(row)
        row += 1

    return canvas.render()


# ---------------------------------------------------------------------------
# TREE: fully calculated classic indentation matching the `tree` command.
# ---------------------------------------------------------------------------

def render_tree(data):
    root = data['root']

    def walk(node, prefix, is_last, is_root):
        lines = []
        label = node.get('label', '')
        if is_root:
            lines.append(label)
            child_prefix = ""
        else:
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + label)
            child_prefix = prefix + ("    " if is_last else "│   ")
        children = node.get('children', [])
        for i, child in enumerate(children):
            lines.extend(walk(child, child_prefix, i == len(children) - 1, False))
        return lines

    return '\n'.join(walk(root, "", True, True))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

RENDERERS = {
    'flowchart': render_flowchart,
    'sequence': render_sequence,
    'tree': render_tree,
}


def main():
    # Windows may default redirected output to a legacy code page that cannot
    # represent box-drawing characters. Codex captures stdout/stderr, so make
    # the renderer's text contract explicit and consistent across platforms.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

    parser = argparse.ArgumentParser(description="Render ASCII diagrams from JSON.")
    parser.add_argument('input', help="Input JSON file, or '-' for stdin.")
    parser.add_argument('-o', '--output', help="Output file (default: stdout).")
    args = parser.parse_args()

    if args.input == '-':
        raw = sys.stdin.read()
    else:
        with open(args.input, 'r', encoding='utf-8') as f:
            raw = f.read()

    data = json.loads(raw)
    dtype = data.get('type')
    if dtype not in RENDERERS:
        print(f"Unknown diagram type: {dtype!r}. Use one of {list(RENDERERS)}.", file=sys.stderr)
        sys.exit(1)

    output = RENDERERS[dtype](data)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output + '\n')
        print(f"Diagram written to {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()
