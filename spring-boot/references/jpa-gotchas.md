# JPA gotchas and external references

Read this when debugging N+1 queries, slow pagination, batching that silently does nothing,
or data quietly lost in the entity ↔ domain mapper.

---

## JPA gotchas

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

**Debugging**: keep the SQL logging from `project-setup.md` §4 on while developing. Multiple SELECTs in a loop
= N+1; `OFFSET 100000` on a deep page = switch to keyset. Performance first: check SQL
logging on every read path and test N+1 with small datasets, before the data grows.

---

## External references

- Spring Boot Docs: https://docs.spring.io/spring-boot/docs/current/reference/html/
- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Hibernate ORM: https://docs.jboss.org/hibernate/orm/current/userguide/
- Java Persistence API: https://jakarta.ee/specifications/persistence/
- Log4j2 Spring Boot integration: https://docs.spring.io/spring-boot/reference/features/logging.html
- Java 21 Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview
