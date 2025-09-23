# LazyGit LLM Commit Generator

LazyGit用のLLM駆動コミットメッセージ自動生成ツール

## 概要

このツールは、LazyGitと連携してLarge Language Model（LLM）を使用し、
ステージ済みの変更からコミットメッセージを自動生成します。

## 主な機能

- LazyGitのカスタムコマンドとして統合
- 複数のLLMプロバイダーに対応（OpenAI、Anthropic、Google Gemini）
- セキュアなAPI認証
- YAML設定ファイルによるカスタマイズ
- 包括的なエラーハンドリング

## 対応プロバイダー

### API型
- OpenAI GPT (GPT-4, GPT-3.5-turbo)
- Anthropic Claude (Claude-3.5 Sonnet, Opus, Haiku)
- Google Gemini API (Gemini-1.5 Pro, Flash)

### CLI型
- Google Gemini CLI (gcloud経由)
- Claude Code CLI

## インストール

```bash
git clone https://github.com/yohi/lazygit-llm-commit-generator.git
cd lazygit-llm-commit-generator
python3 install.py
```

## 設定

### 1. 環境変数設定

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
export GOOGLE_API_KEY="your-api-key"
```

### 2. 設定ファイル作成

```bash
mkdir -p ~/.config/lazygit-llm
cp lazygit-llm/config/config.yml.example ~/.config/lazygit-llm/config.yml
```

### 3. LazyGit設定

`~/.config/lazygit/config.yml`に追加:

```yaml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

## 使用方法

1. ファイルをステージング: `git add .`
2. LazyGitを起動: `lazygit`
3. Ctrl+Gでコミットメッセージ生成
4. 生成されたメッセージを確認・編集

## システム要件

- Python 3.9以上
- Git 2.0以上
- LazyGit 0.35以上

## 設定例

```yaml
provider: "openai"
model_name: "gpt-4"
api_key: "${OPENAI_API_KEY}"
timeout: 30
max_tokens: 100

prompt_template: |
  Based on the following git diff, generate a concise commit message:

  {diff}

  Generate only the commit message, no additional text.

additional_params:
  temperature: 0.3
  top_p: 0.9
```

## コマンドライン使用

```bash
# 基本使用
lazygit-llm-generate

# 設定ファイル指定
lazygit-llm-generate --config /path/to/config.yml

# 詳細ログ
lazygit-llm-generate --verbose

# 設定テスト
lazygit-llm-generate --test-config
```

## トラブルシューティング

### API認証エラー
```
ConfigError: API認証に失敗しました
```
- 環境変数のAPIキーを確認
- プロバイダーの利用制限を確認

### モジュールエラー
```
ModuleNotFoundError: No module named 'openai'
```
解決方法:
```bash
pip install -r requirements.txt
```

### 権限エラー
```
PermissionError: [Errno 13] Permission denied
```
解決方法:
```bash
chmod 600 ~/.config/lazygit-llm/config.yml
chmod +x ~/.local/bin/lazygit-llm-generate
```

## パフォーマンス

推奨設定:
- diffサイズ: 50KB以下
- 利用頻度: 200回/時間以下
- タイムアウト: 15-30秒

## 開発

```bash
# 開発モードインストール
pip install -e .

# テスト実行
python -m pytest tests/

# コード品質チェック
flake8 lazygit-llm/
mypy lazygit-llm/
```

## ドキュメント

- [ユーザーガイド](docs/USER_GUIDE.md)
- [API仕様書](docs/API_REFERENCE.md)
- [開発者ガイド](docs/DEVELOPMENT.md)
- [ドキュメント索引](docs/README_DOCS.md)

## ライセンス

MIT License

## 関連リンク

- [LazyGit](https://github.com/jesseduffield/lazygit)
- [OpenAI](https://openai.com/)
- [Anthropic](https://www.anthropic.com/)
- [Google AI](https://ai.google.dev/)

## コントリビューション

- Issues: 不具合報告・機能要望
- Discussions: 質問・議論
- Wiki: 詳細ドキュメント

Happy coding with AI-powered commit messages!
