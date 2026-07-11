---
name: spring-data-jpa-claude-code
description: >
  Skill for writing Spring Data JPA entities, repositories, and queries in Claude Code
  with Clean Architecture. Covers entity conventions (no Lombok, explicit constructors),
  N+1 prevention (JOIN FETCH, @EntityGraph), projections for read-only views, pagination
  patterns (OFFSET vs keyset), batch inserts, and H2 in-memory database setup. Debugging
  via SQL logging in console. Activate on entity, repository, JPA, query, N+1, projection,
  pagination, or any persistence layer task.
---

# Spring Data JPA for Claude Code — Entities, Queries, Performance

You are a senior Java developer writing production-grade Spring Data JPA code in Claude Code
with explicit conventions (no Lombok), strict entity isolation, and performance best practices.

---

## 0. Claude Code + JPA context

**Environment**: In-memory H2 database, SLF4J logging to console, no external DB setup needed.

**Key points**:
- Entities live **only** in `infrastructure/persistence/entity/`; never expose outside adapter.
- Repositories implement domain ports in `infrastructure/persistence/repository/`.
- Query debugging via SQL logging in `application.properties`.
- Schema initialized via `schema.sql` on startup (`spring.jpa.hibernate.ddl-auto=create-drop`).
- Tests use `@DataJpaTest` for fast slice testing without full Spring context.

---

## 1. application.properties — JPA + H2 + SQL logging

```properties
# H2 database (in-memory, auto-initialized)
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
spring.jpa.properties.hibernate.use_sql_comments=true

# Batching (for bulk inserts)
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
spring.jpa.database-platform=org.hibernate.dialect.PostgreSQL10Dialect
spring.jpa.hibernate.ddl-auto=validate
```

---

## 2. schema.sql — H2 initialization

```sql
-- src/main/resources/schema.sql
-- Runs automatically when spring.jpa.hibernate.ddl-auto=create-drop

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

-- Indexes for common queries
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_customer_email ON orders(customer_email);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_orders_keyset ON orders(status, created_at DESC, id DESC);
```

---

## 3. Entity conventions (no Lombok, explicit)

### Order entity (aggregate root)

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "orders")
public class OrderEntity {

    @Id
    @Column(columnDefinition = "CHAR(36)", updatable = false, nullable = false)
    private UUID id;

    @Column(nullable = false)
    private String customerEmail;

    @Enumerated(EnumType.STRING)  // ✅ STRING, never ORDINAL
    @Column(nullable = false)
    private OrderStatus status;

    @OneToMany(
        mappedBy = "order",
        cascade = CascadeType.ALL,
        orphanRemoval = true,  // ✅ removes child when removed from collection
        fetch = FetchType.LAZY
    )
    private List<OrderItemEntity> items = new ArrayList<>();

    @Column(updatable = false, nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    // ✅ Protected no-arg constructor (JPA requirement, hidden from app code)
    protected OrderEntity() {}

    // ✅ Static factory method
    public static OrderEntity create(String customerEmail) {
        var order = new OrderEntity();
        order.id = UUID.randomUUID();
        order.customerEmail = customerEmail;
        order.status = OrderStatus.PENDING;
        order.createdAt = Instant.now();
        order.updatedAt = Instant.now();
        return order;
    }

    // Getters (no setters on entities — use behavior methods instead)
    public UUID getId()                  { return id; }
    public String getCustomerEmail()     { return customerEmail; }
    public OrderStatus getStatus()       { return status; }
    public List<OrderItemEntity> getItems() { return List.copyOf(items); }
    public Instant getCreatedAt()        { return createdAt; }
    public Instant getUpdatedAt()        { return updatedAt; }

    // ✅ Behavior methods (domain logic on entity)
    public void addItem(OrderItemEntity item) {
        items.add(item);
        item.setOrder(this);  // keep both sides in sync
    }

    public void confirm() {
        if (status != OrderStatus.PENDING)
            throw new IllegalStateException("Only PENDING orders can be confirmed");
        this.status = OrderStatus.CONFIRMED;
        this.updatedAt = Instant.now();
    }

    public void cancel() {
        if (status == OrderStatus.COMPLETED || status == OrderStatus.CANCELLED)
            throw new IllegalStateException("Cannot cancel " + status + " order");
        this.status = OrderStatus.CANCELLED;
        this.updatedAt = Instant.now();
    }
}

public enum OrderStatus {
    PENDING, CONFIRMED, COMPLETED, CANCELLED
}
```

### OrderItem entity (child)

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "order_items")
public class OrderItemEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)  // ✅ LAZY always on @ManyToOne
    @JoinColumn(name = "order_id", nullable = false)
    private OrderEntity order;

    @Column(name = "product_id", nullable = false)
    private UUID productId;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false)
    private BigDecimal unitPrice;

    protected OrderItemEntity() {}

    public static OrderItemEntity create(UUID productId, Integer quantity, BigDecimal unitPrice) {
        var item = new OrderItemEntity();
        item.productId = productId;
        item.quantity = quantity;
        item.unitPrice = unitPrice;
        return item;
    }

    // Getters
    public Long getId()          { return id; }
    public OrderEntity getOrder() { return order; }
    public UUID getProductId()   { return productId; }
    public Integer getQuantity() { return quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }

    // For bidirectional sync only (package-private)
    protected void setOrder(OrderEntity order) { this.order = order; }
}
```

### Product entity

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "products")
public class ProductEntity {

