---
name: spring-boot-claude-code
description: >
  Skill for writing executable Spring Boot applications with Java 21 in Claude Code
  using Clean / Hexagonal Architecture. Domain layer holds pure objects and repository
  port interfaces. Application layer holds use cases (one per operation) depending only
  on domain. Infrastructure holds web adapter (controller, DTOs, WebMapper) and
  persistence adapter (JPA entity, JpaRepository, PersistenceMapper, RepositoryAdapter).
  DTOs never cross into application/domain. JPA entities never leave persistence.
  Includes Maven/Gradle setup for Claude Code terminal execution, logging, embedded
  database (H2), and complete runnable examples. No Lombok. Constructor injection always.
  Records for immutable types. Activate on Spring Boot, Spring, use case, service,
  controller, repository, entity, REST, JPA, clean architecture, hexagonal, or any
  JVM backend task in Claude Code.
---

# Spring Boot + Java 21 for Claude Code — Clean / Hexagonal Architecture

You are a senior Java developer writing modern, executable Spring Boot applications using
Java 21 with strict Clean Architecture in Claude Code environments (terminal, VS Code,
JetBrains, desktop). Apply every convention in this skill to all code you generate or review.

---

## Architecture overview

```
src/main/java/com/example/
├── domain/
│   ├── model/
│   │   └── Product.java                         ← pure domain object (no framework)
│   └── repository/
│       └── ProductRepository.java               ← repository port (interface)
│
├── application/
│   └── usecase/
│       ├── CreateProductUseCase.java
│       ├── FindProductUseCase.java
│       └── DeleteProductUseCase.java
│
└── infrastructure/
    ├── web/
    │   ├── controller/
    │   │   └── ProductController.java
    │   ├── dto/
    │   │   ├── CreateProductRequest.java
    │   │   └── ProductResponse.java
    │   └── mapper/
    │       └── ProductWebMapper.java
    │
    └── persistence/
        ├── entity/
        │   └── ProductEntity.java
        ├── repository/
        │   ├── ProductJpaRepository.java
        │   └── ProductRepositoryAdapter.java
        └── mapper/
            └── ProductPersistenceMapper.java

src/main/resources/
├── application.properties                       ← Spring Boot config (H2 for demo)
└── schema.sql                                   ← database init (optional)

pom.xml                                          ← Maven config (Spring Boot 3.x + Java 21)
```

**Layer rules (never break these):**

| Layer | Knows about | Must NOT know about |
|---|---|---|
| `domain` | itself | Spring, JPA, DTOs |
| `application` | domain | Spring, JPA, DTOs, HTTP |
| `infrastructure/web` | domain, application use cases | JPA, entities |
| `infrastructure/persistence` | domain, JPA | DTOs, use cases, controllers |

---

## 0. Claude Code context for Spring Boot

**Environment**: Claude Code runs Spring Boot applications on Linux/macOS/Windows via Maven/Gradle or `java -jar`.

**Key characteristics**:
- Tomcat or Netty embedded HTTP server listening on `localhost:8080` (or configured port).
- In-memory H2 database recommended for demos and testing (no external setup).
- Application lifecycle: start → handle requests → graceful shutdown.
- Logging via SLF4J + Logback output to console (not files).
- Single-instance, stateless: each run is isolated.
- Execution model: `mvn spring-boot:run` or `gradle bootRun` in terminal.

**Execution patterns**:
1. **Simple REST API demo**: Single aggregate, 3–4 endpoints, H2 database.
2. **CLI data processor**: Spring Boot app that reads input and produces output.
3. **Scheduled task**: Spring Boot with `@Scheduled` for batch processing.
4. **Integration test**: Full stack tested in `@SpringBootTest`.

---

## 1. Maven pom.xml — Spring Boot 3.x + Java 21 + H2

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>my-app</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>

    <name>My Spring Boot App</name>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.0</version>
        <relativePath/>
    </parent>

    <properties>
        <java.version>21</java.version>
        <maven.compiler.source>21</maven.compiler.source>
        <maven.compiler.target>21</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
    </properties>

    <dependencies>
        <!-- Spring Boot Web (REST API) -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>

        <!-- Spring Data JPA -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>

        <!-- H2 in-memory database (for demo / testing) -->
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>

        <!-- PostgreSQL driver (uncomment for production) -->
        <!--
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        -->

        <!-- Logging (SLF4J + Logback already included in spring-boot-starter) -->

        <!-- Testing -->
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <!-- Spring Boot Maven plugin for mvn spring-boot:run -->
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>

            <!-- Compiler plugin (Java 21) -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.11.0</version>
                <configuration>
                    <source>21</source>
                    <target>21</target>
                    <release>21</release>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

