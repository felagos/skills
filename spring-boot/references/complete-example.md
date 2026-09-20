# Complete example — Product CRUD (Clean/Hexagonal Architecture)

Full runnable reference for a `Product` resource: domain → application → infrastructure
(web + persistence) → tests. Assumes Gradle + Log4j2 + H2 (swap the datasource/driver per
the database the user chose if the user picked Postgres/MySQL instead), with
`application.properties` and `schema.sql` exactly as in project-setup.md §4–§5.

```
my-spring-app/
├── build.gradle
├── src/main/java/com/example/
│   ├── Application.java
│   ├── domain/
│   │   ├── model/{Product,Order,OrderLine,OrderStatus}.java
│   │   └── repository/ProductRepository.java
│   ├── application/
│   │   ├── usecase/{CreateProductUseCase,FindProductUseCase,DeleteProductUseCase}.java
│   │   └── exception/ResourceNotFoundException.java
│   ├── infrastructure/web/
│   │   ├── controller/{ProductController,GlobalExceptionHandler}.java
│   │   ├── dto/{CreateProductRequest,ProductResponse}.java
│   │   └── mapper/ProductWebMapper.java
│   └── infrastructure/persistence/
│       ├── entity/ProductEntity.java
│       ├── repository/{ProductJpaRepository,ProductRepositoryAdapter}.java
│       └── mapper/ProductPersistenceMapper.java
├── src/main/resources/
│   ├── application.properties
│   ├── schema.sql
│   └── log4j2.xml
└── src/test/java/...
```

**Run**: `./gradlew bootRun` → `http://localhost:8080/api/v1/products`

---

## §1. Domain layer — pure Java, zero framework dependencies

### Domain model (record for immutable data)

```java
package com.example.domain.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

// record: immutable value object
public record Product(UUID id, String name, BigDecimal price, UUID categoryId, Instant createdAt) {}
```

### Domain model (class for mutable aggregate)

```java
package com.example.domain.model;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

// class: aggregate with behavior
public class Order {
    private UUID id;
    private OrderStatus status;
    private List<OrderLine> lines;
    private Instant createdAt;

    public Order(UUID id, OrderStatus status, List<OrderLine> lines, Instant createdAt) {
        this.id        = id;
        this.status    = status;
        this.lines     = new ArrayList<>(lines);
        this.createdAt = createdAt;
    }

    public UUID getId()                 { return id; }
    public OrderStatus getStatus()      { return status; }
    public List<OrderLine> getLines()   { return List.copyOf(lines); }
    public Instant getCreatedAt()       { return createdAt; }

    public void confirm() {
        if (status != OrderStatus.PENDING)
            throw new IllegalStateException("Only PENDING orders can be confirmed");
        this.status = OrderStatus.CONFIRMED;
    }

    public void cancel() {
        if (status == OrderStatus.COMPLETED || status == OrderStatus.CANCELLED)
            throw new IllegalStateException("Cannot cancel " + status + " order");
        this.status = OrderStatus.CANCELLED;
    }
}
```

```java
package com.example.domain.model;

public enum OrderStatus {
    PENDING, CONFIRMED, COMPLETED, CANCELLED
}
```

```java
package com.example.domain.model;

public record OrderLine(Long id, Product product, int quantity) {}
```

### Repository port (interface, no Spring annotations)

```java
package com.example.domain.repository;

import com.example.domain.model.Product;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface ProductRepository {
    List<Product> findAll();
    Optional<Product> findById(UUID id);
    Product save(Product product);
    void deleteById(UUID id);
    boolean existsById(UUID id);
}
```

---

## §2. Application layer — use cases

One `@Component` class per use case. Never depend on DTOs, HTTP, or JPA.

### Custom exception (define this first — the use cases below import it)

```java
package com.example.application.exception;

public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) {
        super(message);
    }
}
```

### CreateProductUseCase

```java
package com.example.application.usecase;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

@Component
public class CreateProductUseCase {

    private static final Logger log = LoggerFactory.getLogger(CreateProductUseCase.class);

    private final ProductRepository productRepository;

    public CreateProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public Product execute(String name, BigDecimal price, UUID categoryId) {
        // UUID generated in code (not IDENTITY) so JDBC batching stays enabled
        var product = new Product(UUID.randomUUID(), name, price, categoryId, Instant.now());
        var saved = productRepository.save(product);
        log.info("Created product {}", saved.id());
        return saved;
    }
}
```

