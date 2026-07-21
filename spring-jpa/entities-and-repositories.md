# Entities, repositories, mappers — full reference

Corrected, internally-consistent code for the `Order` aggregate (root `OrderEntity` +
child `OrderItemEntity`) plus a supporting `ProductEntity`. Assumes a domain `Order` /
`OrderLine` shaped to match these entities field-for-field (adjust accessor names to your
actual domain model — the mapper in §5 is the one place that needs to change if it differs):

```java
// domain/model/Order.java  (shape assumed by the mapper below)
record Order(UUID id, String customerEmail, OrderStatus status,
             List<OrderLine> lines, Instant createdAt, Instant updatedAt) {}

// domain/model/OrderLine.java
record OrderLine(Long id, UUID productId, int quantity, BigDecimal unitPrice) {}

// domain/model/OrderStatus.java — same constant names as the entity-level enum
enum OrderStatus { PENDING, CONFIRMED, COMPLETED, CANCELLED }
```

---

## §1. OrderEntity (aggregate root)

```java
// infrastructure/persistence/entity/OrderEntity.java
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

    @Enumerated(EnumType.STRING)  // STRING, never ORDINAL
    @Column(nullable = false)
    private OrderStatus status;

    @OneToMany(
        mappedBy = "order",
        cascade = CascadeType.ALL,
        orphanRemoval = true,       // removes child when removed from collection
        fetch = FetchType.LAZY
    )
    private List<OrderItemEntity> items = new ArrayList<>();

    @Column(updatable = false, nullable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    // Protected no-arg constructor (JPA requirement, hidden from app code)
    protected OrderEntity() {}

    // Static factory for BRAND NEW orders — always generates id + timestamps
    public static OrderEntity create(String customerEmail) {
        var order = new OrderEntity();
        order.id = UUID.randomUUID();
        order.customerEmail = customerEmail;
        order.status = OrderStatus.PENDING;
        order.createdAt = Instant.now();
        order.updatedAt = Instant.now();
        return order;
    }

    // Static factory used ONLY by OrderPersistenceMapper to rebuild an entity from
    // domain data — preserves the original id/timestamps instead of generating new
    // ones. Must be public: the mapper lives in a different package than this entity.
    public static OrderEntity reconstitute(
            UUID id, String customerEmail, OrderStatus status,
            Instant createdAt, Instant updatedAt) {
        var order = new OrderEntity();
        order.id = id;
        order.customerEmail = customerEmail;
        order.status = status;
        order.createdAt = createdAt;
        order.updatedAt = updatedAt;
        return order;
    }

    // Getters (no setters on entities — use behavior methods instead)
    public UUID getId()                     { return id; }
    public String getCustomerEmail()        { return customerEmail; }
    public OrderStatus getStatus()          { return status; }
    public List<OrderItemEntity> getItems() { return List.copyOf(items); }
    public Instant getCreatedAt()           { return createdAt; }
    public Instant getUpdatedAt()           { return updatedAt; }

    // Behavior methods (domain logic on the entity)
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
```

```java
// infrastructure/persistence/entity/OrderStatus.java — separate file: a .java file
// can only have one public top-level type, so this can't live inside OrderEntity.java.
package com.example.infrastructure.persistence.entity;

public enum OrderStatus {
    PENDING, CONFIRMED, COMPLETED, CANCELLED
}
```

### OrderItemEntity (child)

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.util.UUID;

@Entity
@Table(name = "order_items")
public class OrderItemEntity {

    // Long/IDENTITY here is a deliberate exception to "UUID for entities": this is a
    // child row never queried by id directly and rarely bulk-inserted in large batches.
    // If you DO start bulk-inserting order items, switch this to GenerationType.UUID —
    // IDENTITY disables JDBC batching because Hibernate needs the generated key per row.
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)  // LAZY always on @ManyToOne
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

    // Used only by OrderPersistenceMapper to rebuild an item with its original id
    // (null id is fine for a not-yet-persisted item — IDENTITY assigns it on insert).
    public static OrderItemEntity reconstitute(Long id, UUID productId, Integer quantity, BigDecimal unitPrice) {
        var item = new OrderItemEntity();
        item.id = id;
        item.productId = productId;
        item.quantity = quantity;
        item.unitPrice = unitPrice;
        return item;
    }

    public Long getId()              { return id; }
    public OrderEntity getOrder()    { return order; }
    public UUID getProductId()       { return productId; }
    public Integer getQuantity()     { return quantity; }
    public BigDecimal getUnitPrice() { return unitPrice; }

    // For bidirectional sync only (package-private — same package as OrderEntity)
    void setOrder(OrderEntity order) { this.order = order; }
}
```

---

## §2. ProductEntity

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

    public UUID getId()           { return id; }
    public String getName()       { return name; }
    public BigDecimal getPrice()  { return price; }
    public UUID getCategoryId()   { return categoryId; }
    public Instant getCreatedAt() { return createdAt; }
}
```

