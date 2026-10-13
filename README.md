# Automatización IA: Agente Clasificador de Tickets

Agente de soporte que clasifica tickets de clientes. Un modelo local (Ollama) decide qué herramientas usar (buscar en manuales con RAG, consultar tickets anteriores en PostgreSQL), entrega una clasificación validada con Pydantic y, si el ticket es urgente, el código lo guarda en la base de datos.

El proyecto empezó como un **flujo** con LangGraph (el código decidía el camino) y evolucionó a un **agente con herramientas** (el modelo decide). Las secciones finales documentan ese cambio, las pruebas que se hicieron y los problemas encontrados.

## Tecnologías

- Python 3.11
- FastAPI
- LangChain 1.x (`create_agent`) sobre LangGraph
- ChromaDB + `langchain-chroma` (RAG)
- Ollama: `qwen2.5:7b` (agente) y `nomic-embed-text` (embeddings)
- Pydantic y pydantic-settings (esquemas y configuración)
- PostgreSQL 15
- Docker y Docker Compose (la API, Postgres y n8n se levantan con un comando; Ollama corre fuera de Docker)
- n8n (levantado en el compose, **aún no conectado** a la API)

## Arquitectura

```
Ticket llega (POST /procesar-ticket)
        |
        v
   AGENTE (qwen2.5:7b) decide qué hacer
        |-- buscar_manuales     -> rag/store.py       -> chroma_db/
        |-- tickets_similares   -> db/repository.py   -> PostgreSQL
        v
   Clasificacion (validada con Pydantic)
        |
        v
   CÓDIGO: si urgente == true -> repository.guardar_ticket() -> PostgreSQL
        |
        v
   Respuesta TicketOut
```

Decisión de diseño importante: **el agente decide qué herramientas de lectura usar, pero el guardado en la base lo hace el código**. Ver la sección "Por qué el guardado no es una herramienta del agente".

### Despliegue con Docker

```
Navegador (127.0.0.1:8000)
        |
        v
[contenedor tickets-api] --"postgres:5432"--> [contenedor postgres-tickets]
        |
        +--"host.docker.internal:11434"--> Ollama (en tu computador, fuera de Docker)
```

Ollama se deja fuera de Docker a propósito: los modelos ya están descargados en el computador y así no se duplican varios GB dentro de un contenedor.

## Estructura del proyecto

```
automatizacion-ia/
├── app/
│   ├── main.py          # crea la app FastAPI; construye el agente una vez (lifespan)
│   ├── routes.py        # endpoints GET / y POST /procesar-ticket
│   ├── config.py        # variables de entorno tipadas (pydantic-settings)
│   └── schemas.py       # TicketIn, Clasificacion, TicketOut
├── agent/
│   ├── builder.py       # construir_agente, clasificar_ticket, procesar_ticket
│   ├── tools.py         # buscar_manuales, tickets_similares
│   └── prompts.py       # prompt de sistema
├── rag/
│   ├── ingest.py        # indexa los PDFs (se corre una vez)
│   └── store.py         # abre el índice y busca
├── db/
│   ├── init.sql         # crea la tabla al primer arranque de Postgres
│   └── repository.py    # único archivo con SQL
├── eval/
│   ├── dataset.json     # 15 tickets etiquetados a mano
│   └── run_eval.py      # mide aciertos de urgencia y categoría
├── legacy/              # copias del proyecto original (flujo LangGraph), solo referencia
├── data/                # PDFs que se indexan
├── .env.example
├── .dockerignore        # qué no se copia a la imagen (venv, .env, chroma_db...)
├── Dockerfile           # imagen de la API
├── docker-compose.yml   # postgres + api + n8n
└── requirements.txt
```

## Requisitos previos

- Python 3.11 y un entorno virtual
- Ollama instalado y corriendo
- Docker Desktop corriendo
- Modelos descargados:

