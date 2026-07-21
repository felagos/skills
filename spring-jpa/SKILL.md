---
name: spring-data-jpa-claude-code
description: >
  Skill for writing Spring Data JPA entities, repositories, mappers, and queries in
  Claude Code with Clean Architecture. Covers entity conventions (no Lombok, protected
  no-arg constructor, no setters, static factory methods), N+1 prevention (JOIN FETCH,
  @EntityGraph, projections), pagination (OFFSET vs keyset), batch inserts, and H2
  in-memory setup with a hand-written schema.sql. Companion to the spring-boot-claude-code
  architecture skill — use both together when the task involves a full REST + JPA
  feature. Activate on entity, repository, JPA, Hibernate, query, N+1, projection,
  pagination, batch insert, or any Spring Data / persistence-layer task, even if the
  user only mentions "database" or "query performance" without naming JPA explicitly.
---

# Spring Data JPA for Claude Code — Entities, Queries, Performance

You are a senior Java developer writing production-grade Spring Data JPA code in Claude Code
with explicit conventions (no Lombok), strict entity isolation, and performance best practices.

For the full entity, repository, mapper, and testing code, see
`./entities-and-repositories.md`. This file covers the rules, config, and the
gotchas that matter most — read it fully before generating persistence code.

---

## 0. Claude Code + JPA context

- Default target is H2 in-memory (see the companion `spring-boot-claude-code` skill §0 —
  it asks the user which database to use *before* scaffolding; if they picked
  PostgreSQL/MySQL instead, adjust `schema.sql` column types accordingly: H2's
  `CHAR(36)` for UUIDs becomes Postgres's native `uuid` type or MySQL's `BINARY(16)`/`CHAR(36)`,
  and `AUTO_INCREMENT` becomes `GENERATED ALWAYS AS IDENTITY` / `SERIAL` on Postgres).
