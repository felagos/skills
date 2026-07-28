# Ejemplos completos de configuración pitest

Antes de copiar estos bloques, reemplaza los paquetes de ejemplo (`com.empresa.miapp`) por los reales del proyecto, y verifica que las versiones (`info.solidsoft.pitest`, `pitestVersion`, `junit5PluginVersion`) sigan siendo las más recientes estables — búscalas en el Gradle Plugin Portal y Maven Central antes de fijar el número.

## Kotlin DSL (`build.gradle.kts`)

```kotlin
plugins {
    id("java")
    id("org.springframework.boot") version "4.1.0"
    id("io.spring.dependency-management") version "1.1.7"
    id("info.solidsoft.pitest") version "1.19.0"
}

java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(21))
    }
}

pitest {
    junit5PluginVersion.set("1.2.1")
    pitestVersion.set("1.25.5")

    // Qué se muta: solo el código de producción del proyecto, nunca dependencias
    targetClasses.set(listOf("com.empresa.miapp.*"))

    // Qué tests corren contra cada mutante: solo unitarios rápidos, sin @SpringBootTest
    targetTests.set(listOf("com.empresa.miapp.*Test", "com.empresa.miapp.*Tests"))

    // Clases sin lógica real que solo generan ruido en el reporte
    excludedClasses.set(listOf(
        "com.empresa.miapp.MiAppApplication",
        "com.empresa.miapp.config.*",
        "com.empresa.miapp.dto.*",
        "com.empresa.miapp.*Exception"
    ))

    // Excluir explícitamente los tests de integración pesados
    excludedTestClasses.set(listOf("com.empresa.miapp.*IT", "com.empresa.miapp.*IntegrationTest"))

    threads.set(Runtime.getRuntime().availableProcessors())
    outputFormats.set(listOf("HTML", "XML"))

    mutationThreshold.set(70)
    coverageThreshold.set(80)

    jvmArgs.set(listOf("-Xmx2048m"))

    // Análisis incremental: acelera corridas repetidas en CI reutilizando resultados previos
    historyInputLocation.set(file("$buildDir/pitHistory.bin"))
    historyOutputLocation.set(file("$buildDir/pitHistory.bin"))
}
```

## Groovy DSL (`build.gradle`)

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.0'
    id 'io.spring.dependency-management' version '1.1.7'
    id 'info.solidsoft.pitest' version '1.19.0'
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

pitest {
    junit5PluginVersion = '1.2.1'
    pitestVersion = '1.25.5'

    targetClasses = ['com.empresa.miapp.*']
    targetTests = ['com.empresa.miapp.*Test', 'com.empresa.miapp.*Tests']

    excludedClasses = [
        'com.empresa.miapp.MiAppApplication',
        'com.empresa.miapp.config.*',
        'com.empresa.miapp.dto.*',
        'com.empresa.miapp.*Exception'
    ]
    excludedTestClasses = ['com.empresa.miapp.*IT', 'com.empresa.miapp.*IntegrationTest']

    threads = Runtime.runtime.availableProcessors()
    outputFormats = ['HTML', 'XML']

    mutationThreshold = 70
    coverageThreshold = 80

    jvmArgs = ['-Xmx2048m']

    historyInputLocation = file("$buildDir/pitHistory.bin")
    historyOutputLocation = file("$buildDir/pitHistory.bin")
}
```

## Notas sobre las opciones menos obvias

- **`outputFormats`**: `HTML` es para revisión humana; `XML` es el que necesita `scripts/summarize_mutations.py` (u otra herramienta) para procesar el resultado por código. Genera ambos, no solo uno.
- **`mutationThreshold` / `coverageThreshold`**: si se configuran, la tarea `pitest` falla el build cuando no se alcanzan. Útil en CI, pero introdúcelo después de tener una primera corrida y una línea base razonable — fijar un umbral alto sin haber corrido nunca la herramienta suele bloquear el pipeline el primer día.
- **`historyInputLocation` / `historyOutputLocation`**: en CI, cachea ese archivo entre builds (mismo mecanismo que cachear `.gradle` o `node_modules`). Sin esto, cada corrida de CI vuelve a analizar todos los mutantes desde cero.
- **Multi-módulo**: si el proyecto tiene varios subproyectos Gradle, el plugin se aplica por subproyecto. Si hay código compartido entre módulos, mira la sección de proyectos multi-módulo en la documentación de `szpak/gradle-pitest-plugin` — requiere `mainSourceSets` y `additionalMutableCodePaths` para que pitest vea el código de módulos hermanos.