---

## §3. Repository (Spring Data JPA)

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

// package-private: never injected outside this package
interface OrderJpaRepository extends JpaRepository<OrderEntity, UUID> {

    List<OrderEntity> findByStatus(OrderStatus status);

    boolean existsByIdAndStatus(UUID id, OrderStatus status);

    Page<OrderEntity> findByStatus(OrderStatus status, Pageable pageable);

    // N+1 FIX: JOIN FETCH for a single entity
    @Query("SELECT o FROM OrderEntity o JOIN FETCH o.items WHERE o.id = :id")
    Optional<OrderEntity> findByIdWithItems(@Param("id") UUID id);

    // N+1 FIX: JOIN FETCH + DISTINCT for a list (avoids duplicate rows from the join)
    @Query("SELECT DISTINCT o FROM OrderEntity o JOIN FETCH o.items WHERE o.status = :status")
    List<OrderEntity> findByStatusWithItems(@Param("status") OrderStatus status);

    // N+1 FIX (alternative): @EntityGraph — cleaner than @Query for simple cases
    @EntityGraph(attributePaths = {"items"})
    List<OrderEntity> findByStatusAndCustomerEmail(OrderStatus status, String customerEmail);

    // KEYSET pagination (O(1) vs O(N) for deep pages)
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

    // Interface-based projection — plain property reads only, no computed columns
    List<OrderSummaryProjection> findByCustomerEmail(String customerEmail);
}

// Interface projection: Spring Data proxies this and only selects the matching columns.
// Only plain entity properties here — computed values (SIZE(), aggregates) need the
// class/record-based (DTO) projection shown in the N+1 reference below instead.
interface OrderSummaryProjection {
    UUID getId();
    String getCustomerEmail();
    OrderStatus getStatus();
    Instant getCreatedAt();
}
```

### Repository adapter (implements domain port)

```java
package com.example.infrastructure.persistence.repository;

