---
name: jest-test-structure
description: Organizes and writes test files (.test.ts, .test.js, .spec.ts, .spec.js) for JavaScript/TypeScript projects using a consistent describe/test hierarchy and mock lifecycle (beforeEach with spyOn, afterEach cleanup, afterAll timer cleanup). Works with both Jest and Vitest — detects which one the project actually uses and adapts syntax accordingly. Use this skill whenever the user asks to write, organize, restructure, or review test files for a JS/TS project, wants to add test coverage for a function/class/component, asks how to set up mocks or spies, or mentions Jest/Vitest test conventions — even if they don't explicitly say "skill" or "structure".
---

# Jest / Vitest Test Structure

A skill for structuring test files consistently across a JS/TS codebase, so any test file looks and behaves the same way regardless of who wrote it, what it's testing, or which runner the project uses.

## Step 0: Detect the test runner

Before writing or editing anything, figure out whether the project uses **Jest** or **Vitest** — the structure rules below are identical either way, but the API namespace and imports differ (`jest.spyOn` vs `vi.spyOn`, etc.), and guessing wrong produces code that won't run.

Check, in order, until one is conclusive:

1. **`package.json`** — look in `dependencies`/`devDependencies` for `vitest` or `jest` (or `ts-jest`, `babel-jest`, `@types/jest`, which imply Jest).
2. **Config files** — `vitest.config.ts`/`.js`/`.mts`, or a `test` block inside `vite.config.ts` → Vitest. `jest.config.ts`/`.js`/`.json`, or a `"jest"` key in `package.json` → Jest.
3. **Existing test files** — check an existing `*.test.ts`/`*.spec.ts` for `import { vi } from 'vitest'` (Vitest) vs. no import needed or `import { jest } from '@jest/globals'` (Jest).
4. If genuinely ambiguous (e.g. a brand-new project with neither installed yet), ask the user which one they're using rather than guessing.

Once known, use it consistently for the whole file:

| | Jest | Vitest |
|---|---|---|
| Spy/mock namespace | `jest.spyOn`, `jest.fn` | `vi.spyOn`, `vi.fn` |
| Import needed | none (globals) — or `import { jest, describe, it, expect } from '@jest/globals'` if the project doesn't use globals | `import { describe, it, expect, vi, beforeEach, afterEach, afterAll } from 'vitest'` |
| Restore mocks | `jest.restoreAllMocks()` | `vi.restoreAllMocks()` |
| Clear mocks | `jest.clearAllMocks()` | `vi.clearAllMocks()` |
| Fake timers | `jest.useFakeTimers()` / `jest.useRealTimers()` | `vi.useFakeTimers()` / `vi.useRealTimers()` |
| Advance timers | `jest.advanceTimersByTime(ms)` | `vi.advanceTimersByTime(ms)` |

Everything below uses `jest.*` in examples for brevity — swap in `vi.*` (and add the Vitest import) when the project uses Vitest. Nothing else about the structure changes.

## Why structure matters here

Two things make test suites hard to maintain over time: inconsistent organization (so nobody knows where a new test should go) and mock leakage between tests (so test order starts to matter, which is a bug in the test suite itself). This skill fixes both by giving every test file the same skeleton and the same mock lifecycle.

## File structure

Every test file follows this shape:

```ts
describe('<SubjectUnderTest>', () => {
  // 1. Mocks/spies created here — see "Mocking rules" below
  beforeEach(() => {
    jest.spyOn(dependency, 'method').mockReturnValue(/* ... */);
  });

  // 2. Mocks restored here — every file that has a beforeEach needs this
  afterEach(() => {
    jest.restoreAllMocks();
  });

  // 3. Only needed if this file touches timers — see "Timer cleanup" below
  afterAll(() => {
    jest.useRealTimers();
  });

  // 4. One nested describe per scenario/method/branch being covered
  describe('<scenario or method name>', () => {
    it('should <expected behavior> when <condition>', () => {
      // arrange, act, assert
    });

    it('should <expected behavior> when <other condition>', () => {
      // arrange, act, assert
    });
  });

  describe('<another scenario or method name>', () => {
    it('should <expected behavior>', () => {
      // arrange, act, assert
    });
  });
});
```

Rules for this skeleton:

- **One top-level `describe`** names the subject under test exactly (the function, class, or component name) — this is what shows up in the test runner output, so it should be unmistakable.
- **One nested `describe` per test case** (a method, a branch of logic, a rendering scenario, an edge case group). Don't put unrelated `it`s directly under the top-level `describe`; give every scenario its own nested `describe` even if it currently only has one `it` inside it — it keeps the suite easy to extend later.
- **Every `it`/`test` covers one behavior** and is named `should <expected behavior> when <condition>` so a failing test tells you what broke without opening the file.

## Mocking rules

Create mocks/spies inside `beforeEach`, and default to `spyOn` (`jest.spyOn` or `vi.spyOn`, per Step 0):

```ts
beforeEach(() => {
  jest.spyOn(apiClient, 'fetchUser').mockResolvedValue({ id: 1, name: 'Ada' });
});
```

`spyOn` is the default because it only overrides the one method you name, keeps the rest of the real module intact, and pairs cleanly with `restoreAllMocks()` in `afterEach`. It also fails loudly if the method doesn't exist, which catches typos and refactors that `jest.mock()`/`vi.mock()` would silently hide.

**Only reach for `jest.mock()` / `vi.mock()`** when `spyOn` genuinely can't do the job, for example:

- The module has import-time side effects you need to prevent entirely (e.g. it opens a DB connection or reads env vars on load).
- You're mocking a module with no real implementation that should ever run in tests (e.g. a native binding, a CSS/asset import, a config file).
- The thing you need to replace isn't a spy-able property (e.g. a named export in an ESM module, or a default export that isn't an object method).

When `jest.mock()`/`vi.mock()` is genuinely required, keep it as narrow as possible (mock only the specific export needed, not the whole module if avoidable) and say in a short comment why `spyOn` wasn't an option — that comment is what tells the next person this wasn't a default choice.

### Components are rendered, not mocked

Never mock the component under test, and never mock its child components either — render them for real (e.g. with Testing Library's `render()`) so the test exercises actual markup, props flow, and conditional rendering. A test that mocks a component out and just checks it "was called with the right props" doesn't catch rendering bugs, so it isn't really testing the component.

Mock the *dependencies* the component reaches out to instead: API clients, data-fetching hooks, routers, browser APIs (`localStorage`, `IntersectionObserver`, etc.), timers. Everything that's actually UI stays real.

```tsx
// ❌ Don't: mocking the component defeats the point of rendering it
jest.mock('./UserCard', () => () => <div>mocked</div>);

// ✅ Do: render the real component, mock what it depends on
jest.spyOn(apiClient, 'fetchUser').mockResolvedValue({ id: 1, name: 'Ada' });

describe('UserProfile', () => {
  it('should show the user name once loaded', async () => {
    render(<UserProfile userId={1} />);
    expect(await screen.findByText('Ada')).toBeInTheDocument();
  });
});
```

The one exception is a component that's expensive or unstable to render and isn't the subject of the current test (e.g. a heavy third-party chart or map widget nested deep in the tree) — mocking that specific child is fine as long as the component actually under test still renders for real, and the exception is left as a short comment.

### Query with `screen`, not `container`

Always call `getBy*`/`queryBy*`/`findBy*` on `screen`, never on the `container` returned by `render()`:

```tsx
// ❌ Don't
const { container } = render(<UserProfile userId={1} />);
expect(container.querySelector('.user-name')).toHaveTextContent('Ada');

// ✅ Do
render(<UserProfile userId={1} />);
expect(screen.getByText('Ada')).toBeInTheDocument();
```

`screen` queries the whole document rather than a detached subtree, doesn't need `render()`'s return value threaded through the test, and its error messages print the full accessible DOM tree, which is what actually helps when a query fails. `container` is reserved for the rare case a query genuinely can't express what's needed (e.g. asserting on a raw CSS class or inline style) — reach for it only then, and prefer `container.querySelector` over `getByTestId` even in that case only if there's truly no accessible role/text/label to query by.

## Cleanup: afterEach

Every file with a `beforeEach` that creates mocks needs a matching `afterEach`:

```ts
afterEach(() => {
  jest.restoreAllMocks();
});
```

`restoreAllMocks()` puts spies back to their real implementation (not just clears call history), which is what prevents one test's mock from leaking into the next test. If the file also has `jest.mock()`/`vi.mock()`-based mocks that `restoreAllMocks` doesn't fully reset, add `clearAllMocks()` alongside it.

## Cleanup: afterAll for timers

Only needed when the file uses fake timers or leaves real timers running. If any test in the file calls `jest.useFakeTimers()`, add:

```ts
afterAll(() => {
  jest.useRealTimers();
});
```

This prevents fake timers from bleeding into other test files that run after this one in the same process. If the code under test schedules real `setTimeout`/`setInterval` calls that aren't awaited or flushed, clear them explicitly in `afterAll` too (e.g. via a handle captured in the test, or `jest.clearAllTimers()` if fake timers are active).

Skip this block entirely for files that never touch timers — don't add it out of habit.

## Full example

```ts
import { UserService } from './user-service';
import { apiClient } from './api-client';

describe('UserService', () => {
  let service: UserService;

  beforeEach(() => {
    service = new UserService();
    jest.spyOn(apiClient, 'get').mockResolvedValue({ id: 1, name: 'Ada' });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  describe('getUser', () => {
    it('should return the user when the id exists', async () => {
      const user = await service.getUser(1);
      expect(user).toEqual({ id: 1, name: 'Ada' });
    });

    it('should throw when the api call fails', async () => {
      jest.spyOn(apiClient, 'get').mockRejectedValue(new Error('network error'));
      await expect(service.getUser(1)).rejects.toThrow('network error');
    });
  });

  describe('scheduleRefresh', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    it('should call refresh after the configured delay', () => {
      const refreshSpy = jest.spyOn(service, 'refresh').mockImplementation(() => {});
      service.scheduleRefresh(1000);
      jest.advanceTimersByTime(1000);
      expect(refreshSpy).toHaveBeenCalledTimes(1);
    });
  });
});
```

The same file in a Vitest project — identical structure, only the namespace and import change:

```ts
import { describe, it, expect, vi, beforeEach, afterEach, afterAll } from 'vitest';
import { UserService } from './user-service';
import { apiClient } from './api-client';

describe('UserService', () => {
  let service: UserService;

  beforeEach(() => {
    service = new UserService();
    vi.spyOn(apiClient, 'get').mockResolvedValue({ id: 1, name: 'Ada' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  afterAll(() => {
    vi.useRealTimers();
  });

  describe('getUser', () => {
    it('should return the user when the id exists', async () => {
      const user = await service.getUser(1);
      expect(user).toEqual({ id: 1, name: 'Ada' });
    });

    it('should throw when the api call fails', async () => {
      vi.spyOn(apiClient, 'get').mockRejectedValue(new Error('network error'));
      await expect(service.getUser(1)).rejects.toThrow('network error');
    });
  });

  describe('scheduleRefresh', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    it('should call refresh after the configured delay', () => {
      const refreshSpy = vi.spyOn(service, 'refresh').mockImplementation(() => {});
      service.scheduleRefresh(1000);
      vi.advanceTimersByTime(1000);
      expect(refreshSpy).toHaveBeenCalledTimes(1);
    });
  });
});
```

## Naming and location

- File name: `<subject>.test.ts` (or `.spec.ts`), colocated with the source file or under a mirrored `__tests__/` directory — match whatever the project already uses; don't introduce a second convention into an existing codebase.
- Top-level `describe`: exact name of the function, class, or component.
- Nested `describe`: the method name (e.g. `'#getUser'`) or the scenario being covered (e.g. `'when the user is not authenticated'`).
- `it`/`test`: `'should <expected behavior> when <condition>'`.

## When organizing an existing test file

If asked to reorganize a file that already has tests, preserve every existing assertion — don't drop or rewrite test logic while moving it into the new structure. Group existing `it`s into the nested `describe` that matches their scenario, add a `beforeEach`/`afterEach` if mocks aren't cleaned up yet, and only add an `afterAll` timer block if the file actually uses timers.