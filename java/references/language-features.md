# Java 21 language features

Reference for the modern Java 21 idioms this skill mandates: `var`, records, sealed classes,
pattern matching (including record patterns), functional style, text blocks, virtual threads,
and sequenced collections. `SKILL.md` carries the non-negotiables; the examples live here.
Section numbers (§1–§6) are kept from the original SKILL.md.

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
