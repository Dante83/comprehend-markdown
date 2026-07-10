"""
Orchestrator that drives the translate <-> critique loop against your
FastMCP translation server, using LM Studio's OpenAI-compatible endpoint
for the actual model calls.

Requires:
    ./run.sh installs everything into .venv (see requirements.txt); or
    pip install fastmcp mcp openai pydantic

Usage:
    python main.py <absolute-path-to-project-folder>
    ./run.sh pipeline <absolute-path-to-project-folder>

Configuration (LM Studio URL / model name) is read from config.json, with
any keys in config.local.json (gitignored) taking priority -- copy
config.local.json.example to config.local.json to override locally without
touching the committed defaults.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import openai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- Configuration ---
SCRIPT_DIR = Path(__file__).resolve().parent
SERVER_SCRIPT = str(SCRIPT_DIR / "server.py")


def load_config():
    config = {}
    for filename in ("config.json", "config.local.json"):
        path = SCRIPT_DIR / filename
        if path.is_file():
            config.update(json.loads(path.read_text(encoding="utf-8")))
    return config


_config = load_config()
LM_STUDIO_URL = _config.get("lm_studio_url", "http://localhost:1234/v1")
MODEL_NAME = _config.get("model_name", "model-identifier")
API_KEY = _config.get("api_key", "lm-studio")
# Large local models on modest hardware can take far longer than the
# openai client's 10-minute default to finish a single huge-context
# completion -- that's not a hang, just slow token generation. Configurable
# since it depends entirely on model size/hardware.
REQUEST_TIMEOUT_SECONDS = _config.get("request_timeout_seconds", 1800)
# Explicit output-token cap. LM Studio's per-request default is often small
# (a few hundred to a couple thousand tokens), which silently truncates a
# large README mid-document. Set high so a full section/draft can complete;
# falsy (0/null) omits it and defers to the server default.
MAX_TOKENS = _config.get("max_tokens", 32768)
# Large READMEs are translated section-by-section instead of in one shot --
# far more reliable on local models, which otherwise run out of output tokens
# or context partway through a big document.
CHUNK_TRANSLATION = _config.get("chunk_translation", True)
CHUNK_THRESHOLD_CHARS = _config.get("chunk_threshold_chars", 12000)
# For chunked (large) READMEs, run the critique->revise loop per section instead
# of skipping review entirely. Each section is small enough to review and rewrite
# without the whole-document truncation that made single-shot review unsafe.
REVIEW_SECTIONS = _config.get("review_sections", True)

_EXTRA_COMPLETION_KWARGS = {"max_tokens": MAX_TOKENS} if MAX_TOKENS else {}

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <absolute-path-to-project-folder>", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = str(Path(sys.argv[1]).resolve())  # passed as argv[1] to the server
if not Path(PROJECT_ROOT).is_dir():
    print(f"Not a directory: {PROJECT_ROOT}", file=sys.stderr)
    sys.exit(1)

LANGUAGES = ["Deutsch", "Español", "Français", "Italiano", "Polski", "Português",
"Русский", "Tiếng Việt", "ไทย", "中文", "日本語", "한국어",
"العربية", "हिन्दी", "বাংলা", "Bahasa Indonesia", "اردو", "Naijá"]
MAX_ITERATIONS = 3  # Don't let them argue forever! 😅

client = openai.OpenAI(
    base_url=LM_STUDIO_URL, api_key=API_KEY, timeout=REQUEST_TIMEOUT_SECONDS
)
VERDICT_RE = re.compile(r"<verdict>\s*(AGREE|REVISE|REVISED)\s*</verdict>", re.IGNORECASE)
# Reviewer feedback and writer self-report summaries are multi-line (numbered
# points), so DOTALL is required or the capture stops at the first newline and
# matches nothing. Non-greedy so a stray later tag doesn't swallow the block.
FEEDBACK_RE = re.compile(r"<feedback>\s*(.*?)\s*</feedback>", re.IGNORECASE | re.DOTALL)
SUMMARY_RE = re.compile(r"<summary>\s*(.*?)\s*</summary>", re.IGNORECASE | re.DOTALL)


def _translator_rules(target_lang):
    """The shared translation rules, used by both the whole-document writer
    and the per-section chunk writer. Both return their translation as plain
    text (the orchestrator saves it); kept in one place so the two can't
    drift apart."""
    return f"""RULES:
