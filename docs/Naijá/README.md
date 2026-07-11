# comprehend-markdown

*Touch that scroll, chant the magic words. After few minutes or maybe an hour (depending on how heavy the scroll be), you go fit understand Markdown for any language.*

Na MCP server wey dey translate project `README.md` go other languages, plus one standalone pipeline wey dey run writer/reviewer loop using local LM Studio model.

You fit configure both the source and target languages — English na just the default. Set `source_language` if you wan translate *out of* Chinese, Indonesian, or any other language, and use `target_languages` to choose which ones e go fan out into (see [Choosing source and target languages](#choosing-source-and-target-languages)).

For any project wey you dey target, e expect (and e go create if e no dey):

```
<project-root>/docs/<source>/README.md  the canonical source (English by default)
<project-root>/docs/<lang>/README.md    translated versions, one per language
<project-root>/README.md                language-picker landing page (generated)
```

If project never migrate — and the source still dey for root — e go still work: the root `README.md` na him e go use as source, and when `pipeline` run finish, e go move am enter `docs/<source>/` (e.g. `docs/English/`) and replace am with one short generated landing page wey get links to all available translations.

## Setup

Everything (venv creation, dependency install/sync) na `run.sh` dey handle — you no need separate install step. E dey read packages from `requirements.txt` and e dey reinstall every time you run am, so if you wan pull new dependencies, just run am again.

If you wan point am go local LM Studio model wey no be the default, change the values inside `config.json`.

### Choosing source and target languages

Two config keys for `config.json` dey control the translation direction:

- **`source_language`** — the language wey your main `README.md` write for, and the name of its `docs/<source_language>/` folder. Default na `English`. Set am to `中文`, `Indonesia`, or any other thing if you wan translate *out of* that language instead.
- **`target_languages`** — the list wey the pipeline dey translate *into*. Any entry wey equal to `source_language` go be skipped automatically, so e no matter if you leave the source inside the list.

For example, if you wan translate Chinese README go English and Spanish:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

If you omit `target_languages`, the pipeline go just use its built-in list of 18 languages.

`api_key` only matter if you don turn on "Require API Key" for LM Studio's Developer server settings — otherwise, leave am as `"lm-studio"`, because LM Studio no dey care about am. Note say this one na only for `pipeline` mode, because na only that part dey call LM Studio's OpenAI-compatible endpoint directly; `serve` mode no dey talk to LM Studio's API itself since LM Studio *na* the MCP client wey dey call am.

You fit set `max_tokens` here, but I no too sure if LM Studio really respect am. Make sure say you set this one to at least 24576 inside the model itself before you run this script.

## Usage

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP server
./run.sh pipeline /absolute/path/to/project   # runs main.py end-to-end
```

Both modes need **absolute** path to the project folder wey get the `README.md` wey you wan translate. For `pipeline` mode, you fit leave am and e go prompt you instead, as long as you dey run am interactively for terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(`serve` mode no dey prompt — once e start, stdin/stdout na the MCP JSON-RPC channel itself, and MCP hosts normally launch am non-interactively.)

### `serve` — as an MCP host tool

Na this one MCP host (e.g. LM Studio) suppose point its server `command` go, with the target project's absolute path as fixed argument. E expose these ones:

- **tool** `write_readme(language, content)` (write README for specific language)
- **tool** `write_directory_readme(content)` (write the root landing page wey get language picker)
- **resource** `docs://readme` (the source — `docs/<source_language>/README.md`, or root `README.md` if e no dey)
- **resource** `docs://readme/{language}` (existing translation, if any)
- **resource** `docs://dir_readme` (the root `README.md`)
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` (the fresh-translation loop)
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` (update path: compare existing translation with current source and patch am with small changes)
- **prompt** `create_docs_language_directory` (build the root language-picker page from list of available translations)

The host's own model na him dey drive the tool calls; this server just provide the file I/O and prompt templates.

#### Adding it to LM Studio

LM Studio's MCP config dey for `~/.lmstudio/mcp.json`. Add entry like this:

```json
{
  "mcpServers": {
    "comprehend-markdown": {
      "command": "/absolute/path/to/comprehend-markdown/run.sh",
      "args": [
        "serve",
        "/absolute/path/to/the/project/you/want/to/translate"
      ]
    }
  }
}
```

The second `args` entry na fixed value during connection — LM Studio's config na static JSON wey no get interactive prompt support, so e must be the actual path of the project you wan translate, not this repo's own path (unless na this repo you wan translate).