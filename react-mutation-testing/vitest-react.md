# Stryker + Vitest en un proyecto React web

Verifica versiones actuales de `@stryker-mutator/core`, `@stryker-mutator/vitest-runner` y `@stryker-mutator/typescript-checker` en npm antes de fijar `package.json` — deben ir alineadas entre sí.

## `stryker.config.mjs`

```js
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  testRunner: 'vitest',
  checkers: ['typescript'],
  tsconfigFile: 'tsconfig.json',

  mutate: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.stories.tsx',
    '!src/**/*.d.ts',
    '!src/**/__mocks__/**',
    '!src/**/*.{test,spec}.{ts,tsx}',
  ],

  vitest: {
    // Si el proyecto tiene un config custom fuera del default vite.config.ts
    configFile: 'vitest.config.ts',
    // Si los tests no importan el código fuente directamente (poco común en React),
    // desactiva esto para no perderte mutantes:
    related: true,
  },

  reporters: ['html', 'clear-text', 'progress', 'json'],
  thresholds: { high: 80, low: 60, break: 50 },

  // Análisis incremental: reutiliza resultados de mutantes no afectados por el cambio
  incremental: true,
  incrementalFile: 'reports/stryker-incremental.json',
};
```

## Particularidades de Vitest como runner de Stryker

- **`coverageAnalysis` no aplica**: el vitest-runner ignora esa opción; Stryker usa su propio mecanismo de análisis de cobertura con Vitest, no hace falta configurarlo.
- **Solo `threads: true`**: si el proyecto tiene el pool de Vitest configurado en `forks` o `vmThreads`, Stryker fuerza `threads` internamente para su propio paralelismo. No es necesario (ni siempre posible) alinear esto con la config de Vitest del proyecto.
- **Browser Mode no soportado**: si el proyecto corre tests con `@vitest/browser` (Playwright/WebdriverIO), StrykerJS todavía no lo soporta — en ese caso, para mutation testing hay que apuntar a la porción de la suite que corre en modo Node/jsdom, o esperar soporte upstream.
- **In-source testing** (`if (import.meta.vitest) { ... }` dentro del mismo archivo fuente): hay que excluir explícitamente esos bloques de la mutación con el comentario de Stryker, o el propio test terminará mutado:

  ```ts
  // Stryker disable all
  if (import.meta.vitest) {
    const { it, expect } = import.meta.vitest;
    it('...', () => { ... });
  }
  // Stryker restore all
  ```

## Testing Library y aserciones que sí matan mutantes

Si el usuario usa React Testing Library, prioriza revisar que las aserciones no se queden solo en "el componente renderizó sin crashear" (`expect(container).toBeTruthy()`, que no mata casi ningún mutante) y sí verifiquen comportamiento observable: texto renderizado (`getByText`), estado de elementos (`toBeDisabled`, `toHaveAttribute`), o llamadas a callbacks (`toHaveBeenCalledWith`). Un mutante que invierte una condición de `disabled` solo muere si algún test realmente comprueba el estado `disabled` del elemento, no solo que el componente exista en el DOM.