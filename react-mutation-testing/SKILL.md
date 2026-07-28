---
name: react-mutation-testing
description: Configura y ejecuta pruebas de mutación (mutation testing) con StrykerJS en proyectos TypeScript de React (web, con Vitest) y React Native (con Jest). Úsala siempre que el usuario mencione "mutation testing", "pruebas de mutación", "Stryker", "StrykerJS", "mutantes", "mutation score/coverage", "kill mutants", o quiera saber si sus tests unitarios de componentes, hooks, o lógica de negocio realmente detectan bugs más allá de la cobertura de líneas. Aplica tanto a setup desde cero (instalar Stryker, escribir stryker.config.mjs, elegir el runner correcto según Jest o Vitest) como a ejecutar una config existente, diagnosticar corridas lentas o que fallan, o interpretar el reporte HTML/JSON. Cubre tanto proyectos React web como React Native, cada uno con su propio runner y particularidades (Metro/mocks nativos en RN, JSX/TSX, snapshots).
---

# Mutation testing en React / React Native + TypeScript (StrykerJS)

## Por qué esto no es trivial en un stack de frontend

La cobertura de líneas dice qué código *se ejecutó*, no si un test fallaría al romperse ese código. StrykerJS cambia el código fuente de forma controlada (invierte condiciones, cambia operadores, altera valores de props, elimina llamadas) y vuelve a correr los tests contra cada mutante. Si algún test falla, el mutante "muere"; si todo sigue pasando, "sobrevive" — señal de que esa rama no está realmente verificada.

En React/React Native hay una trampa específica que no existe igual en otros stacks: **los tests basados solo en snapshots casi nunca matan mutantes**. Un test `expect(tree).toMatchSnapshot()` vuelve a capturar cualquier salida que produzca el componente mutado y la compara contra el snapshot ya guardado — si el snapshot no se regeneró, el test sigue pasando aunque el render haya cambiado por completo, y si sí se regeneró (`--ci=false` con `-u`), el mutante nunca es detectado porque el snapshot "aprende" el bug. Antes de correr Stryker sobre una base grande de componentes, dile esto al usuario: un mutation score bajo en componentes cubiertos "al 100%" con snapshots no es un bug de configuración, es exactamente lo que la herramienta está diseñada para exponer. La solución no es Stryker, es escribir aserciones explícitas (`getByText`, `expect(prop).toBe(...)`) en los tests críticos.

Otras dos fricciones a anticipar:
1. **Costo en React Native**: los tests que montan árboles de componentes completos con mocks pesados de módulos nativos son lentos, y Stryker los re-ejecuta por cada mutante. Igual que con tests de integración en otros stacks, conviene acotar el mutation testing a hooks, utilidades y lógica de negocio pura antes de expandirlo a componentes completos.
2. **ESM**: StrykerJS es ESM puro desde la v6. El archivo de configuración es `stryker.config.mjs` (o `.cjs`/`.json` si el proyecto no es ESM), no lo confundas con configuración CommonJS antigua que pueda aparecer en tutoriales viejos.

## Paso 1: Detectar qué tiene cada proyecto

Como son repos separados, trata cada uno de forma independiente — no asumas que la config de uno sirve para el otro:

- **Proyecto React web**: revisa `package.json` y el archivo de config de Vitest (`vitest.config.ts` o dentro de `vite.config.ts`). Confirma que el runner de tests sea efectivamente Vitest (no Jest heredado de un boilerplate viejo).
- **Proyecto React Native**: revisa `package.json` → `jest` (o `jest.config.js`) y confirma que usa el preset `react-native` o `@react-native/jest-preset`. Anota si hay `transformIgnorePatterns` custom (típico en RN por los módulos nativos en `node_modules` que necesitan transformarse) — Stryker necesita que Jest siga funcionando igual dentro de su sandbox.
- En ambos: confirma la versión de TypeScript y si hay un `tsconfig.json` único o varios (monorepo interno, paths distintos para app/tests).
- Si ya existe `stryker.config.mjs`/`.json`: es ajuste/diagnóstico, no setup desde cero — edítalo, no lo dupliques.

## Paso 2: Instalar y configurar

### Antes de fijar versiones

Verifica en npm (`@stryker-mutator/core`, `@stryker-mutator/jest-runner`, `@stryker-mutator/vitest-runner`, `@stryker-mutator/typescript-checker`) cuáles son las versiones más recientes antes de escribir un `package.json` — StrykerJS publica seguido y usar versiones desalineadas entre `core` y el runner es la causa más común de errores crípticos al arrancar.

### React web (Vitest)

```bash
npm install --save-dev @stryker-mutator/core @stryker-mutator/vitest-runner @stryker-mutator/typescript-checker
```

Ver `vitest-react.md` para el `stryker.config.mjs` completo y las particularidades de Vitest (coverageAnalysis se ignora, solo soporta `threads: true`, no soporta Browser Mode).

