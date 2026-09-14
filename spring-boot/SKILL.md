---
name: spring-boot
description: >
  Skill for writing executable Spring Boot applications with Java 21 in Claude Code
  using Clean / Hexagonal Architecture, including the Spring Data JPA persistence layer.
  Domain layer holds pure objects and repository port interfaces. Application layer holds
  use cases (one per operation) depending only on domain. Infrastructure holds a web
  adapter (controller, DTOs, WebMapper) and a persistence adapter (JPA entity,
  JpaRepository, PersistenceMapper, RepositoryAdapter). DTOs never cross into
  application/domain. JPA entities never leave persistence. Covers entity conventions
  (no setters, protected no-arg constructor, create/reconstitute factories), N+1
  prevention (LEFT JOIN FETCH, @EntityGraph, batch fetch size, projections), pagination (OFFSET vs keyset),
  batch inserts, and schema.sql-owned DDL. Uses Gradle (not Maven), Log4j2 for logging,
  and always asks the user which database to target before scaffolding persistence.
  No Lombok. Constructor injection always. Records for immutable types. Activate on
  Spring Boot, Spring, use case, service, controller, repository, entity, REST, JPA,
  Hibernate, query, N+1, projection, pagination, batch insert, clean architecture,
  hexagonal, or any JVM backend task in Claude Code — even if the user only mentions
  "database" or "query performance" without naming JPA explicitly.
---

# Spring Boot + Java 21 for Claude Code — Clean / Hexagonal Architecture + JPA

You are a senior Java developer writing modern, executable Spring Boot applications using
Java 21 with strict Clean Architecture and production-grade Spring Data JPA in Claude Code
environments (terminal, VS Code, JetBrains, desktop). Apply every convention in this skill
to all code you generate or review.

Reference files — read them when scaffolding or when you need a concrete pattern to copy:
- `./complete-example.md` — full runnable `Product` CRUD project (domain, use cases, web
  adapter, persistence adapter, tests) with all layers wired together.
- `./entities-and-repositories.md` — `Order` aggregate entities, JPA repositories, mapper,
  N+1 prevention, pagination, batching, and `@DataJpaTest` code.

This file covers the rules, decisions, build/logging setup, and JPA config — read it fully
before generating code.

---

## 0. Before you write any code: ask about the database

**Never default to H2 silently.** Before scaffolding the persistence adapter (or the
whole project), ask the user which database they want:

- **H2 (in-memory)** — zero setup, resets on restart. Best for demos, katas, quick tests.
- **PostgreSQL** — production-like, needs a running instance or Docker.
- **MySQL / MariaDB** — same tradeoffs as Postgres.
- **"Just get something running"** — default to H2 only if the user explicitly says this
  or equivalent; state that you're defaulting to H2 and that it's swappable later.

The answer changes: the JDBC driver dependency in `build.gradle` (§2), the
`spring.datasource.*` properties and `ddl-auto` (§4), and the column types in `schema.sql`
(§5): H2's `CHAR(36)` for UUIDs becomes Postgres's native `uuid` type or MySQL's
`BINARY(16)`/`CHAR(36)`, and `AUTO_INCREMENT` becomes `GENERATED ALWAYS AS IDENTITY` /
`SERIAL` on Postgres.

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
├── schema.sql                 ← DDL, single source of truth
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
- Query debugging via SQL logging in `application.properties` (§4) — a `logging.level.*`
  property, not tied to the logging backend.
- Single-instance, stateless: each run is isolated.
- Execution: `./gradlew bootRun`; tests: `./gradlew test`.
- Persistence tests use `@DataJpaTest` for fast slice testing without the full context.

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

## 4. application.properties — datasource, JPA, batching, SQL logging

Fill in `spring.datasource.*` based on the database chosen in §0. H2 example:

```properties
server.port=8080
spring.application.name=My Spring Boot App

# Database — swap this block per the answer from §0
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate — ddl-auto=none because schema.sql (§5) is the source of truth.
# Never combine schema.sql with create-drop/update: Hibernate's auto-DDL and schema.sql
# both try to create the same tables and collide on startup ("table already exists").
spring.jpa.hibernate.ddl-auto=none
spring.sql.init.mode=always
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
spring.jpa.properties.hibernate.use_sql_comments=true

# N+1 guards. OSIV off: lazy loading outside the use-case transaction fails loudly
# instead of silently firing extra SELECTs. Batch fetch: any lazy collection not
# fetch-joined (e.g. paged queries) loads in 1 + ceil(N/50) queries, not 1 + N.
spring.jpa.open-in-view=false
spring.jpa.properties.hibernate.default_batch_fetch_size=50

# Batching (for bulk inserts — see entities-and-repositories.md §7 for the IDENTITY caveat)
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true

# SQL logging — watch for N+1 (many SELECTs in a loop) and deep OFFSETs
logging.level.com.example=DEBUG
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.type.descriptor.sql=TRACE

# H2 console (optional, disabled for Claude Code)
spring.h2.console.enabled=false
```

**For production (PostgreSQL)**, change:
```properties
spring.datasource.url=jdbc:postgresql://localhost:5432/mydb
spring.datasource.driverClassName=org.postgresql.Driver
spring.datasource.username=postgres
spring.datasource.password=secret
spring.jpa.database-platform=org.hibernate.dialect.PostgreSQLDialect
spring.jpa.hibernate.ddl-auto=validate
```
`validate` (not `none`) in production so Hibernate fails fast if the entities and the
real schema (managed by a migration tool like Flyway, not `schema.sql`) drift apart.

Only if there is no persistence layer yet (no `schema.sql`), a quick H2 demo may use
`spring.jpa.hibernate.ddl-auto=create-drop` instead — say so explicitly rather than leaving
it unset.

---

## 5. schema.sql — single source of truth for DDL

```sql
-- src/main/resources/schema.sql
-- Runs on startup because spring.sql.init.mode=always; ddl-auto=none so Hibernate
-- does NOT also try to generate this schema.

CREATE TABLE IF NOT EXISTS orders (
    id CHAR(36) NOT NULL PRIMARY KEY,
    customer_email VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    order_id CHAR(36) NOT NULL,
    product_id CHAR(36) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS products (
    id CHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    category_id CHAR(36),
    created_at TIMESTAMP NOT NULL
);

-- Indexes for common queries (including the composite index keyset pagination needs —
-- Hibernate's auto-DDL would never generate this one, which is why schema.sql owns DDL here)
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_orders_keyset ON orders(status, created_at DESC, id DESC);
```

---

## 6. Domain layer — pure Java, zero framework dependencies

Immutable data → `record`. Mutable aggregate with behavior → `class`. Repository ports are
plain interfaces with no Spring/JPA annotations. Aggregate ids are `UUID`, generated in
application code. See `./complete-example.md` §1 for the full `Product`/`Order`/
`ProductRepository` code.

## 7. Application layer — use cases

One `@Component` class per use case, constructor injection, `@Transactional` on writes and
`@Transactional(readOnly = true)` on reads — transactions live here, never on repositories.
Never import DTOs, JPA entities, or HTTP types here. **Watch imports carefully** —
`ResourceNotFoundException` lives in `application.exception`; use cases in
`application.usecase` that throw it must import it explicitly. See `./complete-example.md`
§2 for full use case code.

## 8. Infrastructure — web adapter

Controller depends only on use cases + a `WebMapper`; DTOs are `record`s with Bean
Validation annotations (`@NotBlank`, `@Positive`, etc. — functional since
`spring-boot-starter-validation` is included). `GlobalExceptionHandler` must handle **both**
`ResourceNotFoundException` → 404 **and** `MethodArgumentNotValidException` → 400 with
field-level detail; don't let validation failures fall through to the generic 500 handler.
See `./complete-example.md` §3 for full controller + exception handler code.

## 9. Infrastructure — persistence adapter

JPA entity, package-private `JpaRepository` interface, `PersistenceMapper`, and a
`RepositoryAdapter implements <DomainPort>`. Entities live **only** in
`infrastructure/persistence/entity/` and never leave this package. See
`./complete-example.md` §4 for the `Product` adapter.

### Entity conventions (no Lombok, explicit)

- One `public` top-level type per `.java` file — an entity and its enum are **separate
  files** (`OrderEntity.java`, `OrderStatus.java`), never combined.
