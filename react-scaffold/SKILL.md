---
name: react-scaffold
description: "Scaffolds and reorganizes React/TypeScript components and feature folders (component folder with .tsx, style module and index barrel) and structures Jest/Vitest tests, deferring to existing project conventions. Use when creating or refactoring React components, organizing a feature-based frontend layout, or writing and restructuring React tests."
---

# React Scaffold

## Activation Contract

Use this skill to create or reorganize React/TypeScript components, scaffold feature folders, or add and restructure Jest/Vitest tests. Treat the bundled convention as a fallback when the repository does not already define one.

## Hard Rules

- Inspect an existing nearby component, feature, and test before choosing names, exports, styles, or test syntax.
- Declare every React/TypeScript function, hook, and component created or edited by this skill as an arrow function, even when nearby code uses function declarations.
- Prefer the repository's established convention over this skill's defaults.
- When no convention exists, place each component in a PascalCase folder containing `ComponentName.tsx`, `ComponentName.module.scss`, and `index.ts`.
- Export the component and its `ComponentNameProps` type from `index.ts`.
- Add tests only when requested or when colocated tests are an established repository rule.
- Do not leave placeholder props, JSX, tests, or styles when the user requested working behavior.
- Never overwrite a non-empty target unless the user explicitly authorizes replacement.

## Decision Gates

| Situation | Action |
| --- | --- |
| Existing project convention differs | Follow the project, including `type` vs `interface`, CSS technology, export style, and test runner; retain the arrow-function rule above. |
| One custom component | Create or edit the files directly. |
| Repeated mechanical scaffolding | Use the bundled script, then replace generated stubs with requested behavior. |
| Feature-based organization | Read `references/feature-folders.md` and use `create_feature.py` when appropriate. |
| Tests requested or existing | Read `references/testing.md`; detect Jest or Vitest from repository configuration. |
| Cross-feature code | Place it under the repository's shared area, not inside an unrelated feature. |

## Execution Steps

1. Inspect the target tree, package scripts, aliases, styling, exports, and nearby tests.
2. Choose the repository convention or, if absent, the defaults in this skill.
3. Resolve bundled scripts relative to this `SKILL.md`, not the user's current working directory. Invoke them with the available Python launcher (`python`, falling back to `python3`); use `--help` for options instead of reading their source.
4. For components, run `scripts/create_component.py NAME --dir PARENT` and add `--test` only when required.
5. For features, follow `references/feature-folders.md` and run `scripts/create_feature.py` with the needed flags.
6. Implement real props, JSX, styles, exports, and tests; then run focused type checks and tests.

## Output Contract

Return the created or changed paths, the convention selected, and exact verification results. Mention generated placeholders that still require user-supplied product behavior, if any.

## References

- [Feature folders](references/feature-folders.md) — feature and shared layouts plus script options.
- [Testing](references/testing.md) — Jest/Vitest structure, queries, mocks, and lifecycle.
