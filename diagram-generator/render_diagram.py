#!/usr/bin/env python3
"""
render_diagram.py — Renderiza diagramas ASCII (flowchart, sequence, tree)
a partir de una descripcion JSON, calculando anchos, paddings, columnas y
espaciados matematicamente (nunca "a mano").

Uso:
    python3 render_diagram.py input.json
    python3 render_diagram.py input.json -o output.txt
    echo '{...}' | python3 render_diagram.py -

Ver references/schema.md (o el SKILL.md) para el formato de entrada de
cada tipo de diagrama: "flowchart", "sequence", "tree".
"""

import sys
import json
import argparse
import textwrap

# ---------------------------------------------------------------------------
# Utilidades de canvas disperso (sparse canvas)
# ---------------------------------------------------------------------------

class Canvas:
    """Canvas disperso de caracteres. Permite dibujar en coordenadas
    (fila, columna) arbitrarias sin pre-calcular el tamano total, y
    fusiona lineas que se cruzan usando los caracteres de box-drawing
    correctos (┼, ├, ┤, etc.) en vez de sobrescribir a ciegas."""

    # Tabla de fusion para cuando dos trazos de linea se cruzan.
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
# Calculo de cajas (wrap + padding calculado, nunca fijo a mano)
# ---------------------------------------------------------------------------

def wrap_label(label, max_width=22):
    """Envuelve el texto en varias lineas si excede max_width, respetando
    palabras. Devuelve (lineas, ancho_del_contenido)."""
    label = str(label)
    if not label:
        return [""], 0
    wrapped = textwrap.wrap(label, width=max_width) or [""]
    content_width = max(len(line) for line in wrapped)
    return wrapped, content_width


def box_dimensions(label, shape='box', max_width=22, padding=1):
    """Calcula las lineas de texto y el tamano exacto de caja necesario
    para contenerlas, dado el padding interno deseado."""
    lines, content_width = wrap_label(label, max_width=max_width)
    inner_width = content_width + 2 * padding
    total_width = inner_width + 2  # bordes izq/der
    total_height = len(lines) + 2  # bordes sup/inf
    return {
        'lines': lines,
        'content_width': content_width,
        'inner_width': inner_width,
        'width': total_width,
        'height': total_height,
    }


def draw_box(canvas, top, left, dims, shape='box'):
    """Dibuja la caja en el canvas. Devuelve metadatos de geometria
    (top/bottom/left/right/center_col) para que el enrutador de flechas
    los use."""
    lines = dims['lines']
    inner_width = dims['inner_width']
    width = dims['width']
    height = dims['height']

    if shape == 'diamond':
        # Rombo dimensionado segun el ancho real del texto (una sola linea).
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

    # Caja rectangular estandar.
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
# FLOWCHART: layering topologico + enrutado ortogonal de aristas
# ---------------------------------------------------------------------------

