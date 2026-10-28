# 1.6 · Catálogo de herramientas del agente

El agente decide qué herramienta usar y en qué orden. De cada herramienta solo ve el **nombre**,
la **descripción** y los **parámetros**, así que la descripción funciona como un prompt: dice qué
hace, cuándo usarla y cuándo NO.

El guardrail de entrada (inyección y longitud) y el guardrail de salida no son herramientas:
se ejecutan siempre, antes y después del agente (ver 01_diseno/cadena.md).

## Orden y reglas de orquestación

```
analizar_consulta ──► ¿fuera de alcance? ── sí ──► redactar_respuesta (abstención)
        │
        ├─► ¿falta un dato imprescindible? ── sí ──► pedir_aclaracion (máx. 1)
        │
        ├─► tipo técnica  ──► buscar_normativa
        ├─► tipo trámite  ──► consultar_tramites (+ buscar_normativa si hace falta la base legal)
        └─► tipo mixta    ──► buscar_normativa + consultar_tramites
                                   │
                          comprobar_cobertura ── buscar_mas (máx. 2 rondas) ──┐
                                   │                                         │
                                   ◄─────────────────────────────────────────┘
                                   │
                          redactar_respuesta (siempre la última, una vez)
```

Reglas:
1. `analizar_consulta` es siempre la primera y se llama una sola vez.
2. Si la consulta está fuera de alcance, se pasa directamente a `redactar_respuesta` sin buscar.
3. `pedir_aclaracion` como máximo una vez por consulta y siempre antes de buscar.
4. Nunca se llama a `redactar_respuesta` sin pasar antes por `comprobar_cobertura`, salvo en la abstención temprana de la regla 2.
5. Como máximo 2 rondas de búsqueda adicionales tras `comprobar_cobertura`.
6. Límite total: 8 llamadas a herramientas por consulta. Si se alcanza, se redacta con lo disponible y un aviso de cobertura parcial.
7. `redactar_respuesta` es siempre la última y se llama una sola vez (más el reintento interno del validador).

## Cuándo usar cada herramienta de búsqueda

| La pregunta busca… | Herramienta | Ejemplo |
|---|---|---|
| Qué exige una norma, a qué se aplica, qué requisito fija | `buscar_normativa` | ¿Qué instalaciones quedan fuera del RITE? |
| Qué formulario presentar, ante quién, con qué pasos | `consultar_tramites` | ¿Con qué modelo comunico la puesta en servicio en Aragón? |
| Las dos cosas | ambas | ¿Qué autorizaciones necesito para una geotermia en Zaragoza? |

---

### analizar_consulta

**Descripción (lo que lee el LLM):**
Analiza la pregunta del usuario antes de hacer nada más. Indica si es técnica (qué exige la norma),
de trámite (qué presentar y ante quién) o mixta; qué tipos de instalación y niveles normativos
implica; si está dentro del alcance del asistente y qué dato imprescindible falta, si falta alguno.
Úsala siempre como primer paso, una sola vez por consulta.
NO busca documentos ni responde al usuario.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| pregunta | texto (máx. 1000 caracteres) | sí | La pregunta del usuario, tal cual |
| filtro_nivel | lista de: Estado, Aragón, Zaragoza | no | Filtro elegido por el usuario en la interfaz |
| filtro_tipo_instalacion | lista de: incendios, calefacción, suelo radiante, agua, climatización, geotermia | no | Filtro elegido por el usuario |

**Devuelve:**
| Campo | Tipo | Contenido |
|---|---|---|
| tipo | uno de: tecnica, tramite, mixta | Clase de pregunta (T-01) |
| tipos_instalacion | lista | Instalaciones detectadas o filtradas (T-02) |
| niveles | lista | Niveles implicados (T-02) |
| en_alcance | booleano | Si el corpus puede responderla (T-03) |
| motivo_fuera_alcance | texto o nulo | Por ejemplo: «norma UNE de pago», «municipio fuera del ámbito», «pide un cálculo» |
| dato_que_falta | uno de: tipo_instalacion, tipo_actuacion, potencia, municipio, ninguno | Si hay que pedir aclaración |

**Si falla:** se continúa con tipo = mixta, sin filtros extra y en_alcance = true; la búsqueda y
`comprobar_cobertura` harán de red de seguridad.

**Cuándo se usa en el orden:** siempre la primera.

