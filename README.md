# 🚀 LazyGit LLM Commit Generator

LazyGitと連携してLLM（Large Language Model）でコミットメッセージを自動生成するPythonツールです。

## ✨ 主な機能

- **🔧 LazyGit統合**: LazyGitのカスタムコマンドとして組み込み可能
- **🤖 マルチLLM対応**: OpenAI GPT、Anthropic Claude、Google Gemini、Claude Codeに対応
- **🔒 セキュアな認証**: API認証と環境変数による安全な管理
- **⚙️ 柔軟な設定**: YAML設定ファイルによる詳細なカスタマイズ
- **🛡️ 堅牢性**: 包括的なエラーハンドリングとログ出力

## 🎯 対応プロバイダー

### API型プロバイダー
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude-3.5 Sonnet, Opus, Haiku
- **Google Gemini API**: Gemini-1.5 Pro, Flash

### CLI型プロバイダー
- **Google Gemini CLI**: gcloud CLIを通じたGemini利用
- **Claude Code**: claude-code CLIを通じたClaude利用

## 🚀 クイックスタート

### 1. インストール

```bash
# プロジェクトをクローン
git clone https://github.com/yohi/lazygit-llm-commit-generator.git
cd lazygit-llm-commit-generator

# UV環境のセットアップ（推奨）
uv sync --extra dev

# または、インストールスクリプトを実行
uv run python install.py
```

### 2. 設定

環境変数でAPIキーを設定し、設定ファイルを作成：

```bash
# API認証設定
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GOOGLE_API_KEY="your-google-api-key"

# 設定ファイルを作成
mkdir -p ~/.config/lazygit-llm
cp lazygit-llm/config/config.yml.example ~/.config/lazygit-llm/config.yml
nano ~/.config/lazygit-llm/config.yml
```

### 3. LazyGit統合

LazyGitの設定ファイル（`~/.config/lazygit/config.yml`）に以下を追加：

```yaml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

### 4. 使用方法

1. ファイルをステージング: `git add .`
2. LazyGitを起動: `lazygit`
3. FilesセクションでCtrl+Gを押下
4. 生成されたコミットメッセージを確認・編集

## 📋 システム要件

- **Python**: 3.9以上（推奨: 3.11+）
- **UV**: 0.4.0以上（パッケージ管理、推奨）
- **Git**: 2.0以上
- **LazyGit**: 0.35以上
- **OS**: Linux, macOS, Windows

### 主要Python依存関係
- `openai` - OpenAI API利用
- `anthropic` - Anthropic Claude API利用
- `google-generativeai` - Google Gemini API利用
- `PyYAML` - 設定ファイル処理

### UVのインストール
```bash
# Unix系OS（Linux/macOS）
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# pipを使用
pip install uv  # グローバル環境に入る点に注意

# pipxを使用（推奨）
pipx install uv
```

## ⚙️ 設定

### 基本設定例

```yaml
# プロバイダー指定
provider: "openai"  # openai, anthropic, gemini-api, gemini-cli, claude-code

# APIキー（環境変数参照推奨）
api_key: "${OPENAI_API_KEY}"

# モデル名
model_name: "gpt-4"

# タイムアウト設定
timeout: 30

# 最大トークン数
max_tokens: 100

# プロンプトテンプレート
prompt_template: |
  Based on the following git diff, generate a concise commit message
  that follows conventional commits format:

  {diff}

  Generate only the commit message, no additional text.

# プロバイダー固有パラメータ
additional_params:
  temperature: 0.3
  top_p: 0.9
```

### プロンプトテンプレート例

#### 日本語コミットメッセージ
```yaml
prompt_template: |
  以下のgit diffに基づいて、簡潔で分かりやすいコミットメッセージを日本語で生成してください：

  {diff}

  コミットメッセージのみを出力してください。
```

#### 詳細なコミットメッセージ
```yaml
prompt_template: |
  Generate a detailed commit message based on this git diff:

  {diff}

  Format:
  <type>(<scope>): <subject>

  <body>

  - Focus on the 'why' rather than 'what'
  - Use imperative mood
  - Wrap lines at 72 characters
```

## 🔧 コマンドライン使用

### 基本的な使用法

```bash
# ステージ済み変更からコミットメッセージ生成
git diff --staged | uv run lazygit-llm-generate

# 設定ファイル指定
uv run lazygit-llm-generate --config /path/to/config.yml

# 詳細ログ出力
uv run lazygit-llm-generate --verbose