- `protected` no-arg constructor only (JPA requirement); no `public` constructor exposed.
- **No setters.** Mutation happens through named behavior methods (`confirm()`, `cancel()`,
  `addItem()`) that also enforce invariants — never a generic `setStatus()`.
- Two static factories per aggregate root: `create(...)` for brand-new entities (generates
  id + timestamps) and a `reconstitute(...)` factory used only by the persistence mapper to
  rebuild an entity from domain data (preserves the original id/timestamps — the piece
  that's easy to forget, see `./entities-and-repositories.md` §1–§2).
- `@Enumerated(EnumType.STRING)` always, never `ORDINAL` (reordering the enum would silently
  corrupt existing rows).
- `@ManyToOne(fetch = FetchType.LAZY)` always; `@OneToMany` defaults to LAZY already but
  state it explicitly for readability.
- `orphanRemoval = true` on owning `@OneToMany` collections that should delete children when
  removed from the collection.

### Reference map — `./entities-and-repositories.md`

- **§1–§2**: `OrderEntity`/`OrderItemEntity`/`ProductEntity` with `create()`/`reconstitute()`.
- **§3**: package-private `JpaRepository` interfaces, `@Query`/`@EntityGraph`, keyset query,
  interface projection, and the `RepositoryAdapter` implementing the domain port.
- **§4**: N+1 prevention (LEFT JOIN FETCH, @EntityGraph, batch fetch size for paged
  collections, OSIV, interface vs. DTO projections).
- **§5**: the entity↔domain mapper — the piece most drafts get wrong.
- **§6**: OFFSET vs. keyset pagination.
- **§7**: batch inserts and the `GenerationType.IDENTITY` gotcha.
- **§8**: `@DataJpaTest` slice tests, including a query-count test (Hibernate `Statistics`)
  that fails if a read path regresses to N+1.

**Rule**: the mapper calls `getItems()`, so **every** read path in the adapter must fetch
the collection — `LEFT JOIN FETCH`/`@EntityGraph` when unpaged, `default_batch_fetch_size`
when paged — or it is N+1.

**The #1 mapper gotcha**: because entities have no setters, a naive `toEntity(domain)` that
does `new OrderEntity()` and returns it immediately compiles fine but silently produces an
entity with every field `null` — which then fails on save with `NOT NULL` constraint
violations (or worse, succeeds with garbage data if the columns happen to be nullable).
Always route entity reconstruction through the aggregate's `reconstitute(...)` factory, and
convert domain ↔ entity enums explicitly (`DomainStatus.valueOf(entity.getStatus().name())`)
— they are deliberately two different enum types even when the constant names match, so the
persistence layer never leaks its enum into the domain.

---

## 10. Style and conventions

| Aspect | Rule |
|---|---|
| Domain model | No Spring/JPA annotations; `record` if immutable, class if mutable |
| Repository port | Interface in `domain/repository/`; no `@Repository` |
| Use cases | One `@Component` class per use case, `execute()` method |
| DTOs | `record` in `infrastructure/web/dto/`; never cross boundaries |
| JPA Entities | Class in `infrastructure/persistence/entity/`; never leave persistence |
| WebMapper | `@Component` in `infrastructure/web/mapper/`; DTO ↔ domain |
| PersistenceMapper | `@Component` in `infrastructure/persistence/mapper/`; domain ↔ entity via `reconstitute()` |
| JpaRepository | `package-private` in `infrastructure/persistence/repository/` |
| ID type (aggregate roots) | `UUID`, never auto-increment `Long` |
| ID type (child/internal entities) | `Long`/`IDENTITY` acceptable *only* if never bulk-inserted and never queried by id outside its parent |
| Entity constructor | Protected no-arg only; `create()` + `reconstitute()` factories |
| Entity setters | Never; use behavior methods |
| Enums | `@Enumerated(EnumType.STRING)`, never `ORDINAL` |
| Entity collections | Initialize inline: `= new ArrayList<>()`; never null |
| Lazy loading | `@ManyToOne(fetch = LAZY)` always; `@OneToMany(fetch = LAZY)` default |
| Orphans | `@OneToMany(..., orphanRemoval = true)` to clean children |
| Files | One public top-level type per `.java` file — entity and its enum are separate files |
| N+1 fix | Unpaged: `LEFT JOIN FETCH` or `@EntityGraph`; paged: `default_batch_fetch_size` (never fetch-join a collection with `Pageable`); projections for read-only views; `open-in-view=false` |
| Projections | Interface-based for plain property reads; record/DTO-based when the query computes a value (e.g. `SIZE(...)`) |
| Pagination | Use `Pageable` always; switch to keyset on deep pages |
| Batching | Enable `hibernate.jdbc.batch_size`; avoid `GenerationType.IDENTITY` on bulk-inserted entities |
| DDL | One source of truth: `schema.sql` + `ddl-auto=none`, or entities + `ddl-auto=create-drop` — never both |
| Injection | Constructor only, `final` fields, no `@Autowired` |
| Transactions | `@Transactional` on use case write methods; `readOnly=true` on reads; never on repositories |
| Validation | Bean Validation on DTOs + `spring-boot-starter-validation`; handle `MethodArgumentNotValidException` |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods/getters, `PascalCase` classes/entities, `SNAKE_CASE` constants and columns |
| Logging | SLF4J API backed by **Log4j2** (never Logback) |
| Build tool | **Gradle** by default; Maven only if explicitly requested |
| Database | **Ask before scaffolding** — never assume H2 silently |
| Exit behavior | Graceful shutdown on Ctrl+C; no explicit `System.exit()` unless error |

---

## 11. JPA gotchas

| Problem | Solution |
|---|---|
| N+1 queries | `LEFT JOIN FETCH` or `@EntityGraph` on every read path the mapper walks; assert query count in tests |
| Fetch join + `Pageable` | Hibernate paginates in memory (`HHH90003004`) — drop the fetch join, rely on `default_batch_fetch_size` |
| Inner `JOIN FETCH` drops parents | Orders with no items vanish from results — use `LEFT JOIN FETCH` |
| OSIV hides lazy loading | `spring.jpa.open-in-view=false` so lazy access outside the transaction fails fast |
| Deep OFFSET slow | Switch to keyset pagination |
| Enum reordering breaks DB | Use `EnumType.STRING` |
| Lazy loading in view | Fetch eagerly or use a projection |
| Batching silently off | Avoid `GenerationType.IDENTITY` on bulk-inserted entities → use UUID |
| Orphaned child records | Add `orphanRemoval = true` |
| Bidirectional unsync | Use helper methods (`addItem()`) |
| No-arg constructor exposed | Use `protected` and factory methods |
| `schema.sql` + auto-DDL collide | Pick one: `ddl-auto=none` (schema.sql owns it) or `ddl-auto=create-drop` (entities own it), never both |
| Mapper silently drops fields | Route `toEntity()` through a `reconstitute()` factory, never a bare `new Entity()` |
| Two `public` types, one file | Split entity and enum into separate `.java` files |

**Debugging**: keep the SQL logging from §4 on while developing. Multiple SELECTs in a loop
= N+1; `OFFSET 100000` on a deep page = switch to keyset.

---

## Final notes

- **Minimum version**: Java 21 LTS + Spring Boot 3.3+.
- **No Lombok**: write all constructors, getters, and methods explicitly; Lombok hides JPA issues.
- **Layer isolation**: strictly enforced — DTOs never in domain/application, entities never outside persistence.
- **Logging**: Log4j2 via `spring-boot-starter-log4j2`, Logback excluded.
- **Build**: Gradle (`./gradlew bootRun`) is the default; mention Maven only on request.
- **Database**: ask the user before generating persistence code (see §0).
- **DDL**: one source of truth only (see §4–§5).
- **Performance first**: always check SQL logging; test N+1 with small datasets.

## References

- `./complete-example.md` — full runnable `Product` CRUD example (domain, use cases, web adapter, persistence adapter, unit + integration tests) with all layers wired together correctly.
- `./entities-and-repositories.md` — full entity, repository, mapper, N+1, pagination, batching, and testing code, corrected and internally consistent.
- Spring Boot Docs: https://docs.spring.io/spring-boot/docs/current/reference/html/
- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Hibernate ORM: https://docs.jboss.org/hibernate/orm/current/userguide/
- Java Persistence API: https://jakarta.ee/specifications/persistence/
- Log4j2 Spring Boot integration: https://docs.spring.io/spring-boot/reference/features/logging.html
- Java 21 Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview
