#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト（フィードバック付き）

set -e

# 一時的なステータス表示（ターミナルタイトルで表示可能な場合）
if [ -n "$TERM" ] && command -v tput >/dev/null 2>&1; then
    # ターミナルが対応している場合、タイトルバーにステータス表示
    echo -ne "\033]0;🤖 Generating AI commit message...\007" >/dev/tty 2>/dev/null || true
fi

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    DIFF_OUTPUT=$(git diff --staged)
else
    # 初回コミット（HEADが存在しない）
    DIFF_OUTPUT=$(git diff --cached)
fi

# 差分があるかチェック
if [ -z "$DIFF_OUTPUT" ]; then
    echo "No staged changes found" >&2
    exit 1
fi

# AIコミットメッセージ生成
RESULT=$(echo "$DIFF_OUTPUT" | (cd "/home/y_ohi/program/lazygit-llm-commit-generator" && uv run lazygit-llm-generate --config "/home/y_ohi/.config/lazygit-llm/config.yml"))

# ターミナルタイトルをリセット
if [ -n "$TERM" ] && command -v tput >/dev/null 2>&1; then
    echo -ne "\033]0;\007" >/dev/tty 2>/dev/null || true
fi

echo "$RESULT"