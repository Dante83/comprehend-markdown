# comprehend-markdown

*Tocas el pergamino y pronuncias el encantamiento. Minutos o una hora más tarde (dependiendo del grosor del pergamino), comprendes el Markdown en cualquier idioma.*

Un servidor MCP que traduce el `README.md` de un proyecto a otros idiomas, además de un pipeline independiente que ejecuta un bucle de redacción y revisión utilizando un modelo local de LM Studio.

Tanto el idioma de origen como los de destino son configurables; el inglés es solo el valor predeterminado. Configura `source_language` para traducir *desde* chino, indonesio o cualquier otro idioma, y `target_languages` para elegir hacia cuáles se distribuirá la traducción (consulta [Elección de idiomas de origen y destino](#elección-de-idiomas-de-origen-y-destino)).

Para cualquier proyecto objetivo, el sistema espera (y crea según sea necesario):

```
<project-root>/docs/<source>/README.md  la fuente canónica (inglés por defecto)
<project-root>/docs/<lang>/README.md    versiones traducidas, una por idioma
<project-root>/README.md                página de inicio para la selección de idiomas (generada)
```

También funciona con proyectos que aún no han sido migrados —donde la fuente sigue estando en la raíz—: se utiliza el `README.md` de la raíz como fuente y, al finalizar una ejecución del `pipeline`, este se mueve a `docs/<source>/` (por ejemplo, `docs/English/`) y es reemplazado por una breve página de inicio generada que enlaza todas las traducciones disponibles.

## Configuración

Todo (creación del venv, instalación/sincronización de dependencias) es gestionado por `run.sh`; no hay un paso de instalación independiente. Lee los paquetes desde `requirements.txt` y los reinstala en cada ejecución, por lo que obtener nuevas dependencias solo requiere ejecutarlo de nuevo.

Si deseas apuntar a un modelo local de LM Studio distinto al predeterminado, copia el ejemplo de configuración y edítalo:

```bash
cp config.local.json.example config.local.json
```

El archivo `config.local.json` está en el `.gitignore` y anula las claves de `config.json` una a una, por lo que puedes ajustar `lm_studio_url`, `model_name` o `api_key` localmente sin modificar los valores predeterminados commitados.

### Elección de idiomas de origen y destino

Dos claves de configuración controlan la dirección de la traducción, y tanto el servidor como el pipeline las leen (desde `config.py`), por lo que nunca hay discrepancias:

- **`source_language`** — el idioma en el que está escrito tu `README.md` canónico y el nombre de su carpeta `docs/<source_language>/`. Por defecto es `"English"`. Configúralo como `"中文"`, `"Bahasa Indonesia"` o cualquier otro para traducir *desde* ese idioma.
- **`target_languages`** — la lista hacia la cual el pipeline traduce. Cualquier entrada igual a `source_language` se omite automáticamente, por lo que dejar el idioma de origen en la lista es inofensivo.

Por ejemplo, para traducir un README en chino al inglés y al español:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Si se omite `target_languages`, el pipeline recurre a su lista integrada de 18 idiomas.

La clave `api_key` solo es relevante si has activado "Require API Key" en la configuración del servidor de desarrollador de LM Studio; de lo contrario, déjala como `"lm-studio"`, que es ignorada por LM Studio. Ten en cuenta que esto solo se aplica al modo `pipeline`, que es la única parte que llama directamente al endpoint compatible con OpenAI de LM Studio; el modo `serve` nunca habla con la API de LM Studio directamente, ya que LM Studio *es* el cliente MCP que lo invoca.

## Uso

```bash
./run.sh serve    /ruta/absoluta/al/proyecto   # servidor MCP stdio
./run.sh pipeline /ruta/absoluta/al/proyecto   # ejecuta main.py de extremo a extremo
```

Ambos modos requieren una ruta **absoluta** a la carpeta del proyecto que contiene el `README.md` a traducir. En el modo `pipeline`, puedes omitirla y el sistema te la solicitará, siempre que estés ejecutando en una terminal interactiva:

```bash
./run.sh pipeline
Enter absolute path to project folder: /ruta/absoluta/al/proyecto
```

(El modo `serve` nunca solicita datos; una vez que inicia, stdin/stdout son el canal JSON-RPC de MCP, y los hosts de MCP lo lanzan de forma no interactiva).

### `serve` — como herramienta de un host MCP

Esto es a lo que un host MCP (por ejemplo, LM Studio) debe apuntar en su `command` del servidor, con la ruta absoluta del proyecto objetivo como argumento fijo. Expone:

- **tool** `write_readme(language, content)` — escribe el archivo `docs/<language>/README.md`.
- **tool** `write_directory_readme(content)` — escribe el `README.md` de la raíz (la página de selección de idiomas).
- **resource** `docs://readme` — la fuente (`docs/<source_language>/README.md`, recurriendo al `README.md` de la raíz si no existe).
- **resource** `docs://readme/{language}` — la traducción existente, si la hay.
- **resource** `docs://dir_readme` — el `README.md` de la raíz.
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — el bucle de traducción nueva.
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — la ruta de actualización: compara una traducción existente con la fuente actual y la corrige con cambios mínimos.
- **prompt** `create_docs_language_directory` — construye la página de selección de idiomas en la raíz a partir de la lista de traducciones disponibles.

El modelo del propio host es el que dirige las llamadas a las herramientas; este servidor solo proporciona la E/S de archivos y las plantillas de prompts.

#### Cómo añadirlo a LM Studio

La configuración MCP de LM Studio se encuentra en `~/.lmstudio/mcp.json`. Añade una entrada como esta:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/ruta/absoluta/a/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/ruta/absoluta/al/proyecto/que/quieres/traducir"
      ]
    }
  }
}
```

La segunda entrada de `args` queda fija al momento de la conexión; la configuración de LM Studio es un JSON estático sin soporte para prompts interactivos, por lo que debe ser la ruta real del proyecto que deseas traducir, no la ruta de este repositorio (a menos que este sea el proyecto a traducir).

### `pipeline` — independiente, sin host MCP

Ejecuta por sí mismo el bucle completo de traducción $\rightarrow$ crítica $\rightarrow$ revisión para los `target_languages` configurados (lista predeterminada de 18: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — consulta [Elección de idiomas de origen y destino](#elección-de-idiomas-de-origen-y-destino) para cambiar la lista o el idioma de origen).

Llama directamente al endpoint compatible con OpenAI de LM Studio para los turnos del escritor/revisor y lanza su propia copia interna de `server.py` sobre stdio para gestionar la E/S de archivos. Es útil para traducciones por lotes sin tener que gestionarlo a través de la interfaz de usuario de LM Studio. El tiempo de ejecución escala con el tamaño del documento en un modelo local: minutos para un README pequeño, hasta una hora aproximadamente para uno grande fragmentado.

Los idiomas que ya tienen un `docs/<language>/README.md` no se traducen desde cero: el revisor compara la traducción existente con la fuente actual y, solo si algo ha cambiado, el escritor la corrige con ediciones mínimas. Las traducciones actualizadas se omiten por completo, por lo que volver a ejecutar el pipeline tras editar un README solo procesa las partes obsoletas.

Tras el trabajo por idioma, la ejecución finaliza (si es necesario) moviendo el `README.md` de origen de la raíz a `docs/<source_language>/` y regenerando el `README.md` de la raíz como una breve página de selección de idiomas que enlaza cada traducción no vacía.

Requiere que el servidor local de LM Studio esté ejecutándose (consulta `config.json`) con cualquier modelo de chat cargado. El pipeline dirige al modelo mediante completados de texto plano y realiza las escrituras de archivos él mismo, por lo que el modelo **no** necesita soportar llamadas a herramientas estilo OpenAI (consulta "Gestión de READMEs grandes" más abajo). Aun así, se recomienda probar un solo idioma antes de confiar en una ejecución completa de toda la lista.

### Gestión de READMEs grandes

Traducir un README grande (los documentos hermanos `A-Starry-Sky` / `a-restless-ocean` tienen entre 35 y 60 KB) en un solo completado es el principal riesgo de fiabilidad en un modelo local: se agotan los tokens de salida o el contexto a mitad del proceso y la parte final se trunca silenciosamente. El modo `pipeline` está diseñado para evitar esto:

- **Sin herramientas por diseño.** El modelo solo produce texto plano; cada traducción, revisión y página de directorio regresa como su respuesta, y el orquestador la guarda mediante las herramientas `write_readme` / `write_directory_readme` del servidor. Nada le pide al modelo que meta un documento entero en un argumento de llamada a herramienta. En modelos de *razonamiento* locales (por ejemplo, Gemma 4), esa ruta trunca el JSON del argumento y el endpoint lo rechaza con un error de `peg-gemma4 format` / salida malformada; devolver texto evita esto por completo.
- **`max_tokens`** (predeterminado `32768`) se envía explícitamente en cada completado para que una sección o borrador completo pueda finalizar en lugar de cortarse por el valor predeterminado más pequeño de LM Studio por solicitud. El pipeline advierte si un completado aún se detiene por `length` (longitud), para que sepas que debes aumentarlo.
- **Fragmentación por secciones (Chunking)** — cuando la fuente excede `chunk_threshold_chars` (predeterminado `12000`) y `chunk_translation` es `true`, la fuente se divide en los encabezados de Markdown de nivel superior (`## `) (detectando bloques de código, por lo que un `##` dentro de un bloque de código no se toca). Cada sección se traduce en su propio completado, y el orquestador ensambla las piezas y las guarda. Ninguna llamada al modelo tiene que emitir el documento completo.
- **Revisión por sección** — con `review_sections` en `true` (por defecto), cada sección ejecuta el mismo bucle de crítica $\rightarrow$ revisión que usa la ruta de disparo único, pero limitado a esa sección: el revisor compara la sección traducida con su fuente y el escritor la revisa hasta que el revisor esté de acuerdo (o se alcance `MAX_ITERATIONS`). Como una sección es pequeña, la revisión y reescritura se mantienen lejos del techo de truncamiento que hacía que la revisión de un README grande fuera insegura.

La ruta fragmentada deliberadamente **no** ejecuta una segunda revisión de todo el documento al final; volver a emitir el README grande completo en un solo completado reintroduciría el mismo truncamiento, y la pasada por secciones ya lo ha cubierto. Configura `review_sections` como `false` para traducir documentos grandes sin ninguna revisión, o `chunk_translation` como `false` para forzar el comportamiento original de disparo único (que sigue ejecutando el bucle completo de revisión del documento). La ruta de disparo único por debajo del umbral permanece inalterada.