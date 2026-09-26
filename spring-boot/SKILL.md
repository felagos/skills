---
name: spring-boot
description: "Builds and reviews Spring Boot 3 services in Java 21 using hexagonal architecture: REST controllers, use cases, JPA/Hibernate persistence, repositories and query tuning (N+1, pagination, batching). Use when working on a Spring or Spring Boot backend, REST API, JPA entity or repository, or database query performance in a JVM service."
---

# Spring Boot 3 + Java 21

## Activation Contract

Use this skill for Spring Boot backend work, including REST APIs, use cases, persistence, JPA query behavior, and project scaffolding. Apply Clean/Hexagonal Architecture without replacing sound conventions already established by the repository.

## Hard Rules

- Read `references/conventions.md` before writing or reviewing Java code; skip it for questions these rules already answer.
- Use Java 21, Spring Boot 3.3+, and Gradle by default; use Maven only when requested or already established.
- Do not use Lombok, field injection, or `@Autowired`; use explicit constructors and `final` dependencies.
- Keep domain models free of Spring, JPA, HTTP, and DTO types.
- Keep web DTOs inside the web adapter and JPA entities inside the persistence adapter.
- Put transactions on use-case methods; mark reads `readOnly = true`.
- Map enums with `EnumType.STRING` and aggregate-root identifiers with `UUID`.
- Use exactly one DDL owner: `schema.sql` with `ddl-auto=none`, or entities with generated DDL.
- Use SLF4J in application code and Log4j2 as the configured backend.

## Decision Gates

| Situation | Action |
| --- | --- |
| Existing repository | Preserve its build tool, package layout, database, migration tool, and tested conventions unless change is requested. |
| New project or persistence adapter | Ask which database to target; use H2 only when the user explicitly wants an in-memory or quick-running setup. |
| Web-only or review-only change | Do not ask about the database unless persistence behavior is affected. |
| Entity, repository, mapper, pagination, or batching work | Read `references/entities-and-repositories.md`. |
| N+1, slow queries, pagination, or batching problem | Read `references/jpa-gotchas.md` and verify generated SQL. |
| Full project setup | Read `references/project-setup.md`; consult `references/complete-example.md` only when end-to-end wiring is needed. |

## Verification

Run focused tests, and inspect the generated SQL on persistence-sensitive paths. Report any behavior you could not verify.

## Output Contract

Return the implemented or reviewed result, note architecture and database decisions, and list exact verification commands and outcomes. For performance work, include the observed query behavior that supports the conclusion.

## References

- [Conventions](references/conventions.md) — mandatory architecture and coding rules.
- [Project setup](references/project-setup.md) — Gradle, logging, configuration, and DDL.
- [Complete example](references/complete-example.md) — end-to-end CRUD wiring.
- [Entities and repositories](references/entities-and-repositories.md) — persistence patterns.
- [JPA gotchas](references/jpa-gotchas.md) — query and mapping failure modes.
