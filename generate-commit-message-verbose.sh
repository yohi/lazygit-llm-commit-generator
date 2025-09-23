#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト（詳細進捗表示版）

set -e

# 初期メッセージとして表示
echo "🤖 Starting AI commit message generation..." >&2
echo "📊 Analyzing staged changes..." >&2
echo "🔍 Checking repository status..." >&2

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    DIFF_OUTPUT=$(git diff --staged)
    echo "📝 Found staged changes (existing repository)" >&2
else
    # 初回コミット（HEADが存在しない）
    DIFF_OUTPUT=$(git diff --cached)
    echo "📝 Found staged changes (initial commit)" >&2
fi

# 差分があるかチェック
if [ -z "$DIFF_OUTPUT" ]; then
    echo "❌ No staged changes found" >&2
    exit 1
fi

echo "🤖 Connecting to AI service..." >&2
echo "⚡ Processing changes with Gemini..." >&2

# AIコミットメッセージ生成
RESULT=$(echo "$DIFF_OUTPUT" | (cd "/home/y_ohi/program/lazygit-llm-commit-generator" && uv run lazygit-llm-generate --config "/home/y_ohi/.config/lazygit-llm/config.yml" 2>&1))
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || [ -z "$RESULT" ]; then
    echo "❌ Failed to generate commit message (exit code: $EXIT_CODE)" >&2
    echo "Error details: $RESULT" >&2
    exit 1
fi

# 結果に明らかなエラーメッセージが含まれていないかチェック
if echo "$RESULT" | grep -qi "error\|failed\|timeout"; then
    echo "❌ AI service returned error" >&2
    echo "Error details: $RESULT" >&2
    exit 1
fi

echo "✅ AI commit message generated successfully!" >&2
echo "📋 Preparing form with generated message..." >&2

# 生成されたメッセージを返す
echo "$RESULT"