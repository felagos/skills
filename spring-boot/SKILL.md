---
name: spring-boot
description: >
  Skill for writing Spring Boot applications with Java 21 following Clean / Hexagonal
  Architecture. Domain layer holds pure objects and repository port interfaces. Application
  layer holds use cases (one class per use case) that only depend on the domain. Infrastructure
  holds two adapters: web (controller, DTOs, WebMapper) and persistence (JPA entity,
  JpaRepository, PersistenceMapper, RepositoryAdapter). DTOs never cross into application or
  domain. JPA entities never leave the persistence adapter. Mappers translate at each boundary.
  No Lombok. Constructor injection always. Records for immutable types.
  Activate on any mention of Spring, Spring Boot, use case, service, controller, repository,
  entity, REST, JPA, dependency injection, clean architecture, hexagonal, or any JVM backend task.
---

# Spring Boot + Java 21 — Clean / Hexagonal Architecture

You are a senior Java developer who writes modern Spring Boot applications using Java 21 with a strict Clean Architecture. Apply every convention in this skill to all code you generate or review.

---

## Architecture overview

```
src/main/java/com/example/
├── domain/
│   ├── model/
│   │   └── Product.java                         ← pure domain object (no framework deps)
│   └── repository/
│       └── ProductRepository.java               ← repository port (interface, no Spring)
│
├── application/
│   └── usecase/
│       ├── CreateProductUseCase.java             ← one class per use case
│       ├── FindProductUseCase.java
│       └── DeleteProductUseCase.java
│
└── infrastructure/
    ├── web/                                      ← input adapter
    │   ├── controller/
    │   │   └── ProductController.java
    │   ├── dto/
    │   │   ├── CreateProductRequest.java         ← input DTO (record)
    │   │   └── ProductResponse.java              ← output DTO (record)
    │   └── mapper/
    │       └── ProductWebMapper.java             ← DTO ↔ domain (@Component)
    │
    └── persistence/                              ← output adapter
        ├── entity/
        │   └── ProductEntity.java               ← @Entity (JPA only)
        ├── repository/
        │   ├── ProductJpaRepository.java         ← package-private JpaRepository
        │   └── ProductRepositoryAdapter.java     ← implements domain port (@Repository)
        └── mapper/
            └── ProductPersistenceMapper.java     ← domain ↔ entity (@Component)
```

**Layer rules (never break these):**

| Layer | Knows about | Must NOT know about |
|---|---|---|
| `domain` | itself | Spring, JPA, DTOs |
| `application` | domain | Spring, JPA, DTOs, HTTP |
| `infrastructure/web` | domain, application use cases | JPA, entities |
| `infrastructure/persistence` | domain, JPA | DTOs, use cases, controllers |

---

## 0. Before coding — Consult Context7

**Always** consult the official documentation via MCP Context7 before using any Spring Boot API:

```
resolve-library-id → "spring-boot", "spring-framework", "spring-data"
get-library-docs   → "Dependency Injection", "Spring Data JPA", "Spring MVC",
                     "Spring Security", "@Transactional"
```

If the tool is unavailable, explicitly inform the user.

---

## 1. Domain layer — pure Java, zero framework dependencies

### Domain model

```java
package com.example.domain.model;

// ✅ record for immutable domain objects (value objects, read-only aggregates)
public record Product(Long id, String name, BigDecimal price, Long categoryId) {}

// ✅ class for mutable domain objects (aggregates with behaviour)
public class Order {
    private Long id;
    private OrderStatus status;
    private List<OrderLine> lines;

    public Order(Long id, OrderStatus status, List<OrderLine> lines) {
        this.id     = id;
        this.status = status;
        this.lines  = new ArrayList<>(lines);
    }

    public Long getId()               { return id; }
    public OrderStatus getStatus()    { return status; }
    public List<OrderLine> getLines() { return List.copyOf(lines); }

    public void confirm() {
        if (status != OrderStatus.PENDING)
            throw new IllegalStateException("Only PENDING orders can be confirmed");
        this.status = OrderStatus.CONFIRMED;
    }
}
```

### Repository port — interface only, no Spring annotations

```java
package com.example.domain.repository;

import com.example.domain.model.Product;
import java.util.List;
import java.util.Optional;

public interface ProductRepository {
    List<Product> findAll();
    Optional<Product> findById(Long id);
    Product save(Product product);
    void deleteById(Long id);
    boolean existsById(Long id);
}
```

---

## 2. Application layer — use cases, domain only

One class per use case. Each use case is a `@Component` with a single `execute()` method. Use cases depend only on domain types and domain repository ports — never on DTOs, HTTP types, or JPA.

### Pattern

```java
package com.example.application.usecase;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class CreateProductUseCase {

    private final ProductRepository productRepository;

    public CreateProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public Product execute(Product product) {
        return productRepository.save(product);
    }
}
```

```java
@Component
public class FindProductUseCase {

    private final ProductRepository productRepository;

    public FindProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    public List<Product> findAll() {
        return productRepository.findAll();
    }

    public Product findById(Long id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product", id));
    }
}
```

```java
@Component
public class DeleteProductUseCase {

    private final ProductRepository productRepository;

    public DeleteProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public void execute(Long id) {
        if (!productRepository.existsById(id))
            throw new ResourceNotFoundException("Product", id);
        productRepository.deleteById(id);
    }
}
```

### Use case naming convention
| Operation | Class name |
|---|---|
| Create / register | `Create{Entity}UseCase` |
| Query one | `Find{Entity}ByIdUseCase` or `Find{Entity}UseCase` |
| Query many | `List{Entities}UseCase` or `Find{Entity}UseCase` |
| Update | `Update{Entity}UseCase` |
| Delete | `Delete{Entity}UseCase` |

---

## 3. Infrastructure — web adapter (input)

### DTOs — records, controller boundary only

```java
// infrastructure/web/dto/CreateProductRequest.java
package com.example.infrastructure.web.dto;

public record CreateProductRequest(
    @NotBlank String name,
    @Positive BigDecimal price,
    @NotNull Long categoryId
) {}

// infrastructure/web/dto/ProductResponse.java
package com.example.infrastructure.web.dto;

public record ProductResponse(Long id, String name, BigDecimal price) {}
```

### WebMapper — DTO ↔ domain

```java
// infrastructure/web/mapper/ProductWebMapper.java
package com.example.infrastructure.web.mapper;

import com.example.domain.model.Product;
import com.example.infrastructure.web.dto.CreateProductRequest;
import com.example.infrastructure.web.dto.ProductResponse;
import org.springframework.stereotype.Component;

@Component
public class ProductWebMapper {

    public Product toDomain(CreateProductRequest request) {
        return new Product(null, request.name(), request.price(), request.categoryId());
    }

    public ProductResponse toResponse(Product product) {
        return new ProductResponse(product.id(), product.name(), product.price());
    }
}
```

### Controller — injects use cases + WebMapper

```java
// infrastructure/web/controller/ProductController.java
package com.example.infrastructure.web.controller;

@RestController
@RequestMapping("/api/v1/products")
public class ProductController {

    private final CreateProductUseCase createProductUseCase;
    private final FindProductUseCase   findProductUseCase;
    private final DeleteProductUseCase deleteProductUseCase;
    private final ProductWebMapper     mapper;

    public ProductController(
            CreateProductUseCase createProductUseCase,
            FindProductUseCase findProductUseCase,
            DeleteProductUseCase deleteProductUseCase,
            ProductWebMapper mapper) {
        this.createProductUseCase = createProductUseCase;
        this.findProductUseCase   = findProductUseCase;
        this.deleteProductUseCase = deleteProductUseCase;
        this.mapper               = mapper;
    }

    @GetMapping
    public ResponseEntity<List<ProductResponse>> list() {
        var products = findProductUseCase.findAll().stream()
            .map(mapper::toResponse)
            .toList();
        return ResponseEntity.ok(products);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ProductResponse> get(@PathVariable Long id) {
        return ResponseEntity.ok(mapper.toResponse(findProductUseCase.findById(id)));
    }

    @PostMapping
    public ResponseEntity<ProductResponse> create(
            @Valid @RequestBody CreateProductRequest request) {
        var created = createProductUseCase.execute(mapper.toDomain(request));
        return ResponseEntity.status(HttpStatus.CREATED).body(mapper.toResponse(created));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        deleteProductUseCase.execute(id);
        return ResponseEntity.noContent().build();
    }
}
```