```
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

> El modelo debe soportar *tool calling*. `llama3` original no lo soporta bien en Ollama, por eso se usa `qwen2.5:7b`.

## Configuración

Copia la plantilla y completa tus valores:

```
copy .env.example .env
```

```
APP_ENV=development
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tickets
DB_USER=admin
DB_PASSWORD=tu_contraseña
OLLAMA_HOST=http://localhost:11434
N8N_USER=admin
N8N_PASSWORD=tu_contraseña_de_n8n
```

`.env` no se sube a GitHub. El `docker-compose.yml` lee las mismas variables, así que las credenciales viven en un solo lugar. Si falta una variable obligatoria, la app falla al arrancar con un mensaje claro.

Con Docker, el compose **pisa** dos valores del `.env` para el contenedor de la API: `DB_HOST=postgres` y `OLLAMA_HOST=http://host.docker.internal:11434`. Las variables de entorno tienen prioridad sobre el archivo `.env`, así que el `.env` puede seguir con `localhost` para correr la API directamente en tu computador.

## Cómo correr el proyecto

### Opción A: con Docker (recomendada)

Levanta Postgres, la API y n8n con un solo comando. Ollama sigue corriendo en tu computador, fuera de Docker.

1. **Clona el repositorio y entra a la carpeta:**
   ```
   git clone https://github.com/Raigou/automatizacion-ia.git
   cd automatizacion-ia
   ```
2. **Crea tu `.env`** a partir de la plantilla y completa las contraseñas (incluidas `N8N_USER` y `N8N_PASSWORD`):
   ```
   copy .env.example .env
   ```
3. **Agrega tus PDFs** en `data/`.
4. **Asegúrate de que Ollama esté corriendo** y de tener los modelos descargados (ver "Requisitos previos").
5. **Construye y levanta los contenedores.** La tabla se crea sola desde `db/init.sql`:
   ```
   docker-compose up -d --build
   ```
6. **Indexa los PDFs** dentro de Docker (una sola vez, o cuando cambien los PDFs):
   ```
   docker-compose run --rm api python -m rag.ingest
   ```
7. **Prueba** en http://127.0.0.1:8000/docs

Cómo se conectan las piezas:

- La API llega a Postgres por el nombre del servicio (`DB_HOST=postgres`) y a Ollama por `host.docker.internal:11434`. Esos valores se definen en el `docker-compose.yml`.
- El índice del RAG vive en el volumen de Docker `chroma_data`, distinto de la carpeta `chroma_db/` de tu computador.
- Si la API no responde, revisa el log con `docker-compose logs api`.

### Opción B: sin Docker para la API

1. Levanta solo la base de datos:
   ```
   docker-compose up -d postgres
   ```
2. Instala las dependencias y crea tu `.env`:
   ```
   pip install -r requirements.txt
   copy .env.example .env
   ```
3. Indexa los PDFs y corre la API:
   ```
   python -m rag.ingest
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

> `init.sql` solo se ejecuta cuando el volumen de Postgres está vacío. Si cambias la tabla, usa `docker-compose down -v` (borra los datos) y vuelve a levantar.
>
> No ejecutes la API en Docker y en local a la vez: usan el mismo puerto 8000.

## Ejemplo

Ticket no urgente:

```json
{"texto": "Hola, tengo una consulta sobre cómo funciona GPT-4"}
```

```json
{
  "texto_original": "Hola, tengo una consulta sobre cómo funciona GPT-4",
  "clasificacion": {
    "urgente": false,
    "categoria": "consulta",
    "resumen": "Consulta sobre cómo funciona GPT-4",
    "solucion_sugerida": null
  },
  "guardado_en_db": false
}
```

Ticket urgente:

```json
{"texto": "El sistema de pagos está caído, no podemos procesar ninguna transacción"}
```

```json
{
  "texto_original": "El sistema de pagos está caído, no podemos procesar ninguna transacción",
  "clasificacion": {
    "urgente": true,
    "categoria": "tecnico",
    "resumen": "El sistema de pagos está caído y no podemos procesar ninguna transacción.",
    "solucion_sugerida": null
  },
  "guardado_en_db": true
}
```

## Evaluación

```
python -m eval.run_eval
```

Corre el agente sobre `eval/dataset.json` (15 tickets: 6 urgentes y 9 no urgentes, con casos ambiguos a propósito y uno en inglés) y compara con las etiquetas. Usa `clasificar_ticket`, que **no escribe en la base de datos**, así que la evaluación no ensucia la tabla.

También se puede correr dentro de Docker, con la misma configuración que usa la API:

```
docker-compose run --rm api python -m eval.run_eval
```

Con la API dockerizada se obtuvo el mismo resultado que en local: 15/15 en urgencia, 14/15 en categoría y 0 errores. En esa corrida el ticket 1 volvió a salir como `facturacion`, y la tabla solo tenía un ticket (el de inicio de sesión), sin tickets de pagos previos. Es coherente con la hipótesis de abajo, pero no la prueba.

### Resultados por variante

| Variante | Urgencia | Categoría | Errores |
|---|---|---|---|
| `ToolStrategy`, sin reintento | 13/15 | 10/15 | 2 |
| `ToolStrategy` + reintento simple | 14/15 | 11/15 | 1 |
| `ProviderStrategy` (no es un agente, ver abajo) | 15/15 | 7/15 | 0 |
| `ToolStrategy` + categorías definidas en el prompt | 14/15 | 13/15 | 1 |
| **`ToolStrategy` + categorías + reintento con continuación (final)** | **15/15** | **14/15** | **0** |

Cuando hay errores, los porcentajes de urgencia y categoría se calculan sobre los 15 tickets, así que un error cuenta como fallo.

### Sobre la etiqueta del ticket 1

El ticket "El sistema de pagos está caído..." estaba etiquetado como `facturacion`. Se decidió que una caída del sistema es un problema **técnico** (aunque involucre pagos) y se cambió la etiqueta a `tecnico`.

Después del cambio, la categoría **siguió en 14/15**, porque la respuesta del modelo para este ticket **no es estable**: en las mediciones anteriores respondía `tecnico` y en la última respondió `facturacion`, aun con `temperature=0`. Solo se invirtió cuál es el desacierto.

Hipótesis sin verificar: la diferencia viene de lo que devuelve `tickets_similares`. En las mediciones anteriores la tabla tenía tickets de pagos ya guardados como `tecnico`, y en la última la tabla pudo estar vacía tras un `DELETE`. Si es así, el resultado del agente depende del contenido de la base, algo a tener en cuenta al evaluar.

Es un caso genuinamente ambiguo, y la cifra honesta de la variante final es **14/15 en categoría**.

### Cómo interpretar estos números

- Son 15 tickets: un solo caso mueve 7 puntos porcentuales.
- El prompt se ajustó mirando estos mismos 15 tickets, así que hay **riesgo de sobreajuste**. Es una medición inicial, no una cifra definitiva.
- Una mejora pendiente: agregar tickets nuevos que no se hayan usado para ajustar nada y medir solo con ellos.

## Historial de cambios: del flujo al agente

### Punto de partida (proyecto original)

- `model/agent.py`: grafo de LangGraph con dos nodos (`clasificar` y `guardar_db`) y una arista condicional (`decidir_siguiente`). El **código** decidía el camino; el modelo solo rellenaba un JSON.
- `model/rag.py`: cargaba y indexaba los PDFs.
- `app/main.py`: ejecutaba el RAG **siempre** antes de clasificar, e **indexaba los PDFs en cada arranque**.
- Modelo: `llama3`, llamado con el cliente `ollama` directamente.

Problemas detectados al revisarlo:

1. Cada arranque de la API reindexaba el PDF y duplicaba los chunks en Chroma.
2. `json.loads` sin protección: una respuesta ligeramente inválida causaba un error 500.
3. Conexión a Postgres sin cierre garantizado si el `INSERT` fallaba.
4. `os.getenv` repartido en varios archivos, sin validación.
5. Se exponía `str(e)` al cliente en los errores.
6. La tabla se creaba a mano con `docker exec`.
7. `llama3` no soporta bien *tool calling*, que es lo que necesita un agente.

### Cambios por archivo

| Archivo | Qué se hizo | Por qué |
|---|---|---|
| `.env` / `.env.example` | Variables de entorno en un solo lugar, con plantilla sin secretos. | Eliminar la inconsistencia de credenciales entre README, compose y código. |
| `docker-compose.yml` | Credenciales leídas desde `.env` (`${DB_USER}`...), `healthcheck` en Postgres, montaje de `db/init.sql`, se eliminó `version:` (obsoleto). | Una sola fuente de credenciales; saber cuándo Postgres está listo; tabla automática. |
| `db/init.sql` (nuevo) | Crea la tabla `tickets`, con una columna nueva `urgente`. | Reemplaza el paso manual y deja explícito el estado de urgencia. |
| `app/config.py` (nuevo) | Clase `Settings` (pydantic-settings) y `get_settings()` con `lru_cache`. | Falla al arrancar si falta una variable; valida tipos (`db_port` como `int`). El modelo queda como configuración (`llm_model`). |
| `app/schemas.py` (nuevo) | `TicketIn`, `Clasificacion` (con `Categoria` como `Literal`) y `TicketOut`. | Contrato de entrada y salida validado. Una categoría inventada por el modelo se rechaza en vez de llegar a la base. |
| `db/repository.py` (nuevo) | `guardar_ticket` y `buscar_tickets_similares`, con consultas parametrizadas. | Único lugar con SQL. Los `with` confirman o deshacen la transacción. |
| `rag/ingest.py` (nuevo) | Carga PDFs, los trocea (1000 caracteres, solape de 100), genera embeddings y los guarda en Chroma. Usa `langchain-chroma`. | Separar **indexar** de **consultar**: se acaban los chunks duplicados y los arranques lentos. |
| `rag/store.py` (nuevo) | `get_vectorstore()` (con `lru_cache`) y `buscar_contexto()`. | Abre el índice existente sin reindexar. Usa el mismo modelo de embeddings que la indexación. |
| `agent/tools.py` (nuevo) | Herramientas `buscar_manuales` y `tickets_similares` con `@tool`. | El modelo decide si usarlas y con qué consulta. Los docstrings son lo que el modelo lee para decidir. |
| `agent/prompts.py` (nuevo) | Prompt de sistema con pasos, definición de urgencia y definición de cada categoría. | Separar el comportamiento del agente de la lógica. Las categorías definidas subieron el acierto (ver resultados). |
| `agent/builder.py` (nuevo) | `construir_agente`, `clasificar_ticket` y `procesar_ticket`. | Ver detalle abajo. |
| `app/main.py` (reescrito) | `lifespan` construye el agente una vez y lo guarda en `app.state`. | Ya no se ejecuta código al importar el módulo. |
| `app/routes.py` (nuevo) | Endpoints con `response_model=TicketOut`; el error se registra en el log y el cliente recibe un mensaje genérico. | La salida queda validada y documentada en `/docs`; no se filtran detalles internos. |
| `eval/dataset.json` y `eval/run_eval.py` (nuevos) | Set de 15 tickets y script de evaluación. | Poder responder "¿cómo mediste si funciona?". |
| `legacy/` | Copias de `main.py`, `agent.py` y `rag.py` originales. | Conservar el flujo original para comparar. |
| `Dockerfile` (reescrito) | El original copiaba `model/agent.py` y `model/rag.py`, que ya no existen, así que no se podía construir. Se borró y se creó uno nuevo que copia `app/`, `agent/`, `rag/`, `db/` y `eval/`. | Poder construir una imagen de la API con la estructura nueva. El original sigue en la rama `legacy`. |
| `.dockerignore` (nuevo) | Excluye `venv/`, `.git/`, `.env`, `chroma_db/`, `legacy/` y archivos de caché. | Que la contraseña del `.env` y el entorno virtual no entren a la imagen. |
| `docker-compose.yml` (ampliado) | Nuevo servicio `api` con `env_file`, `DB_HOST=postgres`, `OLLAMA_HOST=http://host.docker.internal:11434`, volumen `chroma_data` para el índice, montaje de solo lectura de `data/` y `depends_on` con el `healthcheck` de Postgres. Las credenciales de n8n pasaron a variables del `.env`. | Levantar todo con un comando; que la API llegue a Postgres y a Ollama desde el contenedor; no dejar contraseñas escritas en un archivo que se sube a GitHub. |
| `.env.example` | Se agregaron `N8N_USER` y `N8N_PASSWORD`. | Plantilla completa sin secretos. |

