---
name: java21-claude-code
description: >
  Skill for writing modern Java 21 code in Claude Code environment. Use whenever the user
  asks to write, refactor, review, or generate Java code intended to run in Claude Code
  (terminal, VS Code, JetBrains, desktop). Covers var, functional programming (Streams,
  lambdas, Optional), records, sealed classes, pattern matching, text blocks, and
  executable patterns for Claude Code. No Lombok. Activate on any mention of Java
  language features or "Claude Code" with Java.
---

# Java 21 for Claude Code — Executable Modern Java

You are a senior Java developer writing modern, idiomatic, clean Java 21 code optimized for execution in Claude Code environments (terminal, VS Code, JetBrains, desktop). Apply these conventions to all generated or reviewed code.

---

## 0. Claude Code Context

**Environment**: Claude Code runs Java 21+ on Linux/macOS/Windows via terminal, VS Code, JetBrains, or desktop.

**Execution model**:
- Code runs **headless** (no GUI) in the Claude Code terminal by default.
- Standard I/O, file systems, and networking are available.
- Maven or Gradle can be used for dependency management; inline scripts are also fine.

**Key considerations**:
- Keep execution time reasonable (seconds to minutes, not hours).
- Use clear console output for results (System.out, logging).
- Avoid GUI frameworks unless explicitly requested.
- Include a `main` method as entry point (or multiple executables for multi-file projects).

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
    .toList();

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
2. **No special serialization is required** (frameworks requiring a no-arg constructor are exceptions).

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

// ❌ NEVER a class with getters/setters for immutable data
public class UserDTO {                                // ← forbidden
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

Use text blocks for multiline strings: SQL, JSON, HTML, configuration, queries.

```java
var sql = """
    SELECT u.id, u.name, u.email
    FROM users u
    WHERE u.active = true
      AND u.created_at > ?
    ORDER BY u.name
    """;

var json = """
    {
        "name": "Alice",
        "role": "admin"
    }
    """;
    
var markdown = """
    # Report
    
    Processing completed.
    - Items: %d
    - Success: %d
    - Failed: %d
    """.formatted(total, success, failed);
```

---

## 7. Executable patterns for Claude Code

### Pattern 1: Single-file executable with `main`
```java
public class DataProcessor {
    
    public static void main(String[] args) {
        System.out.println("Processing data...");
        
        var data = loadData();
        var result = processData(data);
        
        System.out.println("Result: " + result);
    }
    
    static List<String> loadData() {
        return List.of("item1", "item2", "item3");
    }
    
    static int processData(List<String> data) {
        return data.size();
    }
}
```

### Pattern 2: Multi-class project with clear module structure
```
src/
  main/java/
    com/example/
      app/
        Application.java      (entry point)
      domain/
        Product.java          (record)
      service/
        ProductService.java   (business logic)
```

Entry point:
```java
public class Application {
    public static void main(String[] args) {
        var service = new ProductService();
        var products = service.loadAll();
        products.forEach(System.out::println);
    }
}
```

### Pattern 3: Exception handling for robustness
```java
public class FileProcessor {
    
    public static void main(String[] args) {
        try {
            var files = listFiles("./data");
            var result = processFiles(files);
            System.out.println("✓ Complete. Processed: " + result);
        } catch (FileNotFoundException e) {
            System.err.println("✗ File error: " + e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("✗ Unexpected error: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    static List<Path> listFiles(String dir) throws FileNotFoundException {
        var path = Path.of(dir);
        if (!Files.exists(path))
            throw new FileNotFoundException("Directory not found: " + dir);
        
        try (var stream = Files.list(path)) {
            return stream.toList();
        } catch (IOException e) {
            throw new RuntimeException("Failed to list files", e);
        }
    }
    
    static int processFiles(List<Path> files) throws IOException {
        return (int) files.stream()
            .filter(f -> Files.isRegularFile(f))
            .count();
    }
}
```

### Pattern 4: Logging and progress output
```java
import java.util.logging.*;

public class LongRunningTask {
    
    private static final Logger LOGGER = Logger.getLogger(LongRunningTask.class.getName());
    
    public static void main(String[] args) {
        configureLogging();
        
        LOGGER.info("Starting task...");
        var items = List.of(1, 2, 3, 4, 5);
        
        var results = items.stream()
            .peek(i -> LOGGER.fine("Processing item: " + i))
            .map(LongRunningTask::processItem)
            .toList();
        
        LOGGER.info("✓ Complete. Processed " + results.size() + " items.");
    }
    
    static int processItem(int item) {
        return item * 2;
    }
    
    static void configureLogging() {
        var handler = new ConsoleHandler();
        handler.setLevel(Level.INFO);
        LOGGER.addHandler(handler);
        LOGGER.setLevel(Level.INFO);
    }
}
```

---

## 8. Style and conventions

| Aspect | Rule |
|---|---|
| Local variables | Always `var` when the type is clear |
| Immutable data | `record` mandatory; never a class with getters/setters |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods, `PascalCase` classes, `SNAKE_CASE` constants |
| No Lombok | Write all constructors, accessors, and methods explicitly |
| Entry point | Always include a `main` method or clearly designate the executable class |
| Output | Use `System.out` for results, `System.err` for errors |
| Exit codes | Return 0 on success, non-zero on failure |

---

## 9. Dependencies and build

### Maven (simple projects)
```xml
<project>
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>myapp</artifactId>
    <version>1.0</version>
    
    <properties>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>
    
    <dependencies>
        <!-- Add dependencies here -->
    </dependencies>
    
    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>21</source>
                    <target>21</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

### Gradle (alternative)
```gradle
plugins {
    id 'java'
    id 'application'
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

application {
    mainClass = "com.example.Application"
}

repositories {
    mavenCentral()
}

dependencies {
    // Add dependencies here
}
```

### Single-file execution (no build tool)
For simple scripts, save as `App.java` and run:
```bash
javac App.java
java App
```

---

## 10. Final notes

- **Minimum version**: Java 21 LTS.
- **No Lombok**: Do not use any Lombok annotation. Always write constructors, accessors, and methods explicitly.
- **Records, sealed classes, pattern matching, and text blocks** are stable since Java 16–21 — use them freely.
- **Claude Code execution**: Code must have a clear entry point (`main` method) and produce output via `System.out` or logs.
- **For more info on Claude Code**: https://docs.anthropic.com/en/docs/claude-code/overview

---

## References

- Java Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/man/javac.html
- JDK 21 API: https://docs.oracle.com/en/java/javase/21/docs/api/
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview