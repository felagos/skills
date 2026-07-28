---
name: spring-boot-mutation-testing
description: Configura y ejecuta pruebas de mutación (mutation testing) con PIT/pitest en proyectos Spring Boot que usan Gradle y Java 21. Úsala siempre que el usuario mencione "mutation testing", "pruebas de mutación", "PIT", "pitest", "mutantes", "mutation score/coverage", "kill mutants", o pida mejorar/medir la calidad real de sus pruebas unitarias más allá de la cobertura de líneas, en un proyecto Java/Spring Boot con Gradle. Aplica tanto si el proyecto no tiene pitest configurado todavía (setup desde cero en build.gradle/build.gradle.kts) como si ya lo tiene y el usuario quiere ejecutarlo, ajustarlo, diagnosticar fallos, interpretar el reporte HTML/XML, o integrarlo en CI con un umbral de mutación mínimo.
---

# Mutation testing en Spring Boot + Gradle + Java 21

## Por qué esto no es trivial

La cobertura de líneas dice qué código *se ejecutó* durante los tests, no si esos tests realmente detectarían un bug. PIT (pitest) introduce pequeños cambios ("mutantes") en el bytecode compilado — invierte una condición, cambia un operador, elimina una llamada — y vuelve a correr la suite de tests contra cada mutante. Si algún test falla, el mutante "muere" (bueno); si todos los tests siguen pasando, el mutante "sobrevive" (mala señal: hay una rama de lógica sin verificar de verdad).

En un proyecto Spring Boot esto tiene dos fricciones específicas que hay que anticipar, no descubrir a mitad de la ejecución:
1. **Costo**: pitest recompila y re-ejecuta la suite completa por cada mutante. Si la suite incluye tests de integración con `@SpringBootTest` que levantan el contexto de Spring, una corrida de mutación puede tardar horas en vez de minutos. Por eso casi siempre conviene apuntar pitest solo a los tests unitarios rápidos.
2. **Ruido falso**: clases sin lógica de negocio (la clase `@SpringBootApplication`, DTOs/records planos, configuración `@Configuration`, entidades JPA sin métodos custom) generan mutantes que nunca podrán "matarse" con sentido, porque no hay comportamiento que testear. Dejarlas dentro del target infla el número de mutantes sobrevivientes sin que eso indique un problema real, y desanima al equipo a mirar el reporte.

Diseña la configuración teniendo esto en cuenta desde el principio, en vez de correr pitest sobre todo el código fuente y filtrar después.

## Paso 1: Inspeccionar el proyecto antes de tocar nada

Antes de escribir configuración, mira:
- `build.gradle` o `build.gradle.kts` (DSL Groovy vs Kotlin) y el bloque `plugins {}` existente.
- La versión de Java configurada (`sourceCompatibility`, `toolchain`, o `JavaLanguageVersion`) — el usuario indicó Java 21.
- La versión de Spring Boot (aquí 4.1.0, que corre sobre Spring Framework 7 y JUnit 6/JUnit Platform; el motor de tests real sigue siendo JUnit 5 Jupiter salvo que el proyecto haya migrado explícitamente).
- Qué framework de testing usan los tests unitarios: JUnit 5 (lo normal en Spring Boot) requiere el plugin `pitest-junit5-plugin`.
- La estructura de paquetes, para poder acotar `targetClasses` al paquete raíz real del proyecto en vez de dejarlo en el wildcard por defecto.
- Si ya existe algún bloque `pitest { ... }`: en ese caso el trabajo es de ajuste/diagnóstico, no de setup desde cero — no dupliques el bloque, edítalo.

## Paso 2: Añadir el plugin de Gradle

Usa el plugin `info.solidsoft.pitest`, que es el estándar de facto para pitest + Gradle. Las versiones cambian con el tiempo — antes de fijar una versión concreta en el `build.gradle`, verifica cuál es la más reciente estable buscando en la web (Gradle Plugin Portal: `info.solidsoft.pitest`, y Maven Central: `org.pitest:pitest` y `org.pitest:pitest-junit5-plugin`) en vez de asumir una versión de memoria, porque este ecosistema publica releases con frecuencia y una versión vieja puede tener incompatibilidades con Java 21 o con la versión de JUnit Platform que trae Spring Boot 4.1.

Bloque mínimo (Kotlin DSL, `build.gradle.kts`):

```kotlin
plugins {
    id("java")
    id("org.springframework.boot") version "4.1.0"
    id("info.solidsoft.pitest") version "1.19.0" // verificar última versión estable
}

pitest {
    // Ejecuta los tests JUnit 5 de Jupiter; añade la dependencia pitest-junit5-plugin automáticamente
    junit5PluginVersion.set("1.2.1") // verificar última versión estable
    pitestVersion.set("1.25.5")      // verificar última versión estable
}
```

Equivalente en Groovy DSL (`build.gradle`):

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.0'
    id 'info.solidsoft.pitest' version '1.19.0'
}

