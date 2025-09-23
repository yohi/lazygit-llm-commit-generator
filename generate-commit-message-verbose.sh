#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト（詳細進捗表示版）

set -euo pipefail
IFS=$'\n\t'

# 初期メッセージとして表示
echo "🤖 Starting AI commit message generation..." >&2
echo "📊 Analyzing staged changes..." >&2
echo "🔍 Checking repository status..." >&2

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    DIFF_OUTPUT=$(git diff --staged --no-ext-diff)
    echo "📝 Found staged changes (existing repository)" >&2
else
    # 初回コミット（HEADが存在しない）
    DIFF_OUTPUT=$(git diff --cached --no-ext-diff)
    echo "📝 Found staged changes (initial commit)" >&2
fi

# 差分があるかチェック
if [ -z "$DIFF_OUTPUT" ]; then
    echo "❌ No staged changes found" >&2
    exit 1
fi

echo "🤖 Connecting to AI service..." >&2
echo "⚡ Processing changes with Gemini..." >&2

# AIコミットメッセージ生成（堅牢化）
# uv の存在確認
if ! command -v uv >/dev/null 2>&1; then
  echo "❌ uv not found. Please install uv." >&2
  exit 1
fi

# コンフィグ/プロジェクトディレクトリの解決（上書き可能）
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
CONFIG_PATH="${LAZYGIT_LLM_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/lazygit-llm/config.yml}"

# 実行（エラー出力は別に保持）
pushd "$PROJECT_DIR" >/dev/null
RESULT=$(uv run lazygit-llm-generate --config "$CONFIG_PATH" <<<"$DIFF_OUTPUT" 2>./.lazygit-llm.err)
EXIT_CODE=$?
ERRMSG="$(cat ./.lazygit-llm.err || true)"
rm -f ./.lazygit-llm.err
popd >/dev/null

if [ $EXIT_CODE -ne 0 ]; then
  echo "❌ AI service returned error (exit code: $EXIT_CODE)" >&2
  [ -n "$ERRMSG" ] && echo "Error details: $ERRMSG" >&2
  exit 1
fi

if [ -z "$RESULT" ]; then
  echo "❌ AI service returned empty result" >&2
  exit 1
fi

echo "✅ AI commit message generated successfully!" >&2
echo "📋 Preparing form with generated message..." >&2

# 生成されたメッセージを返す
echo "$RESULT"
