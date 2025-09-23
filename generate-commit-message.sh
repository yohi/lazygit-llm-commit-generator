#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト

set -e

# 簡単な進捗メッセージを表示
echo "🤖 Generating..." >&2

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
    echo "❌ No staged changes found" >&2
    exit 1
fi

# AIコミットメッセージ生成
RESULT=$(echo "$DIFF_OUTPUT" | (cd "/home/y_ohi/program/lazygit-llm-commit-generator" && uv run lazygit-llm-generate --config "/home/y_ohi/.config/lazygit-llm/config.yml" 2>&1))
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || [ -z "$RESULT" ]; then
    echo "❌ Failed to generate commit message" >&2
    exit 1
fi

echo "$RESULT"