### FindProductUseCase

```java
package com.example.application.usecase;

import com.example.application.exception.ResourceNotFoundException;
import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;
import java.util.UUID;

@Component
public class FindProductUseCase {

    private final ProductRepository productRepository;

    public FindProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional(readOnly = true)
    public List<Product> findAll() {
        return productRepository.findAll();
    }

    @Transactional(readOnly = true)
    public Product findById(UUID id) {
        return productRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Product not found: " + id));
    }
}
```

### DeleteProductUseCase

```java
package com.example.application.usecase;

import com.example.application.exception.ResourceNotFoundException;
import com.example.domain.repository.ProductRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import java.util.UUID;

@Component
public class DeleteProductUseCase {

    private final ProductRepository productRepository;

    public DeleteProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public void execute(UUID id) {
        if (!productRepository.existsById(id))
            throw new ResourceNotFoundException("Product not found: " + id);
        productRepository.deleteById(id);
    }
}
```

---

## §3. Infrastructure layer — web adapter

### DTOs (records, with Bean Validation — requires `spring-boot-starter-validation`)

```java
package com.example.infrastructure.web.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.math.BigDecimal;
import java.util.UUID;

public record CreateProductRequest(
    @NotBlank(message = "Name is required") String name,
    @Positive(message = "Price must be positive") BigDecimal price,
    @NotNull(message = "Category ID is required") UUID categoryId
) {}
```

```java
package com.example.infrastructure.web.dto;

import java.math.BigDecimal;
import java.util.UUID;

public record ProductResponse(UUID id, String name, BigDecimal price) {}
```

### WebMapper (domain → DTO)

The request side needs no mapper method: the controller passes the request's fields
straight to the use case, which owns id/timestamp generation.

```java
package com.example.infrastructure.web.mapper;

import com.example.domain.model.Product;
import com.example.infrastructure.web.dto.ProductResponse;
import org.springframework.stereotype.Component;

@Component
public class ProductWebMapper {

    public ProductResponse toResponse(Product product) {
        return new ProductResponse(product.id(), product.name(), product.price());
    }
}
```

### REST Controller

```java
package com.example.infrastructure.web.controller;

import com.example.application.usecase.CreateProductUseCase;
import com.example.application.usecase.FindProductUseCase;
import com.example.application.usecase.DeleteProductUseCase;
import com.example.infrastructure.web.dto.CreateProductRequest;
import com.example.infrastructure.web.dto.ProductResponse;
import com.example.infrastructure.web.mapper.ProductWebMapper;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import java.util.List;
import java.util.UUID;

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
    public ResponseEntity<List<ProductResponse>> listAll() {
        var products = findProductUseCase.findAll().stream()
            .map(mapper::toResponse)
            .toList();
        return ResponseEntity.ok(products);
    }

    @GetMapping("/{id}")
    public ResponseEntity<ProductResponse> getById(@PathVariable UUID id) {
        var product = findProductUseCase.findById(id);
        return ResponseEntity.ok(mapper.toResponse(product));
    }

    @PostMapping
    public ResponseEntity<ProductResponse> create(
            @Valid @RequestBody CreateProductRequest request) {
        var created = createProductUseCase.execute(
            request.name(), request.price(), request.categoryId()
        );
        return ResponseEntity.status(HttpStatus.CREATED)
            .body(mapper.toResponse(created));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable UUID id) {
        deleteProductUseCase.execute(id);
        return ResponseEntity.noContent().build();
    }
}
```

### Global exception handler (handles both 404 and validation 400)

```java
package com.example.infrastructure.web.controller;

import com.example.application.exception.ResourceNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

@ControllerAdvice
public class GlobalExceptionHandler {

    public record ErrorResponse(
        int status,
        String message,
        LocalDateTime timestamp
    ) {}

    public record ValidationErrorResponse(
        int status,
        Map<String, String> fieldErrors,
        LocalDateTime timestamp
    ) {}

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException e) {
        var error = new ErrorResponse(404, e.getMessage(), LocalDateTime.now());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ValidationErrorResponse> handleValidation(MethodArgumentNotValidException e) {
        var fieldErrors = new LinkedHashMap<String, String>();
        e.getBindingResult().getFieldErrors()
            .forEach(fe -> fieldErrors.put(fe.getField(), fe.getDefaultMessage()));
        var error = new ValidationErrorResponse(400, fieldErrors, LocalDateTime.now());
        return ResponseEntity.badRequest().body(error);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception e) {
        var error = new ErrorResponse(500, "Internal server error", LocalDateTime.now());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}
```