---

## 4. Infrastructure — persistence adapter (output)

### JPA Entity — no-arg constructor, no domain annotations

```java
// infrastructure/persistence/entity/ProductEntity.java
package com.example.infrastructure.persistence.entity;

@Entity
@Table(name = "products")
public class ProductEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    @Column(nullable = false)
    private BigDecimal price;

    @Column(name = "category_id", nullable = false)
    private Long categoryId;

    public ProductEntity() {}

    public Long getId()          { return id; }
    public String getName()      { return name; }
    public BigDecimal getPrice() { return price; }
    public Long getCategoryId()  { return categoryId; }

    public void setId(Long id)                { this.id = id; }
    public void setName(String name)          { this.name = name; }
    public void setPrice(BigDecimal price)    { this.price = price; }
    public void setCategoryId(Long categoryId){ this.categoryId = categoryId; }
}
```

### Spring Data JPA repository — package-private

```java
// infrastructure/persistence/repository/ProductJpaRepository.java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;

// package-private: never inject outside this package
interface ProductJpaRepository extends JpaRepository<ProductEntity, Long> {}
```

### PersistenceMapper — domain ↔ entity

```java
// infrastructure/persistence/mapper/ProductPersistenceMapper.java
package com.example.infrastructure.persistence.mapper;

import com.example.domain.model.Product;
import com.example.infrastructure.persistence.entity.ProductEntity;
import org.springframework.stereotype.Component;

@Component
public class ProductPersistenceMapper {

    public Product toDomain(ProductEntity entity) {
        return new Product(
            entity.getId(),
            entity.getName(),
            entity.getPrice(),
            entity.getCategoryId()
        );
    }

    public ProductEntity toEntity(Product domain) {
        var entity = new ProductEntity();
        entity.setId(domain.id());
        entity.setName(domain.name());
        entity.setPrice(domain.price());
        entity.setCategoryId(domain.categoryId());
        return entity;
    }
}
```

### Repository adapter — implements domain port

```java
// infrastructure/persistence/repository/ProductRepositoryAdapter.java
package com.example.infrastructure.persistence.repository;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import com.example.infrastructure.persistence.mapper.ProductPersistenceMapper;
import org.springframework.stereotype.Repository;

@Repository
public class ProductRepositoryAdapter implements ProductRepository {

    private final ProductJpaRepository    jpaRepository;
    private final ProductPersistenceMapper mapper;

    public ProductRepositoryAdapter(
            ProductJpaRepository jpaRepository,
            ProductPersistenceMapper mapper) {
        this.jpaRepository = jpaRepository;
        this.mapper        = mapper;
    }

    @Override
    public List<Product> findAll() {
        return jpaRepository.findAll().stream()
            .map(mapper::toDomain)
            .toList();
    }

    @Override
    public Optional<Product> findById(Long id) {
        return jpaRepository.findById(id).map(mapper::toDomain);
    }

    @Override
    public Product save(Product product) {
        return mapper.toDomain(jpaRepository.save(mapper.toEntity(product)));
    }

    @Override
    public void deleteById(Long id) {
        jpaRepository.deleteById(id);
    }

    @Override
    public boolean existsById(Long id) {
        return jpaRepository.existsById(id);
    }
}
```

---

## 5. Dependency injection — constructor only

**Forbidden**: `@Autowired` on fields or setters. Always use explicit constructor injection.

```java
// ❌ NEVER
@Autowired
private ProductRepository productRepository;

// ✅ ALWAYS
private final ProductRepository productRepository;

public CreateProductUseCase(ProductRepository productRepository) {
    this.productRepository = productRepository;
}
```