    @Id
    @Column(columnDefinition = "CHAR(36)", updatable = false, nullable = false)
    private UUID id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private BigDecimal price;

    @Column(name = "category_id")
    private UUID categoryId;

    @Column(updatable = false, nullable = false)
    private Instant createdAt;

    protected ProductEntity() {}

    public static ProductEntity create(String name, BigDecimal price, UUID categoryId) {
        var product = new ProductEntity();
        product.id = UUID.randomUUID();
        product.name = name;
        product.price = price;
        product.categoryId = categoryId;
        product.createdAt = Instant.now();
        return product;
    }

    // Getters only
    public UUID getId()        { return id; }
    public String getName()    { return name; }
    public BigDecimal getPrice() { return price; }
    public UUID getCategoryId() { return categoryId; }
    public Instant getCreatedAt() { return createdAt; }
}
```

---

## 4. Repository patterns (Spring Data JPA)

### Package-private JpaRepository

```java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderStatus;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

// ✅ package-private: never injected outside this package
interface OrderJpaRepository extends JpaRepository<OrderEntity, UUID> {

    // Simple derived query
    List<OrderEntity> findByStatus(OrderStatus status);

    // EXISTS check — faster than findById().isPresent()
    boolean existsByIdAndStatus(UUID id, OrderStatus status);

    // Pagination with default OFFSET
    Page<OrderEntity> findByStatus(OrderStatus status, Pageable pageable);

    // ✅ N+1 FIX: JOIN FETCH for single entity
    @Query("SELECT o FROM OrderEntity o JOIN FETCH o.items WHERE o.id = :id")
    Optional<OrderEntity> findByIdWithItems(@Param("id") UUID id);

    // ✅ N+1 FIX: @EntityGraph for lists (avoids duplicate rows from joins)
    @EntityGraph(attributePaths = {"items"})
    List<OrderEntity> findByStatusAndCustomerEmailWithItems(
        OrderStatus status,
        String customerEmail
    );

    // ✅ KEYSET pagination (O(1) vs O(N) for deep pages)
    @Query("""
        SELECT o FROM OrderEntity o
        WHERE o.status = :status
          AND (o.createdAt < :lastCreatedAt
               OR (o.createdAt = :lastCreatedAt AND o.id < :lastId))
        ORDER BY o.createdAt DESC, o.id DESC
        """)
    List<OrderEntity> findNextPageByStatus(
        @Param("status") OrderStatus status,
        @Param("lastCreatedAt") Instant lastCreatedAt,
        @Param("lastId") UUID lastId,
        Pageable pageable
    );

    // Projection for read-only views (no full entity loaded)
    List<OrderSummaryProjection> findByCustomerEmail(String customerEmail);
}