---

## §4. Infrastructure layer — persistence adapter

### JPA Entity (no setters, protected constructor, factories — conventions.md §9)

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
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

    // Protected no-arg constructor (JPA requirement, hidden from app code)
    protected ProductEntity() {}

    // Static factory for BRAND NEW products — generates id + timestamp
    public static ProductEntity create(String name, BigDecimal price, UUID categoryId) {
        return reconstitute(UUID.randomUUID(), name, price, categoryId, Instant.now());
    }

    // Used ONLY by ProductPersistenceMapper to rebuild an entity from domain data,
    // preserving the original id/timestamp.
    public static ProductEntity reconstitute(
            UUID id, String name, BigDecimal price, UUID categoryId, Instant createdAt) {
        var product = new ProductEntity();
        product.id = id;
        product.name = name;
        product.price = price;
        product.categoryId = categoryId;
        product.createdAt = createdAt;
        return product;
    }

    public UUID getId()           { return id; }
    public String getName()       { return name; }
    public BigDecimal getPrice()  { return price; }
    public UUID getCategoryId()   { return categoryId; }
    public Instant getCreatedAt() { return createdAt; }
}
```

### Spring Data JPA repository (package-private)

```java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.UUID;

// package-private: never inject outside this package
interface ProductJpaRepository extends JpaRepository<ProductEntity, UUID> {}
```

### PersistenceMapper (domain ↔ entity)

```java
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
            entity.getCategoryId(),
            entity.getCreatedAt()
        );
    }

    public ProductEntity toEntity(Product domain) {
        // Always reconstitute(): no setters exist, and a bare `new ProductEntity()`
        // would be all nulls.
        return ProductEntity.reconstitute(
            domain.id(),
            domain.name(),
            domain.price(),
            domain.categoryId(),
            domain.createdAt()
        );
    }
}
```

### Repository adapter (implements domain port)

```java
package com.example.infrastructure.persistence.repository;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import com.example.infrastructure.persistence.mapper.ProductPersistenceMapper;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public class ProductRepositoryAdapter implements ProductRepository {

    private final ProductJpaRepository jpaRepository;
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
    public Optional<Product> findById(UUID id) {
        return jpaRepository.findById(id).map(mapper::toDomain);
    }

    @Override
    public Product save(Product product) {
        var entity = mapper.toEntity(product);
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

## §5. Application entry point

```java
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

---

## §6. Testing

### Unit test (plain JUnit, no Spring)

```java
package com.example.application.usecase;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CreateProductUseCaseTest {

    private final ProductRepository repository = mock(ProductRepository.class);
    private final CreateProductUseCase useCase = new CreateProductUseCase(repository);

    @Test
    void shouldSaveAndReturnProduct() {
        var categoryId = UUID.randomUUID();
        var expected = new Product(UUID.randomUUID(), "Widget", new BigDecimal("9.99"), categoryId, Instant.now());
        when(repository.save(any())).thenReturn(expected);

        var result = useCase.execute("Widget", new BigDecimal("9.99"), categoryId);

        assertThat(result.id()).isEqualTo(expected.id());
        verify(repository).save(any(Product.class));
    }
}
```

### Integration test (full Spring context)

```java
package com.example;

import com.example.infrastructure.web.dto.CreateProductRequest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import java.util.UUID;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class ProductControllerIntegrationTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void shouldCreateAndReturnProduct() throws Exception {
        var request = new CreateProductRequest("Widget", BigDecimal.valueOf(9.99), UUID.randomUUID());

        mockMvc.perform(post("/api/v1/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("Widget"))
            .andExpect(jsonPath("$.price").value(9.99));
    }

    @Test
    void shouldReturn400OnInvalidPayload() throws Exception {
        var request = new CreateProductRequest("", BigDecimal.valueOf(-1), null);

        mockMvc.perform(post("/api/v1/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isBadRequest());
    }
}
```

Run tests: `./gradlew test`