- Entities live **only** in `infrastructure/persistence/entity/`; never expose outside the adapter.
- Repositories implement domain ports in `infrastructure/persistence/repository/`.
- Query debugging via SQL logging in `application.properties` (works the same whether the
  logging backend is Logback or Log4j2 — it's a `logging.level.*` property, not tied to a backend).
- Tests use `@DataJpaTest` for fast slice testing without the full Spring context.
- Run tests with `./gradlew test` (this skill assumes Gradle, matching `spring-boot-claude-code`).

---

## 1. application.properties — JPA + H2 + SQL logging

```properties
# H2 database (in-memory, auto-initialized)
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate — ddl-auto=none because schema.sql (§2) is the source of truth.
# Never combine schema.sql with create-drop/update: Hibernate's auto-DDL and schema.sql
# both try to create the same tables and collide on startup ("table already exists").
spring.jpa.hibernate.ddl-auto=none
spring.sql.init.mode=always
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
spring.jpa.properties.hibernate.use_sql_comments=true

# Batching (for bulk inserts — see §8 in the reference file for the IDENTITY caveat)
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true

# Logging
logging.level.root=INFO
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
real schema (managed by a migration tool, not `schema.sql`) drift apart.

---

## 2. schema.sql — H2 initialization (single source of truth for DDL)

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

## 3. Entity conventions (no Lombok, explicit)

- One `public` top-level type per `.java` file — an entity and its enum are **separate
  files** (`OrderEntity.java`, `OrderStatus.java`), never combined.
- `protected` no-arg constructor only (JPA requirement); no `public` constructor exposed.
- **No setters.** Mutation happens through named behavior methods (`confirm()`, `cancel()`,
  `addItem()`) that also enforce invariants — never a generic `setStatus()`.
- Two static factories per aggregate root: `create(...)` for brand-new entities (generates
  id + timestamps) and a `reconstitute(...)` factory used only by the persistence mapper to
  rebuild an entity from domain data (preserves the original id/timestamps — this is the
  piece that's easy to forget, see `./entities-and-repositories.md` §1–§2).
- `@Enumerated(EnumType.STRING)` always, never `ORDINAL` (reordering the enum would silently
  corrupt existing rows).
- `@ManyToOne(fetch = FetchType.LAZY)` always; `@OneToMany` defaults to LAZY already but
  state it explicitly for readability.
- `orphanRemoval = true` on owning `@OneToMany` collections that should delete children when
  removed from the collection.

Full code for `OrderEntity`, `OrderItemEntity`, `ProductEntity` is in the reference file.

---

## 4. Repository & mapper patterns — see reference file

`./entities-and-repositories.md` covers, with corrected/working code:
- **§1–§2**: entities with the `reconstitute()` factories.
- **§3**: package-private `JpaRepository` interfaces + `@Query`/`@EntityGraph` patterns.
- **§4**: `RepositoryAdapter` implementing the domain port.
- **§5**: the entity↔domain mapper — this is the one piece most drafts get wrong (see the
  gotcha below), fully corrected here.
- **§6**: N+1 prevention (JOIN FETCH, @EntityGraph, interface vs. DTO projections).
- **§7**: OFFSET vs. keyset pagination.
- **§8**: batch inserts and the `GenerationType.IDENTITY` gotcha.
- **§9**: `@DataJpaTest` slice tests.

**The #1 mapper gotcha**: because entities have no setters, a naive `toEntity(domain)` that
does `new OrderEntity()` and returns it immediately compiles fine but silently produces an
entity with every field `null` — which then fails on save with `NOT NULL` constraint
violations (or worse, succeeds with garbage data if the columns happen to be nullable).
Always route entity reconstruction through the aggregate's `reconstitute(...)` factory, and
convert domain ↔ entity enums explicitly (`DomainStatus.valueOf(entity.getStatus().name())`)
— they are deliberately two different enum types even when the constant names match, so the
persistence layer never leaks its enum into the domain.

---

## 5. Style and conventions

| Aspect | Rule |
|---|---|
| ID type (aggregate roots) | `UUID`, never auto-increment `Long` |
| ID type (child/internal entities) | `Long`/`IDENTITY` is acceptable *only* if the entity is never bulk-inserted and never queried by id directly outside its parent (see batching gotcha in §8 of the reference file) |
| Enums | `@Enumerated(EnumType.STRING)`, never `ORDINAL` |
| Collections | Initialize inline: `= new ArrayList<>()`; never null |
| Lazy loading | `@ManyToOne(fetch = LAZY)` always; `@OneToMany(fetch = LAZY)` default |
| Orphans | `@OneToMany(..., orphanRemoval = true)` to clean children |
| Constructor | Protected no-arg only (JPA requirement); hide from app |
| Setters | Never on entities; use behavior methods + a `reconstitute()` factory for mapping |
| Files | One public top-level type per `.java` file — entity and its enum are separate files |
| N+1 fix | `JOIN FETCH` for singles, `@EntityGraph` for lists, projections for reads |
| Projections | Interface-based for plain property reads; class/record (DTO) based when the query computes a value (e.g. `SIZE(...)`) — don't mix the two for the same query |
| Pagination | Use `Pageable` always; switch to keyset on deep pages |
| Batching | Enable `hibernate.jdbc.batch_size`; avoid `GenerationType.IDENTITY` on entities you bulk-insert |
| DDL | One source of truth: `schema.sql` + `ddl-auto=none`, or entities + `ddl-auto=create-drop` — never both |
| Transactions | `@Transactional` on service/use-case methods (application layer), not repositories |
| Imports | No wildcards |
| Naming | `PascalCase` entities, `SNAKE_CASE` columns, `camelCase` getters |

---

## 6. Gotchas summary

| Problem | Solution |
|---|---|
| N+1 queries | Use `JOIN FETCH` or `@EntityGraph` |
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

---

## 7. Debugging: SQL logging in console

```properties
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.type.descriptor.sql=TRACE
spring.jpa.properties.hibernate.use_sql_comments=true
```

**Watch for N+1**: multiple SELECTs in a loop.
**Watch for OFFSET**: `OFFSET 100000` on a deep page → switch to keyset pagination.

---

## Final notes

- **Minimum version**: Spring Boot 3.3+, Java 21, H2 for Claude Code (swap per §0 if the
  user chose a different database in the companion architecture skill).
- **No Lombok**: write explicit constructors and getters; Lombok hides JPA issues.
- **Entity isolation**: entities never leave the persistence adapter; map to domain objects
  through a mapper that uses `reconstitute()`, never a bare constructor call.
- **Performance first**: always check SQL logging; test N+1 with small datasets.
- **Transactions**: applied at the application/use-case layer, not the repository.
- **DDL**: one source of truth only — see §6.

## References

- `./entities-and-repositories.md` — full entity, repository, mapper, N+1,
  pagination, batching, and testing code, corrected and internally consistent.
- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Hibernate ORM: https://docs.jboss.org/hibernate/orm/current/userguide/
- Java Persistence API: https://jakarta.ee/specifications/persistence/
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview