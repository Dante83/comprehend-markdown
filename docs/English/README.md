# comprehend-markdown

*You touch the scroll and utter the incantation. Minutes to an hour later
(per document, depending on the scroll's heft), you comprehend Markdown in
any language.*

An MCP server that translates a project's `README.md` into other languages,
plus a standalone pipeline that runs a writer/reviewer loop against it using
a local LM Studio model.

The source and target languages are both configurable — English is only the
default. Set `source_language` to translate *out of* Chinese, Indonesian, or
anything else, and `target_languages` to choose what it fans out into (see
[Choosing source and target languages](#choosing-source-and-target-languages)).

For any target project, it expects (and creates as needed):

```
<project-root>/docs/<source>/README.md  the canonical source (English by default)
<project-root>/docs/<lang>/README.md    translated versions, one per language
<project-root>/README.md                language-picker landing page (generated)
```

A project that hasn't been migrated yet — source still at the root —
works too: the root `README.md` is used as the source, and at the end of a
`pipeline` run it is moved into `docs/<source>/` (e.g. `docs/English/`) and
replaced by a short generated landing page that links every available
translation.

## Setup

Everything (venv creation, dependency install/sync) is handled by `run.sh` —
there's no separate install step. It reads packages from `requirements.txt`
and reinstalls on every run, so pulling new dependencies just means running
it again.

If you want to point at a local LM Studio model other than the default, modify the values in `config.json`

### Choosing source and target languages

Two config keys control the translation direction in `config.json`:

- **`source_language`** — the language your canonical `README.md` is written
  in, and the name of its `docs/<source_language>/` folder. Defaults to
  `English`. Set it to `中文`, `Indonesia`, or anything else to
  translate *out of* that language instead.
- **`target_languages`** — the list the pipeline translates *into*. Any entry
  equal to `source_language` is skipped automatically, so leaving the source in
  the list is harmless.

For example, to translate a Chinese README into English and Spanish:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

If `target_languages` is omitted, the pipeline falls back to its built-in
18-language list.

`api_key` only matters if you've turned on "Require API Key" under LM
Studio's Developer server settings — otherwise leave it as `"lm-studio"`,
which LM Studio ignores. Note this only applies to `pipeline` mode, which
is the only piece here that calls LM Studio's OpenAI-compatible endpoint
directly; `serve` mode never talks to LM Studio's API itself since LM
Studio *is* the MCP client calling into it.

`max_tokens` is available to be set here, but I'm uncertain if LM Studio
really respects this or not. Make sure to set this to a value of at least
about 24576 in the model itself, before running this script.

## Usage

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP server
./run.sh pipeline /absolute/path/to/project   # runs main.py end-to-end
```

Both modes require an **absolute** path to the project folder containing the
`README.md` to translate. In `pipeline` mode you can omit it and get
prompted instead, as long as you're running interactively at a terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(`serve` mode never prompts — once it starts, stdin/stdout are the MCP
JSON-RPC channel itself, and MCP hosts launch it non-interactively anyway.)

### `serve` — as an MCP host tool

This is what an MCP host (e.g. LM Studio) should point its server
`command` at, with the target project's absolute path as a fixed argument.
It exposes:

- **tool** `write_readme(language, content)` — writes `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — writes the root `README.md`
  (the language-picker landing page)
- **resource** `docs://readme` — the source (`docs/<source_language>/README.md`,
  falling back to the root `README.md`)
- **resource** `docs://readme/{language}` — the existing translation, if any
- **resource** `docs://dir_readme` — the root `README.md`
- **prompts** `translate_readme`, `critique_translation`,
  `rewrite_translation` — the fresh-translation loop
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` —
  the update path: compare an existing translation against the current
  source and patch it with minimal changes
- **prompt** `create_docs_language_directory` — build the root
  language-picker page from the list of available translations

The host's own model drives the tool calls; this server just provides the
file I/O and prompt templates.

#### Adding it to LM Studio

LM Studio's MCP config lives at `~/.lmstudio/mcp.json`. Add an entry like:

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

The second `args` entry is fixed at connection time — LM Studio's config is
static JSON with no interactive prompt support, so it has to be the actual
path you want translated, not this repo's own path unless that's the
project you mean to translate.