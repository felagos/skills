# Stryker + Jest en un proyecto React Native

Verifica versiones actuales de `@stryker-mutator/core`, `@stryker-mutator/jest-runner` y `@stryker-mutator/typescript-checker` en npm antes de fijar `package.json` — deben ir alineadas entre sí.

## `stryker.config.mjs`

```js
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  testRunner: 'jest',
  checkers: ['typescript'],
  tsconfigFile: 'tsconfig.json',

  jest: {
    // Apunta explícitamente al config real del proyecto en vez de confiar en el
    // autodetect — en RN suele haber transformIgnorePatterns/moduleNameMapper
    // custom para módulos nativos que Stryker necesita respetar dentro de su sandbox.
    configFile: 'jest.config.js',
    enableFindRelatedTests: true, // solo corre los tests relacionados con cada mutante
  },

  mutate: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/__mocks__/**',
    '!src/**/__tests__/**',
    '!src/**/*.{test,spec}.{ts,tsx}',
  ],

  reporters: ['html', 'clear-text', 'progress', 'json'],
  thresholds: { high: 80, low: 60, break: 50 },

  incremental: true,
  incrementalFile: 'reports/stryker-incremental.json',
};
```

## Particularidades de React Native

- **`coverageAnalysis: 'perTest'`**: a diferencia del vitest-runner, el jest-runner de Stryker sí soporta y se beneficia de esta opción — junto con `enableFindRelatedTests`, reduce muchísimo el tiempo de corrida porque Jest no vuelve a correr toda la suite por cada mutante, solo los tests relacionados con el archivo mutado.
- **Mocks de módulos nativos**: si el proyecto tiene un `jest.setup.js` que mockea `react-native-reanimated`, `@react-native-async-storage/async-storage`, cámaras, notificaciones push, etc., confirma que ese setup se referencia igual en `jest.config.js` (`setupFilesAfterEach`/`setupFiles`) — Stryker ejecuta Jest dentro de un sandbox que copia el proyecto, así que cualquier ruta relativa rota ahí falla de forma distinta a como falla en local.
- **Metro vs Jest**: Stryker no toca el bundler de Metro en ningún momento — solo instrumenta el código fuente TypeScript antes de que Jest (con su propio transform, normalmente `babel-jest` vía `babel.config.js`) lo compile para los tests. Si los tests ya corren bien con `jest` a secas, no debería haber sorpresas adicionales de bundling.
- **Preset `react-native` / `@react-native/jest-preset`**: no hace falta declarar nada especial para esto en la config de Stryker — se hereda automáticamente al apuntar `jest.configFile` al `jest.config.js` real del proyecto, que ya trae el preset.
- **Rendimiento en tests con `render()` de React Native Testing Library**: montar árboles completos de pantallas (con navegación, providers de tema, stores) es lo más costoso de re-ejecutar por mutante. Si la primera corrida tarda demasiado, la palanca más efectiva no es aumentar `concurrency`, sino acotar `mutate` a hooks y utilidades primero, y expandir a componentes de pantalla completos después, cuando ya haya una línea base.

## Testing Library y aserciones que sí matan mutantes

Igual que en el proyecto web: revisa que las aserciones vayan más allá de "no crasheó". En React Native Testing Library eso significa preferir `getByText`, `getByTestId(...).props`, o verificar llamadas a funciones de navegación (`toHaveBeenCalledWith('Screen', params)`) sobre snapshots de árboles completos, que son el principal generador de falsos "cubierto al 100%" en mutation testing de componentes RN.