#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト（フィードバック付き）

set -euo pipefail
IFS=$'\n\t'

# 一時的なステータス表示（ターミナルタイトルで表示可能な場合）
if [ -n "$TERM" ] && command -v tput >/dev/null 2>&1; then
    # ターミナルが対応している場合、タイトルバーにステータス表示
    echo -ne "\033]0;🤖 Generating AI commit message...\007" >/dev/tty 2>/dev/null || true
fi

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    DIFF_OUTPUT=$(git diff --staged --no-ext-diff)
else
    # 初回コミット（HEADが存在しない）
    DIFF_OUTPUT=$(git diff --cached --no-ext-diff)
fi

# 差分があるかチェック
if [ -z "$DIFF_OUTPUT" ]; then
    echo "No staged changes found" >&2
    exit 1
fi

# AIコミットメッセージ生成（堅牢化）
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Please install uv." >&2
  exit 1
fi
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
CONFIG_PATH="${LAZYGIT_LLM_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/lazygit-llm/config.yml}"
pushd "$PROJECT_DIR" >/dev/null
RESULT=$(uv run lazygit-llm-generate --config "$CONFIG_PATH" <<<"$DIFF_OUTPUT")
EXIT_CODE=$?
popd >/dev/null
if [ $EXIT_CODE -ne 0 ] || [ -z "$RESULT" ]; then
  echo "Failed to generate commit message" >&2
  exit 1
fi

# ターミナルタイトルをリセット
if [ -n "$TERM" ] && command -v tput >/dev/null 2>&1; then
    echo -ne "\033]0;\007" >/dev/tty 2>/dev/null || true
fi

echo "$RESULT"
