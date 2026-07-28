#!/usr/bin/env python3
"""
Resume el reporte JSON de StrykerJS (mutation-testing-report-schema) en una
tabla por archivo, para no tener que navegar el HTML archivo por archivo.

Genera el JSON con:
    npx stryker run --reporters json,html,clear-text

Uso:
    python3 summarize_mutants.py reports/mutation/mutation.json
    python3 summarize_mutants.py reports/mutation/mutation.json --sort survived
"""
import argparse
import json
import sys
from collections import defaultdict

# Estados que cuentan como "mutante muerto" a efectos del score, igual que Stryker
KILLED_LIKE = {"Killed", "Timeout"}
# Estados que se descartan del cálculo de score (no aportan señal real)
IGNORED_LIKE = {"Ignored", "CompileError"}


def load_report(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def summarize(report):
    files = report.get("files", {})
    rows = []
    for file_path, data in files.items():
        mutants = data.get("mutants", [])
        counts = defaultdict(int)
        for m in mutants:
            counts[m.get("status", "Unknown")] += 1

        scoreable = sum(c for status, c in counts.items() if status not in IGNORED_LIKE)
        killed_equivalent = sum(c for status, c in counts.items() if status in KILLED_LIKE)
        score = (killed_equivalent / scoreable * 100) if scoreable else 0.0

        rows.append({
            "file": file_path,
            "total": len(mutants),
            "killed": counts.get("Killed", 0),
            "survived": counts.get("Survived", 0),
            "no_coverage": counts.get("NoCoverage", 0),
            "timeout": counts.get("Timeout", 0),
            "runtime_error": counts.get("RuntimeError", 0),
            "score": score,
        })
    return rows


def print_table(rows, sort_key):
    if sort_key == "survived":
        rows.sort(key=lambda r: r["survived"], reverse=True)
    else:
        rows.sort(key=lambda r: r["score"])

    header = f"{'Archivo':<60} {'Total':>6} {'Killed':>7} {'Survived':>9} {'NoCov':>6} {'Score':>7}"
    print(header)
    print("-" * len(header))
    total_all = 0
    killed_all = 0

    for r in rows:
        name = r["file"]
        if len(name) > 60:
            name = "…" + name[-59:]
        print(f"{name:<60} {r['total']:>6} {r['killed']:>7} {r['survived']:>9} "
              f"{r['no_coverage']:>6} {r['score']:>6.1f}%")
        total_all += r["total"]
        killed_all += r["killed"]

    print("-" * len(header))
    overall = (killed_all / total_all * 100) if total_all else 0.0
    print(f"{'TOTAL':<60} {total_all:>6} {'':>7} {'':>9} {'':>6} {overall:>6.1f}%")

    no_coverage = sorted((r for r in rows if r["no_coverage"] > 0),
                          key=lambda r: r["no_coverage"], reverse=True)
    if no_coverage:
        print("\nArchivos con mutantes sin cobertura (no hay tests corriendo ahí):")
        for r in no_coverage[:10]:
            print(f"  - {r['file']}: {r['no_coverage']} sin cobertura de {r['total']} mutantes")

    survivors = sorted((r for r in rows if r["survived"] > 0),
                        key=lambda r: r["survived"], reverse=True)
    if survivors:
        print("\nArchivos con más mutantes sobrevivientes (hay tests, pero no aseveran lo suficiente):")
        for r in survivors[:10]:
            print(f"  - {r['file']}: {r['survived']} sobrevivientes de {r['total']} mutantes")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("json_path", help="Ruta al mutation.json generado por Stryker")
    parser.add_argument("--sort", choices=["score", "survived"], default="score",
                         help="Orden de la tabla: por score ascendente (peor primero) o por cantidad de sobrevivientes")
    args = parser.parse_args()

    try:
        report = load_report(args.json_path)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"No se pudo leer {args.json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    rows = summarize(report)
    if not rows:
        print("El reporte no contiene archivos con mutantes.", file=sys.stderr)
        sys.exit(1)

    print_table(rows, args.sort)


if __name__ == "__main__":
    main()