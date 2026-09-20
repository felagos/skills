# Conventions — layers, entities, mappers, style

The full convention set for this skill. Read this before writing or reviewing any Java code.
`SKILL.md` only carries the non-negotiables; the complete rules live here.
Section numbers (§6–§10) are kept from the original SKILL.md so existing cross-references
from `complete-example.md` and `entities-and-repositories.md` still resolve.

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