// ✅ Projection: only fetches needed columns
public interface OrderSummaryProjection {
    UUID getId();
    String getCustomerEmail();
    OrderStatus getStatus();
    Instant getCreatedAt();
    int getItemCount();  // computed in query if needed
}
```

### Repository adapter (implements domain port)

```java
package com.example.infrastructure.persistence.repository;

import com.example.domain.model.Order;
import com.example.domain.repository.OrderRepository;
import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderStatus;
import com.example.infrastructure.persistence.mapper.OrderPersistenceMapper;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Repository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class OrderRepositoryAdapter implements OrderRepository {

    private final OrderJpaRepository jpaRepository;
    private final OrderPersistenceMapper mapper;

    public OrderRepositoryAdapter(
            OrderJpaRepository jpaRepository,
            OrderPersistenceMapper mapper) {
        this.jpaRepository = jpaRepository;
        this.mapper = mapper;
    }

    @Override
    public List<Order> findAll() {
        return jpaRepository.findAll().stream()
            .map(mapper::toDomain)
            .toList();
    }

    @Override
    public Optional<Order> findById(UUID id) {
        return jpaRepository.findById(id).map(mapper::toDomain);
    }

    // ✅ Load with items (N+1 prevention)
    @Override
    public Optional<Order> findByIdWithItems(UUID id) {
        return jpaRepository.findByIdWithItems(id).map(mapper::toDomain);
    }

    @Override
    public Page<Order> findByStatus(OrderStatus status, Pageable pageable) {
        var page = jpaRepository.findByStatus(status, pageable);
        return new PageImpl<>(
            page.getContent().stream().map(mapper::toDomain).toList(),
            pageable,
            page.getTotalElements()
        );
    }

    // ✅ Keyset pagination (for large datasets)
    @Override
    public List<Order> findNextPage(
            OrderStatus status,
            Instant lastCreatedAt,
            UUID lastId,
            Pageable pageable) {
        return jpaRepository.findNextPageByStatus(status, lastCreatedAt, lastId, pageable)
            .stream()
            .map(mapper::toDomain)
            .toList();
    }

    @Override
    public Order save(Order order) {
        var entity = mapper.toEntity(order);
        var saved = jpaRepository.save(entity);
        return mapper.toDomain(saved);
    }

    @Override
    public void deleteById(UUID id) {
        jpaRepository.deleteById(id);
    }

    @Override
    public boolean existsById(UUID id) {
        return jpaRepository.existsById(id);
    }
}
```

---

## 5. Mapper (entity ↔ domain)

```java
package com.example.infrastructure.persistence.mapper;

import com.example.domain.model.Order;
import com.example.domain.model.OrderLine;
import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderItemEntity;
import org.springframework.stereotype.Component;

@Component
public class OrderPersistenceMapper {

    // Entity → Domain
    public Order toDomain(OrderEntity entity) {
        if (entity == null) return null;

        var lines = entity.getItems().stream()
            .map(item -> new OrderLine(
                (long) item.getId(),
                item.getProductId(),
                item.getQuantity()
            ))
            .toList();

        return new Order(
            entity.getId(),
            entity.getCustomerEmail(),
            entity.getStatus().name(),  // or enum if domain supports
            lines,
            entity.getCreatedAt()
        );
    }

    // Domain → Entity
    public OrderEntity toEntity(Order domain) {
        if (domain == null) return null;

        var entity = new OrderEntity();
        // Map fields manually (reflection avoided for performance)
        // Note: JPA will regenerate IDs on save if null
        return entity;
    }
}
```

---

## 6. N+1 prevention patterns

### Pattern 1: JOIN FETCH for single queries

```java
// ❌ N+1 PROBLEM
List<OrderEntity> orders = jpaRepository.findByStatus(OrderStatus.PENDING);
for (var order : orders) {
    System.out.println(order.getItems().size());  // triggers N queries!
}

// ✅ SOLUTION: JOIN FETCH
@Query("SELECT DISTINCT o FROM OrderEntity o JOIN FETCH o.items WHERE o.status = :status")
List<OrderEntity> findByStatusWithItems(@Param("status") OrderStatus status);
```

### Pattern 2: @EntityGraph for list queries

```java
// ✅ Cleaner than @Query for simple cases
@EntityGraph(attributePaths = {"items", "items.order"})
List<OrderEntity> findByStatus(OrderStatus status);
```

### Pattern 3: Projections for read-only views

```java
// ✅ Only fetches the columns you need
public interface OrderSummary {
    UUID getId();
    String getCustomerEmail();
    int getItemCount();  // can be computed
}

