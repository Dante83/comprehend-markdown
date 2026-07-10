#!/usr/bin/env bash
# Sets up the venv and launches either the MCP server or the standalone
# translate<->critique pipeline for a single project folder.
#
# Usage:
#   ./run.sh serve    /absolute/path/to/project   # stdio MCP server
#   ./run.sh pipeline /absolute/path/to/project   # runs main.py end-to-end
#
# "serve" is what an MCP host (e.g. LM Studio) should point its "command"
# at, with the target project's absolute path as the argument. "pipeline"
# drives the full writer/reviewer loop itself via LM Studio's OpenAI-
# compatible endpoint (see config.json / config.local.json) and spawns its
# own copy of server.py internally -- no MCP host needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ $# -lt 1 ]; then
    echo "Usage: $0 {serve|pipeline} <absolute-path-to-project-folder>" >&2
    exit 1
fi

MODE="$1"
TARGET_DIR="${2:-}"

case "$MODE" in
    serve|pipeline) ;;
    *)
        echo "Error: mode must be 'serve' or 'pipeline', got: $MODE" >&2
        exit 1
        ;;
esac

if [ -z "$TARGET_DIR" ]; then
    # serve mode can't prompt: once server.py starts, stdin/stdout are the
    # MCP JSON-RPC channel, and MCP hosts like LM Studio spawn it
    # non-interactively anyway -- the path must come in as an argument.
    if [ "$MODE" = "pipeline" ] && [ -t 0 ]; then
        read -r -p "Enter absolute path to project folder: " TARGET_DIR
    else
        echo "Usage: $0 {serve|pipeline} <absolute-path-to-project-folder>" >&2
        exit 1
    fi
fi

if [[ "$TARGET_DIR" != /* ]]; then
    echo "Error: path must be absolute, got: $TARGET_DIR" >&2
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: not a directory: $TARGET_DIR" >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR" >&2
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

pip install --quiet --upgrade pip
pip install --quiet -r "$SCRIPT_DIR/requirements.txt"

if [ "$MODE" = "serve" ]; then
    exec python "$SCRIPT_DIR/server.py" "$TARGET_DIR"
else
    exec python "$SCRIPT_DIR/main.py" "$TARGET_DIR"
fi
