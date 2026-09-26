# Conventions — layers, entities, mappers, style

Complete rule set for writing or reviewing code with this skill. Full code lives in
`./complete-example.md` (Product CRUD, §1–§6) and `./entities-and-repositories.md` (Order
aggregate, §1–§8).

## 6. Layers

| Layer | Rules |
|---|---|
| Domain | Pure Java. `record` if immutable, class if mutable aggregate with behavior. Ports are plain interfaces. |
| Application | One `@Component` per use case with `execute()`. Never import DTOs, entities, or HTTP types. `ResourceNotFoundException` lives in `application.exception` — import it explicitly from use cases. |
| Web adapter | Controller depends only on use cases + `WebMapper`. `GlobalExceptionHandler` maps **both** `ResourceNotFoundException` → 404 and `MethodArgumentNotValidException` → 400 with field detail; never let validation fall through to 500. |
| Persistence adapter | Entity + package-private `JpaRepository` + `PersistenceMapper` + `RepositoryAdapter implements <DomainPort>`. Entities never leave `infrastructure/persistence/`. |

## 9. Entities and mappers

- No public constructor and no setters; mutate through behavior methods (`confirm()`,
  `addItem()`) that enforce invariants.
- Two factories per aggregate root: `create(...)` (new id + timestamps) and
  `reconstitute(...)` (used only by the mapper; preserves id/timestamps).
- **Mapper gotcha**: `new OrderEntity()` in `toEntity()` compiles but yields all-`null`
  fields. Always go through `reconstitute(...)`, and convert enums explicitly
  (`DomainStatus.valueOf(entity.getStatus().name())`) — domain and entity enums are separate
  types on purpose.
- The mapper walks `getItems()`, so every adapter read path must fetch the collection, or it
  is N+1 (fixes: `./entities-and-repositories.md` §4).

Where to look in `./entities-and-repositories.md`: §1–§2 entities and factories · §3
repositories, `@Query`/`@EntityGraph`, projections, adapter · §4 N+1 · §5 mapper · §6
pagination · §7 batch inserts and the `IDENTITY` caveat · §8 `@DataJpaTest` with query-count
assertion.

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
| Lazy loading | `@ManyToOne(fetch = LAZY)` always; `@OneToMany(fetch = LAZY)` stated explicitly |
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
