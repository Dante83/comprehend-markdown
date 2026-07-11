# comprehend-markdown

*Touch that magic paper, chant the spell. After few minutes or maybe one hour (depending on how heavy the paper be), you go fit understand Markdown for any language.*

Na MCP server be this wey dey translate project `README.md` go other languages, and e get standalone pipeline wey dey run writer/reviewer loop using local LM Studio model.

You fit change both the source and target languages — English na just the default. Set `source_language` if you wan translate *from* Chinese, Indonesian, or any other language, and use `target_languages` to choose which ones e go fan out into (see [Choosing source and target languages](#choosing-source-and-target-languages)).

For any project wey you wan use am on, e dey expect (and e go create if e no dey):

```
<project-root>/docs/<source>/README.md  the main original copy (English by default)
<project-root>/docs/<lang>/README.md    translated versions, one for each language
<project-root>/README.md                language-picker landing page (generated)
```

If project never migrate — and the source still dey the root — e go still work: the root `README.md` na him e go use as source, and when `pipeline` run finish, e go move am enter `docs/<source>/` (e.g. `docs/English/`) and replace am with small generated landing page wey get links to all available translations.

## Setup

Everything (venv creation, dependency install/sync) dey inside `run.sh` — you no need separate install step. E dey read packages from `requirements.txt` and e dey reinstall every time you run am, so if you wan pull new dependencies, just run am again.

If you wan use local LM Studio model wey no be the default, copy the example config and edit am:

```bash
cp config.local.json.example config.local.json
```

`config.local.json` dey inside `.gitignore` and e dey override `config.json` key-by-key, so you fit tweak `lm_studio_url` / `model_name` / `api_key` for your own local machine without touching the defaults wey don commit.

### Choosing source and target languages

Two config keys dey control how translation go flow, and both the server and pipeline dey read them (from `config.py`), so dem no go ever disagree:

- **`source_language`** — the language wey your main `README.md` write for, and the name of its `docs/<source_language>/` folder. Default na `"English"`. Set am to `"中文"`, `"Bahasa Indonesia"`, or any other thing if you wan translate *from* that language instead.
- **`target_languages`** — the list wey the pipeline dey translate *into*. Any entry wey equal `source_language` go be skipped automatically, so e no matter if you leave the source for the list.

For example, to translate Chinese README go English and Spanish:

```json
{
  "source_language": "中文",
  "target_languages": ["English", "Español"]
}
```

If you no put `target_languages`, the pipeline go just use its built-in list of 18 languages.

`api_key` only matter if you don turn on "Require API Key" for LM Studio's Developer server settings — otherwise leave am as `"lm-studio"`, wey LM Studio dey ignore. Note say this one na only for `pipeline` mode, because na only that part dey call LM Studio's OpenAI-compatible endpoint directly; `serve` mode no dey talk to LM Studio's API itself since LM Studio *na* the MCP client wey dey call am.

## Usage

```bash
./run.sh serve    /absolute/path/to/project   # stdio MCP server
./run.sh pipeline /absolute/path/to/project   # runs main.py end-to-end
```

Both modes need **absolute** path to the project folder wey get the `README.md` wey you wan translate. For `pipeline` mode, you fit leave am and e go prompt you instead, as long as you dey run am for terminal:

```bash
./run.sh pipeline
Enter absolute path to project folder: /absolute/path/to/project
```

(`serve` mode no dey prompt — once e start, stdin/stdout na the MCP JSON-RPC channel itself, and MCP hosts dey launch am non-interactively anyway.)

### `serve` — as an MCP host tool

Na this one MCP host (e.g. LM Studio) suppose point its server `command` go, with the target project's absolute path as fixed argument. E get these ones:

- **tool** `write_readme(language, content)` — write `docs/<language>/README.md`
- **tool** `write_directory_readme(content)` — write the root `README.md` (the language-picker landing page)
- **resource** `docs://readme` — the source (`docs/<source_language>/README.md`, or root `README.md` if e no dey)
- **resource** `docs://readme/{language}` — existing translation, if any
- **resource** `docs://dir_readme` — the root `README.md`
- **prompts** `translate_readme`, `critique_translation`, `rewrite_translation` — the fresh-translation loop
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` — update path: compare existing translation with current source and patch am with small changes
- **prompt** `create_docs_language_directory` — build the root language-picker page from the list of available translations

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

The second `args` entry na fixed one for connection time — LM Studio's config na static JSON wey no get interactive prompt support, so e must be the actual path you wan translate, not this repo's own path unless na that project you mean.

### `pipeline` — standalone, no MCP host

E dey run the full translate $\rightarrow$ critique $\rightarrow$ revise loop by itself for the configured `target_languages` (default list of 18: Deutsch, Español, Français, Italiano, Polski, Português, Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা, Bahasa Indonesia, اردو, Naijá — see [Choosing source and target languages](#choosing-source-and-target-languages) to change the list or the source language), calling LM Studio's OpenAI-compatible endpoint directly for the writer/reviewer turns and spawning its own internal copy of `server.py` over stdio to do the file I/O. E very useful if you wan batch-translate without using LM Studio UI. Runtime depend on how big the document be for local model — few minutes for small README, maybe one hour or more for large chunked one.

Languages wey already get `docs/<language>/README.md` no go start from scratch: the reviewer go compare existing translation with current source and, only if something change, the writer go patch am with minimal edits. Translations wey don up-to-date go be skipped entirely, so if you run pipeline again after you edit README, na only the stale parts e go redo.

After e finish per-language work, the run go end by (if e need) moving root-level source `README.md` enter `docs/<source_language>/` and regenerating the root `README.md` as small language-picker page wey link every non-empty translation.

E require say LM Studio's local server dey run (see `config.json`) with any chat model loaded — the pipeline dey drive the model with plain text completions and e dey do the file writes itself, so the model **no** need to support OpenAI-style tool calls (see "Large-README handling" below). Still, e good make you test one language first before you trust am for full run across the whole list.

### Large-README handling

To translate large README (like those two sibling `A-Starry-Sky` / `a-restless-ocean` docs wey be ~35–60 KB) in one single completion na the main risk for local model: e fit run out of output tokens or context half-way, and the tail go just cut silently. `pipeline` mode build to avoid that one:

- **Tool-free by design.** The model only produce plain text — every translation, rewrite, and directory page dey come back as its reply, and the orchestrator save am via the server's `write_readme` / `write_directory_readme` tools. Nothing dey ask the model to stuff whole document inside tool-call argument. For local *reasoning* models (e.g. Gemma 4), that path dey truncate the argument JSON and the endpoint go reject am with `peg-gemma4 format` / malformed-output error; returning text sidestep this problem entirely.
- **`max_tokens`** (default `32768`) dey send explicitly for every completion so full section/draft fit finish instead make e cut off for LM Studio's smaller per-request default. The pipeline go warn you if completion still stop on `length`, so you go know say you need raise am.
- **Section chunking** — when source pass `chunk_threshold_chars` (default `12000`) and `chunk_translation` na `true`, the source go split for top-level (`## `) Markdown headings (e sabi fence, so `##` inside code block no dey count), each section go translate in its own completion, and the orchestrator go join the pieces together and save them. No single model call ever need to emit the whole document.
- **Per-section review** — with `review_sections` `true` (the default), each section go run the same critique $\rightarrow$ revise loop wey the single-shot path dey use, just say e focus on that one section: the reviewer compare translated section with its source and the writer revise until the reviewer agree (or `MAX_ITERATIONS` reach). Because section small, review and rewrite go stay far from the truncation ceiling wey make whole-document review of big README unsafe.

The chunked path deliberately **no** run second whole-document review after — to emit entire large README in one completion go just bring back the same truncation, and the per-section pass don already cover am. Set `review_sections` to `false` if you wan translate large docs without any review, or `chunk_translation` to `false` to force original single-shot behaviour (wey still run full whole-document review loop). The single-shot path below the threshold no change.