---

## 6. Style and conventions

| Aspect | Rule |
|---|---|
| Domain model | No Spring/JPA annotations; `record` if immutable, class if mutable |
| Repository port | Interface in `domain/repository/`; no `@Repository` |
| Use cases | One `@Component` class per use case in `application/usecase/` |
| DTOs | `record` in `infrastructure/web/dto/`; never cross into application/domain |
| JPA Entities | Class in `infrastructure/persistence/entity/`; never leave persistence |
| WebMapper | `@Component` in `infrastructure/web/mapper/`; DTO ↔ domain |
| PersistenceMapper | `@Component` in `infrastructure/persistence/mapper/`; domain ↔ entity |
| JpaRepository | `package-private` in `infrastructure/persistence/repository/` |
| Injection | Constructor only, `final` fields, no `@Autowired` |
| Transactions | `@Transactional` on use case write methods; `@Transactional(readOnly=true)` on reads |
| Nulls | Avoid; use `Optional` or throw a specific exception |
| Collections | `List.of()`, `Map.of()`, `Set.of()` for immutable collections |
| Imports | No wildcards |
| Naming | `camelCase` vars/methods, `PascalCase` classes, `SNAKE_CASE` constants |

---

## 7. Code generation order

When generating a new feature, always follow this order:

```
1. domain/model/{Entity}.java                          ← domain object
2. domain/repository/{Entity}Repository.java           ← port interface
3. application/usecase/Create{Entity}UseCase.java      ← use cases
4. application/usecase/Find{Entity}UseCase.java
5. infrastructure/persistence/entity/{Entity}Entity.java
6. infrastructure/persistence/mapper/{Entity}PersistenceMapper.java
7. infrastructure/persistence/repository/{Entity}JpaRepository.java
8. infrastructure/persistence/repository/{Entity}RepositoryAdapter.java
9. infrastructure/web/dto/Create{Entity}Request.java
10. infrastructure/web/dto/{Entity}Response.java
11. infrastructure/web/mapper/{Entity}WebMapper.java
12. infrastructure/web/controller/{Entity}Controller.java
```

---

## 8. Workflow with Context7

```
1. User requests a feature
2. → resolve-library-id("spring-boot") via Context7
3. → get-library-docs(libraryId, topic: "Spring Data JPA") via Context7
4. Follow the code generation order above
5. Apply var + functional style (streams, Optional) where appropriate
```

---

## 9. Testing strategy

| Component | Test type | Annotation |
|---|---|---|
| Use case | Unit test (no Spring) | plain JUnit + Mockito |
| Repository adapter | Slice test | `@DataJpaTest` |
| Controller | Slice test | `@WebMvcTest` |
| Full flow | Integration test | `@SpringBootTest` |

Use cases are instantiated directly with mock ports — no Spring context needed:

```java
class CreateProductUseCaseTest {

    private final ProductRepository productRepository = mock(ProductRepository.class);
    private final CreateProductUseCase useCase = new CreateProductUseCase(productRepository);

    @Test
    void shouldSaveAndReturnDomainProduct() {
        var input  = new Product(null, "Widget", new BigDecimal("9.99"), 1L);
        var saved  = new Product(1L,   "Widget", new BigDecimal("9.99"), 1L);
        when(productRepository.save(input)).thenReturn(saved);

        var result = useCase.execute(input);

        assertThat(result.id()).isEqualTo(1L);
        verify(productRepository).save(input);
    }
}
```

---

## Final notes

- **Minimum version**: Java 21 LTS + Spring Boot 3.x.
- **Context7**: Official documentation takes precedence over training knowledge.
- **No Lombok**: Write all constructors, getters, and methods explicitly.
- **Layer isolation**: DTOs never cross into application or domain. JPA entities never leave `infrastructure/persistence`. Domain objects are the shared language between all layers.
- **`@Transactional` placement**: on use case methods (not on repository adapters), since the transaction boundary belongs to the application layer.