- Preserve exactly, untranslated: code blocks, inline code, URLs, badges/shields,
  YAML front matter, HTML comments, placeholder variables,
  and markdown syntax/structure (headers, lists, tables).
- Translate everything else naturally — prose, headers, alt text, comments in
  plain English within docs. Avoid literal/calque translation; write like a
  native technical writer in {target_lang} would.
- If a passage is clearly poetic, playful, or personal in tone (not pure
  technical instruction), prioritize rhythm, feeling, and voice over literal
  word-for-word accuracy. You have license to take translator's liberties there.
- Maintain terminology consistency with any glossary provided.
- Placeholder-style tokens that are self-descriptive words rather than real
  syntax (e.g. `{{JSON_FILE_NAME}}` in a sentence explaining what a file is for)
  may have their descriptive words translated if it aids clarity. Never do
  this for anything that must be typed verbatim for the software to work --
  actual code identifiers, CLI flags, environment variable names, file
  extensions, and anything inside a real code block stay untouched. If you
  are not certain a token is purely descriptive, leave it as-is.
- If the source has a table of tags, function names, or other identifiers
  that must stay in English, keep the identifier exactly as written but add
  a short {target_lang} gloss next to it (a new column, or a parenthetical)
  so a reader knows what it means at a glance -- never rename the identifier
  itself."""


def _text_writer_prompt(target_lang, scope_note=""):
    """Shared system prompt for the text-return writers. The model replies with
    ONLY the translated Markdown -- no tools -- and the orchestrator saves that
    reply verbatim. This keeps whole documents out of tool-call arguments, which
    is what truncates (and produces malformed JSON) on local reasoning models."""
    scope = f"\n{scope_note}\n" if scope_note else "\n"
    return f"""You are an expert technical translator specializing in software documentation,
translating from american english to {target_lang}. You also have strong instincts
for literary/poetic translation when the text calls for it.
{scope}
{_translator_rules(target_lang)}
- Reply with ONLY the translated Markdown. Do NOT call any tools, do NOT add
  commentary or notes, and do NOT wrap the whole reply in a code fence. The
  orchestrator saves your reply verbatim, so anything that isn't the translation
  itself ends up in the saved file.
"""


def get_document_writer_prompt(target_lang):
    return _text_writer_prompt(target_lang)


def get_chunk_writer_prompt(target_lang):
    return _text_writer_prompt(
        target_lang,
        "You are translating ONE section of a larger README. Other sections are "
        "handled separately, so translate only what you are given and do not add a "
        "document title, intro, or closing that belongs to the whole file.",
    )


def get_reviewer_prompt(target_lang):
    return f"""You are a bilingual technical editor reviewing a translation from american english
to {target_lang} for a README/documentation file.

Evaluate:
1. Technical accuracy — does the meaning match the source exactly for
   instructions, code references, and claims?
2. Naturalness — does it read like it was written by a native {target_lang}
   technical writer, not translated?
3. Structural integrity — are code blocks, links, badges, placeholders, and
   markdown formatting untouched from the source?
4. Terminology consistency — same term translated the same way throughout.
5. Tone match — for any poetic/personal passages, does it preserve voice and
   feeling rather than reading stiff or literal?
6. Placeholder discipline — descriptive placeholder tokens outside real code
   may be translated for clarity, but nothing that must be typed verbatim
   (code identifiers, CLI flags, env vars, file extensions) was renamed.
7. Glossed identifiers — where the source keeps a tag/function name in
   English inside a table, does the translation add a short {target_lang}
   gloss next to it rather than translating or dropping the identifier?

If the translation is publication-ready, respond with:
<verdict>AGREE</verdict>
<feedback>One sentence on why it's solid.</feedback>

If it needs work, respond with:
<verdict>REVISE</verdict>
<feedback>
- Numbered, specific, actionable points only.
- Quote the problem phrase and suggest a fix where possible.
- Do not nitpick style choices that are merely different from what you'd
  personally pick — only flag actual errors or awkwardness.
</feedback>

Never invent problems to extend the conversation. If it's genuinely good, agree.
"""


def get_directory_writer_prompt():
    return """You are maintaining the root README.md of a project as a language-picker
landing page that links out to translated READMEs stored under docs/<language>/.

RULES:
- This page is a directory, not documentation -- keep it short.
- Never invent content that isn't in the provided language list.
- Reply with ONLY the finished Markdown page. Do NOT call any tools and do NOT
  wrap the reply in a code fence -- the orchestrator saves your reply verbatim.