### Run with Maven:
```bash
mvn clean spring-boot:run
# → Server starts on http://localhost:8080
```

---

## 2. Gradle build.gradle — alternative to Maven

```gradle
plugins {
    id 'java'
    id 'org.springframework.boot' version '3.3.0'
    id 'io.spring.dependency-management' version '1.1.4'
}

group = 'com.example'
version = '1.0.0'
sourceCompatibility = '21'

repositories {
    mavenCentral()
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    runtimeOnly 'com.h2database:h2'
    
    testImplementation 'org.springframework.boot:spring-boot-starter-test'
}

tasks.named('test') {
    useJUnitPlatform()
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

### Run with Gradle:
```bash
./gradlew bootRun
# → Server starts on http://localhost:8080
```

---

## 3. application.properties — H2 + logging

```properties
# Server
server.port=8080
server.servlet.context-path=/

# Database: H2 in-memory (Claude Code friendly)
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true

# H2 console (optional: http://localhost:8080/h2-console)
spring.h2.console.enabled=false

# Logging (output to console)
logging.level.root=INFO
logging.level.com.example=DEBUG
logging.pattern.console=%d{yyyy-MM-dd HH:mm:ss} [%-5level] %logger{36} - %msg%n

# Application name (printed on startup)
spring.application.name=My Spring Boot App
```

---

## 4. Domain layer — pure Java, zero framework dependencies

### Domain model (record for immutable data)

```java
package com.example.domain.model;

import java.math.BigDecimal;

// ✅ record: immutable value object
public record Product(Long id, String name, BigDecimal price, Long categoryId) {}
```

### Domain model (class for mutable aggregate)

```java
package com.example.domain.model;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

// ✅ class: aggregate with behavior
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

    // Getters
    public Long getId()                    { return id; }
    public OrderStatus getStatus()         { return status; }
    public List<OrderLine> getLines()      { return List.copyOf(lines); }
    public LocalDateTime getCreatedAt()    { return createdAt; }

    // Domain behavior
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

// Domain enums
public enum OrderStatus {
    PENDING, CONFIRMED, COMPLETED, CANCELLED
}

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

## 5. Application layer — use cases

One `@Component` class per use case. Never depend on DTOs, HTTP, or JPA.

### CreateProductUseCase

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
    public Product execute(String name, java.math.BigDecimal price, Long categoryId) {
        var product = new Product(null, name, price, categoryId);
        return productRepository.save(product);
    }
}
```

### FindProductUseCase

```java
package com.example.application.usecase;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

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

### Custom exceptions

```java
package com.example.application.exception;

public class ResourceNotFoundException extends RuntimeException {
    public ResourceNotFoundException(String message) {
        super(message);
    }
}
```

---

## 6. Infrastructure layer — web adapter

### DTOs (records)

```java
// infrastructure/web/dto/CreateProductRequest.java
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

// infrastructure/web/dto/ProductResponse.java
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

### Global exception handler

```java
package com.example.infrastructure.web.controller;

import com.example.application.exception.ResourceNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import java.time.LocalDateTime;

@ControllerAdvice
public class GlobalExceptionHandler {

    public record ErrorResponse(
        int status,
        String message,
        LocalDateTime timestamp
    ) {}

