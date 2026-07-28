---
name: spring-boot-smoke-tests
description: Genera smoke tests (pruebas de humo) para proyectos Java con Spring Boot y Gradle — cobertura completa de carga de contexto, endpoints REST clave, conectividad a base de datos, y Actuator health checks — más la configuración de Gradle para correr solo los smoke tests como una tarea/grupo separado (p.ej. `./gradlew smokeTest`). Usa este skill siempre que el usuario pida "smoke tests", "pruebas de humo", "verificar que el proyecto levanta/arranca", "sanity check del build", o cuando pida asegurar que un despliegue no rompió lo esencial en un proyecto Spring Boot + Gradle. También aplica si el usuario pide integrar smoke tests en CI/CD (GitHub Actions, GitLab CI, Jenkins) para un proyecto Spring Boot.
---

# Smoke Tests para Spring Boot + Gradle

Genera un conjunto de smoke tests con cobertura completa para un proyecto Java/Spring Boot que usa Gradle, y configura Gradle para poder ejecutarlos de forma aislada (separados del resto del test suite).

## Cobertura objetivo

El skill siempre apunta a estas 4 capas, salvo que el usuario pida explícitamente menos:

1. **Carga de contexto** — que la aplicación Spring levante sin errores (`@SpringBootTest`).
2. **Actuator health** — que `/actuator/health` responda `200 OK` (requiere `spring-boot-starter-actuator`).
3. **Endpoints REST clave** — camino feliz de 2-4 endpoints críticos del dominio (login, health de negocio, endpoint principal, etc.), vía `MockMvc` o `WebTestClient`.
4. **Conectividad a base de datos** — que el `DataSource` (o `EntityManager`/repositorio) responda, si el proyecto usa una base de datos.

Si alguna capa no aplica (p.ej. el proyecto no tiene base de datos), omítela y dilo explícitamente — no inventes recursos que no existen en el proyecto.

## Flujo de trabajo

### 1. Inspeccionar el proyecto antes de escribir nada

No generes tests a ciegas. Investiga primero:

```bash
# Ubicar la clase principal (@SpringBootApplication) y el paquete base
grep -rl "@SpringBootApplication" --include="*.java" .

# Ver si usa Groovy DSL o Kotlin DSL
ls build.gradle build.gradle.kts 2>/dev/null

# Ver dependencias actuales
cat build.gradle 2>/dev/null || cat build.gradle.kts

# Detectar si hay actuator, base de datos, y qué framework de test ya usa
grep -E "actuator|starter-data|starter-test|junit" build.gradle build.gradle.kts 2>/dev/null

# Detectar controladores REST existentes para elegir endpoints candidatos
grep -rl "@RestController\|@Controller" --include="*.java" .
```

Determina:
- Paquete base de la app (para ubicar el test en el paquete correcto, típicamente `src/test/java/<mismo-paquete>`).
- Si usa Gradle Groovy (`build.gradle`) o Kotlin DSL (`build.gradle.kts`).
- Si `spring-boot-starter-actuator` ya está en las dependencias; si no, hay que agregarla.
- Si `spring-boot-starter-test` ya está (casi siempre lo está por defecto).
- Si el proyecto tiene una base de datos configurada (`spring-boot-starter-data-jpa`, `DataSource`, `application.yml` con `spring.datasource`).
- 2-4 endpoints REST realmente críticos (no todos) inspeccionando los `@RestController`.

### 2. Generar los archivos de test

Usa las plantillas de `./test-templates.md` como base y adáptalas al paquete, nombres de clase, y endpoints reales del proyecto. No pegues las plantillas tal cual — personalízalas.

Ubica todos los smoke tests bajo el mismo paquete raíz, sufijo `SmokeTest`, y en un subpaquete `smoke` para poder filtrarlos fácilmente por convención de nombre/paquete además del tag JUnit:

```
src/test/java/<paquete-base>/smoke/
├── ApplicationContextSmokeTest.java
├── ActuatorHealthSmokeTest.java
├── CriticalEndpointsSmokeTest.java
└── DatabaseConnectivitySmokeTest.java   (solo si el proyecto tiene BD)
```

Cada clase de test debe llevar `@Tag("smoke")` (JUnit 5) — esto es lo que permite filtrarlas en Gradle en el paso 4.

### 3. Verificar/agregar dependencias necesarias

Si falta `spring-boot-starter-actuator`, agrégala. Si falta exponer el endpoint de health, agrega o revisa `application.yml`/`application.properties`:

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info
  endpoint:
    health:
      show-details: always
```

### 4. Configurar Gradle para correr solo los smoke tests

Lee `./gradle-config.md` para la sintaxis exacta (Groovy vs Kotlin DSL) y agrega al `build.gradle`/`build.gradle.kts`:

- Una tarea `smokeTest` de tipo `Test` que filtra por el tag JUnit `smoke`.
- Configuración para que `smokeTest` NO se ejecute automáticamente con `./gradlew build` (para no duplicar tiempo de CI), sino que se invoque explícitamente.
- Opcional pero recomendado: hacer que la tarea estándar `test` excluya el tag `smoke` (así `./gradlew test` corre el resto del suite y `./gradlew smokeTest` corre solo estos).

### 5. Verificar que todo compila y corre

Si tienes acceso a bash y el proyecto tiene wrapper de Gradle:

```bash
./gradlew smokeTest --info
```

Si falla por dependencias faltantes o por un endpoint que no existe, corrige el test o la configuración antes de entregar — no dejes al usuario un smoke test roto.

### 6. Resumen final al usuario

Al terminar, entrega en el chat (no como archivo aparte, es un resumen conversacional):
- Qué capas de smoke test se generaron y cuáles se omitieron (y por qué).
- Los archivos creados/modificados.
- El comando para correrlos: `./gradlew smokeTest`.
- Si aplica, un ejemplo de cómo integrarlo en CI/CD (ofrece esto, no lo generes de más si no lo piden).

## Notas importantes

- **No sobre-generar**: 2-4 endpoints críticos, no todos los controladores del proyecto. El objetivo es velocidad y detección de fallos catastróficos, no cobertura funcional.
- **Camino feliz solamente**: los smoke tests no prueban casos límite ni errores de validación — eso son tests funcionales/de regresión, un asunto distinto.
- **Idempotencia con la base de datos**: si el smoke test toca la BD, que sea de solo lectura o use una transacción que se revierta (`@Transactional` en el test), para no dejar residuos.
- Si el proyecto usa Kotlin en vez de Java para el código de producción pero Gradle Kotlin DSL para el build, los tests pueden seguir siendo Java si el resto del test suite es Java — sigue la convención existente del proyecto.