### Cambios por función (`agent/builder.py`)

- **`construir_agente()`**: crea `ChatOllama(temperature=0)` y llama a `create_agent` con las herramientas, el prompt y `response_format=ToolStrategy(Clasificacion)`.
- **`clasificar_ticket(agente, texto)`**: solo clasifica y **no escribe en la base**. Evolucionó en tres versiones:
  1. Sin reintento: devolvía `resultado["structured_response"]` directamente. Fallaba con `KeyError` cuando el modelo no entregaba la clasificación.
  2. Reintento simple: repetía la misma pregunta hasta 3 veces. Con `temperature=0` el modelo daba casi siempre la misma respuesta, así que servía poco.
  3. **Reintento con continuación (final):** si falta la clasificación, agrega al historial "Entrega ahora la clasificación final." y vuelve a invocar. Cada intento es distinto del anterior y el modelo conserva lo que ya buscó.
- **`procesar_ticket(agente, texto)`**: llama a `clasificar_ticket` y, si `urgente` es verdadero, guarda con `repository.guardar_ticket`. `guardado_en_db` es verdadero solo si el código ejecutó el guardado.

### Por qué el guardado no es una herramienta del agente

Primero `guardar_ticket` sí era una herramienta. En las pruebas, el modelo **nunca la llamó**: clasificaba el ticket como urgente y entregaba la clasificación final directamente. Reescribir el prompt con más énfasis hizo que usara las herramientas de lectura, pero siguió sin guardar.

