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

## 1. Variable declaration — `var` first

Use `var` for local variables whenever the type is evident from the right-hand side.

```java
var list    = new ArrayList<String>();
var result  = stream.collect(Collectors.toList());
var product = repository.findById(id).orElseThrow();

for (var entry : map.entrySet()) { ... }
try (var connection = dataSource.getConnection()) { ... }
```

**Don't use `var`** for method parameters/fields (not legal in Java) or when the inferred type isn't obvious to a reader — prefer an explicit type there for clarity.

---

## 2. Records — immutable value objects (MANDATORY)

Use `record` for any immutable value object, DTO, or result when: (1) it never needs mutation after creation, and (2) no special serialization requires a no-arg constructor. **Never** write a getters/setters class when a record suffices.

```java
public record Point(int x, int y) {}

public record UserDTO(Long id, String name, String email) {
    public static UserDTO from(User u) {
        return new UserDTO(u.getId(), u.getName(), u.getEmail());
    }
}

// Compact constructor for validation
public record PositiveAmount(BigDecimal value) {
    public PositiveAmount {
        if (value.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("Amount must be positive");
    }
}
```

| Situation | Type to use |
|---|---|
| Immutable data carrier | `record` |
| Needs mutation after construction | class |
| Framework requires no-arg constructor | class |
| Mandatory inheritance from a class | class |

---

## 3. Sealed classes & pattern matching

Use sealed interfaces/classes for a fixed, closed set of subtypes, then handle them exhaustively with pattern matching — no `default` branch needed since the compiler verifies coverage.

```java
public sealed interface Shape permits Shape.Circle, Shape.Rectangle, Shape.Triangle {
    record Circle(double radius)                  implements Shape {}
    record Rectangle(double width, double height) implements Shape {}
    record Triangle(double base, double height)   implements Shape {}
}

double area = switch (shape) {
    case Shape.Circle c    -> Math.PI * c.radius() * c.radius();
    case Shape.Rectangle r -> r.width() * r.height();
    case Shape.Triangle t  -> 0.5 * t.base() * t.height();
};
```

**`instanceof` pattern matching** — avoid manual casts:
```java
if (obj instanceof String s) System.out.println(s.length());
```

**Record patterns (Java 21)** — deconstruct records directly in `instanceof`/`switch`, including nested records:
```java
record Point(int x, int y) {}
record Line(Point start, Point end) {}

if (shape instanceof Line(Point(var x1, var y1), Point(var x2, var y2))) {
    System.out.println("From (%d,%d) to (%d,%d)".formatted(x1, y1, x2, y2));
}

String describe = switch (obj) {
    case Integer i               -> "Integer: " + i;
    case String s                -> "String of length " + s.length();
    case Point(var x, var y)     -> "Point at " + x + "," + y;
    case null                    -> "null";
    default                      -> "Other: " + obj.getClass().getSimpleName();
};
```

---

## 4. Functional programming — when and how

Apply functional style when it clarifies data transformations; don't force it on trivial flows or logic with complex checked exceptions.

```java
var names = employees.stream()
    .filter(Employee::active)
    .map(Employee::name)
    .sorted()
    .toList();

var byDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::department));

// Optional — never call get() without checking presence
var name = repo.findById(id).map(User::name).orElse("Anonymous");

list.forEach(System.out::println);
stream.filter(Objects::nonNull).map(String::toUpperCase);
```

Prefer imperative style for step-by-step debugging needs or hot paths where `IntStream`/`LongStream` primitives matter more than readability.

---

## 5. Text blocks

Use for multiline strings — SQL, JSON, HTML, config.

```java
var sql = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
    ORDER BY u.name
    """;

var report = """
    # Report
    - Items: %d
    - Success: %d
    """.formatted(total, success);
```

---

## 6. Virtual threads & sequenced collections (Java 21)

**Virtual threads** — finalized in Java 21. Prefer them over platform-thread pools for I/O-bound, high-concurrency workloads (thousands of blocking tasks):
```java
try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
    var futures = urls.stream()
        .map(url -> executor.submit(() -> fetch(url)))
        .toList();
    var results = futures.stream().map(Future::join).toList();
}
```
Keep using fixed platform-thread pools for CPU-bound work; virtual threads help when threads mostly block on I/O.

**Sequenced collections** — `List`, `Set`, `Map` (via `SequencedCollection`/`SequencedMap`) now expose defined-order access without boilerplate:
```java
var list = new ArrayList<>(List.of(1, 2, 3));
list.getFirst();       // 1
list.getLast();        // 3
list.reversed();       // view, not a copy
```

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

## 10. Final notes

- **Minimum version**: Java 21 LTS.
- **No Lombok**: write constructors, accessors, and methods explicitly.
- Records, sealed classes, pattern matching (including record patterns), text blocks, virtual threads, and sequenced collections are all stable in Java 21 — use them freely.
- Every deliverable needs a clear entry point (`main`) and output via `System.out`/logs.

## References

- Java Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/man/javac.html
- JDK 21 API: https://docs.oracle.com/en/java/javase/21/docs/api/
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview