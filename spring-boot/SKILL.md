---
name: spring-boot-claude-code
description: >
  Skill for writing executable Spring Boot applications with Java 21 in Claude Code
  using Clean / Hexagonal Architecture. Domain layer holds pure objects and repository
  port interfaces. Application layer holds use cases (one per operation) depending only
  on domain. Infrastructure holds a web adapter (controller, DTOs, WebMapper) and a
  persistence adapter (JPA entity, JpaRepository, PersistenceMapper, RepositoryAdapter).
  DTOs never cross into application/domain. JPA entities never leave persistence. Uses
  Gradle (not Maven) for Claude Code terminal execution, Log4j2 for logging, and always
  asks the user which database to target before scaffolding persistence. No Lombok.
  Constructor injection always. Records for immutable types. Activate on Spring Boot,
  Spring, use case, service, controller, repository, entity, REST, JPA, clean
  architecture, hexagonal, or any JVM backend task in Claude Code.
---

# Spring Boot + Java 21 for Claude Code — Clean / Hexagonal Architecture

You are a senior Java developer writing modern, executable Spring Boot applications using
Java 21 with strict Clean Architecture in Claude Code environments (terminal, VS Code,
JetBrains, desktop). Apply every convention in this skill to all code you generate or review.

For the full runnable reference project (domain, use cases, web adapter, persistence
adapter, tests — all wired together for a `Product` resource), see
`./complete-example.md`. Read it when scaffolding a new project or when you need
a concrete pattern to copy; this file covers the rules, decisions, and build/logging setup.

---

## 0. Before you write any code: ask about the database

**Never default to H2 silently.** Before scaffolding the persistence adapter (or the
whole project), ask the user which database they want:

- **H2 (in-memory)** — zero setup, resets on restart. Best for demos, katas, quick tests.
- **PostgreSQL** — production-like, needs a running instance or Docker.
- **MySQL / MariaDB** — same tradeoffs as Postgres.
- **"Just get something running"** — default to H2 only if the user explicitly says this
  or equivalent; state that you're defaulting to H2 and that it's swappable later.

The answer changes: the JDBC driver dependency in `build.gradle`, the
`spring.datasource.*` properties, and `spring.jpa.hibernate.ddl-auto` (H2 demos are fine
with `create-drop`; anything persistent should use `validate` or a migration tool like
Flyway instead — mention this tradeoff if the user picks Postgres/MySQL).

---

## Architecture overview

```
src/main/java/com/example/
├── domain/
│   ├── model/Product.java                        ← pure domain object (no framework)
│   └── repository/ProductRepository.java         ← repository port (interface)
│
├── application/
│   ├── usecase/
│   │   ├── CreateProductUseCase.java
│   │   ├── FindProductUseCase.java
│   │   └── DeleteProductUseCase.java
│   └── exception/ResourceNotFoundException.java
│
└── infrastructure/
    ├── web/
    │   ├── controller/ProductController.java
    │   ├── controller/GlobalExceptionHandler.java
    │   ├── dto/{CreateProductRequest,ProductResponse}.java
    │   └── mapper/ProductWebMapper.java
    └── persistence/
        ├── entity/ProductEntity.java
        ├── repository/{ProductJpaRepository,ProductRepositoryAdapter}.java
        └── mapper/ProductPersistenceMapper.java

src/main/resources/
├── application.properties     ← Spring Boot config (datasource, JPA)
└── log4j2.xml                 ← logging config

build.gradle                   ← Gradle config (Spring Boot 3.x + Java 21)
```

**Layer rules (never break these):**

| Layer | Knows about | Must NOT know about |
|---|---|---|
| `domain` | itself | Spring, JPA, DTOs |
| `application` | domain | Spring web, JPA, DTOs, HTTP |
| `infrastructure/web` | domain, application use cases | JPA, entities |
| `infrastructure/persistence` | domain, JPA | DTOs, use cases, controllers |

`application` may use Spring's `@Component`/`@Transactional` for wiring, but never imports
`jakarta.persistence.*`, DTO classes, or servlet/HTTP types.

---

## 1. Claude Code context for Spring Boot

- Embedded Tomcat listening on `localhost:8080` (or configured port).
- Application lifecycle: start → handle requests → graceful shutdown (`Ctrl+C`).
- Logging via SLF4J + **Log4j2**, console output only (see §3).
- Single-instance, stateless: each run is isolated.
- Execution: `./gradlew bootRun` in the terminal.

**Common execution patterns:**
1. **Simple REST API demo** — single aggregate, 3–4 endpoints.
2. **CLI data processor** — Spring Boot app that reads input and produces output, no web server.
3. **Scheduled task** — `@Scheduled` for batch processing.
4. **Integration test** — full stack under `@SpringBootTest`.

---

## 2. Gradle — build.gradle (Spring Boot 3.x + Java 21)

Gradle is the default build tool for this skill — do not generate a `pom.xml` unless the
user explicitly asks for Maven.

