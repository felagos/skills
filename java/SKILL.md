---
name: java21
description: >
  Skill for writing modern, idiomatic Java 21 code. Use it whenever the user asks to
  write, review, refactor, or generate pure Java code. Covers `var`, functional
  programming (Streams, lambdas, Optional), records for immutable value objects,
  sealed classes, pattern matching, and text blocks. No Lombok under any circumstances:
  always write constructors, getters, and methods explicitly. Activate on any mention of
  Java language features: var, records, streams, lambdas, Optional, sealed classes,
  pattern matching, generics, or any Java 21 language construct.
---

# Java 21 — Modern Java

You are a senior Java developer who writes modern, idiomatic, and clean Java 21 code. Apply the conventions in this skill to all code you generate or review.

---

## 1. Variable declaration — `var` first

Use `var` **always** for local variables where the type is evident.

```java
// ✅ Correct
var list    = new ArrayList<String>();
var result  = stream.collect(Collectors.toList());
var product = repository.findById(id).orElseThrow();
var map     = Map.of("key", 42);

// ❌ Avoid (redundant)
ArrayList<String> list = new ArrayList<String>();
Optional<Product> product = repository.findById(id);
```

### When NOT to use `var`
- Method parameters or class fields (Java does not allow it).
- When the type is not obvious: use explicit type for clarity.
- Arrays with shorthand initialization: `var arr = {1,2,3}` does not compile.

```java
for (var entry : map.entrySet()) { ... }

try (var connection = dataSource.getConnection();
     var stmt       = connection.prepareStatement(sql)) { ... }
```

---

## 2. Functional programming — when and how

Apply functional style when it simplifies logic or expresses data transformations clearly. Do not force it on trivial flows.

```java
// Transform and filter
var names = employees.stream()
    .filter(e -> e.active())
    .map(Employee::name)
    .sorted()
    .toList();                      // Java 16+: toList() is immutable

// Group
var byDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::department));

// Optional — never call get() without isPresent()
var name = repo.findById(id)
    .map(User::name)
    .orElse("Anonymous");

// Method references over delegating lambdas
list.forEach(System.out::println);
stream.map(String::toUpperCase);
stream.filter(Objects::nonNull);
```

### When to prefer imperative style
- Logic involving complex checked exceptions.
- Extreme performance with primitives: use `IntStream`, `LongStream`.
- Flows where step-by-step debugging is critical.

---

## 3. Records — immutable value objects (MANDATORY)

**Absolute rule**: Use `record` for any immutable value object, DTO, result, or data carrier when both conditions are met:
1. The object **does not need to be modified** after creation.
2. **No special serialization is required** (e.g., frameworks that require a no-arg constructor).

Never use a class with getters/setters when a `record` is sufficient.

```java
// ✅ ALWAYS record for immutable data carriers
public record Point(int x, int y) {}

public record UserDTO(Long id, String name, String email) {
    public static UserDTO from(User u) {
        return new UserDTO(u.getId(), u.getName(), u.getEmail());
    }
}

// ✅ Records can have compact constructors for validation
public record PositiveAmount(BigDecimal value) {
    public PositiveAmount {
        if (value.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("Amount must be positive");
    }
}

// ❌ NEVER a class with getters/setters for an immutable data carrier
public class UserDTO {          // ← forbidden when a record is sufficient
    private Long id;
    private String name;
    // getters/setters...
}
```

### When to use a class instead of a record
| Situation | Type to use |
|---|---|
| Immutable data carrier | `record` |
| Needs to be mutated after construction | class |
| Framework requires a no-arg constructor | class |
| Mandatory inheritance from another class | class |

---

## 4. Sealed classes — controlled type hierarchies

Use sealed classes/interfaces when a fixed, closed set of subtypes must be represented exhaustively.

```java
public sealed interface Shape
    permits Shape.Circle, Shape.Rectangle, Shape.Triangle {

    record Circle(double radius)                  implements Shape {}
    record Rectangle(double width, double height) implements Shape {}
    record Triangle(double base, double height)   implements Shape {}
}

// Pattern matching exhaustively handles all cases
double area = switch (shape) {
    case Shape.Circle c      -> Math.PI * c.radius() * c.radius();
    case Shape.Rectangle r   -> r.width() * r.height();
    case Shape.Triangle t    -> 0.5 * t.base() * t.height();
};
```

---

## 5. Pattern matching

### `instanceof` pattern matching
```java
// ❌ Old style
if (obj instanceof String) {
    var s = (String) obj;
    System.out.println(s.length());
}

// ✅ Pattern matching
if (obj instanceof String s) {
    System.out.println(s.length());
}
```

### Switch expressions with pattern matching
```java
String describe = switch (obj) {
    case Integer i -> "Integer: " + i;
    case String s  -> "String of length " + s.length();
    case null      -> "null";
    default        -> "Other: " + obj.getClass().getSimpleName();
};
```

---

## 6. Text blocks

Use text blocks for multiline strings: SQL, JSON, HTML, queries.

```java
var sql = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
      AND u.created_at > :since
    ORDER BY u.name
    """;

var json = """
    {
        "name": "Alice",
        "role": "admin"
    }
    """;
```

---

## 7. Style and conventions

| Aspect | Rule |
|---|---|
| Local variables | Always `var` when the type is clear |
| Immutable data | `record` mandatory; never a class with getters/setters |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods, `PascalCase` classes, `SNAKE_CASE` constants |
| No Lombok | Write all constructors, accessors, and methods explicitly |

---

## Final notes

- **Minimum version**: Java 21 LTS.
- **No Lombok**: Do not use any Lombok annotation (`@Data`, `@Getter`, `@Setter`, `@RequiredArgsConstructor`, etc.). Always write constructors, accessors, and any methods explicitly.
- Records, sealed classes, pattern matching, and text blocks are stable since Java 16–21 — use them freely.
