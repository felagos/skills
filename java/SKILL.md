---
name: java
description: "Writes, refactors and reviews modern, idiomatic Java 21 code (records, sealed types, pattern matching, virtual threads) without Lombok, respecting the repository's build tool and conventions. Use when the task involves Java source code, Java 21 features, or a Java code review or refactor."
---

# Java 21

## Activation Contract

Use this skill for writing, refactoring, reviewing, or explaining Java code. Target Java 21 and preserve the repository's established build tool, layout, and conventions unless the user requests a migration.

## Hard Rules

- Use Java 21 language features when they make the code clearer; do not modernize mechanically.
- Do not use Lombok. Write required constructors, accessors, and methods explicitly.
- Use records for immutable data carriers and sealed types for genuinely closed hierarchies.
- Prefer `var` only when the inferred local type is obvious.
- Avoid wildcard imports and ambiguous `null`; use a specific exception or `Optional` at API boundaries where absence is meaningful.
- Preserve the project's public API and dependency choices unless the task authorizes changes.
- Add `main`, standard-stream output, and process exit codes only for standalone executable programs, not libraries, framework components, or review-only tasks.

## Decision Gates

| Situation | Action |
| --- | --- |
| Existing Java repository | Inspect its build files, source level, tests, and style before editing. |
| Standalone program | Provide a clear `main`; send results to stdout and failures to stderr. |
| Library or framework code | Integrate with the existing entry point and lifecycle. |
| Concurrency task | Prefer virtual threads for blocking I/O; do not use them as a default for CPU-bound work. |
| Records, sealed types, pattern matching, streams, text blocks, or virtual threads | Read the relevant section of `references/language-features.md`. |

## Execution Steps

1. Inspect the repository and identify the build tool, Java version, package layout, and test framework.
2. Read only the relevant sections of `references/language-features.md`.
3. Implement the smallest change that satisfies the request while preserving repository conventions.
4. Compile and run focused tests when the environment permits; report anything that could not be verified.
5. Review the result for Java 21 compatibility, explicit resource ownership, and actionable exception handling.

## Output Contract

Return the implemented or reviewed Java result, a concise summary of important decisions, and the exact verification performed. For reviews, lead with concrete findings and file locations.

## References

- [Java 21 language features](references/language-features.md) — idioms, examples, and executable delivery patterns.
