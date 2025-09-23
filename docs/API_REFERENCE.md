# LazyGit LLM Commit Generator - API仕様書

## 概要

LazyGit LLM Commit Generatorは、複数のLLMプロバイダーに対応したコミットメッセージ生成ツールです。プラグインアーキテクチャにより、API系およびCLI系の様々なLLMサービスを統一的に利用できます。

## アーキテクチャ

### プロバイダーシステム

```text
BaseProvider (ABC)
├── API Providers
│   ├── OpenAIProvider    # OpenAI GPT API
│   ├── AnthropicProvider # Anthropic Claude API
│   └── GeminiAPIProvider # Google Gemini API
└── CLI Providers
    ├── ClaudeCodeProvider # Claude Code CLI
    └── GeminiCLIProvider  # Google Gemini CLI (gcloud)
```

## コアクラス

### BaseProvider

**場所**: `lazygit_llm/base_provider.py`

全てのLLMプロバイダーが実装すべき抽象基底クラス。

#### メソッド

##### `generate_commit_message(diff: str, prompt_template: str) -> str`

**概要**: Git差分からコミットメッセージを生成する抽象メソッド

**パラメータ**:
- `diff` (str): `git diff --staged`の出力
- `prompt_template` (str): LLMに送信するプロンプトテンプレート

**戻り値**: 生成されたコミットメッセージ

**例外**:
- `ProviderError`: プロバイダー固有のエラー
- `AuthenticationError`: 認証失敗
- `ProviderTimeoutError`: タイムアウト
- `ResponseError`: レスポンス解析エラー

##### `test_connection() -> bool`

**概要**: プロバイダーへの接続をテストする抽象メソッド

**戻り値**: 接続成功時True

## プロバイダー仕様

### OpenAIProvider

**場所**: `src/api_providers/openai_provider.py`

#### 設定例
```yaml
provider: "openai"
model_name: "gpt-4"  # gpt-4, gpt-3.5-turbo
api_key: "${OPENAI_API_KEY}"
additional_params:
  temperature: 0.3
  top_p: 1.0
```

#### サポートモデル
- GPT-4 (推奨)
- GPT-3.5-turbo
- その他OpenAI Chat Completions API対応モデル

#### 機能
- ✅ ストリーミング対応
- ✅ 自動リトライ機能
- ✅ レート制限対応

### AnthropicProvider

**場所**: `src/api_providers/anthropic_provider.py`

#### 設定例
```yaml
provider: "anthropic"
model_name: "claude-3-5-sonnet-20241022"
api_key: "${ANTHROPIC_API_KEY}"
additional_params:
  max_tokens_to_sample: 100
```

#### サポートモデル
- Claude 3.5 Sonnet (推奨)
- Claude 3 Opus
- Claude 3 Haiku

### GeminiAPIProvider

**場所**: `src/api_providers/gemini_api_provider.py`

#### 設定例
```yaml
provider: "gemini-api"
model_name: "gemini-1.5-pro"
api_key: "${GOOGLE_API_KEY}"
additional_params:
  safety_settings:
    - category: "HARM_CATEGORY_DANGEROUS_CONTENT"
      threshold: "BLOCK_MEDIUM_AND_ABOVE"
```

### ClaudeCodeProvider

**場所**: `src/cli_providers/claude_code_provider.py`

#### 設定例
```yaml
provider: "claude-code"
model_name: "claude-3-5-sonnet-20241022"
# CLIプロバイダーではapi_keyは不要
```

### GeminiCLIProvider

**場所**: `src/cli_providers/gemini_cli_provider.py`

#### 設定例
```yaml
provider: "gemini-cli"
model_name: "gemini-1.5-pro"
additional_params:
  project_id: "your-gcp-project-id"
  location: "us-central1"
```

## コアモジュール

### ConfigManager

**場所**: `lazygit_llm/config_manager.py`

YAML設定ファイルの管理、環境変数展開、セキュリティ検証を担当。

#### 主要メソッド

##### `load_config(config_path: str) -> None`
設定ファイルを読み込み、環境変数を展開

##### `validate_config() -> bool`
設定の妥当性を検証

##### `get_prompt_template() -> str`
プロンプトテンプレートを取得

### GitDiffProcessor

**場所**: `lazygit_llm/git_processor.py`

Git操作とdiff取得を担当。

#### 主要メソッド

##### `has_staged_changes() -> bool`
ステージ済み変更の有無を確認

##### `read_staged_diff() -> str`
ステージ済み差分を取得

### ProviderFactory

**場所**: `lazygit_llm/provider_factory.py`

設定に基づいてプロバイダーインスタンスを作成。

#### 主要メソッド

##### `create_provider(config: Dict[str, Any]) -> BaseProvider`
設定に基づいてプロバイダーを作成

### MessageFormatter

**場所**: `lazygit_llm/message_formatter.py`

LLMレスポンスの整形とクリーンアップを担当。

#### 主要メソッド

##### `format_response(raw_message: str) -> str`
生のLLMレスポンスを整形

## エラーハンドリング

### 例外階層

```text
Exception
└── ProviderError (基底例外)
    ├── AuthenticationError  # 認証エラー
    ├── ProviderTimeoutError # タイムアウト
    └── ResponseError        # レスポンス解析エラー
```

### エラー処理パターン

```python
try:
    provider = factory.create_provider(config)
    message = provider.generate_commit_message(diff, template)
except AuthenticationError:
    # APIキー確認を促す
except ProviderTimeoutError:
    # ネットワーク接続確認を促す
except ProviderError as e:
    # 一般的なプロバイダーエラー
```

## 設定ファイル仕様

### 基本構造

```yaml
# プロバイダー指定 (必須)
provider: "openai"  # openai, anthropic, gemini-api, gemini-cli, claude-code

# モデル名 (必須)
model_name: "gpt-4"

# APIキー (API系プロバイダーのみ必須)
api_key: "${OPENAI_API_KEY}"

# プロンプトテンプレート (必須)
prompt_template: |
  Based on the following git diff, generate a concise commit message:

  {diff}

  Generate only the commit message, no additional text.

# タイムアウト設定 (オプション)
timeout: 30

# 最大トークン数 (オプション)
max_tokens: 100

# プロバイダー固有パラメータ (オプション)
additional_params:
  temperature: 0.3
  top_p: 1.0
```

### 環境変数

API認証には環境変数の使用を推奨：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."
```

## CLIインターフェース

### メインコマンド

```bash
lazygit-llm-generate [OPTIONS]
```

#### オプション

- `--config, -c`: 設定ファイルパス (デフォルト: config/config.yml)
- `--verbose, -v`: 詳細ログ出力
- `--test-config`: 設定テストモード
- `--version`: バージョン表示

### LazyGit統合

```yaml
# ~/.config/lazygit/config.yml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

## セキュリティ考慮事項

### 1. APIキー管理
- 設定ファイルに平文でAPIキーを記載しない
- 環境変数による外部化を推奨
- 設定ファイルの適切な権限設定 (600)

### 2. 入力検証
- Git diff内容のサニタイゼーション
- 不正なプロンプトインジェクション対策
- ファイルパスの検証

### 3. ログ管理
- 一時ファイルによる安全なログ保存
- 機密情報の自動マスキング
- 適切なログローテーション

## 拡張方法

### 新しいプロバイダーの追加

1. **BaseProviderを継承**したクラスを作成
2. 必要メソッドを実装
3. プロバイダーファクトリーに登録
4. 設定例とドキュメントを追加

### 例: カスタムプロバイダー

```python
from lazygit_llm.base_provider import BaseProvider

class CustomProvider(BaseProvider):
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        # カスタム実装
        pass

    def test_connection(self) -> bool:
        # 接続テスト実装
        pass
```

## パフォーマンス考慮事項

### レスポンス時間
- API系: 通常2-10秒
- CLI系: 初回起動時に追加時間

### リトライ戦略
- 指数バックオフによる自動リトライ
- 最大3回まで再試行
- ネットワークエラー時の適切な待機

### キャッシュ戦略
- 設定ファイルの変更監視
- プロバイダーインスタンスの再利用
- Git diff結果の一時キャッシュ

## トラブルシューティング

### よくある問題

#### 1. 認証エラー
```text
❌ 認証エラー: APIキーを確認してください
```
**解決方法**: 環境変数のAPIキーを確認

#### 2. タイムアウト
```text
❌ タイムアウト: ネットワーク接続を確認してください
```
**解決方法**: ネットワーク接続とtimeout設定を確認

#### 3. プロバイダーエラー
```text
❌ プロバイダーエラー: 利用制限に達しました
```
**解決方法**: APIの利用制限とクレジット残高を確認

### デバッグモード

```bash
lazygit-llm-generate --verbose
```

詳細ログが一時ファイルに出力され、問題の特定が容易になります。