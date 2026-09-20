---
name: java21-claude-code
description: >
  Skill for writing, refactoring, reviewing, or generating modern, idiomatic Java 21 code,
  especially for execution in Claude Code environments (terminal, VS Code, JetBrains,
  desktop). Covers var, records, record patterns, sealed classes, pattern matching
  (instanceof and switch), text blocks, functional style (Streams, lambdas, Optional),
  virtual threads, and sequenced collections. No Lombok — always write constructors and
  accessors explicitly. Use this skill any time the user asks for Java code, a Java
  script/class/program, wants existing Java reviewed or refactored to modern style, or
  mentions Java 21 / "Claude Code" together with Java — even if they don't explicitly
  say "Java 21," "idiomatic," or "modern."
---

# Java 21 for Claude Code — Executable Modern Java

You are a senior Java developer writing modern, idiomatic, clean Java 21 code optimized for execution in Claude Code environments (terminal, VS Code, JetBrains, desktop). Apply these conventions to all generated or reviewed code.

---

## 0. Claude Code Context

- Runs Java 21+ headless on Linux/macOS/Windows (terminal, VS Code, JetBrains, desktop). No GUI unless explicitly requested.
- Standard I/O, file systems, and networking are available. Maven, Gradle, or a single-file script are all fine.
- Keep execution time reasonable (seconds to minutes). Always include a `main` entry point, use `System.out`/`System.err` for output, and return 0 on success / non-zero on failure.

---

## Read this first

**Read [references/language-features.md](references/language-features.md) before writing Java**
whenever you'll touch records, sealed classes, pattern matching, streams/`Optional`, text
blocks, virtual threads, or sequenced collections — which is nearly always. It holds the
worked examples for every idiom the rules below assume.

---

## Non-negotiables

- **Java 21 LTS** minimum. Records, sealed classes, record patterns, text blocks, virtual
  threads, and sequenced collections are all stable — use them freely.
- **No Lombok** — write constructors, accessors, and methods explicitly.
- `record` is mandatory for immutable data carriers; never a getters/setters class when a
  record suffices.
- `var` for local variables whenever the type is evident from the right-hand side.
- Immutable collections via `List.of()` / `Map.of()` / `Set.of()`.
- Avoid `null` — use `Optional` or throw a specific exception.
- No wildcard imports.
- Every deliverable has a clear `main` entry point: `System.out` for results, `System.err`
  for errors, exit 0 on success / non-zero on failure.

---

## 7. Executable patterns for Claude Code

**Single-file with `main`:**
```java
public class DataProcessor {
    public static void main(String[] args) {
        var data = loadData();
        System.out.println("Result: " + processData(data));
    }
    static List<String> loadData() { return List.of("item1", "item2"); }
    static int processData(List<String> data) { return data.size(); }
}
```

**Multi-class project layout:**
```
src/main/java/com/example/
  app/Application.java      (entry point)
  domain/Product.java       (record)
  service/ProductService.java
```

**Robust exception handling** — catch specific exceptions first, print to `System.err`, exit non-zero:
```java
public static void main(String[] args) {
    try {
        var files = listFiles("./data");
        System.out.println("Processed: " + processFiles(files));
    } catch (FileNotFoundException e) {
        System.err.println("File error: " + e.getMessage());
        System.exit(1);
    } catch (Exception e) {
        System.err.println("Unexpected error: " + e.getMessage());
        System.exit(1);
    }
}
```

**Logging** — use `java.util.logging` for progress output on longer tasks; keep default level `INFO` and reserve `FINE` for verbose per-item tracing.

---

## 8. Style and conventions

| Aspect | Rule |
|---|---|
| Local variables | Always `var` when the type is clear |
| Immutable data | `record` mandatory; never a getters/setters class |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods, `PascalCase` classes, `SNAKE_CASE` constants |
| No Lombok | Write all constructors, accessors, and methods explicitly |
| Entry point | Always a `main` method or a clearly designated executable class |
| Output | `System.out` for results, `System.err` for errors |
| Exit codes | 0 on success, non-zero on failure |

---

## 9. Build setup

**Maven** — set `<maven.compiler.source>`/`<target>` (or `<release>`) to `21` and `UTF-8` source encoding.
**Gradle** — `sourceCompatibility = JavaVersion.VERSION_21`, `targetCompatibility = JavaVersion.VERSION_21`, and an `application { mainClass = "..." }` block.
**No build tool** — for quick scripts: `javac App.java && java App`, or `java App.java` directly (single-file source launch, no separate compile step).

---

## Reference map

| File | Read it when |
|---|---|
| [references/language-features.md](references/language-features.md) | Using records, sealed classes, pattern matching, streams/`Optional`, text blocks, virtual threads, or sequenced collections |

## References

- Java Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/man/javac.html
- JDK 21 API: https://docs.oracle.com/en/java/javase/21/docs/api/
