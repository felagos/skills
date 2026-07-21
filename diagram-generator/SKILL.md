---
name: ascii-diagrams
description: >-
  Genera diagramas ASCII (de flujo/flowchart, de secuencia/interaccion, arboles/jerarquias) con anchos, paddings, margenes y alineacion de flechas calculados automaticamente por un script, nunca escritos "a mano" caracter por caracter. Usa esta skill siempre que el usuario pida un diagrama en texto plano, ASCII o monoespaciado: diagramas de flujo, flowcharts, diagramas de secuencia, diagramas de interaccion entre servicios o actores, arboles de directorios, jerarquias organizacionales, arboles de decision, o cualquier diagrama de cajas y nodos conectados por flechas que deba pegarse en un README, comentario de codigo, ticket, o terminal. Tambien usala si el usuario pide "dibujar" o "esquematizar" un proceso, flujo, arquitectura o conversacion entre componentes en formato texto (no imagen).
---

# Diagramas ASCII

Esta skill genera diagramas ASCII precisos renderizando una descripcion JSON del
diagrama con `./render_diagram.py`. El script calcula matematicamente:

- El ancho de cada caja segun el texto que contiene (con wrap de palabras si es largo).
- El padding interno y los bordes.
- La separacion horizontal entre cajas de una misma fila/capa.
- Las columnas donde caen las lineas de flujo/lifelines.
- El enrutado de flechas (incluidas las que "saltan" niveles) sin atravesar cajas.

**Nunca dibujes el diagrama tecleando caracteres de caja a mano línea por línea.**
Aunque el diagrama parezca simple, siempre construye el JSON y ejecuta el script.
Esto es lo que garantiza que el padding, el centrado del texto y el espaciado de
las flechas sean correctos incluso cuando las etiquetas tienen longitudes distintas.

## Flujo de trabajo

1. Identifica el tipo de diagrama que se necesita: `flowchart`, `sequence`, o `tree`
   (ver "Elegir el tipo" abajo).
2. Construye el JSON de entrada siguiendo el esquema de esa seccion.
3. Ejecuta:
   ```bash
   python3 ./render_diagram.py input.json
   ```
   (o pipea el JSON por stdin con `-`). Usa `-o archivo.txt` si el usuario quiere
   el resultado guardado en un archivo.
4. Revisa la salida: confirma que ningun texto quedo cortado y que las flechas
   apuntan a donde corresponde. Si una etiqueta es muy larga y rompe la
   legibilidad, acortala en el JSON y vuelve a ejecutar — no edites el ASCII
   resultante a mano.
5. Pega el resultado tal cual (dentro de un bloque de codigo ```) en tu
   respuesta. Si el usuario pidio un archivo, ya se genero con `-o`.

## Elegir el tipo

- **`flowchart`** — procesos, algoritmos, diagramas de decision, pipelines,
  cualquier cosa con pasos y (opcionalmente) ramas condicionales ("si"/"no").
- **`sequence`** — interaccion entre actores/servicios en el tiempo: quien le
  manda que mensaje a quien y en que orden (APIs, protocolos, llamadas entre
  microservicios, flujos de autenticacion, etc).
- **`tree`** — jerarquias: estructuras de carpetas/archivos, organigramas,
  arboles de decision sin condiciones de "vuelta", taxonomias.

Si el diagrama pedido no encaja claramente en ninguno (p. ej. un diagrama de
arquitectura con cajas dispersas y flechas en cualquier direccion), usa
`flowchart` de todas formas: las cajas conectadas por flechas con dirección son
el caso general que mejor soporta el layout automatico.

## Esquema: flowchart

```json
{
  "type": "flowchart",
  "nodes": [
    {"id": "A", "label": "Inicio"},
    {"id": "B", "label": "Es valido?", "shape": "diamond"},
    {"id": "C", "label": "Procesar"}
  ],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C", "label": "si"}
  ]
}
```

- `id`: identificador corto, unico, usado solo para conectar `edges`.
- `label`: el texto visible dentro de la caja. Puede tener varias palabras;
  el script hace wrap automatico si es largo (no hace falta insertar saltos
  de linea a mano).
- `shape`: `"box"` (default) o `"diamond"` para decisiones. Mantén las
  etiquetas de los diamantes cortas (1 linea, idealmente < 20 caracteres):
  el rombo se calcula para una sola linea de texto.
- `edges[].label`: opcional, texto sobre la flecha (p. ej. "si"/"no").
- El layout (capas, orden, alineacion de cadenas simples) se calcula solo a
  partir de las conexiones — no hay forma de fijar posiciones manualmente, y
  no deberia hacer falta.
- El script detecta automaticamente cuando una flecha "salta" mas de un nivel
  (por ejemplo un `if` que se reincorpora varios pasos despues) y la enruta
  por un carril lateral para no atravesar cajas intermedias.

## Esquema: sequence

```json
{
  "type": "sequence",
  "participants": ["Cliente", "API", "BaseDeDatos"],
  "messages": [
    {"from": "Cliente", "to": "API", "label": "POST /login", "style": "solid"},
    {"from": "API", "to": "BaseDeDatos", "label": "SELECT usuario", "style": "solid"},
    {"from": "BaseDeDatos", "to": "API", "label": "fila encontrada", "style": "dashed"},
    {"from": "API", "to": "Cliente", "label": "200 OK", "style": "dashed"}
  ]
}
```

- `participants`: orden de izquierda a derecha de las lifelines.
- `messages`: en el orden temporal en que ocurren (de arriba hacia abajo).
- `style`: `"solid"` para llamadas/requests, `"dashed"` para respuestas/retornos
  (convencion estandar en diagramas de secuencia).
- El ancho de cada columna y el espacio entre lifelines se recalculan
  automaticamente (con varias pasadas) hasta que hasta el mensaje con la
  etiqueta mas larga —incluidos mensajes entre participantes no adyacentes—
  entra sin cortarse.
- Mensajes con `from == to` (auto-llamadas) se muestran como una nota inline;
  no dibujan un loop completo.

## Esquema: tree

```json
{
  "type": "tree",
  "root": {
    "label": "src/",
    "children": [
      {"label": "components/", "children": [
        {"label": "Button.tsx"},
        {"label": "Header.tsx"}
      ]},
      {"label": "index.ts"}
    ]
  }
}
```

- Estructura recursiva estandar. `children` es opcional (hojas no lo llevan).
- El indentado y los conectores (`├──`, `└──`, `│`) se calculan recursivamente
  segun la profundidad y si cada nodo es el ultimo de su nivel — igual que el
  comando `tree` de Unix.

## Limitaciones a tener en cuenta

- El layout de `flowchart` ordena las cajas de cada capa en el orden en que
  aparecen los nodos en el JSON (mas una heuristica de alineacion para
  cadenas simples de 1 padre → 1 hijo). En grafos con muchas ramas que se
  cruzan entre si, el resultado sigue siendo correcto y sin solapamientos,
  pero puede no ser el mas compacto visualmente — si el usuario pide algo
  muy elaborado, considera dividirlo en sub-diagramas mas simples.
- Los diamantes (`shape: diamond`) estan pensados para etiquetas de una sola
  linea; si el texto es muy largo, acortalo (p. ej. "¿Stock disponible?" en
  vez de una oracion completa).
- En `sequence`, las auto-llamadas (`from == to`) no dibujan un loop visual,
  solo una nota — si el usuario necesita el loop clasico, acláralo como
  limitacion conocida.