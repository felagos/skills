#!/usr/bin/env python3
"""
Resume el reporte mutations.xml generado por pitest en una tabla por clase,
para no tener que navegar el HTML clase por clase.

Uso:
    python3 summarize_mutations.py build/reports/pitest/*/mutations.xml
    python3 summarize_mutations.py ruta/a/mutations.xml --sort survived

Ordena por defecto de peor a mejor mutation score, para que las clases
que más necesitan atención aparezcan primero.
"""
import argparse
import glob
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict


def parse_mutations(xml_path):
    """Devuelve dict: clase -> {status: count}"""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    per_class = defaultdict(lambda: defaultdict(int))
    for mutation in root.findall("mutation"):
        mutated_class = mutation.findtext("mutatedClass", default="UNKNOWN")
        status = mutation.get("status") or mutation.findtext("status", default="UNKNOWN")
        per_class[mutated_class][status] += 1
    return per_class


def summarize(per_class):
    """Devuelve lista de filas (clase, killed, survived, no_coverage, timed_out, total, score)"""
    rows = []
    for cls, statuses in per_class.items():
        killed = statuses.get("KILLED", 0)
        survived = statuses.get("SURVIVED", 0)
        no_coverage = statuses.get("NO_COVERAGE", 0)
        timed_out = statuses.get("TIMED_OUT", 0)
        memory_error = statuses.get("MEMORY_ERROR", 0)
        run_error = statuses.get("RUN_ERROR", 0)
        total = sum(statuses.values())
        # timed_out cuenta como "muerto" a efectos de score, igual que hace pitest
        killed_equivalent = killed + timed_out
        score = (killed_equivalent / total * 100) if total else 0.0
        rows.append({
            "class": cls,
            "killed": killed,
            "survived": survived,
            "no_coverage": no_coverage,
            "timed_out": timed_out,
            "memory_error": memory_error,
            "run_error": run_error,
            "total": total,
            "score": score,
        })
    return rows


def print_table(rows, sort_key):
    if sort_key == "survived":
        rows.sort(key=lambda r: r["survived"], reverse=True)
    else:
        rows.sort(key=lambda r: r["score"])

    header = f"{'Clase':<55} {'Total':>6} {'Killed':>7} {'Survived':>9} {'NoCov':>6} {'Score':>7}"
    print(header)
    print("-" * len(header))
    total_all = 0
    killed_all = 0
    timed_out_all = 0
    for r in rows:
        name = r["class"]
        if len(name) > 55:
            name = "…" + name[-54:]
        print(f"{name:<55} {r['total']:>6} {r['killed']:>7} {r['survived']:>9} "
              f"{r['no_coverage']:>6} {r['score']:>6.1f}%")
        total_all += r["total"]
        killed_all += r["killed"]
        timed_out_all += r["timed_out"]

    print("-" * len(header))
    overall = (killed_all + timed_out_all) / total_all * 100 if total_all else 0.0
    print(f"{'TOTAL':<55} {total_all:>6} {'':>7} {'':>9} {'':>6} {overall:>6.1f}%")

    survivors = sorted((r for r in rows if r["survived"] > 0),
                        key=lambda r: r["survived"], reverse=True)
    if survivors:
        print("\nClases con más mutantes sobrevivientes (revisar primero):")
        for r in survivors[:10]:
            print(f"  - {r['class']}: {r['survived']} sobrevivientes de {r['total']} mutantes")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xml_paths", nargs="+", help="Ruta(s) a mutations.xml (acepta globs ya expandidos por el shell)")
    parser.add_argument("--sort", choices=["score", "survived"], default="score",
                         help="Orden de la tabla: por score ascendente (peor primero) o por cantidad de sobrevivientes")
    args = parser.parse_args()

    paths = []
    for p in args.xml_paths:
        matched = glob.glob(p)
        paths.extend(matched if matched else [p])

    if not paths:
        print("No se encontraron archivos mutations.xml", file=sys.stderr)
        sys.exit(1)

    per_class = defaultdict(lambda: defaultdict(int))
    for path in paths:
        try:
            for cls, statuses in parse_mutations(path).items():
                for status, count in statuses.items():
                    per_class[cls][status] += count
        except (ET.ParseError, FileNotFoundError) as e:
            print(f"Aviso: no se pudo leer {path}: {e}", file=sys.stderr)

    if not per_class:
        print("No se encontraron mutaciones en los archivos indicados.", file=sys.stderr)
        sys.exit(1)

    rows = summarize(per_class)
    print_table(rows, args.sort)


if __name__ == "__main__":
    main()