import com.example.domain.model.Order;
import com.example.domain.repository.OrderRepository;
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

    public OrderRepositoryAdapter(OrderJpaRepository jpaRepository, OrderPersistenceMapper mapper) {
        this.jpaRepository = jpaRepository;
        this.mapper = mapper;
    }

    @Override
    public List<Order> findAll() {
        return jpaRepository.findAll().stream().map(mapper::toDomain).toList();
    }

    @Override
    public Optional<Order> findById(UUID id) {
        return jpaRepository.findById(id).map(mapper::toDomain);
    }

    @Override
    public Optional<Order> findByIdWithItems(UUID id) {
        return jpaRepository.findByIdWithItems(id).map(mapper::toDomain);
    }

    @Override
    public Page<Order> findByStatus(com.example.domain.model.OrderStatus status, Pageable pageable) {
        var entityStatus = OrderStatus.valueOf(status.name());
        var page = jpaRepository.findByStatus(entityStatus, pageable);
        return new PageImpl<>(
            page.getContent().stream().map(mapper::toDomain).toList(),
            pageable,
            page.getTotalElements()
        );
    }

    @Override
    public List<Order> findNextPage(
            com.example.domain.model.OrderStatus status,
            Instant lastCreatedAt, UUID lastId, Pageable pageable) {
        var entityStatus = OrderStatus.valueOf(status.name());
        return jpaRepository.findNextPageByStatus(entityStatus, lastCreatedAt, lastId, pageable)
            .stream().map(mapper::toDomain).toList();
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

## §4. N+1 prevention patterns (side-by-side)

```java
// PROBLEM
List<OrderEntity> orders = jpaRepository.findByStatus(OrderStatus.PENDING);
for (var order : orders) {
    System.out.println(order.getItems().size());  // triggers N extra SELECTs
}

// FIX 1: JOIN FETCH (see findByStatusWithItems in §3)
// FIX 2: @EntityGraph (see findByStatusAndCustomerEmail in §3)

// FIX 3: DTO/record projection when the query needs a COMPUTED value (SIZE, aggregates) —
// interface projections (OrderSummaryProjection in §3) can't do this cleanly.
public record OrderSummary(UUID id, String customerEmail, long itemCount) {}
```

```java
// In the repository — full package path required for JPQL constructor expressions
@Query("""
    SELECT new com.example.infrastructure.persistence.repository.OrderSummary(
        o.id, o.customerEmail, SIZE(o.items)
    )
    FROM OrderEntity o
    WHERE o.status = :status
    """)
List<OrderSummary> findSummariesByStatus(@Param("status") OrderStatus status);
```

Rule of thumb: **interface projection** for a plain subset of columns; **record/DTO
projection with `SELECT new ...`** the moment the query computes anything (`SIZE`, `SUM`,
`COUNT`, string concatenation). Don't reference a DTO class in `SELECT new` that doesn't
actually exist in that package — the query fails at startup with a JPQL validation error.

---

## §5. Mapper (entity ↔ domain) — the piece most drafts get wrong

```java
package com.example.infrastructure.persistence.mapper;

import com.example.domain.model.Order;
import com.example.domain.model.OrderLine;
import com.example.domain.model.OrderStatus;
import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderItemEntity;
import org.springframework.stereotype.Component;

@Component
public class OrderPersistenceMapper {

    public Order toDomain(OrderEntity entity) {
        if (entity == null) return null;

        var lines = entity.getItems().stream()
            .map(item -> new OrderLine(
                item.getId(),
                item.getProductId(),
                item.getQuantity(),
                item.getUnitPrice()
            ))
            .toList();

        return new Order(
            entity.getId(),
            entity.getCustomerEmail(),
            OrderStatus.valueOf(entity.getStatus().name()),   // entity enum → domain enum
            lines,
            entity.getCreatedAt(),
            entity.getUpdatedAt()
        );
    }

    public OrderEntity toEntity(Order domain) {
        if (domain == null) return null;

        // Always go through reconstitute() — a bare `new OrderEntity()` compiles but
        // leaves every field null (no setters exist), which fails NOT NULL constraints
        // on save. reconstitute() preserves the original id/timestamps; it's distinct
        // from create(), which is only for brand-new orders.
        var entity = OrderEntity.reconstitute(
            domain.id(),
            domain.customerEmail(),
            com.example.infrastructure.persistence.entity.OrderStatus.valueOf(domain.status().name()),
            domain.createdAt(),
            domain.updatedAt()
        );

        domain.lines().forEach(line -> entity.addItem(
            OrderItemEntity.reconstitute(line.id(), line.productId(), line.quantity(), line.unitPrice())
        ));

        return entity;
    }
}
```

---

## §6. Pagination patterns

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

// SQL generated:
// SELECT * FROM orders WHERE status = 'PENDING' ORDER BY created_at DESC LIMIT 20 OFFSET 0
// Page 1: fast. Page 5000: DB scans/discards 100,000 rows before returning 20 — slow.
```

### Keyset pagination (constant-time, for infinite scroll)

```java
public record OrderCursor(java.time.Instant lastCreatedAt, UUID lastId) {}

@GetMapping("/scroll")
public ResponseEntity<List<OrderResponse>> scroll(
        @RequestParam OrderCursor cursor,
        @RequestParam(defaultValue = "20") int size) {
    var orders = orderService.findNextPage(
        OrderStatus.PENDING, cursor.lastCreatedAt(), cursor.lastId(), size
    );
    return ResponseEntity.ok(orders.stream().map(mapper::toResponse).toList());
}

// Repository query: see findNextPageByStatus in §3.
// SQL generated:
// SELECT * FROM orders WHERE status = 'PENDING'
//   AND (created_at < ? OR (created_at = ? AND id < ?))
// ORDER BY created_at DESC, id DESC LIMIT 20
// Always scans ~20 rows regardless of cursor depth — this is why idx_orders_keyset exists.
```

---

## §7. Batch inserts

```java
// GOOD: batches 50 at a time (5 round-trips for 250 items) — works because Product/Order
// use UUID ids, generated in application code before save(), not by the database.
@Service
public class BulkOrderService {

    @Transactional
    public void createOrders(List<Order> orders) {
        for (var order : orders) {
            orderRepository.save(order);  // batched
        }
    }
}
```

**Gotcha**: `GenerationType.IDENTITY` disables batching silently — Hibernate must know the
generated key immediately after each insert, so it can't queue rows into a batch. This is
why aggregate roots (`OrderEntity`, `ProductEntity`) use `UUID` ids generated in code, while
`OrderItemEntity` — which isn't typically bulk-inserted on its own — keeps `IDENTITY` for
simplicity (see §1's comment on `OrderItemEntity`). If you start bulk-inserting order items
directly, switch that id strategy to `GenerationType.UUID` too.

---

## §8. Testing JPA (slice test, fast)

```java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.OrderEntity;
import com.example.infrastructure.persistence.entity.OrderStatus;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.test.autoconfigure.orm.jpa.TestEntityManager;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest  // Only loads the JPA context, no web/service layer
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
        var item = com.example.infrastructure.persistence.entity.OrderItemEntity
            .create(java.util.UUID.randomUUID(), 2, java.math.BigDecimal.valueOf(19.99));
        order.addItem(item);
        em.persistAndFlush(order);

        em.clear();  // clear persistence context to force a real DB query

        var loaded = repository.findByIdWithItems(order.getId()).orElseThrow();

        assertThat(loaded.getItems()).hasSize(1);
    }
}
```

Run: `./gradlew test`