# 設定テスト
uv run lazygit-llm-generate --test-config

# 従来のpip環境でインストール済みの場合
lazygit-llm-generate --test-config
```

## 🛡️ セキュリティ機能

### API認証の安全性
- 設定ファイルには平文でAPIキーを保存しない
- 環境変数による外部化推奨
- 設定ファイルの適切な権限設定

### 入力検証とサニタイゼーション
- Git diff内容の検証と制限
- 不正なプロンプトインジェクション対策
- ファイルパスの安全性チェック

### CLI実行の安全性
- `subprocess.run(shell=False)` による安全なコマンド実行
- 入力パラメータの厳密な検証
- 詳細なログ記録とエラーハンドリング

## 🛠 トラブルシューティング

### よくある問題

#### 1. API認証エラー
```text
ConfigError: API認証に失敗しました
```
**解決方法:**
- 環境変数のAPIキーを確認
- 設定ファイルでAPI認証設定を確認
- プロバイダーの利用制限を確認

#### 2. LazyGitでCtrl+Gが動作しない
```text
LazyGitでCtrl+Gが応答しない
```
**解決方法:**
- LazyGit設定ファイルの確認
- customCommandsの設定確認
- 実行権限の確認

#### 3. Pythonモジュールエラー
```text
ModuleNotFoundError: No module named 'openai'
```
**解決方法:**
```bash
# UV環境を使用（推奨）
uv sync --extra dev

# または従来のpipを使用
pip install openai anthropic google-generativeai PyYAML
```

#### 4. 権限エラー
```text
PermissionError: [Errno 13] Permission denied
```
**解決方法:**
```bash
chmod 600 ~/.config/lazygit-llm/config.yml
chmod +x ~/.local/bin/lazygit-llm-generate
```

### デバッグ

```bash
# 詳細ログで実行して問題を特定
uv run lazygit-llm-generate --verbose

# ログファイル確認
tail -f /tmp/lazygit-llm-*.log

# 設定テスト
uv run lazygit-llm-generate --test-config
```

## ⚡ パフォーマンス

### 高速化設定

```yaml
# レスポンス時間優先
timeout: 15           # タイムアウト短縮
max_tokens: 50        # トークン数制限
additional_params:
  temperature: 0.1    # 創造性抑制
  stream: true        # ストリーミング有効
```

### 使用量制限の考慮

- 50KB以下のdiffサイズを推奨
- プロバイダーごとの利用制限を確認
- 200回/時間程度の利用を推奨

## 🔧 開発

### 開発環境構築

```bash
# UV環境のセットアップ（推奨）
uv sync --extra dev

# テスト実行
uv run pytest tests/

# コード品質チェック
uv run flake8 lazygit-llm/lazygit_llm/
uv run mypy lazygit-llm/lazygit_llm/
uv run black lazygit-llm/lazygit_llm/

# パッケージビルド
uv build
```

### 新しいプロバイダーの追加

1. `base_provider.py`を継承したクラス作成
2. `provider_factory.py`に登録
3. テスト作成
4. ドキュメント更新

## 📚 ドキュメント

- **[📖 ユーザーガイド](docs/USER_GUIDE.md)** - 詳細な使用方法とトラブルシューティング
- **[📋 API仕様書](docs/API_REFERENCE.md)** - 全クラス・メソッドの詳細仕様
- **[🛠 開発者ガイド](docs/DEVELOPMENT.md)** - 開発環境構築と拡張方法
- **[📚 ドキュメント索引](docs/README_DOCS.md)** - 全ドキュメントの概要

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照

## 🔗 関連リンク

- [LazyGit](https://github.com/jesseduffield/lazygit) - 高機能Git UIツール
- [OpenAI](https://openai.com/) - GPT API
- [Anthropic](https://www.anthropic.com/) - Claude API
- [Google](https://ai.google.dev/) - Gemini API

## 🤝 コントリビューション

- **Issues**: GitHubのIssuesで不具合報告や機能要望
- **Discussions**: 一般的な質問や議論
- **Wiki**: 詳細なドキュメントと情報

## 🎯 ロードマップ

- [ ] 🌐 Webインターフェース版の開発
- [ ] 📱 モバイルアプリ対応
- [ ] 🔄 自動コミット機能
- [ ] 📊 使用統計とレポート機能
- [ ] 🎨 カスタムテーマ対応

---

### Happy coding with AI-powered commit messages! 🚀✨