"""


def get_update_reviewer_prompt(target_lang):
    return f"""You are a bilingual technical editor reviewing a translation from american english
to {target_lang} for a README/documentation file. This is an existing document so we are checking if
we need to change it to match potential changes in the english file.

Evaluate:
1. Contents - are there any bits of text or content that need to be added,
   updated or removed?
2. Technical accuracy — does the meaning match the source exactly for
   instructions, code references, and claims?
3. Structural integrity — are code blocks, links, badges, placeholders, and
   markdown formatting untouched from the source?
4. Placeholder discipline — descriptive placeholder tokens outside real code
   may be translated for clarity, but nothing that must be typed verbatim
   (code identifiers, CLI flags, env vars, file extensions) was renamed.
5. Glossed identifiers — where the source keeps a tag/function name in
   English inside a table, does the translation add a short {target_lang}
   gloss next to it rather than translating or dropping the identifier?

If the translation does not require any changes, respond with:
<verdict>AGREE</verdict>
<feedback>One sentence on why it's solid.</feedback>

If it needs changes, respond with:
<verdict>REVISE</verdict>
<feedback>
- Numbered, specific, actionable points only.
- Quote the problem phrase and suggest a fix where possible.
- Do not nitpick style choices that are merely different from what you'd
  personally pick — only flag actual errors or awkwardness.
</feedback>

Never invent problems to extend the conversation. If it's genuinely good, agree.
"""


def complete(system_prompt, user_prompt, *, label="completion"):
    """Run one plain, tool-free chat completion and return its text.

    The whole pipeline is tool-free by design: the model only ever produces
    text, and the orchestrator saves it via session.call_tool itself. That keeps
    large documents out of model-emitted tool-call arguments, which truncate into
    malformed JSON on local reasoning models (the peg-gemma4 format error)."""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **_EXTRA_COMPLETION_KWARGS,
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        print(
            f"   ⚠️  {label} hit the output-token limit (max_tokens={MAX_TOKENS}) "
            "and was truncated -- raise max_tokens in config.local.json if this "
            "text looks cut off."
        )
    return choice.message.content or ""


_WRAPPING_FENCE_LANGS = ("", "markdown", "md")


def _strip_wrapping_fence(text):
    """Strip a single ``` / ```markdown fence that wraps the ENTIRE reply.

    Models sometimes ignore "no code fence" and return the whole translation
    inside one fenced block. We only unwrap when the very first line opens a
    fence (optionally tagged markdown/md) and the very last line closes it, so a
    document that legitimately ends with a code block is left untouched."""
    stripped = text.strip()
    if not stripped:
        return text
    lines = stripped.splitlines()
    if len(lines) < 2:
        return text
    first = lines[0].strip()
    last = lines[-1].strip()
    if first.startswith("```") and last == "```":
        if first.lstrip("`").strip().lower() in _WRAPPING_FENCE_LANGS:
            return "\n".join(lines[1:-1]).strip()
    return text


async def get_mcp_prompt_text(session, prompt_name, arguments):
    """Fetch a prompt template from the MCP server, fully rendered."""
    result = await session.get_prompt(prompt_name, arguments)
    return "\n".join(
        m.content.text for m in result.messages if hasattr(m.content, "text")
    )


def parse_verdict(text):
    match = VERDICT_RE.search(text)
    return match.group(1).upper() if match else None

def parse_feedback(text):
    """Extract a reviewer's <feedback> block verbatim (this is what gets fed
    back to the writer, so case and quoted phrases must be preserved)."""
    match = FEEDBACK_RE.search(text)
    return match.group(1).strip() if match else None

def parse_summary(text):
    """Extract a writer's <summary> self-report verbatim."""
    match = SUMMARY_RE.search(text)
    return match.group(1).strip() if match else None


def read_source_readme_text():
    """Mirror the server's source-README resolution: prefer docs/English, fall
    back to the project-root README.md. Returns '' if neither exists."""
    docs_english = Path(PROJECT_ROOT) / "docs" / "English" / "README.md"
    root = Path(PROJECT_ROOT) / "README.md"
    if docs_english.is_file():
        return docs_english.read_text(encoding="utf-8")
    if root.is_file():
        return root.read_text(encoding="utf-8")
    return ""


