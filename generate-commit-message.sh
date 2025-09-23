#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト

set -e

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    git diff --staged
else
    # 初回コミット（HEADが存在しない）
    git diff --cached
fi | (cd "/home/y_ohi/program/lazygit-llm-commit-generator" && uv run lazygit-llm-generate --config "/home/y_ohi/.config/lazygit-llm/config.yml")