Se decidió separar *decidir* de *ejecutar*: el agente clasifica y el código guarda. Resultado: el guardado es determinista (si es urgente, se guarda siempre). El trade-off es que el agente ya no decide la acción con efecto secundario; sigue decidiendo qué herramientas de lectura usar y con qué consulta. Se probó el cambio con la prueba de pagos caídos y se confirmó la fila en Postgres.

## Pruebas y diagnósticos realizados

Durante el desarrollo se usaron scripts temporales. No forman parte del proyecto final, pero cada uno respondió una pregunta concreta:

| Script | Qué verificaba | Qué se encontró |
|---|---|---|
| `prueba_tools.py` | Si `qwen2.5:7b` hace *tool calling* con `bind_tools`. | Sí: llamó a `buscar_manuales` con la consulta "sistema de pagos caído". |
| Comandos `python -c ...` | `config.py` (valores cargados), `schemas.py` (rechazo de una categoría inventada), `repository.py` (insertar y leer), `rag/store.py` (búsqueda con "GPT-4 capabilities") y las herramientas sin el modelo. | Cada pieza funcionó de forma aislada antes de armar el agente. |
| `python -c "...inspect.signature(create_agent)"` | La firma real de `create_agent` en LangChain 1.3. | Confirmó `system_prompt` y `response_format`. En esta versión el agente se crea con `create_agent`, no con `create_react_agent`. |
| `prueba_agente.py` | El agente con un ticket no urgente y uno urgente. | El ticket urgente salió con `urgente: true` pero `guardado_en_db: false`. |
| `diagnostico.py` (1.ª vez) | Los mensajes internos del agente. | El modelo llamaba directo a `Clasificacion` y se saltaba todas las herramientas. |
| `diagnostico.py` (2.ª vez, tras reescribir el prompt) | Lo mismo con el prompt nuevo. | Ya usaba `buscar_manuales` y `tickets_similares`, pero seguía sin llamar a `guardar_ticket`. Llevó a mover el guardado al código. |
| `diagnostico2.py` | Por qué fallaba el ticket 15 con `KeyError: 'structured_response'`. | El modelo escribió `Clasificacion {...}` como **texto** en vez de hacer la llamada a la herramienta. |
| `diagnostico.py` (con `ProviderStrategy`) | Por qué cayó la categoría a 7/15. | El agente **dejó de usar herramientas**: con el formato forzado por Ollama, la primera respuesta ya es el JSON final. Esa variante es un clasificador de un paso, no un agente, y se descartó. |
| `diagnostico3.py` | Por qué fallaba el ticket 4. | Tras leer el resultado de `tickets_similares`, el modelo respondió **vacío**. Es un fallo distinto al anterior y motivó el reintento con continuación. |

### Pruebas de la dockerización

| Prueba | Qué verificaba | Qué se encontró |
|---|---|---|
| `docker-compose up -d` y `docker-compose ps` | Que los contenedores arrancan. | Postgres sale `healthy` y la API `Up` en el puerto 8000. |
| `docker-compose run --rm api python -m rag.ingest` | Que la API llega a Ollama desde el contenedor y que indexa en el volumen. | Mismas 100 páginas y 361 chunks que en local, con un `POST http://host.docker.internal:11434/api/embed` con `200 OK`. |
| Dos tickets en `/docs` y `SELECT` en Postgres | El camino completo: API, agente, base de datos. | El ticket de consulta salió sin guardar y el de inicio de sesión salió urgente, `tecnico` y guardado, con su fila en la tabla. |
| `docker-compose run --rm api python -m eval.run_eval` | Que el contenedor se comporta como el entorno local. | 15/15 en urgencia, 14/15 en categoría y 0 errores. |