---

### pedir_aclaracion

**Descripción (lo que lee el LLM):**
Hace UNA pregunta breve al usuario para obtener un dato imprescindible que falta en su consulta
y sin el cual la búsqueda daría resultados de otra instalación u otro trámite: el tipo de
instalación, si es nueva, una reforma o una baja, o la potencia cuando el trámite depende de ella.
Úsala solo cuando la consulta es ambigua, por ejemplo «¿Qué necesito para legalizar mi instalación?».
NO la uses si la consulta ya trae los datos necesarios (por ejemplo, «geotermia en Zaragoza»),
ni si está fuera de alcance (otro municipio, normas UNE, cálculos): en ese caso, abstente.
No la uses para confirmar datos que el usuario ya ha dado.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| pregunta_al_usuario | texto (máx. 200 caracteres) | sí | Una sola pregunta, clara y en español |
| dato_que_falta | uno de: tipo_instalacion, tipo_actuacion, potencia, municipio, otro | sí | Qué dato se pide |
| opciones | lista de textos | no | Respuestas sugeridas para que el usuario elija (por ejemplo, las seis instalaciones) |

**Devuelve:** la respuesta del usuario como texto. Mientras espera, la respuesta al usuario
lleva abstencion.aplica = true y la pregunta en abstencion.contexto_solicitado (contrato de la 1.4).

**Si falla:** si el usuario no contesta o su respuesta no aclara nada, no se vuelve a preguntar:
se responde con lo disponible y un aviso de cobertura parcial, o se abstiene.

**Cuándo se usa en el orden:** justo después de analizar_consulta y antes de cualquier búsqueda.
Como máximo una vez por consulta. Nunca después de redactar_respuesta.

---

### buscar_normativa

**Descripción (lo que lee el LLM):**
Busca fragmentos de normativa oficial (BOE, Gobierno de Aragón, Ayuntamiento de Zaragoza)
relevantes para una pregunta técnica: qué exige un reglamento, a qué se aplica, qué requisitos
fija un artículo. Úsala cuando necesites el texto de la norma para citarlo.
NO la uses para saber qué formulario presentar o ante qué órgano: para eso usa consultar_tramites.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| consulta | texto | sí | Pregunta o términos de búsqueda en español |
| niveles | lista de: Estado, Aragón, Zaragoza | no | Filtra por nivel; vacío = todos |
| tipos_instalacion | lista de: incendios, calefacción, suelo radiante, agua, climatización, geotermia | no | Filtra por instalación |
| k | entero (1–20) | no, por defecto 10 | Número de fragmentos a devolver |

**Devuelve:** lista de fragmentos, cada uno con chunk_id, texto, norma, articulo_o_paso, nivel,
organo, url, fecha_captura y puntuación. Internamente: búsqueda híbrida (embeddings + BM25),
filtro por metadatos y re-ranking (T-05, T-06, T-08).

**Si falla:** error `busqueda_no_disponible`. El agente no debe responder sin fuentes.

**Cuándo se usa en el orden:** después de analizar_consulta; puede llamarse varias veces
(por ejemplo, una por nivel).

---

### consultar_tramites

**Descripción (lo que lee el LLM):**
Devuelve los trámites administrativos para legalizar o poner en servicio una instalación:
qué formulario o modelo presentar (por ejemplo, E0002a), ante qué órgano, en qué pasos y qué
documentación se exige. Úsala en preguntas de trámite o mixtas («qué tengo que comunicar»,
«con qué modelo», «ante quién», «qué autorización necesito»).
NO la uses para requisitos técnicos de la norma: para eso usa buscar_normativa.
Si la pregunta pide también la base legal del trámite, combínala con buscar_normativa.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| tipo_instalacion | uno de: incendios, calefacción, suelo radiante, agua, climatización, geotermia | sí | Instalación del trámite |
| tipo_actuacion | uno de: nueva, reforma, baja | no, por defecto nueva | Qué se quiere tramitar |
| niveles | lista de: Estado, Aragón, Zaragoza | no | Vacío = todos los que tengan trámites |

**Devuelve:** lista de trámites, cada uno con chunk_id, nombre, modelo, organo, nivel, pasos,
documentacion (o la referencia a la tabla o anexo que la recoge), url y fecha_captura.
Son datos estructurados extraídos en la ingesta (T-10), no texto libre.

