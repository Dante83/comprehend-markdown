# comprehend-markdown

*Tocas el pergamino y pronuncias el encantamiento. Minutos o una hora después (según la densidad del pergamino), comprendes el Markdown en cualquier idioma.*

Un servidor MCP que traduce el `README.md` de un proyecto a otros idiomas, además de un pipeline independiente que ejecuta un bucle de escritor/revisor utilizando un modelo local de LM Studio.

Tanto el idioma de origen como los de destino son configurables; el inglés es solo el valor predeterminado. Configura `source_language` para traducir *desde* chino, indonesio o cualquier otro idioma, y `target_languages` para elegir hacia cuáles se desplegará la traducción (consulta [Elección de idiomas de origen y destino](#elección-de-idiomas-de-origen-y-destino)).

Para cualquier proyecto objetivo, el sistema espera (y crea según sea necesario):

```
<project-root>/docs/<source>/README.md  la fuente canónica (inglés por defecto)
<project-root>/docs/<lang>/README.md    versiones traducidas, una por idioma
<project-root>/README.md                página de aterrizaje para elegir el idioma (generada)
```

También funciona con proyectos que aún no han sido migrados —donde la fuente sigue estando en la raíz—: se utiliza el `README.md` de la raíz como fuente y, al finalizar la ejecución del `pipeline`, este se mueve a `docs/<source>/` (por ejemplo, `docs/English/`) y es reemplazado por una breve página de aterrizaje generada que enlaza todas las traducciones disponibles.

## Configuración

Todo (creación del venv, instalación/sincronización de dependencias) se gestiona mediante `run.sh`; no hay un paso de instalación independiente. Lee los paquetes desde `requirements.txt` y los reinstala en cada ejecución, por lo que obtener nuevas dependencias solo requiere ejecutarlo de nuevo.

Si deseas apuntar a un modelo local de LM Studio distinto al predeterminado, modifica los valores en `config.json`.

### Elección de idiomas de origen y destino

Dos claves de configuración controlan la dirección de la traducción en `config.json`:

- **`source_language`** — el idioma en el que está escrito tu `README.md` canónico y el nombre de su carpeta `docs/<source_language>/`. Por defecto es `English`. Configúralo como `中文`, `Indonesia` o cualquier otro para traducir *desde* ese idioma.
- **`target_languages`** — la lista de idiomas a los que el pipeline traduce. Cualquier entrada igual a `source_language` se omite automáticamente, por lo que dejar el idioma de origen en la lista es inofensivo.

Por ejemplo, para traducir un README en chino al inglés y al español:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

Si se omite `target_languages`, el pipeline recurre a su lista integrada de 18 idiomas.

La clave `api_key` solo es relevante si has activado "Require API Key" en los ajustes del servidor Developer de LM Studio; de lo contrario, déjala como `"lm-studio"`, que es el valor que LM Studio ignora. Ten en cuenta que esto solo se aplica al modo `pipeline`, que es la única parte que llama directamente al endpoint compatible con OpenAI de LM Studio; el modo `serve` nunca se comunica con la API de LM Studio, ya que LM Studio *es* el cliente MCP que lo invoca.

`max_tokens` puede configurarse aquí, aunque no estoy seguro de si LM Studio realmente lo respeta. Asegúrate de establecer este valor en al menos 24576 en el modelo mismo antes de ejecutar este script.

## Uso

```bash
./run.sh serve    /ruta/absoluta/al/proyecto   # servidor MCP stdio
./run.sh pipeline /ruta/absoluta/al/proyecto   # ejecuta main.py de extremo a extremo
```

Ambos modos requieren una ruta **absoluta** a la carpeta del proyecto que contiene el `README.md` a traducir. En el modo `pipeline`, puedes omitirla y el sistema te la solicitará, siempre que estés ejecutando el comando interactivamente en una terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /ruta/absoluta/al/proyecto
```

(El modo `serve` nunca solicita datos; una vez que inicia, stdin/stdout son el canal JSON-RPC de MCP, y los hosts de MCP lo lanzan de forma no interactiva).

### `serve` — como herramienta de host MCP

Esto es a lo que un host MCP (por ejemplo, LM Studio) debe apuntar en su `command` del servidor, con la ruta absoluta del proyecto objetivo como argumento fijo. Expone:

- **tool** `write_readme(language, content)` — escribe el archivo `docs/<language>/README.md`.
- **tool** `write_directory_readme(content)` — escribe el `README.md` de la raíz (la página de aterrizaje para elegir idioma).
- **resource** `docs://readme` — la fuente (`docs/<source_language>/README.md`, recurriendo al `README.md` de la raíz si no existe).
- **resource** `docs://readme/{language}` — la traducción existente, si la hay.
- **resource** `docs://dir_readme` — el `README.md` de la raíz.
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — el bucle de traducción nueva.
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — la ruta de actualización: compara una traducción existente con la fuente actual y la corrige con cambios mínimos.
- **prompt** `create_docs_language_directory` — construye la página de aterrizaje de la raíz a partir de la lista de traducciones disponibles.

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

La segunda entrada de `args` queda fija al momento de la conexión; la configuración de LM Studio es un JSON estático sin soporte para prompts interactivos, por lo que debe ser la ruta real del proyecto que deseas traducir, y no la ruta de este repositorio (a menos que este sea el proyecto que quieras traducir).