# Documento técnico — call-me-maybe

> Rol de este documento: es tu ticket técnico. Te dice **qué** debe hacer cada
> pieza y **en qué orden** construirla, no **cómo** implementarla por dentro.
> Para el "cómo" (dudas conceptuales, por qué algo funciona así, alternativas)
> ese es el rol "funcional" — pregúntame.

Cada ticket tiene: objetivo, contrato (inputs/outputs), casos a contemplar, y
checklist de aceptación. Ve tachando antes de pasar al siguiente — están
ordenados por dependencia, no por dificultad.

---

## Ticket 0 — Estructura del repo

**Objetivo**: tener el esqueleto de carpetas y ficheros de configuración antes
de escribir lógica.

**Qué crear** (contenido, no lógica):
- `pyproject.toml` con dependencias `pydantic` y `numpy`, y sección `[tool.mypy]`
- `Makefile` con las reglas `install / run / debug / clean / lint / lint-strict`
  (comandos exactos en el PDF, capítulo IV.2)
- `.gitignore`
- `src/__init__.py` (vacío, solo para que `src` sea un paquete)
- `data/input/functions_definition.json` y `data/input/function_calling_tests.json`
  (usa los ejemplos del PDF V.2 para probar)

**Checklist**:
- [ ] `uv sync` corre sin error
- [ ] `make lint` corre (aunque no haya nada que lintar todavía)

---

## Ticket 1 — Modelos de datos (pydantic)

**Objetivo**: representar con pydantic las tres formas de JSON que vas a
manejar: la definición de funciones, los prompts de entrada, y el resultado
de salida. El enunciado exige que **todas las clases usen pydantic**.

**Contrato** — necesitas modelar, como mínimo:

| Concepto | Campos |
|---|---|
| Una función disponible | `name: str`, `description: str`, `parameters: dict[str, ...]`, `returns: ...` |
| Un parámetro de función | `type`: literal `"number" \| "string" \| "boolean"` |
| Un prompt de test | `prompt: str` |
| Un resultado de salida | `prompt: str`, `name: str`, `parameters: dict[str, Any]` |

**Preguntas que te tienes que responder tú (y que yo te ayudo a pensar si
quieres)**:
- ¿Cómo restringes con pydantic que `type` solo pueda ser esos 3 valores y no
  cualquier string?
- ¿Qué pasa si `functions_definition.json` trae un campo `returns` mal
  formado? ¿Debe fallar la carga de *todo* el fichero o solo esa función?

**Checklist**:
- [ ] Puedes cargar el `functions_definition.json` de ejemplo y validarlo sin
  errores
- [ ] Si le metes un JSON con un campo `type` inválido (p. ej. `"list"`),
  pydantic lo rechaza con un error entendible

---

## Ticket 2 — Lectura/escritura de ficheros con manejo de errores

**Objetivo**: cargar JSON y guardarlo, cumpliendo "el programa nunca debe
crashear inesperadamente" (PDF IV.1).

**Contrato**:
- Una función que cargue un JSON desde una ruta y devuelva los datos parseados
- Debe distinguir (con mensajes claros, no un traceback crudo) entre:
  - fichero no existe
  - fichero existe pero no es JSON válido
  - fichero JSON válido pero no cumple el schema esperado (esto lo detecta
    pydantic en el Ticket 1, pero aquí decides *qué hacer* cuando pasa)
- Una función que guarde el resultado final en `data/output/`, creando el
  directorio si no existe

**Checklist**:
- [ ] Borra `functions_definition.json` y comprueba que el programa da un
  mensaje claro, no un traceback
- [ ] Mete `{esto no es json` en un fichero de test y comprueba lo mismo

---

## Ticket 3 — Vocabulario: id ↔ texto de token

**Objetivo**: poder traducir un `token_id` (int) a su representación en texto,
y viceversa dado un texto candidato. Esto es la base de todo lo que viene
después — sin esto no puedes saber qué token representa qué string.

**Contrato**:
- Cargar el fichero de `llm.get_path_to_vocab_file()` (aún no sabes el
  formato exacto — tendrás que inspeccionarlo con el `llm_sdk` real cuando lo
  tengas)
- Dado un `token_id`, devolver el texto que produce
- Dada una lista de `token_ids`, devolver el texto concatenado completo

**Cosa importante a investigar tú mismo/a** (pregúntame si quieres el porqué):
la mayoría de tokenizers BPE tipo GPT-2/Qwen usan un carácter especial para
marcar "este token empieza con un espacio". Vas a tener que abrir el fichero
de vocab real y mirar cómo se representa, no lo vas a poder adivinar sin
mirarlo.

**Checklist**:
- [ ] Puedes cargar el vocab real (cuando tengas `llm_sdk`) y hacer un dump
  de los primeros 20 tokens para ver el formato
- [ ] Tienes una función `id_to_text(token_id) -> str` que ya limpia esos
  marcadores especiales

---

## Ticket 4 — Gramáticas por tipo de valor

**Objetivo**: para cada tipo de "hueco" que el LLM tiene que rellenar
(función a elegir, number, string, boolean), definir dos reglas:

1. `es_continuacion_valida(generado_hasta_ahora, texto_candidato) -> bool`
2. `esta_completo(generado_hasta_ahora) -> bool`

Esto es el corazón conceptual del constrained decoding — te recomiendo que
antes de programar esto hablemos del concepto si no lo tienes 100% claro
(dímelo).