def read_target_readme_text(target_lang):
    """Read the existing translation at docs/<lang>/README.md (matching the
    server's title-cased folder name). Returns None if it's missing or empty."""
    lang_dir = target_lang.strip().title()
    path = Path(PROJECT_ROOT) / "docs" / lang_dir / "README.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    return text if text.strip() else None


_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_SECTION_HEADING_RE = re.compile(r"^## ")  # level-2 headings are the split points


def split_markdown_sections(text):
    """Split a Markdown document into level-2 (`## `) sections, keeping the
    title/preamble before the first `##` as the leading chunk.

    Fence-aware: a `## ` line inside a ``` or ~~~ code block is content, not a
    heading, so it never becomes a split point (these READMEs are full of code
    blocks that contain shell comments and the like)."""
    sections = []
    current = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and _SECTION_HEADING_RE.match(line) and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))
    return sections


def translate_section(target_lang, section_text):
    """Translate a single Markdown section and return the translated text.

    A plain, tool-free completion: the orchestrator assembles the sections and
    saves the file itself, so no local model ever has to emit the whole document
    -- which is what truncates on big READMEs."""
    user_prompt = (
        f"Translate the following Markdown section into {target_lang}. It is one "
        f"section of a larger README being translated section by section.\n\n"
        f"Return ONLY the translated Markdown for this section -- no preamble, no "
        f"explanation, and do not wrap the whole section in a code fence.\n\n"
        f"<section>\n{section_text}\n</section>"
    )
    text = complete(
        get_chunk_writer_prompt(target_lang), user_prompt, label="section"
    )
    return _strip_wrapping_fence(text)


def translate_whole_document(target_lang, source_text):
    """Translate an entire README in one completion and return the text (the
    orchestrator saves it). Used for sources below the chunking threshold."""
    user_prompt = (
        f"Translate the following README into {target_lang}.\n\n"
        f"Return ONLY the translated Markdown -- no preamble, no explanation, and "
        f"do not wrap the whole document in a code fence.\n\n"
        f"<readme>\n{source_text}\n</readme>"
    )
    text = complete(
        get_document_writer_prompt(target_lang), user_prompt, label="draft"
    )
    return _strip_wrapping_fence(text)


def rewrite_whole_document(target_lang, source_text, current_target, critique):
    """Produce a revised full translation addressing the reviewer's critique and
    return the text (the orchestrator saves it)."""
    user_prompt = (
        f"Revise the {target_lang} translation below so it fully addresses the "
        f"editor's feedback while staying faithful to the English source.\n\n"
        f"Return ONLY the revised Markdown -- no preamble, no explanation, and do "
        f"not wrap the whole document in a code fence.\n\n"
        f"<english_source>\n{source_text}\n</english_source>\n\n"
        f"<current_translation>\n{current_target}\n</current_translation>\n\n"
        f"<editor_feedback>\n{critique}\n</editor_feedback>"
    )
    text = complete(
        get_document_writer_prompt(target_lang), user_prompt, label="rewrite"
    )
    return _strip_wrapping_fence(text)


def review_section(target_lang, source_section, translated_section):
    """Critique one translated section against its English source. Reuses the
    whole-document reviewer prompt (same verdict/feedback format) but scopes the
    task to a single section so it doesn't flag a 'missing' title/intro/closing
    that lives in a different section."""
    user_prompt = (
        "Review this translated section against its English source. It is ONE "
        "section of a larger README translated section by section -- judge only "
        "this section, and do not flag a missing document title, intro, or closing "
        "that belongs to other sections.\n\n"
        f"<english_source>\n{source_section}\n</english_source>\n\n"
        f"<translation>\n{translated_section}\n</translation>"
    )
    return complete(
        get_reviewer_prompt(target_lang), user_prompt, label="section-review"
    )


def rewrite_section(target_lang, source_section, current_section, critique):
    """Produce a revised translation of one section addressing the reviewer's
    critique. Returns the revised section text."""
    user_prompt = (
        f"Revise the {target_lang} translation of this section so it fully "
        "addresses the editor's feedback while staying faithful to the English "
        "source. It is ONE section of a larger README.\n\n"
        "Return ONLY the revised Markdown for this section -- no preamble, no "
        "explanation, and do not wrap it in a code fence.\n\n"
        f"<english_source>\n{source_section}\n</english_source>\n\n"
        f"<current_translation>\n{current_section}\n</current_translation>\n\n"
        f"<editor_feedback>\n{critique}\n</editor_feedback>"
    )
    text = complete(
        get_chunk_writer_prompt(target_lang), user_prompt, label="section-rewrite"
    )
    return _strip_wrapping_fence(text)


