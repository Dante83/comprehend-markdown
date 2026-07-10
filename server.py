"""MCP server exposing README-translation tools for a single project folder.

Launched via run.sh (or directly by an MCP host such as LM Studio) with the
target project's absolute path as argv[1]. Every tool below operates on that
one fixed project root for the lifetime of this server process.

Expected layout in the target project:
    <root>/README.md              the canonical English source
    <root>/docs/<lang>/README.md  translated versions, one per language code
"""

import re
import sys
from pathlib import Path

from pydantic import Field
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base

# Unicode-friendly: allow any script (needed for names like "中文", "العربية",
# "हिन्दी"), but block path traversal by rejecting separators, leading dots,
# and capping length -- `language` flows directly into a filesystem path
# built from LLM-controlled input.
_LANGUAGE_RE = re.compile(r"^(?!\.)[^/\\\x00]{1,64}$")

# Some local models leak their own chat-template special tokens into the
# generated text right at the tail end of an otherwise-complete response --
# observed as a literal "```<|tool_call>call:write_readme{content:" fragment
# appended after a full, correct translation. Not real content; strip it
# rather than persist it into the saved file.
_LEAKED_TOOL_CALL_RE = re.compile(
    r"\n?`{1,3}\s*<\|[a-zA-Z_]*tool_call[a-zA-Z_]*\|?>.*", re.IGNORECASE | re.DOTALL
)


def _strip_leaked_tool_call_artifacts(content: str) -> str:
    cleaned, n = _LEAKED_TOOL_CALL_RE.subn("", content)
    if n:
        print(
            "[write_readme] stripped a leaked tool-call artifact from the "
            "end of the draft",
            file=sys.stderr,
        )
    return cleaned


def _normalize_language(language: str) -> str:
    """Canonicalize a model-supplied language name into a stable folder name.

    LLM tool-call arguments drift in case across calls (e.g. "Japanese" vs
    "japanese"), which on a case-sensitive filesystem silently creates a
    second sibling directory instead of reusing the existing one. Title-
    casing collapses that drift to one canonical spelling. This also
    doubles as a path-traversal guard, since `language` otherwise flows
    directly into a filesystem path built from LLM-controlled input.
    """
    language = language.strip()
    if not language or not _LANGUAGE_RE.match(language):
        raise ValueError(f"Invalid language name: {language!r}")
    return language.title()


if len(sys.argv) < 2:
    print("Usage: server.py <absolute-path-to-project-folder>", file=sys.stderr)
    sys.exit(1)

PROJECT_ROOT = Path(sys.argv[1]).resolve()
if not PROJECT_ROOT.is_dir():
    print(f"Not a directory: {PROJECT_ROOT}", file=sys.stderr)
    sys.exit(1)

DOCS_DIR = PROJECT_ROOT / "docs"
SOURCE_README = DOCS_DIR / "English" / "README.md"
DIR_README = PROJECT_ROOT / "README.md"

mcp = FastMCP("comprehend-markdown")


@mcp.tool(
    name="write_readme",
    description="Use this tool to update the text inside the translated README.md file"
)
def write_translated_readme(language: str, content: str) -> str:
    """Write (or overwrite) docs/<language>/README.md with the given content."""
    path = DOCS_DIR / _normalize_language(language) / "README.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_strip_leaked_tool_call_artifacts(content), encoding="utf-8")
    return f"wrote {path.relative_to(PROJECT_ROOT)}"

@mcp.tool(
    name="write_directory_readme",
    description="Use this tool to update the text inside the directory of languages README.md file"
)
def write_directory_readme_tool(content: str) -> str:
    """Write (or overwrite) the root README.md with the given content."""
    DIR_README.write_text(_strip_leaked_tool_call_artifacts(content), encoding="utf-8")
    return "wrote project directory readme."

def _read_source_readme() -> str:
    if SOURCE_README.is_file():
        return SOURCE_README.read_text(encoding="utf-8")
    # Not yet migrated into docs/English -- fall back to the root copy.
    if DIR_README.is_file():
        return DIR_README.read_text(encoding="utf-8")
    raise FileNotFoundError("A README.md file could not be found in either the source or docs directory.")


def _read_dir_readme() -> str:
    if not DIR_README.is_file():
        raise FileNotFoundError("A README.md file could not be found in either the source or docs directory.")
    return DIR_README.read_text(encoding="utf-8")

def _read_target_readme(language: str) -> str | None:
    """Read docs/<language>/README.md, or create an empty one and return None if missing."""
    path = DOCS_DIR / _normalize_language(language) / "README.md"
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return None
    text = path.read_text(encoding="utf-8")
    return text or None


@mcp.resource(
    "docs://readme",
    mime_type="text/markdown"
)
def get_english_readme():
    return _read_source_readme()

@mcp.resource(
    "docs://dir_readme",
    mime_type="text/markdown"
)
def get_directory_readme():
    return _read_dir_readme()

@mcp.resource(
    "docs://readme/{language}",
    mime_type="text/markdown"
)
def get_readme_translated_to(language):
    text = _read_target_readme(language)
    if text is None:
        raise ValueError("The file was created but it's empty and requires a fresh translation.")
    return text

@mcp.prompt(
    name="translate_readme",
    description="Rewrites the contents of the document in Markdown format."
)
def translate_readme_prompt(
    language: str = Field(description="Language we are translating the README.md into from english.")
) -> list[base.Message]:
    target_uri = f"docs://readme/{language}"
    source_content = _read_source_readme()

    prompt = f"""
        You are an expert technical translator and, where the text calls for it, a
        skilled literary translator. Translate the English README into {language}.

        Source Document (English), delimited by <source> tags:
        <source>
        {source_content}
        </source>

        Instructions:
        1. Translate the source document above clearly and accurately into {language}.
        2. Preserve exactly, untranslated: code blocks, inline code, URLs,
           badges/shields, YAML front matter, HTML comments, and placeholder
           variables. Only prose, headers, and comments-about-the-project get
           translated -- never code itself.
        3. For passages that are friendly, casual, or personal in tone, keep
           that energy and feel rather than translating stiffly or literally.
        4. For poetry, prioritize preserving theme, meter, rhyme scheme,
           stanza structure, and literary devices as much as {language}
           allows -- take translator's liberties here over strict literalism.
        5. Use the 'write_readme' tool with language="{language}" to save the
           translation to the target document ({target_uri}). This is the
           only tool that persists your work -- you must call it before
           finishing, and the language argument must be exactly "{language}".
    """

    return [base.Message(role="user", content=prompt)]


@mcp.prompt(
    name="critique_translation",
    description="Critiques the translation of the given readme file and determines if it's satisfactory."
)
def critique_translation_prompt(
    language: str = Field(description="Language that we attempted to translate the README.md file into from english.")
) -> list[base.Message]:
    source_content = _read_source_readme()
    target_content = _read_target_readme(language)
    if target_content is None:
        target_content = "(empty -- no translation has been written yet)"

    prompt = f"""
        You are a bilingual technical editor reviewing a translation of the
        English README into {language}.

        Source Document (English), delimited by <source> tags:
        <source>
        {source_content}
        </source>

        Target Document ({language}), delimited by <target> tags:
        <target>
        {target_content}
        </target>

        Instructions:
        1. Compare the target document above against the source document.
        2. Check: did the translator leave code, code blocks, URLs, badges,
           and placeholders untouched, translating only prose/comments?
        3. Check: do friendly/casual/personal passages keep their energy and
           feel rather than reading stiff or overly literal?
        4. Check: does poetry preserve theme, meter, rhyme scheme, stanza,
           and literary devices as much as {language} reasonably allows?
        5. Note any other accuracy or naturalness issues you'd want fixed.

        Respond in exactly this format:

        If the translation is ready to ship:
        <verdict>AGREE</verdict>
        <feedback>One sentence on why it's solid.</feedback>

        If it needs revision:
        <verdict>REVISE</verdict>
        <feedback>
        Numbered, specific, actionable points. Quote the problem phrase and
        suggest a fix where possible. Do not invent nitpicks just to extend
        the review -- if it's genuinely good, say AGREE.
        </feedback>
    """

    return [base.Message(role="user", content=prompt)]


@mcp.prompt(
    name="rewrite_translation",
    description="Rewrites the translation based on the critique of the reviewer."
)
def rewrite_translation_prompt(
    language: str = Field(description="Language that we attempted to translate the README.md file into from english."),
    critique: str = Field(description="Requested changes made by the reviewer that you may or may not wish to implement.")
) -> list[base.Message]:
    target_uri = f"docs://readme/{language}"
    source_content = _read_source_readme()
    target_content = _read_target_readme(language)
    if target_content is None:
        target_content = "(empty -- no translation has been written yet)"

    prompt = f"""
        Revise the {language} translation of our README.md based on editorial
        critique.

        Source Document (English), delimited by <source> tags:
        <source>
        {source_content}
        </source>

        Current Translation ({language}), delimited by <target> tags:
        <target>
        {target_content}
        </target>

        Critique received:
        {critique}

        Instructions:
        1. Apply every point in the critique that you agree improves accuracy
           or naturalness. You may push back on a point in your response if
           you think the existing choice is actually correct -- explain why.
        2. Keep upholding the core goals: accurate technical meaning, code
           and placeholders left untouched, natural/native-sounding prose,
           preserved energy in casual passages, and preserved meter/rhyme/
           theme in any poetry.
        3. Use the 'write_readme' tool with language="{language}" to save
           the revised translation to the target document ({target_uri}).

        After saving, respond in exactly this format:
        <verdict>REVISED</verdict>
        <summary>One sentence on what changed.</summary>
    """

    return [base.Message(role="user", content=prompt)]


