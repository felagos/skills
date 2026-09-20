---
name: react-scaffold
description: Standardizes the creation of React/TypeScript components with a fixed folder structure (component folder containing ComponentName.tsx, ComponentName.module.scss, and an index.ts barrel export, plus an optional test file), standardizes scaffolding whole feature folders (components/pages/services/hooks/types/index, grouped by use case under features/, plus a shared/ folder for anything transversal) for horizontal scaling of a frontend codebase, and — on demand — structures Jest/Vitest test files (.test.ts, .test.tsx, .spec.ts) with a consistent describe/test hierarchy and mock lifecycle. Use this skill whenever the user asks to create, scaffold, or add a new React component, a new UI component, a new "componente", a new feature/module folder, or mentions wanting components or features organized "each in its own folder", "horizontal scaling", "escalamiento horizontal", or a feature-based/domain-based folder structure — even if they don't explicitly ask for a skill or mention file structure. Also use when the user asks to convert an existing loose component (a lone .tsx file, or a component embedded inline in another file) into this folder convention, and whenever the user asks to write, organize, restructure, or review tests for a JS/TS project, wants test coverage for a function/class/component, asks how to set up mocks or spies, or mentions Jest/Vitest conventions.
---

# React Component Scaffold

This skill encodes a team convention for React/TypeScript components: **every component lives in its own folder**, with a predictable set of files inside. The goal is that any two components in the codebase look structurally identical, so anyone can jump into a new component folder already knowing where everything is.

## The convention

```
ComponentName/
├── ComponentName.tsx           # the component itself
├── ComponentName.module.scss   # scoped styles — always .module.scss
├── index.ts                    # barrel export, always present
└── ComponentName.test.tsx      # only when tests are requested
```

Key rules:
- The folder name and the component name are the same PascalCase identifier (e.g. `UserCard/UserCard.tsx`, not `user-card/UserCard.tsx`).
- Styles are always CSS Modules in `.module.scss`, imported as `styles` from `./ComponentName.module.scss`. Every component gets its own folder with its own style file — no shared/global stylesheet per component.
- `index.ts` always exists, even for a single component, so imports elsewhere in the app can do `import { ComponentName } from '@/components/ComponentName'` rather than reaching into the file directly. It re-exports the component and its props type.
- Props are typed with an interface named `ComponentNameProps`, declared right above the component.

## Component template

```tsx
import styles from './ComponentName.module.scss'

interface ComponentNameProps {}

export const ComponentName = ({}: ComponentNameProps) => {
  return (
    <div className={styles.container}></div>
  )
}
```

## index.ts template

```ts
export { ComponentName } from './ComponentName'
export type { ComponentNameProps } from './ComponentName'
```

## Style module template

```scss
.container {
}
```

## Testing

Tests are **on demand only**. Don't add a test file unless the user asks for one, or the project's existing components all have accompanying tests — scaffolding an empty, never-asked-for test file just adds noise.

When tests *are* requested (writing new tests, adding coverage, restructuring or reviewing an existing test file, setting up mocks/spies), read [references/testing.md](references/testing.md) and follow it. That document is the full convention: Jest vs Vitest detection, the `describe`/`it` hierarchy, the `beforeEach`/`afterEach`/`afterAll` mock lifecycle, when `spyOn` beats `jest.mock()`, rendering real components and hooks instead of mocking them, and querying via `screen`. It applies to any JS/TS test in the project, not just component tests.

For a component scaffolded by this skill, the test file is `ComponentName.test.tsx`, colocated inside the component's folder, and its top-level `describe` is the component name:

```tsx
import { render, screen } from '@testing-library/react'
import { ComponentName } from './ComponentName'

describe('ComponentName', () => {
  describe('rendering', () => {
    it('should render the container when given no props', () => {
      render(<ComponentName />)
    })
  })
})
```

## How to generate a component

For a single component, it's fine to just write the files directly following the templates above — fill in the real prop names and JSX the user described instead of leaving stubs, since these are starting points, not final output.

For scaffolding one or more components mechanically (e.g. "create components for Header, Sidebar, and Footer"), use the bundled script instead of hand-writing each file — it guarantees consistent naming and saves you from typos in the boilerplate:

```bash
python3 scripts/create_component.py ComponentName --dir path/to/components
```