### React Native (Jest)

```bash
npm install --save-dev @stryker-mutator/core @stryker-mutator/jest-runner @stryker-mutator/typescript-checker
```

Ver `jest-react-native.md` para el `stryker.config.mjs` completo, cómo apuntar al `jest.config.js` del proyecto, y cómo lidiar con los mocks de módulos nativos dentro del sandbox de Stryker.

En ambos casos, si el proyecto usa TypeScript (que es el caso), añade el checker de tipos — hace que Stryker descarte mutantes que ni siquiera compilan antes de gastar tiempo corriendo tests contra ellos:

```js
// stryker.config.mjs
export default {
  checkers: ['typescript'],
  tsconfigFile: 'tsconfig.json',
};
```

## Paso 3: Acotar qué se muta

Configura `mutate` explícitamente en vez de dejar el default demasiado amplio:

```js
mutate: [
  'src/**/*.{ts,tsx}',
  '!src/**/*.stories.tsx',      // Storybook, sin lógica que testear
  '!src/**/*.d.ts',
  '!src/**/__mocks__/**',
  '!src/**/__tests__/**',
  '!src/**/*.{test,spec}.{ts,tsx}',
],
```

Ajusta los paths reales del proyecto (puede ser `app/` en vez de `src/` en React Native con Expo Router, por ejemplo — mira la estructura real antes de copiar este bloque literal). Prioriza dejar dentro del alcance:
- Hooks custom (`useX`) — suelen tener la lógica condicional más rica y son baratos de testear sin montar UI.
- Funciones utilitarias, selectors, formateadores, validadores.
- Reducers / lógica de estado (Redux, Zustand, Context reducers).

Y dejar fuera inicialmente, hasta tener una primera línea base:
- Componentes puramente presentacionales sin lógica condicional.
- Código generado (barrels `index.ts`, tipos, configuración de navegación declarativa).

## Paso 4: Ejecutar

```bash
npx stryker run
```

Si la corrida es lenta en React Native, antes de tocar la config de paralelismo revisa si `mutate` sigue incluyendo componentes con montajes pesados — es la causa más frecuente, igual que con tests de integración en otros stacks.

## Paso 5: Leer el reporte

Stryker genera por defecto un reporte HTML interactivo (`reports/mutation/mutation.html`) y puede emitir también JSON (reporter `json`) siguiendo el schema de `mutation-testing-report-schema`, con estados `Killed`, `Survived`, `NoCoverage`, `Timeout`, `RuntimeError`, `CompileError`, `Ignored`.

Usa `summarize_mutants.py` sobre ese JSON para un resumen por archivo sin abrir el HTML uno por uno:

```bash
npx stryker run --reporters json,html,clear-text
python3 summarize_mutants.py reports/mutation/mutation.json
```

Al mostrarle los resultados al usuario, distingue explícitamente entre archivos con mutantes `Survived` genuinos (falta un test) y archivos donde la mayoría son `NoCoverage` (directamente no hay tests corriendo sobre ese código) — son problemas distintos y requieren acciones distintas.

## Paso 6: Umbral para CI

```js
// stryker.config.mjs
export default {
  thresholds: { high: 80, low: 60, break: 50 },
};
```

`break` hace que el proceso termine con código de salida distinto de cero por debajo de ese score — úsalo para fallar el pipeline. Igual que en otros stacks, no fijes un `break` alto sin haber corrido Stryker antes al menos una vez para tener una línea base real.

## Problemas comunes

- **Mutation score sospechosamente alto en componentes con muchos snapshots**: ver la sección "Por qué esto no es trivial" arriba — probablemente los snapshots se regeneraron automáticamente y no están detectando nada. Pide al usuario que revise si corren con `--ci` (falla si el snapshot no coincide) en vez de con auto-actualización.
- **Corrida cuelga o timeouts en React Native**: revisa si hay temporizadores reales (`setTimeout`, animaciones) sin usar fake timers en los tests — Stryker corre cada mutante con un timeout calculado sobre el tiempo base, y tests que dependen de temporizadores reales son inherentemente inestables bajo mutación.
- **Errores de módulos nativos no mockeados dentro del sandbox de Stryker**: confirma que `jest.config.js` (con sus `transformIgnorePatterns` y `moduleNameMapper` para assets/imágenes) se está resolviendo igual dentro del sandbox — normalmente basta con apuntar `jest.configFile` explícitamente en la config de Stryker en vez de confiar en el autodetect.
- **Vitest: `coverageAnalysis` no tiene efecto**: es esperado, el vitest-runner de Stryker ignora esa opción y maneja su propio análisis de cobertura; no es un bug de tu configuración.
- **Mutantes que no compilan inflando el conteo**: si no activaste `checkers: ['typescript']`, cada mutante que rompe el tipado cuenta como `RuntimeError` en vez de descartarse limpio — actívalo, es casi siempre una mejora neta de velocidad y claridad del reporte.