pitest {
    junit5PluginVersion = '1.2.1'
    pitestVersion = '1.25.5'
}
```

Ver `./build-gradle-examples.md` para un bloque `pitest {}` completo y comentado con todas las opciones relevantes descritas en los pasos siguientes.

## Paso 3: Acotar qué se muta y qué tests corren

Esta es la parte que más impacta el tiempo de ejecución y la utilidad del reporte. Configura explícitamente:

- **`targetClasses`**: el/los paquete(s) raíz reales del proyecto (p. ej. `com.empresa.miapp.*`), nunca el wildcard global — de lo contrario pitest intentará mutar también dependencias de terceros presentes en el classpath del proyecto multi-módulo.
- **`targetTests`**: idealmente solo los paquetes de tests unitarios (p. ej. `com.empresa.miapp.*Test`, `com.empresa.miapp.*Tests`), excluyendo explícitamente los de integración si siguen una convención de nombre distinta (`*IT`, `*IntegrationTest`). Si no hay una convención clara para separarlos, coméntalo con el usuario en vez de adivinar — mezclar tests con contexto de Spring dispara el problema de rendimiento descrito arriba.
- **`excludedClasses`**: excluye explícitamente clases sin lógica: la clase principal `@SpringBootApplication`, clases `@Configuration` puras, DTOs/records sin métodos custom, excepciones simples, clases generadas (Lombok, MapStruct). Un patrón típico: `['**.*Application', '**.config.*', '**.dto.*']`, ajustado a la estructura real del proyecto.
- **`threads`**: en Java 21 con múltiples cores, subir el número de threads paralelos acelera bastante la corrida; usa `Runtime.getRuntime().availableProcessors()` como referencia o dejarlo fijo en un valor razonable (4-8) si la máquina de CI es compartida.
- **`mutators`**: el set `STRONGER` o `DEFAULTS` (según versión de pitest) suele ser un buen punto de partida; no actives `ALL` de entrada, genera demasiado ruido para una primera pasada.

No copies estos valores literalmente sin adaptarlos — pídele al usuario (o infiere del `view` del proyecto) los nombres de paquete reales antes de escribir `targetClasses`/`excludedClasses`, porque un wildcard mal ajustado es la causa más común de corridas que tardan demasiado o que no cubren lo que el usuario esperaba.

## Paso 4: Ejecutar

```bash
./gradlew pitest
```

Esto compila, corre pitest y genera el reporte. Si el build ya tiene un `check` que dependa de `pitest`, se ejecutará también con `./gradlew check`, pero para iterar rápido mientras se ajusta la configuración es mejor invocar la tarea `pitest` sola.

Si la corrida es muy lenta, antes de aumentar threads a ciegas revisa si `targetTests` sigue incluyendo tests con `@SpringBootTest` — es la causa más frecuente, muy por encima de falta de paralelismo.

## Paso 5: Leer y resumir el reporte

pitest genera en `build/reports/pitest/<timestamp>/`:
- `index.html` — reporte navegable por paquete y clase, con el código fuente coloreado mostrando cada mutante y su estado.
- `mutations.xml` — el mismo dato en formato máquina, útil para resumir por consola o integrarlo en otra herramienta.

Usa `./summarize_mutations.py` sobre el `mutations.xml` más reciente para obtener un resumen por clase (mutantes generados, matados, sobrevivientes, sin cobertura, y el mutation score) sin tener que abrir el HTML clase por clase:

```bash
python3 ./summarize_mutations.py build/reports/pitest/*/mutations.xml
```

Al presentar los resultados al usuario, prioriza las clases con más mutantes **SURVIVED** (sobrevivientes) sobre el mutation score global — un score global alto puede esconder una clase crítica de lógica de negocio con mala cobertura real, y ese es justamente el tipo de cosa que este tipo de análisis está pensado para exponer.

## Paso 6: Umbral de calidad para CI

Si el usuario quiere que el build falle por debajo de cierto mutation score:

```kotlin
pitest {
    mutationThreshold.set(70)   // % mínimo de mutantes muertos
    coverageThreshold.set(80)   // % mínimo de cobertura de línea, opcional
}
```

Para acelerar corridas repetidas en CI, considera activar análisis incremental con `historyInputLocation`/`historyOutputLocation` apuntando a un archivo cacheado entre builds (ver `./build-gradle-examples.md`), así pitest solo re-analiza mutantes afectados por cambios desde la última corrida.

## Problemas comunes

- **La corrida nunca termina / consume toda la memoria**: casi siempre son tests de integración con contexto de Spring dentro de `targetTests`. Sepáralos primero antes de tocar `jvmArgs` o memoria.
- **`OutOfMemoryError` en los minions de pitest**: sube el heap vía `jvmArgs.set(listOf("-Xmx2048m"))` en el bloque `pitest {}`, no en el `gradle.properties` general (eso afecta al build completo, no solo a pitest).
- **Mutantes "sobrevivientes" en records/DTOs de Spring Boot 4**: pitest filtra por defecto el código sintético que el compilador genera para records (`equals`/`hashCode`/accessors). Si igual aparecen mutantes ahí, probablemente el record tiene lógica custom en el constructor compacto — eso sí merece un test.
- **Choque de versiones entre `pitest-junit5-plugin` y JUnit Platform**: si el proyecto ya trae una versión reciente de JUnit Platform (Spring Boot 4.1 tiende a traer versiones nuevas), y aparece un error de incompatibilidad de API, verifica que `junit5PluginVersion` sea reciente — versiones viejas de ese plugin fijan una versión de `junit-platform-launcher` que puede chocar con la que trae Spring Boot.