def compute_layers(nodes, edges):
    """Asigna a cada nodo una capa (fila) usando el camino mas largo desde
    una raiz (layering topologico tipo Sugiyama simplificado). Si hay un
    ciclo, hace fallback a BFS desde el primer nodo para seguir siendo
    deterministico."""
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
    # Kahn's algorithm con recalculo de capa = max(preds)+1
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

    # Fallback: cualquier nodo no alcanzado (ciclo o nodo aislado) se ubica
    # justo debajo del maximo actual para que el diagrama siga siendo legible.
    max_layer = max(layer.values()) if layer else 0
    for nid in node_ids:
        if nid not in layer:
            max_layer += 1
            layer[nid] = max_layer

    layers = {}
    for nid in node_ids:
        layers.setdefault(layer[nid], []).append(nid)
    # Preserva el orden de aparicion original dentro de cada capa.
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
    H_SPACING = 4   # separacion horizontal minima entre cajas de una capa
    V_SPACING = 4   # alto del carril de conectores entre capas (deja margen
                     # para 1 fila en blanco + hasta 2 carriles de cruce)

    # Predecesores para poder alinear cadenas simples (1 padre -> 1 hijo)
    # bajo el mismo eje vertical, en vez de siempre pegar todo a la izquierda.
    preds_map = {n['id']: [] for n in nodes}
    for e in edges:
        preds_map[e['to']].append(e['from'])

    geom = {}  # id -> geometria de la caja dibujada
    row_cursor = 0

    for layer_idx in sorted(layers.keys()):
        ids_in_layer = layers[layer_idx]
        dims_list = []
        for nid in ids_in_layer:
            node = node_by_id[nid]
            dims = box_dimensions(node.get('label', nid), shape=node.get('shape', 'box'))
            dims_list.append(dims)

        # Posicion horizontal calculada: si la capa tiene un unico nodo con
        # un unico padre, se centra bajo el padre (evita zigzags innecesarios
        # en cadenas lineales). En cualquier otro caso se acomodan en fila
        # con el espaciado minimo calculado H_SPACING.
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

        # Deja espacio para el carril de conectores antes de la proxima capa.
        if layer_idx != max(layers.keys()):
            row_cursor += V_SPACING

    # --- Enrutado de aristas -------------------------------------------
    # Agrupa aristas por capa de origen para asignarles carriles horizontales
    # sin que se pisen entre si (deteccion de colision por rango de columnas).
    layer_of = {}
    for l, ids_ in layers.items():
        for nid in ids_:
            layer_of[nid] = l

    adjacent_edges = [e for e in edges if layer_of[e['to']] - layer_of[e['from']] == 1]
    skip_edges = [e for e in edges if layer_of[e['to']] - layer_of[e['from']] != 1]

    # Las aristas que saltan >1 capa no pueden pasar "por encima" de cajas
    # intermedias, asi que se enrutan por un carril vertical lateral, fuera
    # del ancho ocupado por cualquier caja del diagrama.
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
        # Asigna cada arista a la primera fila del carril donde su rango de
        # columnas [min,max] no se solape con otra arista ya puesta ahi.
        lane_ranges = []  # lista de listas de (c1,c2) por carril
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
                # Esquinas correctas segun direccion (en vez de "+"" generico).
                canvas.set(bend_row, sc, '└' if tc > sc else '┘')
                canvas.set(bend_row, tc, '┐' if tc > sc else '┌')
                canvas.v_line(below_band, ttop - 1, tc)
                if below_band > bend_row + 1:
                    canvas.v_line(bend_row + 1, below_band, tc)
            canvas.set(ttop - 1, tc, '▼')

            label = e.get('label')
            if label:
                if sc != tc:
                    # La etiqueta va incrustada en el propio tramo horizontal,
                    # centrada, para que nunca choque con ninguna caja.
                    c1, c2 = sorted((sc, tc))
                    lc = (c1 + c2) // 2
                    canvas.text(bend_row, lc - len(label) // 2, f" {label} ")
                else:
                    canvas.text(bend_row, sc + 2, label)

    return canvas.render()


# ---------------------------------------------------------------------------
# SEQUENCE: columnas por participante calculadas iterativamente hasta que
# todos los mensajes (incluso los que saltan participantes) quepan.
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
    # Encabezado: nombres centrados sobre cada lifeline.
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
            # Auto-mensaje: nota inline (no se dibuja loop completo).
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
        # Coloca la etiqueta centrada en el tramo.
        if label:
            start = max(0, (len(line) - len(label)) // 2)
            for k, ch in enumerate(label):
                if start + k < len(line):
                    line[start + k] = ch
        text = ''.join(line)
        canvas.text(row, c1, text)
        # Punta de flecha apuntando hacia el destino.
        canvas.set(row, cj, '>' if cj > ci else '<')
        canvas.set(row, ci, '|')
        canvas.set(row, cj, '>' if cj > ci else '<')
        row += 1
        draw_lifelines_row(row)
        row += 1

    return canvas.render()


# ---------------------------------------------------------------------------
# TREE: indentacion clasica (igual al comando `tree`), 100% calculada.
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
    parser = argparse.ArgumentParser(description="Renderiza diagramas ASCII a partir de JSON.")
    parser.add_argument('input', help="Archivo JSON de entrada, o '-' para stdin.")
    parser.add_argument('-o', '--output', help="Archivo de salida (por defecto: stdout).")
    args = parser.parse_args()

    if args.input == '-':
        raw = sys.stdin.read()
    else:
        with open(args.input, 'r', encoding='utf-8') as f:
            raw = f.read()

    data = json.loads(raw)
    dtype = data.get('type')
    if dtype not in RENDERERS:
        print(f"Tipo de diagrama desconocido: {dtype!r}. Usa uno de {list(RENDERERS)}.", file=sys.stderr)
        sys.exit(1)

    output = RENDERERS[dtype](data)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output + '\n')
        print(f"Diagrama escrito en {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()