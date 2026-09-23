#!/usr/bin/env python3
"""
Scaffold a feature-folder for horizontal scaling in a React/TypeScript project.

Convention:

features/featureName/
├── components/            # components local to this feature
│   └── FeatureName/       # optional initial component, same convention as create_component.py
│       ├── FeatureName.tsx
│       ├── FeatureName.module.scss
│       └── index.ts
├── pages/
├── hooks/
│   └── useFeatureName.ts
├── services/
│   └── featureNameService.ts
├── types.ts
└── index.ts                # the ONLY file other features/app code are allowed to import from

Usage:
    python create_feature.py featureName [--style css|scss] [--with-component] [--dir path/to/features] [--shared] [--force]

Examples:
    python create_feature.py billing
    python create_feature.py userProfile --with-component
    python create_feature.py notifications --dir src/features
    python create_feature.py shared --shared --dir src   # scaffolds src/shared/ (no pages/)
"""

import argparse
import os
import re
import sys

# Reuse the same casing helpers as create_component.py so a feature and its
# optional initial component follow identical naming rules.


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[-_\s]+", name)
    parts = [p[0:1].upper() + p[1:] for p in parts if p]
    result = "".join(parts)
    if result and result[0].islower():
        result = result[0].upper() + result[1:]
    return result


def to_camel_case(name: str) -> str:
    pascal = to_pascal_case(name)
    return pascal[0:1].lower() + pascal[1:] if pascal else pascal


def to_kebab_case(name: str) -> str:
    # Insert dashes at camel/Pascal boundaries, then normalize separators.
    s = re.sub(r"[-_\s]+", "-", name)
    s = re.sub(r"(?<!^)(?<![-])(?=[A-Z])", "-", s)
    return s.lower().strip("-")


TYPES_TEMPLATE = """// Shared types for the {feature_pascal} feature.
export interface {feature_pascal}State {{}}
"""

HOOK_TEMPLATE = """import {{ useState }} from 'react'
import type {{ {feature_pascal}State }} from '../types'

export const use{feature_pascal} = () => {{
  const [state, setState] = useState<{feature_pascal}State>({{}} as {feature_pascal}State)

  return {{ state, setState }}
}}
"""

SERVICE_TEMPLATE = """// API calls for the {feature_pascal} feature.
// Keep this the only place in the feature that talks to the network.

export const {feature_camel}Service = {{
  // getAll: async () => {{
  //   const res = await fetch('/api/{feature_kebab}')
  //   return res.json()
  // }},
}}
"""

FEATURE_INDEX_TEMPLATE = """// Public API of the {feature_pascal} feature.
// Other features and app code must only import from here —
// never reach into features/{feature_kebab}/components/... or .../services/... directly.

export * from './hooks/use{feature_pascal}'
export * from './types'
{component_export}"""

# Component templates, mirrored from create_component.py so both scripts
# produce byte-identical component folders.
COMPONENT_TSX_TEMPLATE = """import styles from './{name}.module.{ext}'

export interface {name}Props {{}}

export const {name} = ({{}}: {name}Props) => {{
  return (
    <div className={{styles.container}}></div>
  )
}}
"""

COMPONENT_STYLE_TEMPLATE = """.container {
}
"""

COMPONENT_INDEX_TEMPLATE = """export {{ {name} }} from './{name}'
export type {{ {name}Props }} from './{name}'
"""


def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)
    print(f"Created {path}")


def main():
    parser = argparse.ArgumentParser(description="Scaffold a feature folder for horizontal scaling.")
    parser.add_argument("name", help="Feature name, e.g. billing or user-profile")
    parser.add_argument("--style", choices=["css", "scss"], default="scss", help="Stylesheet extension for the optional initial component (default: scss)")
    parser.add_argument("--with-component", action="store_true", help="Also scaffold an initial component (components/FeatureName/) named after the feature")
    parser.add_argument("--dir", default="features", help="Parent directory to create the feature folder in (default: features)")
    parser.add_argument("--shared", action="store_true", help="Scaffold the shared/ folder instead of a feature: no pages/ subfolder, no barrel index re-exporting a use case")
    parser.add_argument("--force", action="store_true", help="Overwrite files if the feature folder already exists")
    args = parser.parse_args()

    feature_kebab = to_kebab_case(args.name)
    feature_pascal = to_pascal_case(args.name)
    feature_camel = to_camel_case(args.name)

    if args.name != feature_kebab:
        print(f"Note: normalized feature name '{args.name}' -> '{feature_kebab}'")

    feature_dir = os.path.join(args.dir, feature_kebab)

    if os.path.exists(feature_dir) and not args.force:
        existing = os.listdir(feature_dir)
        if existing:
            print(f"Error: '{feature_dir}' already exists and is not empty. Use --force to overwrite.", file=sys.stderr)
            sys.exit(1)

    subdirs = ("components", "hooks", "services") if args.shared else ("components", "pages", "hooks", "services")
    for sub in subdirs:
        os.makedirs(os.path.join(feature_dir, sub), exist_ok=True)
    if not args.shared:
        write_file(os.path.join(feature_dir, "pages", ".gitkeep"), "")

    write_file(os.path.join(feature_dir, "types.ts"), TYPES_TEMPLATE.format(feature_pascal=feature_pascal))
    write_file(
        os.path.join(feature_dir, "hooks", f"use{feature_pascal}.ts"),
        HOOK_TEMPLATE.format(feature_pascal=feature_pascal),
    )
    write_file(
        os.path.join(feature_dir, "services", f"{feature_camel}Service.ts"),
        SERVICE_TEMPLATE.format(feature_pascal=feature_pascal, feature_camel=feature_camel, feature_kebab=feature_kebab),
    )

    component_export = ""
    if args.with_component:
        comp_dir = os.path.join(feature_dir, "components", feature_pascal)
        os.makedirs(comp_dir, exist_ok=True)
        write_file(
            os.path.join(comp_dir, f"{feature_pascal}.tsx"),
            COMPONENT_TSX_TEMPLATE.format(name=feature_pascal, ext=args.style),
        )
        write_file(os.path.join(comp_dir, f"{feature_pascal}.module.{args.style}"), COMPONENT_STYLE_TEMPLATE)
        write_file(os.path.join(comp_dir, "index.ts"), COMPONENT_INDEX_TEMPLATE.format(name=feature_pascal))
        component_export = f"export * from './components/{feature_pascal}'\n"
    else:
        # components/ stays as an empty directory ready for future components;
        # git doesn't track empty dirs, so drop a placeholder.
        write_file(
            os.path.join(feature_dir, "components", ".gitkeep"),
            "",
        )

    write_file(
        os.path.join(feature_dir, "index.ts"),
        FEATURE_INDEX_TEMPLATE.format(
            feature_pascal=feature_pascal, feature_kebab=feature_kebab, component_export=component_export
        ),
    )

    print(f"\nDone. Feature '{feature_kebab}' scaffolded at {feature_dir}/")


if __name__ == "__main__":
    main()
