---
name: spring-boot
description: >
  Spring Boot 3.x + Java 21 backends in Claude Code using Clean / Hexagonal Architecture
  with Spring Data JPA: domain ports, one use case per operation, web adapter and
  persistence adapter. Gradle, Log4j2, no Lombok, constructor injection, records.
  Activate on Spring Boot, Spring, use case, service, controller, repository, entity, REST,
  DTO, JPA, Hibernate, query, N+1, projection, pagination, batch insert, clean architecture,
  hexagonal, or any JVM backend task — even if the user only says "database" or
  "query performance" without naming JPA.
---

# Spring Boot + Java 21 — Clean / Hexagonal Architecture + JPA

You are a senior Java developer writing modern, executable Spring Boot applications with
Java 21, strict Clean Architecture, and production-grade Spring Data JPA.

## Read this first

**Before writing or reviewing any Java code, read [references/conventions.md](references/conventions.md).**
Not optional: it holds the complete convention set (layer responsibilities, entity rules,
mapper rules, injection, transactions, DDL ownership, naming) that this file only summarizes.

## Before any code: ask about the database

**Never default to H2 silently.** Ask which database to target before scaffolding the
persistence adapter (or the whole project):

- **H2 (in-memory)** — zero setup, resets on restart. Demos, katas, quick tests.
- **PostgreSQL** — production-like, needs a running instance or Docker.
- **MySQL / MariaDB** — same tradeoffs as Postgres.
- **"Just get something running"** — default to H2 *only* if the user says this or
  equivalent, and say out loud that you're defaulting to H2 and it's swappable later.

The answer changes the JDBC driver in `build.gradle`, the `spring.datasource.*` properties
and `ddl-auto`, and the column types in `schema.sql` (H2 `CHAR(36)` vs Postgres native
`uuid` vs MySQL `BINARY(16)`; `AUTO_INCREMENT` vs `GENERATED ALWAYS AS IDENTITY`).
Details in [references/project-setup.md](references/project-setup.md).

## Architecture

```
src/main/java/com/example/
├── domain/
│   ├── model/Product.java                        ← pure domain object (no framework)
│   └── repository/ProductRepository.java         ← repository port (interface)
│
├── application/
│   ├── usecase/{Create,Find,Delete}ProductUseCase.java
│   └── exception/ResourceNotFoundException.java
│
└── infrastructure/
    ├── web/
    │   ├── controller/{ProductController,GlobalExceptionHandler}.java
    │   ├── dto/{CreateProductRequest,ProductResponse}.java
    │   └── mapper/ProductWebMapper.java
    └── persistence/
        ├── entity/ProductEntity.java
        ├── repository/{ProductJpaRepository,ProductRepositoryAdapter}.java
        └── mapper/ProductPersistenceMapper.java

src/main/resources/{application.properties, schema.sql, log4j2.xml}
build.gradle
```

| Layer | Knows about | Must NOT know about |
|---|---|---|
| `domain` | itself | Spring, JPA, DTOs |
| `application` | domain | Spring web, JPA, DTOs, HTTP |
| `infrastructure/web` | domain, application use cases | JPA, entities |
| `infrastructure/persistence` | domain, JPA | DTOs, use cases, controllers |

`application` may use Spring's `@Component`/`@Transactional` for wiring, but never imports
`jakarta.persistence.*`, DTO classes, or servlet/HTTP types.

## Non-negotiables

- Java 21 LTS + Spring Boot 3.3+, **Gradle** — never generate a `pom.xml` unless asked.
- **No Lombok** — write constructors, getters, and methods explicitly.
- Constructor injection only, `final` fields, no `@Autowired`.
- JPA entities: `protected` no-arg constructor, **no setters**, `create()` + `reconstitute()`
  factories; mutate through named behavior methods that enforce invariants.
- `@Enumerated(EnumType.STRING)` always, never `ORDINAL`.
- Aggregate-root ids are `UUID`, never auto-increment `Long`.
- DTOs never leave `infrastructure/web`; JPA entities never leave `infrastructure/persistence`.
- `@Transactional` on use-case methods, never on repositories; `readOnly = true` on reads.
- One DDL source of truth: `schema.sql` + `ddl-auto=none`, **or** entities + `create-drop`.
  Never both — they collide on startup.
- Log4j2 (Logback excluded); application code uses the SLF4J API.

## Reference map

| File | Read it when |
|---|---|
| [references/conventions.md](references/conventions.md) | Always, before writing or reviewing Java code |
| [references/project-setup.md](references/project-setup.md) | Starting a project, or touching `build.gradle`, `application.properties`, `log4j2.xml`, `schema.sql` |
| [references/complete-example.md](references/complete-example.md) | You need a full CRUD project wired end to end (domain → use cases → web → persistence → tests) |
| [references/entities-and-repositories.md](references/entities-and-repositories.md) | Writing entities, repositories, mappers, pagination, or batch inserts |
| [references/jpa-gotchas.md](references/jpa-gotchas.md) | Debugging N+1, slow deep pages, batching that does nothing, fields lost in the mapper |
