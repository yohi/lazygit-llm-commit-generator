# 📚 APIリファレンス

LazyGit LLM Commit Generatorの内部APIとクラス構造のリファレンスです。

## 🏗️ アーキテクチャ概要

```
lazygit-llm/
├── src/
│   ├── main.py                 # エントリーポイント
│   ├── base_provider.py        # プロバイダー基底クラス
│   ├── config_manager.py       # 設定管理
│   ├── git_processor.py        # Git差分処理
│   ├── message_formatter.py    # メッセージフォーマット
│   ├── provider_factory.py     # プロバイダーファクトリ
│   ├── error_handler.py        # エラーハンドリング
│   ├── security_validator.py   # セキュリティ検証
│   ├── api_providers/          # API型プロバイダー
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   └── gemini_api_provider.py
│   └── cli_providers/          # CLI型プロバイダー
│       ├── gemini_cli_provider.py
│       └── claude_code_provider.py
```

## 🔧 コアクラス

### BaseProvider

すべてのLLMプロバイダーの基底抽象クラス

```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseProvider(ABC):
    """LLMプロバイダーの基底クラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        プロバイダーを初期化

        Args:
            config: プロバイダー設定辞書
        """

    @abstractmethod
    def generate_commit_message(self, diff: str) -> str:
        """
        Git差分からコミットメッセージを生成

        Args:
            diff: Git差分文字列

        Returns:
            生成されたコミットメッセージ

        Raises:
            ProviderError: 生成に失敗した場合
        """

    @abstractmethod
    def test_connection(self) -> bool:
        """
        プロバイダーへの接続をテスト

        Returns:
            接続成功の場合True
        """

    @abstractmethod
    def supports_streaming(self) -> bool:
        """
        ストリーミング対応状況を返す

        Returns:
            ストリーミング対応の場合True
        """
```

### ConfigManager

設定ファイルの読み込み・管理クラス

```python
class ConfigManager:
    """設定管理クラス"""

    def __init__(self):
        """設定マネージャーを初期化"""

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        設定ファイルを読み込み

        Args:
            config_path: 設定ファイルのパス

        Returns:
            読み込まれた設定データ

        Raises:
            ConfigError: 設定ファイルの読み込みまたは解析に失敗
        """

    def get_api_key(self, provider: str) -> str:
        """
        指定されたプロバイダーのAPIキーを取得

        Args:
            provider: プロバイダー名

        Returns:
            APIキー

        Raises:
            ConfigError: APIキーが見つからない場合
        """

    def get_model_name(self, provider: str) -> str:
        """
        指定されたプロバイダーのモデル名を取得

        Args:
            provider: プロバイダー名

        Returns:
            モデル名
        """

    def get_prompt_template(self) -> str:
        """
        プロンプトテンプレートを取得

        Returns:
            プロンプトテンプレート
        """

    def get_provider_config(self) -> ProviderConfig:
        """
        プロバイダー設定オブジェクトを取得

        Returns:
            プロバイダー設定
        """

    def validate_config(self) -> bool:
        """
        設定を検証

        Returns:
            設定が有効な場合True
        """
```

### GitDiffProcessor

Git差分の処理・解析クラス

```python
@dataclass
class DiffData:
    """Git差分データの構造化表現"""
    raw_diff: str
    file_count: int
    additions: int
    deletions: int
    files_changed: List[str]
    is_binary_change: bool
    total_lines: int

class GitDiffProcessor:
    """Git差分処理クラス"""

    def __init__(self, max_diff_size: int = 50000):
        """
        Git差分プロセッサーを初期化

        Args:
            max_diff_size: 処理する差分の最大サイズ（バイト）
        """

    def read_staged_diff(self) -> str:
        """
        標準入力からステージされた変更の差分を読み取り

        Returns:
            読み取られた差分データ

        Raises:
            GitError: 差分の読み取りに失敗した場合
        """

    def has_staged_changes(self) -> bool:
        """
        ステージされた変更があるかどうかを確認

        Returns:
            ステージされた変更がある場合True
        """

    def format_diff_for_llm(self, diff: str) -> str:
        """
        差分データをLLM向けにフォーマット

        Args:
            diff: 元の差分データ

        Returns:
            LLM向けにフォーマットされた差分データ
        """

    def get_diff_stats(self) -> Dict[str, Any]:
        """
        キャッシュされた差分統計情報を取得

        Returns:
            差分統計情報の辞書
        """

    def validate_diff_format(self, diff: str) -> bool:
        """
        差分フォーマットの妥当性を検証

        Args:
            diff: 検証する差分

        Returns:
            フォーマットが有効な場合True
        """
```

### ProviderFactory

プロバイダーの動的生成・管理クラス

```python
class ProviderRegistry:
    """プロバイダー登録システム"""

    def register_provider(self, name: str, provider_class: type, provider_type: str):
        """
        プロバイダーを登録

        Args:
            name: プロバイダー名
            provider_class: プロバイダークラス
            provider_type: プロバイダータイプ（'api' または 'cli'）
        """

    def get_provider_class(self, name: str) -> Optional[type]:
        """
        プロバイダークラスを取得

        Args:
            name: プロバイダー名

        Returns:
            プロバイダークラス、見つからない場合None
        """

class ProviderFactory:
    """プロバイダーファクトリクラス"""

    def __init__(self):
        """ファクトリを初期化"""

    def create_provider(self, config: ProviderConfig) -> BaseProvider:
        """
        設定に基づいてプロバイダーを作成

        Args:
            config: プロバイダー設定

        Returns:
            作成されたプロバイダーインスタンス

        Raises:
            ProviderError: プロバイダーの作成に失敗した場合
        """

    def get_available_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        利用可能なプロバイダー一覧を取得

        Returns:
            プロバイダー情報の辞書
        """

    def test_provider_connection(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """
        プロバイダーの接続をテスト

        Args:
            provider_name: プロバイダー名
            config: 設定辞書

        Returns:
            接続成功の場合True
        """
```

## 🤖 プロバイダークラス

### OpenAIProvider

```python
class OpenAIProvider(BaseProvider):
    """OpenAI GPT プロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        """
        OpenAIプロバイダーを初期化

        Args:
            config: OpenAI設定（api_key, model_name等）
        """

    def generate_commit_message(self, diff: str) -> str:
        """
        OpenAI APIを使用してコミットメッセージを生成

        Args:
            diff: Git差分

        Returns:
            生成されたコミットメッセージ
        """

    def test_connection(self) -> bool:
        """OpenAI APIへの接続をテスト"""

    def supports_streaming(self) -> bool:
        """ストリーミング対応（True）"""
```

### AnthropicProvider

```python
class AnthropicProvider(BaseProvider):
    """Anthropic Claude プロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        """
        Anthropicプロバイダーを初期化

        Args:
            config: Anthropic設定（api_key, model_name等）
        """

    def generate_commit_message(self, diff: str) -> str:
        """
        Anthropic APIを使用してコミットメッセージを生成

        Args:
            diff: Git差分

        Returns:
            生成されたコミットメッセージ
        """

    def test_connection(self) -> bool:
        """Anthropic APIへの接続をテスト"""

    def supports_streaming(self) -> bool:
        """ストリーミング対応（True）"""
```

### GeminiAPIProvider

```python
class GeminiAPIProvider(BaseProvider):
    """Google Gemini API プロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        """
        Gemini APIプロバイダーを初期化

        Args:
            config: Gemini設定（api_key, model_name等）
        """

    def generate_commit_message(self, diff: str) -> str:
        """
        Gemini APIを使用してコミットメッセージを生成

        Args:
            diff: Git差分

        Returns:
            生成されたコミットメッセージ
        """

    def test_connection(self) -> bool:
        """Gemini APIへの接続をテスト"""

    def supports_streaming(self) -> bool:
        """ストリーミング対応（True）"""
```

### GeminiCLIProvider

```python
class GeminiCLIProvider(BaseProvider):
    """Google Gemini CLI プロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        """
        Gemini CLIプロバイダーを初期化

        Args:
            config: CLI設定（model_name等）
        """

    def generate_commit_message(self, diff: str) -> str:
        """
        gcloud CLIを使用してコミットメッセージを生成

        Args:
            diff: Git差分

        Returns:
            生成されたコミットメッセージ
        """

    def test_connection(self) -> bool:
        """gcloud CLIの利用可能性をテスト"""

    def supports_streaming(self) -> bool:
        """ストリーミング非対応（False）"""
```

### ClaudeCodeProvider

```python
class ClaudeCodeProvider(BaseProvider):
    """Claude Code CLI プロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        """
        Claude Code CLIプロバイダーを初期化

        Args:
            config: CLI設定（model_name等）
        """

    def generate_commit_message(self, diff: str) -> str:
        """
        claude-code CLIを使用してコミットメッセージを生成

        Args:
            diff: Git差分

        Returns:
            生成されたコミットメッセージ
        """

    def test_connection(self) -> bool:
        """claude-code CLIの利用可能性をテスト"""

    def supports_streaming(self) -> bool:
        """ストリーミング非対応（False）"""
```

## 🛡️ セキュリティクラス

### SecurityValidator

```python
@dataclass
class ValidationResult:
    """バリデーション結果"""
    is_valid: bool
    level: str  # "info", "warning", "danger"
    message: str
    recommendations: List[str]

class SecurityValidator:
    """セキュリティ検証クラス"""

    def __init__(self):
        """セキュリティバリデーターを初期化"""

    def validate_api_key(self, provider: str, api_key: str) -> ValidationResult:
        """
        APIキーの形式を検証（内容は露出させない）

        Args:
            provider: プロバイダー名
            api_key: 検証するAPIキー

        Returns:
            検証結果
        """

    def sanitize_git_diff(self, diff_content: str) -> Tuple[str, ValidationResult]:
        """
        Git差分をサニタイゼーション

        Args:
            diff_content: 元の差分内容

        Returns:
            (サニタイゼーション済み差分, 検証結果)
        """

    def check_file_permissions(self, file_path: str) -> ValidationResult:
        """
        ファイル権限をチェック

        Args:
            file_path: チェックするファイルパス

        Returns:
            権限チェック結果
        """

    def validate_input_size(self, content: str, max_size: int = 100000) -> ValidationResult:
        """
        入力サイズを検証

        Args:
            content: 検証する内容
            max_size: 最大サイズ（バイト）

        Returns:
            サイズ検証結果
        """
```

## 🔧 ユーティリティクラス

### MessageFormatter

```python
class MessageFormatter:
    """メッセージフォーマッタークラス"""

    def __init__(self, max_length: int = 500):
        """
        フォーマッターを初期化

        Args:
            max_length: メッセージの最大長
        """

    def clean_llm_response(self, response: str) -> str:
        """
        LLMレスポンスをクリーニング

        Args:
            response: 元のLLMレスポンス

        Returns:
            クリーニング済みメッセージ
        """

    def format_for_lazygit(self, message: str) -> str:
        """
        LazyGit向けにメッセージをフォーマット

        Args:
            message: フォーマットするメッセージ

        Returns:
            LazyGit互換フォーマット
        """

    def validate_commit_message(self, message: str) -> bool:
        """
        コミットメッセージの妥当性を検証

        Args:
            message: 検証するメッセージ

        Returns:
            有効な場合True
        """
```

### ErrorHandler

```python
@dataclass
class ErrorInfo:
    """エラー情報"""
    category: str
    severity: str
    message: str
    suggestions: List[str]
    context: Dict[str, Any]

class ErrorHandler:
    """エラーハンドリングクラス"""

    def __init__(self, verbose: bool = False):
        """
        エラーハンドラーを初期化

        Args:
            verbose: 詳細ログの有効/無効
        """

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """
        エラーを分類して処理

        Args:
            error: 発生したエラー
            context: エラーコンテキスト

        Returns:
            エラー情報
        """

    def get_user_friendly_message(self, error_info: ErrorInfo) -> str:
        """
        ユーザーフレンドリーなエラーメッセージを生成

        Args:
            error_info: エラー情報

        Returns:
            ユーザー向けメッセージ
        """

    def log_error(self, error_info: ErrorInfo):
        """
        エラーをログに記録

        Args:
            error_info: ログするエラー情報
        """
```

## 🔧 例外クラス

```python
class LazygitLLMError(Exception):
    """基底例外クラス"""
    pass

class ConfigError(LazygitLLMError):
    """設定関連エラー"""
    pass

class GitError(LazygitLLMError):
    """Git処理関連エラー"""
    pass

class ProviderError(LazygitLLMError):
    """プロバイダー関連エラー"""
    pass

class AuthenticationError(ProviderError):
    """認証エラー"""
    pass

class TimeoutError(ProviderError):
    """タイムアウトエラー"""
    pass

class ResponseError(ProviderError):
    """レスポンスエラー"""
    pass

class SecurityError(LazygitLLMError):
    """セキュリティエラー"""
    pass
```

## 🚀 使用例

### 基本的な使用例

```python
from lazygit_llm.src.config_manager import ConfigManager
from lazygit_llm.src.provider_factory import ProviderFactory
from lazygit_llm.src.git_processor import GitDiffProcessor

# 設定読み込み
config_manager = ConfigManager()
config_manager.load_config("~/.config/lazygit-llm/config.yml")

# プロバイダー作成
factory = ProviderFactory()
provider_config = config_manager.get_provider_config()
provider = factory.create_provider(provider_config)

# Git差分処理
processor = GitDiffProcessor()
diff = processor.read_staged_diff()

# コミットメッセージ生成
message = provider.generate_commit_message(diff)
print(message)
```

### カスタムプロバイダーの作成

```python
from lazygit_llm.src.base_provider import BaseProvider

class CustomProvider(BaseProvider):
    """カスタムLLMプロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # カスタム初期化処理

    def generate_commit_message(self, diff: str) -> str:
        # カスタム生成ロジック
        return "Custom generated message"

    def test_connection(self) -> bool:
        # カスタム接続テスト
        return True

    def supports_streaming(self) -> bool:
        return False

# プロバイダー登録
from lazygit_llm.src.provider_factory import ProviderFactory
factory = ProviderFactory()
factory.register_provider("custom", CustomProvider)
```

### エラーハンドリング例

```python
from lazygit_llm.src.error_handler import ErrorHandler
from lazygit_llm.src.base_provider import ProviderError

error_handler = ErrorHandler(verbose=True)

try:
    # 何らかの処理
    provider.generate_commit_message(diff)
except ProviderError as e:
    error_info = error_handler.handle_error(e, {"provider": "openai"})
    user_message = error_handler.get_user_friendly_message(error_info)
    print(f"エラー: {user_message}")

    # 解決策の提示
    for suggestion in error_info.suggestions:
        print(f"解決策: {suggestion}")
```

---

このAPIリファレンスは開発者がシステムを拡張・カスタマイズする際の参考資料として活用してください。