Options:
- `--style css|scss` — which stylesheet extension to use (default `scss`, the team standard).
- `--test` — also generate `ComponentName.test.tsx`.
- `--dir path` — parent directory to create the component folder in (default: current directory).
- `--force` — overwrite an existing non-empty folder.

The script accepts kebab-case, snake_case, or camelCase input and normalizes it to PascalCase (e.g. `user-card` → `UserCard`), so the user doesn't need to get the casing exactly right when asking.

After scaffolding, fill in the actual props interface, JSX, and any needed styles based on what the user described — don't leave the empty stub as the final answer unless they explicitly just wanted the skeleton.

## Scaling horizontally: feature folders

As a project grows, don't keep piling components into one flat `components/` folder or nesting things deeper — instead, group by **use case** under `features/`, and keep everything cross-cutting under `shared/`:

```
src/
├── features/
│   ├── auth/                 # one folder per use case
│   │   ├── components/       # components local to this use case
│   │   │   └── LoginForm/
│   │   ├── pages/            # route-level screens for this use case
│   │   ├── services/         # API calls specific to auth
│   │   ├── hooks/            # useAuth, useLogin...
│   │   ├── types.ts
│   │   └── index.ts          # the ONLY file other code may import from
│   ├── dashboard/
│   │   └── ... (same shape)
│   └── billing/
│       └── ... (same shape)
└── shared/                   # everything transversal to the project
    ├── components/           # generic UI (Button, Card, Modal...)
    ├── services/              # base API client / fetch config
    ├── hooks/                 # hooks shared across features
    └── types/                 # global/shared types
```

Rules that make this scale:
- **Group by use case, not by layer.** Each subfolder of `features/` is one use case (`auth`, `billing`, `dashboard`...), and each contains its own `components/`, `pages/`, `services/`, `hooks/`, and `types`.
- **Features never import from each other's internals.** `dashboard/` may only import from `features/billing` (the barrel export in its `index.ts`), never from `features/billing/components/SomeThing/SomeThing.tsx` directly. This keeps every feature swappable or extractable later.
- **`shared/` holds only what's transversal to the whole project** — generic UI, the base API client, cross-feature hooks, global types. Anything domain-specific belongs inside its feature's own folder, not `shared/` — otherwise it becomes a dumping ground as the app grows. `shared/` has no `pages/`, since pages always belong to a specific use case.
- **Each feature reuses the same component convention** described above — a `components/SomeThing/` folder (in a feature or in `shared/`) is scaffolded exactly like a top-level component, with its own `SomeThing.module.scss`.

### Generating a feature folder

Use the bundled script to scaffold a full feature:

```bash
python3 scripts/create_feature.py featureName --dir path/to/features
```

This creates:
```
featureName/
├── components/           # empty (.gitkeep) unless --with-component is passed
├── pages/                # empty (.gitkeep) — route-level screens for this use case
├── hooks/
│   └── useFeatureName.ts # starter hook with useState scaffolding
├── services/
│   └── featureNameService.ts  # starter API-call object, commented-out example
├── types.ts               # starter FeatureNameState interface
└── index.ts                # barrel export — re-exports hooks, types, and components
```

Options:
- `--with-component` — also scaffold an initial component inside `components/FeatureName/`, following the exact same convention as `create_component.py`, and wire it into the feature's `index.ts`.
- `--style css|scss` — stylesheet extension for that initial component (default `scss`).
- `--dir path` — parent directory to create the feature folder in (default: `features`).
- `--shared` — scaffold `shared/` instead of a use-case feature: no `pages/` subfolder.
- `--force` — overwrite an existing non-empty folder.

To scaffold the project's `shared/` folder (once, at project setup):

```bash
python3 scripts/create_feature.py shared --shared --dir src
```

The script normalizes the feature name to kebab-case for the folder (`userProfile` → `user-profile`) and to PascalCase/camelCase for identifiers inside the files, so casing stays consistent automatically.

After scaffolding, fill in the real state shape in `types.ts`, the real hook logic, and the real API calls in the service file — the generated files are a consistent starting skeleton, not the final implementation.

## Adapting to project conventions

If the user's repo is visible (e.g. via an uploaded file or an open project), peek at an existing component folder first to confirm this convention actually matches — indexing style, prop typing (interface vs type), and CSS vs SCSS can vary by project even among teams that otherwise follow "one folder per component." When something differs from the defaults above, follow the project's existing pattern rather than the template.
