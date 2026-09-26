# Feature folders — horizontal scaling

How to group code by use case under `features/`, what goes in `shared/`, and how to scaffold
either with `scripts/create_feature.py`. `SKILL.md` covers single components; this file covers
whole features.

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
- **Each feature reuses the component convention from `SKILL.md`** — a `components/SomeThing/` folder (in a feature or in `shared/`) is scaffolded exactly like a top-level component, with its own `SomeThing.module.scss`.

### Generating a feature folder

Use the bundled script to scaffold a full feature:

```bash
python scripts/create_feature.py featureName --dir path/to/features
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
python scripts/create_feature.py shared --shared --dir src
```

The script normalizes the feature name to kebab-case for the folder (`userProfile` → `user-profile`) and to PascalCase/camelCase for identifiers inside the files, so casing stays consistent automatically.

After scaffolding, fill in the real state shape in `types.ts`, the real hook logic, and the real API calls in the service file — the generated files are a consistent starting skeleton, not the final implementation.