Un problema encontrado: la primera imagen construida falló con `ModuleNotFoundError: No module named 'app'` y la API se cayó al arrancar. Se reconstruyó con `docker-compose build --no-cache api` y funcionó. **No se determinó la causa**; la hipótesis, sin verificar, es que la primera imagen se construyó con algo distinto al `Dockerfile` actual.

### Ramas de Git

Cada etapa del proyecto queda guardada en su propia rama:

- `legacy`: el proyecto original (flujo LangGraph con `model/`, el `Dockerfile` viejo y `llama3`), tal como estaba antes de convertirlo en agente.
- `agente`: el agente con herramientas, la evaluación y el README actualizado, **sin Docker** (se corre con `uvicorn` en local).
- `docker`: la rama donde se desarrolló la dockerización, antes de unirla a `main`.
- `main`: lo más reciente: el agente con la API dockerizada.

### Hallazgos principales

1. **El prompt no garantiza que el modelo use una herramienta.** Se midió y se resolvió moviendo la acción crítica (guardar) al código.
2. **`ToolStrategy` vs `ProviderStrategy`.** `ToolStrategy` mantiene el ciclo de herramientas pero un modelo de 7B a veces falla el formato (texto en vez de llamada, o respuesta vacía). `ProviderStrategy` elimina los errores de formato pero elimina también el comportamiento de agente. Se eligió `ToolStrategy` con reintento.
3. **Definir las categorías en el prompt** fue el cambio que más mejoró la clasificación (de 11/15 a 13/15 en categoría).
4. **Un reintento idéntico no sirve con `temperature=0`.** Hay que cambiar algo entre intentos.

## Limitaciones conocidas

- **El manual es el paper de GPT-4**, no un manual de soporte. El RAG demuestra la arquitectura, pero sus resultados no ayudan a resolver tickets reales (por ejemplo, para "sistema de pagos caído" devolvió texto sobre lavado de dinero). `solucion_sugerida` casi siempre queda en `null`.
- **Evaluación pequeña:** 15 tickets, prompt ajustado sobre los mismos casos, riesgo de sobreajuste.
- **Etiqueta ambigua e inestable:** "pagos caídos" (`tecnico` vs `facturacion`) es una decisión de criterio, y el modelo cambió su respuesta entre mediciones sin que cambiara el código. Una sola corrida no basta para afirmar un resultado.
- **Formato inestable en modelos de 7B:** el reintento lo reduce, pero no lo elimina por completo. Si fallan todos los intentos, la API devuelve 500.
- **`tickets_similares` usa coincidencia de texto (`ILIKE`)**, no búsqueda semántica. Una mejora sería usar `pgvector`.
- **Los tickets guardados influyen en las búsquedas del agente.** Los tickets de prueba en la tabla aparecieron en `tickets_similares`.
- **n8n está en el compose pero no está conectado** a la API. Además, las variables `N8N_BASIC_AUTH_*` probablemente ya no tienen efecto en las versiones recientes de n8n (no se verificó).
- **Ollama no está dockerizado:** el contenedor de la API depende de que Ollama esté corriendo en el computador anfitrión, accesible por `host.docker.internal`. Probado en Docker Desktop con Windows. En otros sistemas puede requerir ajustes.
- **Credenciales antiguas en el historial de Git:** el `docker-compose.yml` original tenía contraseñas de desarrollo escritas, y siguen en commits anteriores aunque ya se movieron al `.env`. No deben reutilizarse en ningún otro sitio.
- **No hay tests automáticos** (por ejemplo con `pytest`); la verificación se hizo con los scripts de arriba y la evaluación.
- `langchain-community` está en proceso de retiro (aparece un `DeprecationWarning` al cargar PDFs con `PyPDFLoader`).

## Próximos pasos

- Reemplazar el PDF por un manual de soporte real.
- Ampliar el set de evaluación y medir con tickets no usados para ajustar el prompt.
- Probar otros modelos (`llama3.1`) y comparar contra `qwen2.5:7b`.
- Exponer una de las herramientas como servidor MCP.
- Conectar n8n a la API con un webhook.
- Agregar tests con `pytest`.