# Plantillas de Smoke Tests (JUnit 5 + Spring Boot)

Todas las clases usan `@Tag("smoke")` para poder filtrarlas desde Gradle (ver `gradle-config.md`).
Sustituye `com.miempresa.miapp` por el paquete real del proyecto, y adapta los endpoints/beans a los que existan de verdad.

---

## 1. Carga de contexto — `ApplicationContextSmokeTest.java`

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@Tag("smoke")
@SpringBootTest
class ApplicationContextSmokeTest {

    @Test
    void contextLoads() {
        // Si este test falla, Spring no pudo inicializar la app:
        // beans mal configurados, propiedades faltantes, errores
        // de arranque, etc. Es el smoke test más básico de todos.
    }
}
```

---

## 2. Actuator health — `ActuatorHealthSmokeTest.java`

Requiere `spring-boot-starter-actuator` y el endpoint `health` expuesto.

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@Tag("smoke")
@SpringBootTest
@AutoConfigureMockMvc
class ActuatorHealthSmokeTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void healthEndpointDeberiaResponderUp() throws Exception {
        mockMvc.perform(get("/actuator/health"))
               .andExpect(status().isOk())
               .andExpect(jsonPath("$.status").value("UP"));
    }
}
```

---

## 3. Endpoints REST críticos — `CriticalEndpointsSmokeTest.java`

Elige de 2 a 4 endpoints realmente críticos del dominio (no todos). Ejemplo genérico:

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@Tag("smoke")
@SpringBootTest
@AutoConfigureMockMvc
class CriticalEndpointsSmokeTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void paginaOEndpointRaizDeberiaResponder() throws Exception {
        mockMvc.perform(get("/"))
               .andExpect(status().isOk());
    }

    @Test
    void endpointPrincipalDelDominioDeberiaResponder() throws Exception {
        // Reemplazar por el endpoint realmente crítico del negocio,
        // p.ej. /api/productos, /api/usuarios, /api/pedidos, etc.
        mockMvc.perform(get("/api/reemplazar-por-endpoint-real")
               .accept(MediaType.APPLICATION_JSON))
               .andExpect(status().isOk());
    }
}
```

Si el proyecto usa WebFlux en vez de MVC clásico, usar `WebTestClient` en lugar de `MockMvc`:

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.reactive.server.AutoConfigureWebTestClient;
import org.springframework.test.web.reactive.server.WebTestClient;

@Tag("smoke")
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class CriticalEndpointsReactiveSmokeTest {

    @Autowired
    private WebTestClient webTestClient;

    @Test
    void endpointPrincipalDeberiaResponder() {
        webTestClient.get().uri("/api/reemplazar-por-endpoint-real")
                     .exchange()
                     .expectStatus().isOk();
    }
}
```

---

## 4. Conectividad a base de datos — `DatabaseConnectivitySmokeTest.java`

Solo generar si el proyecto tiene una base de datos configurada. Usa una conexión directa al `DataSource`, sin depender de datos concretos ni dejar residuos.

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import javax.sql.DataSource;
import java.sql.Connection;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

@Tag("smoke")
@SpringBootTest
class DatabaseConnectivitySmokeTest {

    @Autowired
    private DataSource dataSource;

    @Test
    void deberiaConectarseALaBaseDeDatos() throws Exception {
        try (Connection connection = dataSource.getConnection()) {
            assertNotNull(connection);
            assertTrue(connection.isValid(2)); // timeout de 2 segundos
        }
    }
}
```

Si el proyecto usa Spring Data JPA y se prefiere validar a nivel de repositorio en vez de conexión cruda (opcional, más caro pero más realista):

```java
package com.miempresa.miapp.smoke;

import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.transaction.annotation.Transactional;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;

@Tag("smoke")
@SpringBootTest
@Transactional // revierte cualquier cambio al terminar el test
class RepositorySmokeTest {

    @Autowired
    private /* ReemplazarPorRepositorioReal */ Object repository;

    @Test
    void repositorioDeberiaResponderSinErrores() {
        // Reemplazar por una consulta liviana y de solo lectura,
        // p.ej. repository.count() o repository.findAll(PageRequest.of(0, 1))
        assertDoesNotThrow(() -> { /* llamada al repositorio */ });
    }
}
```