def translate_section_reviewed(target_lang, section_text, label=""):
    """Translate one section, then (if REVIEW_SECTIONS) run the same
    critique->revise loop the single-shot path uses, but scoped to this section
    so nothing ever exceeds the per-section size. Returns the final text."""
    draft = translate_section(target_lang, section_text).strip()
    if not REVIEW_SECTIONS or not draft:
        return draft
    for _ in range(MAX_ITERATIONS):
        critique = review_section(target_lang, section_text, draft)
        if parse_verdict(critique) == "AGREE":
            break
        feedback = parse_feedback(critique) or (critique or "").strip()
        print(f"      🔧 {label} revision: {feedback[:160]!r}")
        revised = rewrite_section(target_lang, section_text, draft, feedback).strip()
        if not revised:
            break
        draft = revised
    return draft


async def translate_document_chunked(session, target_lang, source_text):
    """Translate a large README section by section and save the assembled result
    via the server's write_readme tool. Returns True if a non-empty draft was
    written, False otherwise."""
    sections = split_markdown_sections(source_text)
    review_note = " (with per-section review)" if REVIEW_SECTIONS else ""
    print(f"   Split into {len(sections)} section(s){review_note}.")

    translated = []
    for i, section in enumerate(sections, 1):
        print(f"   ✍️  Section {i}/{len(sections)} ({len(section):,} chars)...")
        text = translate_section_reviewed(
            target_lang, section, label=f"§{i}/{len(sections)}"
        ).strip()
        if text:
            translated.append(text)

    assembled = "\n\n".join(translated)
    if not assembled.strip():
        print(f"   ❌ Chunked translation produced no content for {target_lang}.")
        return False

    # Write directly with the known-correct language -- no tool-argument drift to
    # guard against here, since the orchestrator supplies the language itself.
    await session.call_tool(
        "write_readme", {"language": target_lang, "content": assembled}
    )
    return True

async def save_translation(session, lang, content):
    """Persist a finished translation through the server's write_readme tool.

    The orchestrator owns the content and supplies the ground-truth language, so
    the document never rides inside a model-emitted tool argument (which is what
    truncates into malformed JSON on local reasoning models)."""
    await session.call_tool("write_readme", {"language": lang, "content": content})


