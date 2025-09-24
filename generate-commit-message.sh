#!/bin/bash
# LazyGit用のコミットメッセージ生成スクリプト（統合版）

set -euo pipefail
IFS=$'\n\t'

# 使用方法表示
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -v, --verbose    詳細な進捗表示
    -q, --quiet      最小限の出力
    -t, --title      ターミナルタイトルに進捗表示
    -h, --help       このヘルプを表示

デフォルトは標準的な進捗表示です。
EOF
}

# オプション解析
VERBOSE=false
QUIET=false
TITLE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -q|--quiet)
            QUIET=true
            shift
            ;;
        -t|--title)
            TITLE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_usage
            exit 1
            ;;
    esac
done

# 進捗表示関数
log_info() {
    if [[ "$QUIET" != "true" ]]; then
        echo "$1" >&2
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "$1" >&2
    fi
}

set_terminal_title() {
    if [[ "$TITLE" == "true" && -n "$TERM" ]] && command -v tput >/dev/null 2>&1; then
        echo -ne "\033]0;$1\007" >/dev/tty 2>/dev/null || true
    fi
}

# 開始メッセージ
if [[ "$VERBOSE" == "true" ]]; then
    log_info "🤖 Starting AI commit message generation..."
    log_info "📊 Analyzing staged changes..."
    log_info "🔍 Checking repository status..."
else
    log_info "🤖 Generating..."
fi

set_terminal_title "🤖 Generating AI commit message..."

# HEADが存在するかチェックして適切なgit diffコマンドを選択
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    # 通常のコミット（HEADが存在）
    DIFF_OUTPUT=$(git diff --staged --no-ext-diff)
    log_verbose "📝 Found staged changes (existing repository)"
else
    # 初回コミット（HEADが存在しない）
    DIFF_OUTPUT=$(git diff --cached --no-ext-diff)
    log_verbose "📝 Found staged changes (initial commit)"
fi

# 差分があるかチェック
if [ -z "$DIFF_OUTPUT" ]; then
    log_info "❌ No staged changes found"
    set_terminal_title ""
    exit 1
fi

# AI service接続メッセージ
log_verbose "🤖 Connecting to AI service..."
log_verbose "⚡ Processing changes with Gemini..."

# uvの存在確認
if ! command -v uv >/dev/null 2>&1; then
    log_info "❌ uv not found. Please install uv."
    set_terminal_title ""
    exit 1
fi

# 設定とディレクトリの解決
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$0")" && pwd)}"
CONFIG_PATH="${LAZYGIT_LLM_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/lazygit-llm/config.yml}"

# AI コミットメッセージ生成
pushd "$PROJECT_DIR" >/dev/null

if [[ "$VERBOSE" == "true" ]]; then
    # 詳細モードではエラー出力を別に保持
    RESULT=$(uv run lazygit-llm-generate --config "$CONFIG_PATH" <<<"$DIFF_OUTPUT" 2>./.lazygit-llm.err)
    EXIT_CODE=$?
    ERRMSG="$(cat ./.lazygit-llm.err 2>/dev/null || true)"
    rm -f ./.lazygit-llm.err
else
    # 通常モードでは標準エラー出力をそのまま表示
    RESULT=$(uv run lazygit-llm-generate --config "$CONFIG_PATH" <<<"$DIFF_OUTPUT")
    EXIT_CODE=$?
    ERRMSG=""
fi

popd >/dev/null

# 結果の確認と出力
if [ $EXIT_CODE -ne 0 ]; then
    if [[ "$VERBOSE" == "true" ]]; then
        log_info "❌ AI service returned error (exit code: $EXIT_CODE)"
        [ -n "$ERRMSG" ] && log_info "Error details: $ERRMSG"
    else
        log_info "❌ Failed to generate commit message"
        [ -n "$ERRMSG" ] && echo "$ERRMSG" >&2
    fi
    set_terminal_title ""
    exit 1
fi

if [ -z "$RESULT" ]; then
    if [[ "$VERBOSE" == "true" ]]; then
        log_info "❌ AI service returned empty result"
    else
        log_info "❌ Failed to generate commit message"
    fi
    set_terminal_title ""
    exit 1
fi

# 成功メッセージ
if [[ "$VERBOSE" == "true" ]]; then
    log_info "✅ AI commit message generated successfully!"
    log_info "📋 Preparing form with generated message..."
fi

# ターミナルタイトルをリセット
set_terminal_title ""

# 生成されたメッセージを返す
echo "$RESULT"