    @ExceptionHandler(ResourceNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(ResourceNotFoundException e) {
        var error = new ErrorResponse(404, e.getMessage(), LocalDateTime.now());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(error);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception e) {
        var error = new ErrorResponse(500, "Internal server error", LocalDateTime.now());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(error);
    }
}
```

---

## 7. Infrastructure layer — persistence adapter

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

    // Getters
    public Long getId()          { return id; }
    public String getName()      { return name; }
    public BigDecimal getPrice() { return price; }
    public Long getCategoryId()  { return categoryId; }

    // Setters
    public void setId(Long id)                { this.id = id; }
    public void setName(String name)          { this.name = name; }
    public void setPrice(BigDecimal price)    { this.price = price; }
    public void setCategoryId(Long categoryId){ this.categoryId = categoryId; }
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

## 8. Spring Boot Application entry point

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

## 9. Running in Claude Code

### Option A: Maven
```bash
mvn clean spring-boot:run
# Output:
#   ... INFO Application started ...
#   → Tomcat started on port(s): 8080 (http)
#   → Ready to handle requests.
```

Test endpoint:
```bash
curl http://localhost:8080/api/v1/products
```

### Option B: Gradle
```bash
./gradlew bootRun
```

### Option C: Build JAR and run
```bash
mvn clean package
java -jar target/my-app-1.0.0.jar
```

### Graceful shutdown
```bash
Ctrl+C
```

---

## 10. Testing strategy

### Unit test (plain JUnit, no Spring)

```java
package com.example.application.usecase;

import com.example.domain.model.Product;
import com.example.domain.repository.ProductRepository;
import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.*;

class CreateProductUseCaseTest {

    private final ProductRepository repository = mock(ProductRepository.class);
    private final CreateProductUseCase useCase = new CreateProductUseCase(repository);

    @Test
    void shouldSaveAndReturnProduct() {
        var request = new CreateProductRequest("Widget", new BigDecimal("9.99"), 1L);
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

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class ProductControllerIntegrationTest {

    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;

    @Test
    void shouldCreateAndReturnProduct() throws Exception {
        var request = new CreateProductRequest("Widget", java.math.BigDecimal.valueOf(9.99), 1L);

        mockMvc.perform(post("/api/v1/products")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(jsonPath("$.name").value("Widget"))
            .andExpect(jsonPath("$.price").value(9.99));
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

## 11. Style and conventions

| Aspect | Rule |
|---|---|
| Domain model | No Spring/JPA annotations; `record` if immutable, class if mutable |
| Repository port | Interface in `domain/repository/`; no `@Repository` |
| Use cases | One `@Component` class per use case, `execute()` method |
| DTOs | `record` in `infrastructure/web/dto/`; never cross boundaries |
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
| Logging | Use SLF4J / Logback via `org.slf4j.Logger`; output to console |
| Exit behavior | Graceful shutdown on Ctrl+C; no explicit `System.exit()` unless error |

---

## 12. Complete minimal example

For a quick runnable project, see the structure:

```
my-spring-app/
├── pom.xml
├── src/main/java/com/example/
│   ├── Application.java
│   ├── domain/
│   │   ├── model/Product.java
│   │   └── repository/ProductRepository.java
│   ├── application/usecase/
│   │   ├── CreateProductUseCase.java
│   │   ├── FindProductUseCase.java
│   │   └── DeleteProductUseCase.java
│   ├── infrastructure/web/
│   │   ├── controller/ProductController.java
│   │   ├── dto/{CreateProductRequest,ProductResponse}.java
│   │   └── mapper/ProductWebMapper.java
│   └── infrastructure/persistence/
│       ├── entity/ProductEntity.java
│       ├── repository/{ProductJpaRepository,ProductRepositoryAdapter}.java
│       └── mapper/ProductPersistenceMapper.java
├── src/main/resources/
│   └── application.properties
└── src/test/java/...
```

**Run**:
```bash
mvn clean spring-boot:run
# Access: http://localhost:8080/api/v1/products
```

---

## Final notes

- **Minimum version**: Java 21 LTS + Spring Boot 3.3+.
- **Database**: H2 in-memory for demos; switch to PostgreSQL in production via pom.xml.
- **No Lombok**: Write all constructors, getters, and methods explicitly.
- **Layer isolation**: Strictly enforced — DTOs never in domain/application, entities never outside persistence.
- **Domain objects**: Shared language between all layers; immutable when possible (records).
- **Transactions**: Applied at application layer (use case methods), not infrastructure.
- **Claude Code execution**: Always include `mvn clean spring-boot:run` or equivalent as the execution command in documentation.
- **Official docs**: https://docs.spring.io/spring-boot/docs/current/reference/html/

---

## References

- Spring Boot Docs: https://docs.spring.io/spring-boot/docs/current/reference/html/
- Spring Data JPA: https://docs.spring.io/spring-data/jpa/docs/current/reference/html/
- Java 21 Language Features: https://docs.oracle.com/en/java/javase/21/docs/specs/
- Clean Architecture: https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html
- Claude Code Docs: https://docs.anthropic.com/en/docs/claude-code/overview