// In repository
@Query("""
    SELECT new com.example.infrastructure.persistence.repository.OrderSummaryImpl(
        o.id, o.customerEmail, SIZE(o.items)
    )
    FROM OrderEntity o
    WHERE o.status = :status
    """)
List<OrderSummary> findSummariesByStatus(@Param("status") OrderStatus status);
```

---

## 7. Pagination patterns

### OFFSET pagination (simple, slow on deep pages)

```java
// Controller
@GetMapping
public ResponseEntity<Page<OrderResponse>> list(
        @RequestParam(defaultValue = "0") int page,
        @RequestParam(defaultValue = "20") int size) {
    var orders = orderService.findByStatus(OrderStatus.PENDING, PageRequest.of(page, size));
    return ResponseEntity.ok(orders.map(mapper::toResponse));
}

// Service
public Page<Order> findByStatus(OrderStatus status, Pageable pageable) {
    return orderRepository.findByStatus(status, pageable);
}

// SQL generated:
// SELECT * FROM orders WHERE status = 'PENDING'
// ORDER BY created_at DESC LIMIT 20 OFFSET 0
// ✅ Page 1: 0 rows scanned
// ✅ Page 2: 20 rows scanned
// ❌ Page 5000: 100,000 rows scanned (very slow!)
```

### Keyset pagination (constant-time, for infinite scroll)

```java
// DTO for cursor
public record OrderCursor(java.time.Instant lastCreatedAt, UUID lastId) {}

// Controller
@GetMapping("/scroll")
public ResponseEntity<List<OrderResponse>> scroll(
        @RequestParam OrderCursor cursor,
        @RequestParam(defaultValue = "20") int size) {
    var orders = orderService.findNextPage(
        OrderStatus.PENDING,
        cursor.lastCreatedAt(),
        cursor.lastId(),
        size
    );
    return ResponseEntity.ok(orders.stream().map(mapper::toResponse).toList());
}

// Service
public List<Order> findNextPage(OrderStatus status, Instant lastCreatedAt, UUID lastId, int size) {
    return orderRepository.findNextPage(
        status,
        lastCreatedAt,
        lastId,
        PageRequest.of(0, size)  // only used for limit
    );
}

// Repository
@Query("""
    SELECT o FROM OrderEntity o
    WHERE o.status = :status
      AND (o.createdAt < :lastCreatedAt
           OR (o.createdAt = :lastCreatedAt AND o.id < :lastId))
    ORDER BY o.createdAt DESC, o.id DESC
    """)
List<OrderEntity> findNextPageByStatus(
    @Param("status") OrderStatus status,
    @Param("lastCreatedAt") Instant lastCreatedAt,
    @Param("lastId") UUID lastId,
    Pageable pageable
);

// SQL generated:
// SELECT * FROM orders
// WHERE status = 'PENDING'
//   AND (created_at < ? OR (created_at = ? AND id < ?))
// ORDER BY created_at DESC, id DESC LIMIT 20
// ✅ Always scans ~20 rows, regardless of cursor depth
```

---

## 8. Batch inserts

```yaml
# application.properties
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 50
        order_inserts: true
        order_updates: true
```

```java
// ✅ GOOD: Batches 50 at a time (5 round-trips for 250 items)
@Service
public class BulkOrderService {
    
    @Transactional
    public void createOrders(List<Order> orders) {
        for (var order : orders) {
            orderRepository.save(order);  // batched
        }
    }
}

// ❌ GOTCHA: GenerationType.IDENTITY disables batching silently
// Hibernate needs the generated key per row → no batching possible
// Use UUID or sequence instead:
@Id
@GeneratedValue(strategy = GenerationType.UUID)
private UUID id;
```

---

## 9. Testing JPA (slice test, fast)

```java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest  // ✅ Only loads JPA context, no web/service layer
class OrderJpaRepositoryTest {

    @Autowired private OrderJpaRepository repository;
    @Autowired private TestEntityManager em;

