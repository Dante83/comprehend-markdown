# comprehend-markdown

*You touch the scroll and utter the incantation. Minutes to an hour later
(per document, depending on the scroll's heft), you comprehend Markdown in
any language.*

An MCP server that translates a project's `README.md` into other languages,
plus a standalone pipeline that runs a writer/reviewer loop against it using
a local LM Studio model.

For any target project, it expects (and creates as needed):

```
<project-root>/docs/English/README.md  the canonical English source
<project-root>/docs/<lang>/README.md   translated versions, one per language
<project-root>/README.md               language-picker landing page (generated)
```

A project that hasn't been migrated yet — English source still at the root —
works too: the root `README.md` is used as the source, and at the end of a
`pipeline` run it is moved into `docs/English/` and replaced by a short
generated landing page that links every available translation.

## Setup

Everything (venv creation, dependency install/sync) is handled by `run.sh` —
there's no separate install step. It reads packages from `requirements.txt`
and reinstalls on every run, so pulling new dependencies just means running
it again.

If you want to point at a local LM Studio model other than the default,
copy the example config and edit it:

```bash
cp config.local.json.example config.local.json
```

`config.local.json` is gitignored and overrides `config.json` key-by-key, so
you can tweak `lm_studio_url` / `model_name` / `api_key` locally without
touching the committed defaults.

`api_key` only matters if you've turned on "Require API Key" under LM
Studio's Developer server settings — otherwise leave it as `"lm-studio"`,
which LM Studio ignores. Note this only applies to `pipeline` mode, which
is the only piece here that calls LM Studio's OpenAI-compatible endpoint
directly; `serve` mode never talks to LM Studio's API itself since LM
Studio *is* the MCP client calling into it.

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
- **resource** `docs://readme` — the English source (`docs/English/README.md`,
  falling back to the root `README.md`)
- **resource** `docs://readme/{language}` — the existing translation, if any
- **resource** `docs://dir_readme` — the root `README.md`
- **prompts** `translate_readme`, `critique_translation`,
  `rewrite_translation` — the fresh-translation loop
- **prompts** `check_existing_readme`, `rewrite_from_existing_translation` —
  the update path: compare an existing translation against the current
  English source and patch it with minimal changes
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

### `pipeline` — standalone, no MCP host

Runs the full translate → critique → revise loop itself for a fixed list of
18 languages (Deutsch, Español, Français, Italiano, Polski, Português,
Русский, Tiếng Việt, ไทย, 中文, 日本語, 한국어, العربية, हिन्दी, বাংলা,
Bahasa Indonesia, اردو, Naijá — edit `LANGUAGES` in `main.py` to change),
calling LM Studio's OpenAI-compatible endpoint directly for the
writer/reviewer turns and spawning its own internal copy of `server.py`
over stdio to do the file I/O. Useful for batch-translating without driving
it through the LM Studio UI. Runtime scales with document size on a local
model — minutes for a small README, up to an hour or so for a large
chunked one.

Languages that already have a `docs/<language>/README.md` aren't
re-translated from scratch: the reviewer compares the existing translation
against the current English source and, only if something changed, the
writer patches it with minimal edits. Up-to-date translations are skipped
entirely, so re-running the pipeline after a README edit only redoes the
stale parts.

After the per-language work, the run finishes by (if needed) moving a
root-level English `README.md` into `docs/English/` and regenerating the
root `README.md` as a short language-picker page linking every non-empty
translation.

Requires LM Studio's local server running (see `config.json`) with any chat
model loaded — the pipeline drives the model with plain text completions and
does the file writes itself, so the model does **not** need to support
OpenAI-style tool calls (see "Large-README handling" below). Still worth
testing one language before trusting a full run across the whole list.

### Large-README handling

Translating a large README (the two sibling `A-Starry-Sky` / `a-restless-ocean`
docs are ~35–60 KB) in a single completion is the main reliability risk on a
local model: it runs out of output tokens or context partway through and the
tail silently truncates. `pipeline` mode is built around avoiding that:

- **Tool-free by design.** The model only ever produces plain text — every
  translation, rewrite, and directory page comes back as its reply, and the
  orchestrator saves it itself via the server's `write_readme` /
  `write_directory_readme` tools. Nothing asks the model to stuff a whole
  document into a tool-call argument. On local *reasoning* models (e.g. Gemma
  4) that path truncates the argument JSON and the endpoint rejects it with a
  `peg-gemma4 format` / malformed-output error; returning text sidesteps it
  entirely.
- **`max_tokens`** (default `32768`) is sent explicitly on every completion so a
  full section/draft can finish instead of being cut off at LM Studio's smaller
  per-request default. The pipeline warns if a completion still stops on
  `length`, so you know to raise it.
- **Section chunking** — when the source exceeds `chunk_threshold_chars`
  (default `12000`) and `chunk_translation` is `true`, the source is split on
  top-level (`## `) Markdown headings (fence-aware, so `##` inside a code block
  is left alone), each section is translated in its own completion, and the
  orchestrator assembles the pieces and saves them. No single model call ever
  has to emit the whole document.
- **Per-section review** — with `review_sections` `true` (the default), each
  section runs the same critique→revise loop the single-shot path uses, just
  scoped to that one section: the reviewer compares the translated section to
  its English source and the writer revises until the reviewer agrees (or
  `MAX_ITERATIONS` is hit). Because a section is small, review and rewrite stay
  well clear of the truncation ceiling that made whole-document review of a big
  README unsafe.

The chunked path deliberately does **not** run a second whole-document review
afterwards — re-emitting the entire large README in one completion would
reintroduce the same truncation, and the per-section pass has already covered
it. Set `review_sections` to `false` to translate large docs without any
review, or `chunk_translation` to `false` to force the original single-shot
behaviour (which still runs the full whole-document review loop). The
single-shot path below the threshold is unchanged.