@mcp.prompt(
    name="check_existing_readme",
    description="Determines if existing readme needs to be udpated."
)
def check_if_translation_needs_update(
    language: str = Field(description="Language we are translating the README.md into from english.")
) -> list[base.Message]:
    source_content = _read_source_readme()
    target_content = _read_target_readme(language)
    if target_content is None:
        target_content = "(empty -- no translation has been written yet)"

    prompt = f"""
        You are a bilingual technical editor reviewing a translation of the ENGLISH 
        readme and comparing it to an existing {language} readme.

        Source Document (English), delimited by <source> tags:
        <source>
        {source_content}
        </source>

        Target Document ({language}), delimited by <target> tags:
        <target>
        {target_content}
        </target>

        Double check that the translation file is accurate and no new changes have been made to the existing file.
        If the translation agrees:
        <verdict>AGREE</verdict>
        <feedback>One sentence on why it still matches the source.</feedback>

        If it needs revision:
        <verdict>REVISE</verdict>
        <feedback>List all areas that need to be added, updated, or deleted to match the original content</feedback>
    """

    return [base.Message(role="user", content=prompt)]

@mcp.prompt(
    name="rewrite_from_existing_translation",
    description="Rewrites the translation based on the critique of the reviewer."
)
def rewrite_from_existing_translation_prompt(
    language: str = Field(description="Language that we attempted to translate the README.md file into from english."),
    critique: str = Field(description="Requested changes made by the reviewer that you may or may not wish to implement.")
) -> list[base.Message]:
    target_uri = f"docs://readme/{language}"
    source_content = _read_source_readme()
    target_content = _read_target_readme(language)
    if target_content is None:
        target_content = "(empty -- no translation has been written yet)"

    prompt = f"""
        Revise the {language} translation of our README.md based on editorial
        critique and you're own analalysis. This file has been updated and either
        requires updates, new sections or the removal of old sections. Please update
        it with the minimum number of changes needed to match updates you find in the
        existing english readme.

        Source Document (English), delimited by <source> tags:
        <source>
        {source_content}
        </source>

        Current Translation ({language}), delimited by <target> tags:
        <target>
        {target_content}
        </target>

        Critique received:
        {critique}

        Instructions:
        1. Apply every point in the critique that you agree was changed. 
           You may push back on a point in your response if
           you think the existing choice is actually correct -- explain why.
        2. Keep upholding the core goals: accurate technical meaning, code
           and placeholders left untouched, natural/native-sounding prose,
           preserved energy in casual passages, and preserved meter/rhyme/
           theme in any poetry.
        3. Use the 'write_readme' tool with language="{language}" to save
           the revised translation to the target document ({target_uri}).

        After saving, respond in exactly this format:
        <verdict>REVISED</verdict>
        <summary>One sentence on what changed.</summary>
    """

    return [base.Message(role="user", content=prompt)]

@mcp.prompt(
    name="create_docs_language_directory",
    description="Create a directory of available languages for the user to swap between."
)
def create_docs_language_directory(
    languages: str = Field(description="Comma-separated list of language names that have a docs/<language>/README.md file.")
) -> list[base.Message]:
    dir_source_content = _read_source_readme()
    language_list = [lang.strip() for lang in languages.split(",") if lang.strip()]
    link_lines = "\n".join(
        f'- [{lang}](docs/{lang}/README.md)' for lang in language_list
    )

    prompt = f"""
        You are building the root README.md for this project. Its only job is
        to act as a language picker: a very short, friendly landing point that
        gets every reader -- regardless of what language they read -- to the
        translated README that actually serves them.

        The original English README content, for reference/context only
        (do NOT reproduce it here -- it now lives at docs/English/README.md
        and is one of the links below):
        <source>
        {dir_source_content}
        </source>

        Available languages and their files:
        {link_lines}

        Instructions:
        1. Write a short intro line in English (a sentence or two, e.g. project
           name/one-line description) so English readers immediately recognize
           the project.
        2. Below a simple English instruction intro, render the language list as a single Markdown list
           with exactly one entry per language: each entry is a short
           welcoming sentence written IN that language itself (e.g. the
           Spanish entry written in Spanish, the Japanese entry written in
           Japanese) ending with its link, so every reader can spot their own
           language by eye without needing to read English first. Do not
           produce a second, separate list of the same links.
        3. Feel free to prefix each entry with a fitting flag/region emoji
           where one exists, but do not invent inaccurate flags for languages
           that span many countries or regions (e.g. Arabic, Nigerian Pidgin)
           -- a generic globe or speech-bubble emoji is fine there instead.
        4. Keep the whole page short -- this is a landing page, not documentation.
        5. Use the 'write_directory_readme' tool to save the result as the
           project's root README.md. This is the only tool that persists your
           work -- you must call it before finishing.
    """

    return [base.Message(role="user", content=prompt)]

if __name__ == "__main__":
    mcp.run()