```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.3.0'
    id 'io.spring.dependency-management' version '1.1.4'
}

group = 'com.example'
version = '1.0.0'
sourceCompatibility = '21'

repositories {
    mavenCentral()
}

configurations {
    // Exclude the default Logback so Log4j2 is the only logging backend
    all*.exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'

    // Pick ONE based on the answer from §0 — do not include more than the chosen driver
    runtimeOnly 'com.h2database:h2'                       // H2 (in-memory)
    // runtimeOnly 'org.postgresql:postgresql'             // PostgreSQL
    // runtimeOnly 'com.mysql:mysql-connector-j'           // MySQL

    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}

tasks.named('test') {
    useJUnitPlatform()
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

**Run:**
```bash
./gradlew bootRun
# → Server starts on http://localhost:8080
```

**Build JAR and run:**
```bash
./gradlew build
java -jar build/libs/my-app-1.0.0.jar
```

**Test:**
```bash
./gradlew test
```

> If the user specifically asks for Maven, it works the same way conceptually
> (`spring-boot-starter-parent`, same dependency list minus the Logback exclusion —
> use `<exclusions>` on `spring-boot-starter` instead — plus `spring-boot-maven-plugin`),
> but Gradle is the default output for this skill.

---

## 3. Logging — Log4j2, not the Spring Boot default

Spring Boot ships with Logback by default. This skill always swaps it for **Log4j2**:
exclude `spring-boot-starter-logging` (done above) and add `spring-boot-starter-log4j2`.
Application code still uses the SLF4J API (`org.slf4j.Logger`/`LoggerFactory`) — only the
backend changes, so use-case and controller code never imports Log4j2 classes directly.

`src/main/resources/log4j2.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="%d{yyyy-MM-dd HH:mm:ss} [%-5level] %logger{36} - %msg%n"/>
        </Console>
    </Appenders>
    <Loggers>
        <Logger name="com.example" level="debug" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Root level="info">
            <AppenderRef ref="Console"/>
        </Root>
    </Loggers>
</Configuration>
```

Usage in code:
```java
private static final Logger log = LoggerFactory.getLogger(CreateProductUseCase.class);
log.info("Created product {}", product.id());
```

---

## 4. application.properties — datasource + JPA

Fill in `spring.datasource.*` based on the database chosen in §0. H2 example:

```properties
server.port=8080

# Database — swap this block per the answer from §0
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=false

spring.application.name=My Spring Boot App
```

For PostgreSQL/MySQL: use the real JDBC URL/credentials, the matching dialect, and prefer
`spring.jpa.hibernate.ddl-auto=validate` (with a schema migration tool) over `create-drop`
once data needs to persist across restarts — flag this to the user rather than silently
using `create-drop` in a non-demo context.

---

## 5. Domain layer — pure Java, zero framework dependencies

Immutable data → `record`. Mutable aggregate with behavior → `class`. Repository ports are
plain interfaces with no Spring/JPA annotations. See `./complete-example.md` §1
for the full `Product`/`Order`/`ProductRepository` code.

## 6. Application layer — use cases

One `@Component` class per use case, constructor injection, `@Transactional` on writes and
`@Transactional(readOnly = true)` on reads. Never import DTOs, JPA entities, or HTTP types
here. **Watch imports carefully** — `ResourceNotFoundException` lives in
`application.exception`; use cases in `application.usecase` that throw it must import it
explicitly. See `./complete-example.md` §2 for full use case code.

## 7. Infrastructure — web adapter

Controller depends only on use cases + a `WebMapper`; DTOs are `record`s with Bean
Validation annotations (`@NotBlank`, `@Positive`, etc. — now functional since
`spring-boot-starter-validation` is included). `GlobalExceptionHandler` must handle **both**
`ResourceNotFoundException` → 404 **and** `MethodArgumentNotValidException` → 400 with
field-level detail; don't let validation failures fall through to the generic 500 handler.
See `./complete-example.md` §3 for full controller + exception handler code.

## 8. Infrastructure — persistence adapter

JPA entity, package-private `JpaRepository` interface, `PersistenceMapper`, and a
`RepositoryAdapter implements <DomainPort>`. Entities never leave this package. See
`./complete-example.md` §4 for the full code.

---

## 9. Style and conventions

| Aspect | Rule |
|---|---|
| Domain model | No Spring/JPA annotations; `record` if immutable, class if mutable |
| Repository port | Interface in `domain/repository/`; no `@Repository` |
| Use cases | One `@Component` class per use case, `execute()` method |
| DTOs | `record` in `infrastructure/web/dto/`; never cross boundaries |
| JPA Entities | Class in `infrastructure/persistence/entity/`; never leave persistence |
| WebMapper | `@Component` in `infrastructure/web/mapper/`; DTO ↔ domain |
| PersistenceMapper | `@Component` in `infrastructure/persistence/mapper/`; domain ↔ entity |
| JpaRepository | `package-private` in `infrastructure/persistence/repository/` |
| Injection | Constructor only, `final` fields, no `@Autowired` |
| Transactions | `@Transactional` on use case write methods; `readOnly=true` on reads |
| Validation | Bean Validation on DTOs + `spring-boot-starter-validation`; handle `MethodArgumentNotValidException` |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods, `PascalCase` classes, `SNAKE_CASE` constants |
| Logging | SLF4J API backed by **Log4j2** (never Logback) |
| Build tool | **Gradle** by default; Maven only if explicitly requested |
| Database | **Ask before scaffolding** — never assume H2 silently |
| Exit behavior | Graceful shutdown on Ctrl+C; no explicit `System.exit()` unless error |

---

## Final notes

- **Minimum version**: Java 21 LTS + Spring Boot 3.3+.
- **No Lombok**: write all constructors, getters, and methods explicitly.
- **Layer isolation**: strictly enforced — DTOs never in domain/application, entities never outside persistence.
- **Logging**: Log4j2 via `spring-boot-starter-log4j2`, Logback excluded.
- **Build**: Gradle (`./gradlew bootRun`) is the default; mention Maven only on request.
- **Database**: ask the user before generating persistence code (see §0).

## References

- `./complete-example.md` — full runnable `Product` CRUD example (domain, use cases, web adapter, persistence adapter, unit + integration tests) with all layers wired together correctly.
- Spring Boot Docs: https://docs.spring.io/spring-boot/docs/current/reference/html/
- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Log4j2 Spring Boot integration: https://docs.spring.io/spring-boot/reference/features/logging.html
- Java 21 Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview