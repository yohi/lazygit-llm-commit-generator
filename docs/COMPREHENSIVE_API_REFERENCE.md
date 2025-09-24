# LazyGit LLM Commit Generator - 包括的API仕様書

## 概要

LazyGit LLM Commit Generatorは、Git差分からLLM（Large Language Model）を使用してコミットメッセージを自動生成するPythonツールです。プラグインベースのアーキテクチャを採用し、複数のLLMプロバイダーに対応しています。

## アーキテクチャ概要

```text
main.py → ConfigManager → ProviderFactory → Provider (API/CLI)
    ↓           ↓              ↓               ↓
GitProcessor → Config Load → Provider Create → Message Generate
    ↓
MessageFormatter → Output
```

## コアコンポーネント

### 1. main.py - エントリーポイント

**責任**: アプリケーションの起動、引数解析、全体的な制御フロー

#### 主要関数

##### `setup_logging(verbose: bool = False) -> None`
ログ設定を初期化します。

**パラメータ**:
- `verbose`: 詳細ログ出力の有効化

**機能**:
- ログレベルの設定（INFO/DEBUG）
- ファイルとコンソール出力の設定
- ログフォーマットの統一

##### `parse_arguments() -> argparse.Namespace`
コマンドライン引数を解析します。

**戻り値**: 解析された引数のNamespace

**サポートする引数**:
- `--config`: 設定ファイルパス
- `--verbose`: 詳細ログ出力
- `--test-config`: 設定テストモード

##### `test_configuration(config_manager: ConfigManager) -> bool`
設定の妥当性をテストします。

**パラメータ**:
- `config_manager`: 設定管理インスタンス

**戻り値**: テスト成功時True

**テスト項目**:
- 設定ファイルの読み込み
- プロバイダーの接続テスト
- 環境変数の検証

##### `main() -> int`
メインエントリーポイント。

**戻り値**: 終了コード（0: 成功, 1: エラー）

**処理フロー**:
1. 引数解析とログ設定
2. 設定管理インスタンス作成
3. Git差分の読み込み
4. プロバイダー作成と実行
5. 結果の出力とエラーハンドリング

### 2. ConfigManager - 設定管理

**責任**: YAML設定ファイルの読み込み、環境変数の展開、設定検証

#### クラス設計

##### `ProviderConfig`
```python
@dataclass
class ProviderConfig:
    provider: str
    model_name: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_tokens: int = 100
    prompt_template: str = "..."
    additional_params: Dict[str, Any] = field(default_factory=dict)
```

プロバイダー固有の設定を管理するデータクラス。

##### `ConfigError(Exception)`
設定関連のエラーを表す例外クラス。

##### `ConfigManager`

**主要メソッド**:

###### `__init__(config_path: Optional[str] = None)`
設定管理インスタンスを初期化。

**パラメータ**:
- `config_path`: 設定ファイルパス（省略時はデフォルト検索）

###### `load_config() -> ProviderConfig`
設定を読み込み、ProviderConfigインスタンスを返す。

**機能**:
- YAML設定ファイルの読み込み
- 環境変数の展開（`${VAR_NAME}`形式）
- デフォルト値の適用
- 設定値の検証

**例外**:
- `ConfigError`: 設定ファイルが見つからない、形式エラーなど

###### `validate_config(config: ProviderConfig) -> bool`
設定の妥当性を検証。

**検証項目**:
- 必須パラメータの存在確認
- プロバイダー名の有効性
- APIキーの形式確認
- タイムアウト値の範囲確認

###### `expand_environment_variables(value: str) -> str`
文字列内の環境変数を展開。

**対応形式**:
- `${VAR_NAME}`: 環境変数の値に置換
- `${VAR_NAME:default}`: デフォルト値付き展開

### 3. ProviderFactory - プロバイダー作成

**責任**: 設定に基づいたプロバイダーインスタンスの動的作成

#### `ProviderFactory`

##### `create_provider(config: ProviderConfig) -> BaseProvider`
設定に基づいてプロバイダーインスタンスを作成。

**パラメータ**:
- `config`: プロバイダー設定

**戻り値**: BaseProviderを継承したプロバイダーインスタンス

**対応プロバイダー**:
- `openai`: OpenAI GPT
- `anthropic`: Anthropic Claude
- `gemini`: Google Gemini API
- `gcloud`: Google Gemini CLI (gcloud)
- `gemini-cli`: Google Gemini CLI (直接geminiコマンド)
- `claude-code`: Claude Code CLI

**動的インポート**:
- API プロバイダー: `src.api_providers`から動的インポート
- CLI プロバイダー: `lazygit_llm.cli_providers`から動的インポート

### 4. GitDiffProcessor - Git操作

**責任**: Git差分の取得、処理、検証

#### データクラス

##### `DiffData`
```python
@dataclass
class DiffData:
    raw_diff: str
    file_count: int
    line_additions: int
    line_deletions: int
    is_binary: bool = False
    size_bytes: int = 0
```

Git差分の構造化データを表現。

#### 例外クラス

##### `GitError(Exception)`
Git操作関連のエラーを表す例外。

#### `GitDiffProcessor`

##### `get_staged_diff() -> DiffData`
ステージされた変更の差分を取得。

**実行コマンド**: `git diff --staged`

**戻り値**: DiffData インスタンス

**機能**:
- Git差分の取得と解析
- ファイル数、追加行数、削除行数の算出
- バイナリファイルの検出
- 差分サイズの計算

##### `validate_diff(diff_data: DiffData) -> bool`
差分データの妥当性を検証。

**検証項目**:
- 空の差分チェック
- サイズ制限チェック（デフォルト: 50KB）
- バイナリファイル除外
- ファイル数制限

##### `sanitize_diff(raw_diff: str) -> str`
差分データのサニタイゼーション。

**処理内容**:
- 機密情報のマスキング
- 制御文字の除去
- 不正な文字エンコーディングの修正

## プロバイダー実装

### BaseProvider - 抽象基底クラス

**責任**: 全プロバイダーの共通インターフェースと基本機能

#### 抽象メソッド

##### `generate_commit_message(diff: str, prompt_template: str) -> str`
Git差分からコミットメッセージを生成。

**パラメータ**:
- `diff`: Git差分文字列
- `prompt_template`: プロンプトテンプレート

**戻り値**: 生成されたコミットメッセージ

##### `test_connection() -> bool`
プロバイダーへの接続テスト。

**戻り値**: 接続成功時True

#### 共通プロパティ

- `provider_name`: プロバイダー名
- `model_name`: 使用モデル名
- `timeout`: タイムアウト秒数
- `max_tokens`: 最大トークン数

### API型プロバイダー

#### OpenAI Provider (`src/api_providers/openai_provider.py`)

**特徴**:
- OpenAI GPT-4, GPT-3.5-turbo対応
- HTTP API経由でのリクエスト
- ストリーミング対応

**主要メソッド**:
- `_make_api_request(prompt: str) -> str`
- `_handle_rate_limit() -> None`

#### Anthropic Provider (`src/api_providers/anthropic_provider.py`)

**特徴**:
- Claude-3.5 Sonnet, Opus, Haiku対応
- Messages API使用
- 会話履歴管理

#### Gemini API Provider (`src/api_providers/gemini_api_provider.py`)

**特徴**:
- Gemini-1.5 Pro, Flash対応
- Google Generative AI SDK使用
- 安全性フィルター設定

### CLI型プロバイダー

#### Claude Code Provider (`lazygit_llm/cli_providers/claude_code_provider.py`)

**特徴**:
- claude-codeコマンド統合
- 動的フラグ検出
- セキュアなsubprocess実行

**セキュリティ機能**:
- バイナリパスの検証
- 入力サニタイゼーション
- 環境変数の制限
- shell=False強制

**主要メソッド**:
- `_detect_binary_and_build_args() -> List[str]`
- `_execute_claude_code_command(prompt: str) -> str`
- `_verify_binary_security(binary_path: str) -> None`

#### Gemini CLI Provider (`lazygit_llm/cli_providers/gemini_cli_provider.py`)

**特徴**:
- gcloud CLIとの統合
- 認証状態の確認
- プロジェクト設定の管理

## セキュリティ機能

### SecurityValidator (`src/security_validator.py`)

**責任**: 入力データの検証とサニタイゼーション

#### 主要機能

##### `validate_diff(diff_content: str) -> bool`
Git差分の安全性を検証。

**検証項目**:
- サイズ制限（50KB）
- 機密情報の検出（APIキー、パスワード）
- 不正文字の検出

##### `sanitize_prompt(prompt: str) -> str`
プロンプトの安全化。

**処理内容**:
- SQLインジェクション対策
- スクリプトインジェクション対策
- 制御文字の除去

### ErrorHandler (`src/error_handler.py`)

**責任**: 統一的なエラーハンドリングとログ管理

#### 例外階層

```text
Exception
├── ProviderError              # プロバイダー基底例外
│   ├── AuthenticationError    # 認証失敗
│   ├── ProviderTimeoutError   # タイムアウト
│   ├── ResponseError          # レスポンスエラー
│   └── RateLimitError         # レート制限
├── ConfigError                # 設定エラー
└── GitError                   # Git操作エラー
```

#### 機能

##### `handle_provider_error(error: Exception) -> str`
プロバイダーエラーの統一処理。

##### `log_error_with_context(error: Exception, context: Dict) -> None`
コンテキスト付きエラーログ出力。

## テスト戦略

### テストマーカー

- `unit`: 単体テスト - 個別コンポーネントのテスト
- `integration`: 統合テスト - エンドツーエンドのプロバイダーテスト
- `performance`: パフォーマンステスト - レスポンス時間とリソース使用量
- `slow`: 低速テスト - 除外可能な時間のかかるテスト

### Mock戦略

#### API プロバイダー
- `responses`ライブラリでHTTPリクエストをモック
- レート制限とタイムアウトのシミュレーション

#### CLI プロバイダー
- `subprocess.run`のモック
- コマンド実行結果のシミュレーション

### テストケース例

```python
@pytest.mark.unit
def test_config_validation():
    """設定検証のテスト"""

@pytest.mark.integration
def test_openai_provider_end_to_end():
    """OpenAIプロバイダーの統合テスト"""

@pytest.mark.performance
def test_provider_response_time():
    """レスポンス時間のテスト"""
```

## LazyGit統合

### カスタムコマンド設定

```yaml
# ~/.config/lazygit/config.yml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

### 統合フロー

1. ユーザーがCtrl+Gを押下
2. LazyGitがlazygit-llm-generateを実行
3. ツールがgit diff --stagedを取得
4. LLMでコミットメッセージ生成
5. LazyGitに結果を返却
6. ユーザーが確認・編集

## 設定例

### 基本設定

```yaml
# ~/.config/lazygit-llm/config.yml
provider: "openai"
api_key: "${OPENAI_API_KEY}"
model_name: "gpt-4"
timeout: 30
max_tokens: 100

prompt_template: |
  Based on the following git diff, generate a concise commit message
  that follows conventional commits format:

  {diff}

  Generate only the commit message, no additional text.

additional_params:
  temperature: 0.3
  top_p: 0.9
```

### 多言語対応

```yaml
# 日本語コミットメッセージ
prompt_template: |
  以下のgit diffに基づいて、簡潔で分かりやすいコミットメッセージを日本語で生成してください：

  {diff}

  コミットメッセージのみを出力してください。
```

## パフォーマンス最適化

### 推奨設定

```yaml
# レスポンス時間優先
timeout: 15
max_tokens: 50
additional_params:
  temperature: 0.1
  stream: true
```

### 使用量制限

- 50KB以下の差分サイズを推奨
- プロバイダーごとの利用制限を確認
- 200回/時間程度の利用を推奨

## トラブルシューティング

### よくあるエラー

#### 認証エラー
```
ConfigError: API認証に失敗しました
```
**解決方法**: 環境変数のAPIキーを確認

#### タイムアウトエラー
```
ProviderTimeoutError: リクエストがタイムアウトしました
```
**解決方法**: timeout設定の調整

#### レート制限エラー
```
RateLimitError: API利用制限に達しました
```
**解決方法**: 使用頻度の調整、プロバイダー変更

### デバッグ手順

1. 詳細ログで実行
```bash
uv run lazygit-llm-generate --verbose
```

2. 設定テスト
```bash
uv run lazygit-llm-generate --test-config
```

3. ログファイル確認
```bash
tail -f /tmp/lazygit-llm-*.log
```

## 開発・拡張

### 新プロバイダーの追加

1. BaseProviderを継承したクラス作成
2. provider_factory.pyに登録
3. 設定項目の追加
4. テストの作成
5. ドキュメントの更新

### 設定項目の追加

1. ProviderConfigにフィールド追加
2. デフォルト値の設定
3. 検証ロジックの追加
4. ドキュメントの更新

---

## メタ情報

- **ドキュメント**: LazyGit LLM Commit Generator - 包括的API仕様書
- **バージョン**: 1.0.0
- **対象システム**: LazyGit LLM Commit Generator
- **最終更新**: 2024年12月

このAPI仕様書は、LazyGit LLM Commit Generatorの全機能を網羅し、開発者がシステムを理解し、拡張するための包括的なガイドです。