async def run_translation_pipeline():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT, PROJECT_ROOT],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            source_text = read_source_readme_text()

            for lang in LANGUAGES:
                print(f"🚀 Starting adventure for language: {lang}...")

                try:
                    # Match the folder name the server actually writes to
                    # (server._normalize_language title-cases), or the existence
                    # check and the server disagree and we re-translate forever.
                    lang_dir = lang.strip().title()
                    existing_file_loc = Path(PROJECT_ROOT) / "docs" / lang_dir / "README.md"
                    chunked = False
                    draft = None  # current in-memory translation for the review loop

                    if existing_file_loc.is_file():
                        print("🧐 We found an existing file! Let's check for changes...")

                        critique_task = await get_mcp_prompt_text(
                            session, "check_existing_readme", {"language": lang}
                        )
                        critique = complete(
                            get_update_reviewer_prompt(lang),
                            critique_task,
                            label="update-review",
                        )

                        verdict = parse_verdict(critique)
                        if verdict == "AGREE":
                            print(f"✅ The existing translation for {lang} is already up to date!")
                            continue

                        feedback = parse_feedback(critique) or (critique or "").strip()
                        print(f"⚠️ Reviewer found issues: {feedback[:400]!r}")
                        print("Sending to writer...")

                        current_target = read_target_readme_text(lang) or ""
                        draft = rewrite_whole_document(
                            lang, source_text, current_target, feedback
                        ).strip()
                        if not draft:
                            print(
                                f"❌ Rewrite for {lang} came back empty -- "
                                f"previous draft left unchanged.\n"
                            )
                            continue
                        await save_translation(session, lang, draft)
                        print(f"✍️ Writer updated the existing translation for {lang}.")
                    elif CHUNK_TRANSLATION and len(source_text) > CHUNK_THRESHOLD_CHARS:
                        chunked = True
                        print(
                            f"📚 Large README ({len(source_text):,} chars) -- "
                            f"translating {lang} section by section..."
                        )
                        if not await translate_document_chunked(
                            session, lang, source_text
                        ):
                            print(f"❌ Chunked draft failed for {lang}. Skipping.\n")
                            continue
                        print(f"✍️ Writer has completed the first draft for {lang}.")
                    else:
                        draft = translate_whole_document(lang, source_text).strip()
                        if not draft:
                            print(
                                f"❌ Writer produced no draft for {lang} -- "
                                f"skipping this language.\n"
                            )
                            continue
                        await save_translation(session, lang, draft)
                        print(f"✍️ Writer has completed the first draft for {lang}.")

                    if chunked:
                        # Review already happened per-section inside
                        # translate_document_chunked (when REVIEW_SECTIONS is on).
                        # A second whole-document review would ask the model to
                        # re-emit the entire large README in one shot -- exactly the
                        # truncation chunking avoids -- so we don't. See README
                        # "Large-README handling".
                        note = (
                            "sections reviewed individually"
                            if REVIEW_SECTIONS
                            else "review skipped -- set review_sections true to enable"
                        )
                        print(
                            f"ℹ️  Keeping the section-by-section draft for {lang} "
                            f"({note}).\n"
                        )
                        print(f"✅ Finished processing {lang}.\n")
                        continue

                    iteration = 0
                    while iteration < MAX_ITERATIONS:
                        iteration += 1
                        print(f"🧐 Reviewer is checking draft {iteration}...")

                        critique_task = await get_mcp_prompt_text(
                            session, "critique_translation", {"language": lang}
                        )
                        critique = complete(
                            get_reviewer_prompt(lang), critique_task, label="review"
                        )

                        verdict = parse_verdict(critique)
                        if verdict == "AGREE":
                            print(f"🎉 Success! The translation for {lang} is flawless!")
                            break

                        feedback = parse_feedback(critique) or (critique or "").strip()
                        print(f"⚠️ Reviewer found issues: {feedback[:400]!r}")
                        print("Sending back to writer...")
                        revised = rewrite_whole_document(
                            lang, source_text, draft, feedback
                        ).strip()
                        if not revised:
                            print(
                                f"⚠️ Rewrite for {lang} came back empty -- "
                                f"keeping the previous draft."
                            )
                            continue
                        draft = revised
                        await save_translation(session, lang, draft)
                    else:
                        print(
                            f"⏱️ Hit max iterations ({MAX_ITERATIONS}) for {lang} "
                            "without agreement — keeping the last saved draft."
                        )

                    print(f"✅ Finished processing {lang}.\n")

                except openai.APITimeoutError:
                    print(
                        f"⏱️ Request timed out after {REQUEST_TIMEOUT_SECONDS}s while "
                        f"processing {lang} -- the model may just be slow (raise "
                        "request_timeout_seconds in config.local.json if so), or it "
                        f"may be genuinely stuck. Skipping {lang} for now.\n"
                    )
                except openai.OpenAIError as e:
                    print(
                        f"❌ API error while processing {lang}: {e} -- "
                        f"skipping this language.\n"
                    )

            docs_dir = Path(PROJECT_ROOT) / "docs"
            root_readme = Path(PROJECT_ROOT) / "README.md"
            english_readme = docs_dir / "English" / "README.md"

            if not english_readme.is_file():
                if root_readme.is_file():
                    english_readme.parent.mkdir(parents=True, exist_ok=True)
                    root_readme.rename(english_readme)
                    print(f"📦 Moved root README.md into {english_readme.relative_to(PROJECT_ROOT)}")
                else:
                    print("⚠️ No English README.md found in docs/English or the project root -- skipping directory page.")

            available_languages = sorted(
                p.parent.name
                for p in docs_dir.glob("*/README.md")
                if p.stat().st_size > 0
            )

            if available_languages:
                print(f"📚 Building language directory page for: {', '.join(available_languages)}...")
                directory_task = await get_mcp_prompt_text(
                    session,
                    "create_docs_language_directory",
                    {"languages": ", ".join(available_languages)},
                )
                page = _strip_wrapping_fence(
                    complete(
                        get_directory_writer_prompt(),
                        directory_task,
                        label="directory",
                    )
                ).strip()
                if not page:
                    print("⚠️ Directory page wasn't saved -- model returned no content.")
                else:
                    await session.call_tool(
                        "write_directory_readme", {"content": page}
                    )
                    print("✅ Wrote project directory README.md linking all available languages.")


if __name__ == "__main__":
    asyncio.run(run_translation_pipeline())