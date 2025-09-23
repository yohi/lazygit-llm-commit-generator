#!/bin/bash
# LazyGit LLM Commit Generator Wrapper
# LazyGitから呼び出されるラッパースクリプト

set -e

# 元の作業ディレクトリを保存（これがgitリポジトリ）
REPO_DIR="$(pwd)"
echo "Repository directory: $REPO_DIR" >&2

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(dirname "$0")"
echo "Script directory: $SCRIPT_DIR" >&2

# gitリポジトリであることを確認
if ! git -C "$REPO_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    echo "Error: Not in a git repository" >&2
    exit 1
fi

# ステージされた変更があることを確認
if git -C "$REPO_DIR" diff --staged --quiet 2>/dev/null; then
    echo "No staged changes found. Please stage some changes first." >&2
    exit 1
fi

echo "Staged changes detected, generating commit message..." >&2

# LazyGit LLMコマンドを実行（元のディレクトリで）
cd "$REPO_DIR"
(cd "$SCRIPT_DIR" && uv run lazygit-llm-generate --config "/home/y_ohi/.config/lazygit-llm/config.yml")