    @Test
    void shouldFindByStatus() {
        var order1 = OrderEntity.create("alice@example.com");
        order1.confirm();
        em.persistAndFlush(order1);

        var order2 = OrderEntity.create("bob@example.com");
        em.persistAndFlush(order2);

        var result = repository.findByStatus(OrderStatus.CONFIRMED);

        assertThat(result).hasSize(1).contains(order1);
    }

    @Test
    void shouldLoadItemsWithJoinFetch() {
        var order = OrderEntity.create("alice@example.com");
        var item = OrderItemEntity.create(null, 2, java.math.BigDecimal.valueOf(19.99));
        order.addItem(item);
        em.persistAndFlush(order);

        em.clear();  // clear persistence context to force DB query

        var loaded = repository.findByIdWithItems(order.getId()).orElseThrow();
        
        assertThat(loaded.getItems()).hasSize(1);
        // Verify: only 1 query executed (not 2)
    }
}
```

Run tests:
```bash
mvn test
# or
./gradlew test
```

---

## 10. Debugging: SQL logging in console

Enable SQL query logging in `application.properties`:

```properties
logging.level.org.hibernate.SQL=DEBUG
logging.level.org.hibernate.type.descriptor.sql=TRACE
spring.jpa.properties.hibernate.use_sql_comments=true
```

**Console output**:
```
[DEBUG] org.hibernate.SQL - SELECT o FROM OrderEntity o WHERE o.status = ?
[TRACE] org.hibernate.type - binding parameter [1] as [VARCHAR] - [PENDING]
```

**Watch for N+1**: If you see multiple SELECT queries in a loop, that's N+1.

**Watch for OFFSET**: If you see `OFFSET 100000` on a deep page, switch to keyset pagination.

---

## 11. Style and conventions

| Aspect | Rule |
|---|---|
| ID type | `UUID`, never auto-increment `Long` |
| Enums | `@Enumerated(EnumType.STRING)`, never `ORDINAL` |
| Collections | Initialize inline: `= new ArrayList<>()`; never null |
| Lazy loading | `@ManyToOne(fetch = LAZY)` always; `@OneToMany(fetch = LAZY)` default |
| Orphans | `@OneToMany(..., orphanRemoval = true)` to clean children |
| Constructor | Protected no-arg only (JPA requirement); hide from app |
| Setters | Never on entities; use behavior methods instead |
| N+1 fix | `JOIN FETCH` for singles, `@EntityGraph` for lists, projections for reads |
| Pagination | Use `Pageable` always; switch to keyset on deep pages |
| Batching | Enable `hibernate.jdbc.batch_size`; avoid `GenerationType.IDENTITY` |
| Transactions | `@Transactional` on service methods (application layer) |
| Imports | No wildcards |
| Naming | `PascalCase` entities, `SNAKE_CASE` columns, `camelCase` getters |

---

## 12. Gotchas summary

| Problem | Solution |
|---|---|
| N+1 queries | Use `JOIN FETCH` or `@EntityGraph` |
| Deep OFFSET slow | Switch to keyset pagination |
| Enum reordering breaks DB | Use `EnumType.STRING` |
| Lazy loading in view | Fetch eagerly or use projection |
| Batching silently off | Avoid `GenerationType.IDENTITY` → use UUID |
| Orphaned child records | Add `orphanRemoval = true` |
| Bidirectional unsync | Use helper methods (`addItem()`) |
| No-arg constructor exposed | Use `protected` and factory methods |

---

## Final notes

- **Minimum version**: Spring Boot 3.3+, Java 21, H2 for Claude Code.
- **No Lombok**: Write explicit constructors and getters; Lombok hides JPA issues.
- **Entity isolation**: Entities never leave the persistence adapter; map to domain objects.
- **Performance first**: Always check SQL logging; test N+1 with small datasets.
- **Transactions**: Applied at service/application layer, not repository.
- **Records for immutable projections**: Use DTO records for API responses.
- **Official docs**: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/

---

## References

- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Hibernate ORM: https://docs.jboss.org/hibernate/orm/current/userguide/
- Java Persistence API: https://jakarta.ee/specifications/persistence/
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview