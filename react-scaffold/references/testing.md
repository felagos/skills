# Jest / Vitest Test Structure

Read this file only when tests are requested. Goal: every test file has the same skeleton and the same mock lifecycle, so there is no mock leakage between tests.

## Step 0: Detect the test runner

Check in order until conclusive; guessing wrong produces code that won't run:

1. `package.json` dependencies: `vitest`, or `jest` / `ts-jest` / `babel-jest` / `@types/jest`.
2. Config: `vitest.config.*` or a `test` block in `vite.config.ts` → Vitest; `jest.config.*` or a `"jest"` key in `package.json` → Jest.
3. Existing tests: `import { vi } from 'vitest'` → Vitest; no import or `@jest/globals` → Jest.
4. Still ambiguous (e.g. new project) → ask the user.

| | Jest | Vitest |
|---|---|---|
| Spy/mock namespace | `jest.spyOn`, `jest.fn` | `vi.spyOn`, `vi.fn` |
| Import needed | none (globals) — or `import { jest, describe, it, expect } from '@jest/globals'` if the project doesn't use globals | `import { describe, it, expect, vi, beforeEach, afterEach, afterAll } from 'vitest'` |
| Restore mocks | `jest.restoreAllMocks()` | `vi.restoreAllMocks()` |
| Clear mocks | `jest.clearAllMocks()` | `vi.clearAllMocks()` |
| Fake timers | `jest.useFakeTimers()` / `jest.useRealTimers()` | `vi.useFakeTimers()` / `vi.useRealTimers()` |
| Advance timers | `jest.advanceTimersByTime(ms)` | `vi.advanceTimersByTime(ms)` |

Examples below use `jest.*`; in Vitest swap to `vi.*` and add the import. Nothing else changes.

## File structure

```ts
import { UserService } from './user-service';
import { apiClient } from './api-client';

describe('UserService', () => {                       // exact subject name
  let service: UserService;

  beforeEach(() => {                                  // mocks/spies created here
    service = new UserService();
    jest.spyOn(apiClient, 'get').mockResolvedValue({ id: 1, name: 'Ada' });
  });

  afterEach(() => {                                   // required whenever beforeEach mocks
    jest.restoreAllMocks();
  });

  afterAll(() => {                                    // only if the file uses timers
    jest.useRealTimers();
  });

  describe('getUser', () => {                         // one nested describe per scenario
    it('should return the user when the id exists', async () => {
      expect(await service.getUser(1)).toEqual({ id: 1, name: 'Ada' });
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

- **One top-level `describe`** named exactly after the function, class, or component.
- **One nested `describe` per scenario** (method, branch, rendering case, edge-case group), even if it has a single `it`. No `it` directly under the top-level `describe`.
- **One behavior per `it`/`test`**, named `should <expected behavior> when <condition>`.

## Mocking rules

- Create mocks in `beforeEach` and default to `spyOn`: it overrides only the named method, pairs with `restoreAllMocks()`, and fails loudly if the method no longer exists.
- Use `jest.mock()` / `vi.mock()` only when `spyOn` can't work: import-time side effects (DB connection, env reads), modules that must never run in tests (native bindings, CSS/asset imports, config files), or non-spy-able exports (ESM named exports, non-object default exports). Mock only the needed export and add a short comment explaining why `spyOn` wasn't possible.

### Components are rendered, not mocked

Never mock the component under test, its child components, or the custom hooks it uses; render them for real with Testing Library. Mock the *dependencies* instead: API clients, routers, browser APIs (`localStorage`, `IntersectionObserver`), timers.

```tsx
// ❌ Mocking the hook or a child skips the integration the test should catch
jest.mock('./useUser', () => ({ useUser: () => ({ data: { name: 'Ada' }, loading: false }) }));
jest.mock('./UserCard', () => () => <div>mocked</div>);

// ✅ Mock what the hook calls; render everything real
jest.spyOn(apiClient, 'fetchUser').mockResolvedValue({ id: 1, name: 'Ada' });
render(<UserProfile userId={1} />);
expect(await screen.findByText('Ada')).toBeInTheDocument();
```

Exception: an expensive or unstable child that isn't the subject (e.g. a heavy chart or map widget) may be mocked, with a short comment.

### Query with `screen`, not `container`

Call `getBy*` / `queryBy*` / `findBy*` on `screen`, never `container.querySelector(...)`. Use `container` only when no accessible role, text, or label can express the assertion (e.g. a raw CSS class or inline style).

## Cleanup

- `afterEach(() => jest.restoreAllMocks())` in every file with mocks in `beforeEach`; it restores real implementations, not just call history. Add `clearAllMocks()` if `jest.mock()`-based mocks are also present.
- `afterAll(() => jest.useRealTimers())` only when the file uses fake timers, so they don't bleed into other files. Also clear real `setTimeout`/`setInterval` handles the code leaves running (or `jest.clearAllTimers()` with fake timers). Don't add this block to files without timers.

## Naming and location

- File: `<subject>.test.ts` (or `.spec.ts`), colocated or under `__tests__/`; match the project's existing convention.
- Nested `describe`: method name (`'#getUser'`) or scenario (`'when the user is not authenticated'`).

## When organizing an existing test file

Preserve every existing assertion; don't drop or rewrite test logic. Group existing `it`s into matching nested `describe`s, add missing `beforeEach`/`afterEach` cleanup, and add the `afterAll` timer block only if the file uses timers.
