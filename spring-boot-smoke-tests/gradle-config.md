# Configuración de Gradle para aislar Smoke Tests

Objetivo: poder correr `./gradlew smokeTest` para ejecutar SOLO los tests marcados con `@Tag("smoke")`,
y opcionalmente hacer que `./gradlew test` (el suite normal) los excluya para no duplicar tiempo.

Requiere JUnit 5 (`useJUnitPlatform()`), que ya viene por defecto en proyectos Spring Boot modernos.

---

## Groovy DSL (`build.gradle`)

```groovy
test {
    useJUnitPlatform {
        excludeTags "smoke"   // el suite normal no corre los smoke tests
    }
}

tasks.register('smokeTest', Test) {
    description = 'Corre solo los smoke tests (tag "smoke")'
    group = 'verification'

    testClassesDirs = sourceSets.test.output.classesDirs
    classpath = sourceSets.test.runtimeClasspath

    useJUnitPlatform {
        includeTags "smoke"
    }

    // No lo encadenes a "check" si quieres que sea 100% manual/explícito.
    // Si prefieres que corra siempre en CI junto con el build, descomenta:
    // check.dependsOn smokeTest
}
```

Ejecutar:

```bash
./gradlew smokeTest
```

---

## Kotlin DSL (`build.gradle.kts`)

```kotlin
tasks.test {
    useJUnitPlatform {
        excludeTags("smoke")
    }
}

tasks.register<Test>("smokeTest") {
    description = "Corre solo los smoke tests (tag \"smoke\")"
    group = "verification"

    testClassesDirs = sourceSets["test"].output.classesDirs
    classpath = sourceSets["test"].runtimeClasspath

    useJUnitPlatform {
        includeTags("smoke")
    }

    // Descomentar si se quiere que corra automáticamente en cada build:
    // tasks.check { dependsOn(this@register) }
}
```

Ejecutar:

```bash
./gradlew smokeTest
```

---

## Verificar que actuator está disponible (si se usa el health check)

### Groovy DSL

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
}
```

### Kotlin DSL

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
}
```

---

## Integración opcional en CI/CD (ejemplo GitHub Actions)

Solo generar/mostrar esto si el usuario lo pide explícitamente — no es parte del flujo por defecto del skill.

```yaml
name: CI

on: [push, pull_request]

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
      - name: Run smoke tests
        run: ./gradlew smokeTest --info

  full-test:
    needs: smoke-test   # si el smoke test falla, ni se intenta el resto
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '21'
      - name: Run full test suite
        run: ./gradlew test
```

La idea: los smoke tests corren primero y rápido; si fallan, no tiene sentido gastar tiempo de CI en el resto.