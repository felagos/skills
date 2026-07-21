# Complete example — Product CRUD (Clean/Hexagonal Architecture)

Full runnable reference for a `Product` resource: domain → application → infrastructure
(web + persistence) → tests. Assumes Gradle + Log4j2 + H2 (swap the datasource/driver per
the answer from SKILL.md §0 if the user picked Postgres/MySQL instead).

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

// record: immutable value object
public record Product(Long id, String name, BigDecimal price, Long categoryId) {}
```

### Domain model (class for mutable aggregate)

```java
package com.example.domain.model;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

// class: aggregate with behavior
public class Order {
    private Long id;
    private OrderStatus status;
    private List<OrderLine> lines;
    private LocalDateTime createdAt;

    public Order(Long id, OrderStatus status, List<OrderLine> lines, LocalDateTime createdAt) {
        this.id        = id;
        this.status    = status;
        this.lines     = new ArrayList<>(lines);
        this.createdAt = createdAt;
    }

    public Long getId()                 { return id; }
    public OrderStatus getStatus()      { return status; }
    public List<OrderLine> getLines()   { return List.copyOf(lines); }
    public LocalDateTime getCreatedAt() { return createdAt; }

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

public interface ProductRepository {
    List<Product> findAll();
    Optional<Product> findById(Long id);
    Product save(Product product);
    void deleteById(Long id);
    boolean existsById(Long id);
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

@Component
public class CreateProductUseCase {

    private static final Logger log = LoggerFactory.getLogger(CreateProductUseCase.class);

    private final ProductRepository productRepository;

    public CreateProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public Product execute(String name, BigDecimal price, Long categoryId) {
        var product = new Product(null, name, price, categoryId);
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
    public Product findById(Long id) {
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

@Component
public class DeleteProductUseCase {

    private final ProductRepository productRepository;

    public DeleteProductUseCase(ProductRepository productRepository) {
        this.productRepository = productRepository;
    }

    @Transactional
    public void execute(Long id) {
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

public record CreateProductRequest(
    @NotBlank(message = "Name is required") String name,
    @Positive(message = "Price must be positive") BigDecimal price,
    @NotNull(message = "Category ID is required") Long categoryId
) {}
```

```java
package com.example.infrastructure.web.dto;

import java.math.BigDecimal;

public record ProductResponse(Long id, String name, BigDecimal price) {}
```

### WebMapper (DTO ↔ domain)

```java
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
import org.springframework.web.bind.annotation.*;
import java.util.List;

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
    public ResponseEntity<ProductResponse> getById(@PathVariable Long id) {
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
    public ResponseEntity<Void> delete(@PathVariable Long id) {
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

### JPA Entity

```java
package com.example.infrastructure.persistence.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;

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

    public void setId(Long id)                 { this.id = id; }
    public void setName(String name)           { this.name = name; }
    public void setPrice(BigDecimal price)     { this.price = price; }
    public void setCategoryId(Long categoryId) { this.categoryId = categoryId; }
}
```

### Spring Data JPA repository (package-private)

```java
package com.example.infrastructure.persistence.repository;

import com.example.infrastructure.persistence.entity.ProductEntity;
import org.springframework.data.jpa.repository.JpaRepository;

// package-private: never inject outside this package
interface ProductJpaRepository extends JpaRepository<ProductEntity, Long> {}
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

### Repository adapter (implements domain port)

```java
package com.example.infrastructure.persistence.repository;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import com.example.infrastructure.persistence.mapper.ProductPersistenceMapper;
import org.springframework.stereotype.Repository;
import java.util.List;
import java.util.Optional;

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
    public Optional<Product> findById(Long id) {
        return jpaRepository.findById(id).map(mapper::toDomain);
    }

    @Override
    public Product save(Product product) {
        var entity = mapper.toEntity(product);
        var saved = jpaRepository.save(entity);
        return mapper.toDomain(saved);
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

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class CreateProductUseCaseTest {

    private final ProductRepository repository = mock(ProductRepository.class);
    private final CreateProductUseCase useCase = new CreateProductUseCase(repository);

    @Test
    void shouldSaveAndReturnProduct() {
        var expected = new Product(1L, "Widget", new BigDecimal("9.99"), 1L);
        when(repository.save(any())).thenReturn(expected);

        var result = useCase.execute("Widget", new BigDecimal("9.99"), 1L);

        assertThat(result.id()).isEqualTo(1L);
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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class ProductControllerIntegrationTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void shouldCreateAndReturnProduct() throws Exception {
        var request = new CreateProductRequest("Widget", BigDecimal.valueOf(9.99), 1L);

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