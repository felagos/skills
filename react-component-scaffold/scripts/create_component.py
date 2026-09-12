#!/usr/bin/env python3
"""
Scaffold a React/TypeScript component folder following the standard convention:

ComponentName/
├── ComponentName.tsx
├── ComponentName.module.css   (or .scss)
├── index.ts
└── ComponentName.test.tsx     (only with --test)

Usage:
    python create_component.py ComponentName [--style css|scss] [--test] [--dir path/to/parent] [--force]

Examples:
    python create_component.py UserCard
    python create_component.py UserCard --style scss --test
    python create_component.py UserCard --dir src/components
"""

import argparse
import os
import re
import sys

TSX_TEMPLATE = """import styles from './{name}.module.{ext}'

interface {name}Props {{}}

export const {name} = ({{}}: {name}Props) => {{
  return (
    <div className={{styles.container}}></div>
  )
}}
"""

STYLE_TEMPLATE = """.container {
}
"""

INDEX_TEMPLATE = """export {{ {name} }} from './{name}'
export type {{ {name}Props }} from './{name}'
"""

TEST_TEMPLATE = """import {{ render, screen }} from '@testing-library/react'
import {{ {name} }} from './{name}'

describe('{name}', () => {{
  it('renders without crashing', () => {{
    render(<{name} />)
  }})
}})
"""


def is_pascal_case(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Z][A-Za-z0-9]*", name))


def to_pascal_case(name: str) -> str:
    # Convert kebab-case, snake_case, or camelCase into PascalCase
    parts = re.split(r"[-_\s]+", name)
    parts = [p[0:1].upper() + p[1:] for p in parts if p]
    result = "".join(parts)
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def main():
    parser = argparse.ArgumentParser(description="Scaffold a standardized React component folder.")
    parser.add_argument("name", help="Component name, e.g. UserCard (will be coerced to PascalCase)")
    parser.add_argument("--style", choices=["css", "scss"], default="scss", help="Stylesheet extension (default: scss)")
    parser.add_argument("--test", action="store_true", help="Also generate a ComponentName.test.tsx file")
    parser.add_argument("--dir", default=".", help="Parent directory to create the component folder in (default: current directory)")
    parser.add_argument("--force", action="store_true", help="Overwrite files if the component folder already exists")
    args = parser.parse_args()

    raw_name = args.name
    name = to_pascal_case(raw_name)
    if not is_pascal_case(name):
        print(f"Error: could not derive a valid PascalCase component name from '{raw_name}'.", file=sys.stderr)
        sys.exit(1)
    if name != raw_name:
        print(f"Note: normalized component name '{raw_name}' -> '{name}'")

    component_dir = os.path.join(args.dir, name)

    if os.path.exists(component_dir) and not args.force:
        existing = os.listdir(component_dir)
        if existing:
            print(f"Error: '{component_dir}' already exists and is not empty. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)

    os.makedirs(component_dir, exist_ok=True)

    files = {
        f"{name}.tsx": TSX_TEMPLATE.format(name=name, ext=args.style),
        f"{name}.module.{args.style}": STYLE_TEMPLATE,
        "index.ts": INDEX_TEMPLATE.format(name=name),
    }
    if args.test:
        files[f"{name}.test.tsx"] = TEST_TEMPLATE.format(name=name)

    for filename, content in files.items():
        path = os.path.join(component_dir, filename)
        with open(path, "w") as f:
            f.write(content)
        print(f"Created {path}")

    print(f"\nDone. Component '{name}' scaffolded at {component_dir}/")


if __name__ == "__main__":
    main()