**Si falla:** error `tramites_no_disponibles`. Si no hay trámites para esa combinación, devuelve
lista vacía (no es un error) y `comprobar_cobertura` lo marcará como nivel sin cubrir.

**Cuándo se usa en el orden:** después de analizar_consulta, cuando tipo es tramite o mixta.

---

### comprobar_cobertura

**Descripción (lo que lee el LLM):**
Revisa si los fragmentos y trámites recuperados bastan para responder la pregunta antes de redactar.
Comprueba qué niveles e instalaciones implicados tienen fuentes, si alguna parte de la pregunta queda
sin respaldo, si las fuentes se contradicen y si remiten a tablas o anexos que no se han recuperado.
Úsala siempre antes de redactar_respuesta.
NO redacta la respuesta ni busca documentos por sí misma: recomienda qué hacer.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| pregunta | texto | sí | La pregunta del usuario |
| analisis | objeto | sí | Lo que devolvió analizar_consulta |
| chunk_ids | lista de textos | sí | Fragmentos y trámites recuperados hasta ahora |

**Devuelve:**
| Campo | Tipo | Contenido |
|---|---|---|
| recomendacion | uno de: responder, responder_parcial, buscar_mas, abstenerse | Siguiente paso |
| niveles_cubiertos | lista | Niveles con al menos una fuente pertinente |
| niveles_sin_cubrir | lista | Niveles implicados sin fuentes |
| referencias_ausentes | lista de textos | Tablas, anexos o formularios citados pero no recuperados (por ejemplo, «TABLA 1») |
| contradicciones | booleano | Si hay fuentes que dicen cosas incompatibles |
| motivo | texto | Explicación breve |

Los niveles cubiertos y las referencias ausentes se calculan con código; la pertinencia y las
contradicciones las juzga un LLM.

**Si falla:** se asume recomendacion = responder_parcial y se añade aviso de cobertura parcial.

**Cuándo se usa en el orden:** después de las búsquedas y antes de redactar_respuesta. Si recomienda
buscar_mas, se permite como máximo 2 rondas de búsqueda adicionales.

---

### redactar_respuesta

**Descripción (lo que lee el LLM):**
Genera la respuesta final para el usuario en el formato del contrato (respuesta, texto_literal,
resumen, inferencias, citas, niveles_consultados, abstencion y avisos), usando solo los fragmentos
recuperados. Úsala una sola vez, como último paso: con los fragmentos si comprobar_cobertura
recomienda responder o responder_parcial, o sin fragmentos para abstenerse.
NO busca información ni la completa con conocimiento propio.

**Parámetros:**
| Nombre | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| pregunta | texto | sí | La pregunta del usuario |
| chunk_ids | lista de textos | sí (vacía en abstención) | Fragmentos que puede usar |
| cobertura | objeto | no | Lo que devolvió comprobar_cobertura (para los avisos) |
| motivo_abstencion | texto | no | Obligatorio si se llama para abstenerse |

**Devuelve:** el JSON validado con el contrato de la 1.4. Internamente usa el prompt
03_desarrollo/prompts/respuesta_v2.txt y `validar_respuesta` (citas solo de chunk_ids recibidos).

**Si falla:** si el JSON no valida, un reintento; si vuelve a fallar, abstención con motivo técnico.

**Cuándo se usa en el orden:** siempre la última y una sola vez.

---

## Recorridos de ejemplo

**1. «¿Qué autorizaciones necesito para una geotermia de circuito abierto en Zaragoza?»** (mixta)
analizar_consulta (mixta, geotermia, 3 niveles, en alcance) → buscar_normativa (Ley de Minas, RITE)
→ consultar_tramites (geotermia, nueva) → comprobar_cobertura (responder) → redactar_respuesta.
5 llamadas.

**2. «¿Qué necesito para legalizar mi instalación?»** (ambigua)
analizar_consulta (dato_que_falta = tipo_instalacion) → pedir_aclaracion («¿Qué tipo de instalación
es?», con las seis opciones) → [el usuario responde] → continúa como en el ejemplo 1 o 3.

**3. «¿Qué dice la ordenanza de incendios de Huesca?»** (fuera de alcance)
analizar_consulta (en_alcance = false, «municipio fuera del ámbito») → redactar_respuesta
(abstención). 2 llamadas, sin búsqueda.