**Los 4 casos que necesitas**:

| Tipo | Continuación válida | Completo cuando... |
|---|---|---|
| Enum (nombre de función) | el string generado + candidato sigue siendo prefijo de ALGUNA opción | el string generado coincide EXACTO con alguna opción |
| `number` | sigue el patrón de un número JSON parcial (signo, dígitos, un punto máximo) | ya es un número JSON completo y válido |
| `string` | no contiene caracteres prohibidos (comillas sin escapar, saltos de línea...) | se ha emitido la comilla de cierre |
| `boolean` | es prefijo de `"true"` o `"false"` | coincide exacto con una de las dos |

**Checklist** (puedes testear esto con pytest SIN necesitar el LLM real,
son funciones puras):
- [ ] Test: para enum con opciones `["fn_add", "fn_greet"]`, `"fn_a"` es
  continuación válida pero `"fn_x"` no
- [ ] Test: para number, `"-"` seguido de otro `"-"` no es válido
- [ ] Test: para number, `"3.5"` seguido de otro `"."` no es válido
- [ ] Test: para string, un token que contenga `\n` sin escapar se rechaza

---

## Ticket 5 — Bucle de generación con logit masking

**Objetivo**: dado un contexto (lista de `input_ids`) y unas reglas del
Ticket 4, generar texto token a token usando el LLM real, garantizando que
solo se puedan elegir tokens válidos.

**Contrato** (pseudocódigo, no código):

```
generado = ""
ids = contexto inicial

repetir hasta max_tokens:
    si esta_completo(generado): parar

    logits = llm.get_logits_from_input_ids(ids)

    para cada token_id en el vocabulario:
        texto_candidato = vocab.id_to_text(token_id)
        si NO es_continuacion_valida(generado, texto_candidato):
            logits[token_id] = -infinito

    elegido = el id con el logit más alto
    generado += vocab.id_to_text(elegido)
    ids.append(elegido)

devolver generado
```

**Preguntas para pensar tú (o preguntarme)**:
- ¿Qué pasa si TODOS los logits acaban en `-infinito` en algún paso? ¿Puede
  pasar si tus reglas del Ticket 4 están bien definidas? ¿Qué haces como red
  de seguridad?
- ¿Por qué recorrer todo el vocabulario en cada paso es aceptable aquí
  (tamaño del problema) aunque en general sea "caro"?

**Checklist**:
- [ ] Con el LLM real, generar un enum de 2-3 opciones y comprobar que
  siempre termina en una de ellas
- [ ] Generar un number y comprobar con `json.loads` que el resultado parsea

---

## Ticket 6 — Prompt engineering + orquestación (pipeline)

**Objetivo**: para un prompt en lenguaje natural, montar todo:

1. Construir el texto que le vas a dar al LLM como contexto (describiendo
   las funciones disponibles y el prompt del usuario)
2. Pedir al LLM que elija el nombre de función (Ticket 5 + gramática enum)
3. Para cada parámetro de esa función, en orden, generar su valor
   (Ticket 5 + gramática según su `type`)
4. Ir montando el JSON final como texto literal (tú escribes `{`, `"name":`,
   comas, etc. — NO se lo pides al modelo)

**Decisión de diseño que tienes que tomar tú**:
¿Cómo le "explicas" al LLM, en el prompt de texto, qué funciones existen y
cuál es la pregunta del usuario, para que tenga contexto suficiente al elegir
entre las opciones del enum? Piensa qué información necesita ver y en qué
formato.

**Checklist**:
- [ ] Con las funciones de ejemplo del PDF, el prompt "What is the sum of 2
  and 3?" produce `fn_add_numbers` con `a=2, b=3`
- [ ] "Greet shrek" produce `fn_greet` con `name="shrek"`

---

## Ticket 7 — CLI y main

**Objetivo**: `argparse` con `--functions_definition`, `--input`, `--output`
(valores por defecto en `data/input/` y `data/output/`, según PDF IV.3.2),
que llama a todo lo anterior para cada prompt del fichero de test y escribe
el resultado.

**Checklist**:
- [ ] `uv run python -m src` funciona con los defaults
- [ ] `uv run python -m src --input otro.json` funciona con ruta custom
- [ ] Un prompt que falle (excepción durante su procesado) no debe tirar
  abajo el resto — el programa sigue con los demás prompts

---

## Orden recomendado y por qué

Tickets 0→3 no dependen del LLM real, puedes avanzarlos ya. El Ticket 4 es
puro y testeable sin LLM (¡hazlo con TDD, te va a ahorrar muchísimo tiempo de
debug luego!). El Ticket 5 es donde por fin conectas con `llm_sdk` de
verdad, así que resérvalo para cuando tengas el paquete y hayas hecho el
Ticket 3 completo (inspeccionar el vocab real). El 6 y 7 son integración.

---

## Cuándo preguntarme (rol funcional)

Ideas de cuándo tiene sentido que me preguntes en vez de darle vueltas solo:
- No entiendes por qué una gramática debe comportarse de una forma concreta
- Quieres validar una decisión de diseño antes de programarla (para no tirar
  tiempo si el enfoque tiene un fallo conceptual)
- Un test falla y no ves por qué a nivel conceptual (no pegues el traceback
  esperando que te lo arregle — cuéntame qué esperabas y qué pasó)
