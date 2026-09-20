# Project setup — Gradle, logging, configuration, DDL

Everything needed to stand up a runnable Spring Boot 3.x + Java 21 project for this skill:
build file, Log4j2 config, `application.properties`, and `schema.sql`.

---

## 1. Claude Code context for Spring Boot

- Embedded Tomcat listening on `localhost:8080` (or configured port).
- Application lifecycle: start → handle requests → graceful shutdown (`Ctrl+C`).
- Logging via SLF4J + **Log4j2**, console output only (see §3).
- Query debugging via SQL logging in `application.properties` (§4) — a `logging.level.*`
  property, not tied to the logging backend.
- Single-instance, stateless: each run is isolated.
- Execution: `./gradlew bootRun`; tests: `./gradlew test`.
- Persistence tests use `@DataJpaTest` for fast slice testing without the full context.

**Common execution patterns:**
1. **Simple REST API demo** — single aggregate, 3–4 endpoints.
2. **CLI data processor** — Spring Boot app that reads input and produces output, no web server.
3. **Scheduled task** — `@Scheduled` for batch processing.
4. **Integration test** — full stack under `@SpringBootTest`.

---

## 2. Gradle — build.gradle (Spring Boot 3.x + Java 21)

Gradle is the default build tool for this skill — do not generate a `pom.xml` unless the
user explicitly asks for Maven.

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

configurations {
    // Exclude the default Logback so Log4j2 is the only logging backend
    all*.exclude group: 'org.springframework.boot', module: 'spring-boot-starter-logging'
}

dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    implementation 'org.springframework.boot:spring-boot-starter-log4j2'

    // Pick ONE based on the chosen database (see SKILL.md) — do not include more than the chosen driver
    runtimeOnly 'com.h2database:h2'                       // H2 (in-memory)
    // runtimeOnly 'org.postgresql:postgresql'             // PostgreSQL
    // runtimeOnly 'com.mysql:mysql-connector-j'           // MySQL

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

**Run:**
```bash
./gradlew bootRun
# → Server starts on http://localhost:8080
```

**Build JAR and run:**
```bash
./gradlew build
java -jar build/libs/my-app-1.0.0.jar
```

**Test:**
```bash
./gradlew test
```

> If the user specifically asks for Maven, it works the same way conceptually
> (`spring-boot-starter-parent`, same dependency list minus the Logback exclusion —
> use `<exclusions>` on `spring-boot-starter` instead — plus `spring-boot-maven-plugin`),
> but Gradle is the default output for this skill.

---

## 3. Logging — Log4j2, not the Spring Boot default

Spring Boot ships with Logback by default. This skill always swaps it for **Log4j2**:
exclude `spring-boot-starter-logging` (done above) and add `spring-boot-starter-log4j2`.
Application code still uses the SLF4J API (`org.slf4j.Logger`/`LoggerFactory`) — only the
backend changes, so use-case and controller code never imports Log4j2 classes directly.

`src/main/resources/log4j2.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN">
    <Appenders>
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="%d{yyyy-MM-dd HH:mm:ss} [%-5level] %logger{36} - %msg%n"/>
        </Console>
    </Appenders>
    <Loggers>
        <Logger name="com.example" level="debug" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Root level="info">
            <AppenderRef ref="Console"/>
        </Root>
    </Loggers>
</Configuration>
```

Usage in code:
```java
private static final Logger log = LoggerFactory.getLogger(CreateProductUseCase.class);
log.info("Created product {}", product.id());
```

---

## 4. application.properties — datasource, JPA, batching, SQL logging

Fill in `spring.datasource.*` based on the database the user chose (SKILL.md, "Before any code: ask about the database"). H2 example:

```properties
server.port=8080
spring.application.name=My Spring Boot App

# Database — swap this block per the chosen database (see SKILL.md)
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA / Hibernate — ddl-auto=none because schema.sql (§5) is the source of truth.
# Never combine schema.sql with create-drop/update: Hibernate's auto-DDL and schema.sql
# both try to create the same tables and collide on startup ("table already exists").
spring.jpa.hibernate.ddl-auto=none
spring.sql.init.mode=always
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.show-sql=false
spring.jpa.properties.hibernate.format_sql=true
spring.jpa.properties.hibernate.use_sql_comments=true

# N+1 guards. OSIV off: lazy loading outside the use-case transaction fails loudly
# instead of silently firing extra SELECTs. Batch fetch: any lazy collection not
# fetch-joined (e.g. paged queries) loads in 1 + ceil(N/50) queries, not 1 + N.
spring.jpa.open-in-view=false
spring.jpa.properties.hibernate.default_batch_fetch_size=50

# Batching (for bulk inserts — see entities-and-repositories.md §7 for the IDENTITY caveat)
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
spring.jpa.properties.hibernate.order_updates=true

# SQL logging — watch for N+1 (many SELECTs in a loop) and deep OFFSETs
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
real schema (managed by a migration tool like Flyway, not `schema.sql`) drift apart.

Only if there is no persistence layer yet (no `schema.sql`), a quick H2 demo may use
`spring.jpa.hibernate.ddl-auto=create-drop` instead — say so explicitly rather than leaving
it unset.

---

## 5. schema.sql — single source of truth for DDL

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
