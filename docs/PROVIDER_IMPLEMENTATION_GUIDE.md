# プロバイダー実装ガイド

## 概要

LazyGit LLM Commit Generatorは、プラグインベースのアーキテクチャを採用し、新しいLLMプロバイダーを簡単に追加できるように設計されています。このガイドでは、新しいプロバイダーの実装方法について詳細に説明します。

## プロバイダー種別

### API型プロバイダー

HTTP API経由でLLMサービスにアクセスするプロバイダー。

**特徴**:
- RESTful API通信
- JSONペイロード
- API キー認証
- レート制限対応

**配置場所**: `src/api_providers/`

### CLI型プロバイダー

コマンドライン経由でLLMツールにアクセスするプロバイダー。

**特徴**:
- subprocess実行
- stdin/stdout通信
- バイナリ依存
- セキュリティ考慮事項

**配置場所**: `lazygit_llm/cli_providers/`

## BaseProvider抽象クラス

すべてのプロバイダーは`BaseProvider`を継承する必要があります。

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseProvider(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.provider_name = config.get('provider', 'unknown')
        self.model_name = config.get('model_name', '')
        self.timeout = config.get('timeout', 30)
        self.max_tokens = config.get('max_tokens', 100)
        self.config = config

    @abstractmethod
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """Git差分からコミットメッセージを生成"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """プロバイダーへの接続テスト"""
        pass

    def validate_config(self) -> bool:
        """設定の検証（オプション）"""
        return True

    def supports_streaming(self) -> bool:
        """ストリーミング出力をサポートするか"""
        return False

    def get_required_config_fields(self) -> list[str]:
        """必須設定項目"""
        return ['model_name']
```

## API型プロバイダーの実装

### 1. 基本構造

```python
# src/api_providers/example_provider.py

import requests
import time
import logging
from typing import Dict, Any, Optional

from lazygit_llm.base_provider import (
    BaseProvider,
    ProviderError,
    AuthenticationError,
    ProviderTimeoutError,
    ResponseError
)

logger = logging.getLogger(__name__)

class ExampleProvider(BaseProvider):
    """Example APIプロバイダーの実装例"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # API固有の設定
        self.api_key = config.get('api_key')
        self.api_base = config.get('api_base', 'https://api.example.com')
        self.temperature = config.get('additional_params', {}).get('temperature', 0.3)

        # HTTPセッションの設定
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'lazygit-llm-commit-generator/1.0.0'
        })

        # 設定検証
        if not self.validate_config():
            raise ProviderError("Example API設定が無効です")

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """コミットメッセージ生成"""
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        prompt = prompt_template.replace('$diff', diff)

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        try:
            start_time = time.time()

            response = self.session.post(
                f"{self.api_base}/chat/completions",
                json=payload,
                timeout=self.timeout
            )

            elapsed_time = time.time() - start_time
            logger.info(f"Example API呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンス処理
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise ProviderTimeoutError("Example APIタイムアウト")
        except requests.exceptions.RequestException as e:
            raise ProviderError(f"Example API呼び出し失敗: {e}")

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            # 簡単なテストリクエスト
            response = self.session.get(
                f"{self.api_base}/models",
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Example API接続テストエラー: {e}")
            return False

    def validate_config(self) -> bool:
        """設定検証"""
        if not self.api_key:
            logger.error("Example API キーが設定されていません")
            return False

        if not self.model_name:
            logger.error("モデル名が設定されていません")
            return False

        return True

    def get_required_config_fields(self) -> list[str]:
        """必須設定項目"""
        return ['api_key', 'model_name']

    def _handle_response(self, response: requests.Response) -> str:
        """レスポンス処理"""
        if response.status_code == 401:
            raise AuthenticationError("Example API認証失敗")
        elif response.status_code == 429:
            raise ProviderError("Example APIレート制限")
        elif response.status_code != 200:
            raise ResponseError(f"Example APIエラー: {response.status_code}")

        try:
            data = response.json()
            message = data['choices'][0]['message']['content']

            if not message or not message.strip():
                raise ResponseError("空のレスポンスを受信")

            return message.strip()

        except (KeyError, IndexError, ValueError) as e:
            raise ResponseError(f"レスポンス解析エラー: {e}")
```

### 2. エラーハンドリング

```python
def _handle_api_errors(self, response: requests.Response) -> None:
    """API固有のエラーハンドリング"""
    if response.status_code == 401:
        raise AuthenticationError("API認証失敗")
    elif response.status_code == 429:
        # レート制限の場合は詳細情報を取得
        retry_after = response.headers.get('Retry-After', '60')
        raise ProviderError(f"レート制限: {retry_after}秒後に再試行")
    elif response.status_code >= 500:
        raise ProviderError("サーバーエラー")
    elif response.status_code >= 400:
        error_msg = response.json().get('error', {}).get('message', 'Unknown error')
        raise ResponseError(f"APIエラー: {error_msg}")
```

### 3. レート制限対応

```python
import time
from functools import wraps

def retry_on_rate_limit(max_retries: int = 3):
    """レート制限時のリトライデコレータ"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(self, *args, **kwargs)
                except ProviderError as e:
                    if "レート制限" in str(e) and attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        logger.warning(f"レート制限によりリトライ: {wait_time}秒待機")
                        time.sleep(wait_time)
                        continue
                    raise
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

class ExampleProvider(BaseProvider):
    @retry_on_rate_limit(max_retries=3)
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        # 実装...
```

## CLI型プロバイダーの実装

### 1. 基本構造

```python
# lazygit_llm/cli_providers/example_cli_provider.py

import subprocess
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List

from lazygit_llm.base_provider import (
    BaseProvider,
    ProviderError,
    AuthenticationError,
    ProviderTimeoutError,
    ResponseError
)

logger = logging.getLogger(__name__)

class ExampleCLIProvider(BaseProvider):
    """Example CLIプロバイダーの実装例"""

    # セキュリティ設定
    ALLOWED_BINARIES = ('example-cli', 'example')
    MAX_STDOUT_SIZE = 1024 * 1024  # 1MB
    MAX_STDERR_SIZE = 512 * 1024   # 512KB

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # CLI固有の設定
        self.cli_timeout = min(config.get('timeout', 30), 300)  # 最大5分
        self.temperature = config.get('additional_params', {}).get('temperature', 0.3)

        # CLIバイナリの検証
        self.cli_path = self._verify_cli_binary()

        logger.info(f"Example CLIプロバイダーを初期化: {self.cli_path}")

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """コミットメッセージ生成"""
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        prompt = prompt_template.replace('$diff', diff)
        sanitized_prompt = self._sanitize_input(prompt)

        # コマンド引数の構築
        cmd_args = self._build_command_args()

        try:
            logger.debug(f"Example CLI実行: {' '.join(cmd_args[:3])}...")

            result = subprocess.run(
                cmd_args,
                input=sanitized_prompt,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=self.cli_timeout,
                env=self._create_safe_environment(),
                shell=False,  # セキュリティ要件
                check=False
            )

            return self._handle_command_result(result)

        except subprocess.TimeoutExpired:
            raise ProviderTimeoutError("Example CLIタイムアウト")
        except Exception as e:
            raise ProviderError(f"Example CLI実行エラー: {e}")

    def test_connection(self) -> bool:
        """接続テスト"""
        try:
            result = subprocess.run(
                [self.cli_path, '--version'],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Example CLI接続テストエラー: {e}")
            return False

    def _verify_cli_binary(self) -> str:
        """CLIバイナリの検証"""
        # PATHから検索
        for binary_name in self.ALLOWED_BINARIES:
            path = shutil.which(binary_name)
            if path and os.access(path, os.X_OK):
                self._verify_binary_security(path)
                return path

        raise ProviderError("Example CLIが見つかりません")

    def _verify_binary_security(self, binary_path: str) -> None:
        """バイナリのセキュリティ検証"""
        # パスの正規化
        resolved_path = Path(binary_path).resolve()

        # 許可されたバイナリ名か確認
        if resolved_path.name not in self.ALLOWED_BINARIES:
            raise ProviderError(f"許可されていないバイナリ: {resolved_path}")

        # 危険なパスの確認
        dangerous_patterns = ['/tmp/', '/var/tmp/']
        for pattern in dangerous_patterns:
            if pattern in str(resolved_path):
                raise ProviderError(f"危険なパス: {resolved_path}")

    def _build_command_args(self) -> List[str]:
        """コマンド引数の構築"""
        cmd_args = [
            self.cli_path,
            'generate',
            '--model', self.model_name,
            '--temperature', str(self.temperature),
            '--non-interactive'
        ]
        return cmd_args

    def _sanitize_input(self, input_text: str) -> str:
        """入力のサニタイゼーション"""
        if not input_text:
            return ""

        # 基本的なサニタイゼーション
        sanitized = input_text.strip()

        # 危険な文字の除去
        dangerous_chars = ['\\x00']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # サイズ制限
        max_size = 50000  # 50KB
        if len(sanitized) > max_size:
            sanitized = sanitized[:max_size]
            logger.warning(f"プロンプトを切り詰め: {len(input_text)} -> {len(sanitized)}")

        return sanitized

    def _create_safe_environment(self) -> Dict[str, str]:
        """安全な環境変数の作成"""
        safe_vars = ['PATH', 'HOME', 'USER', 'LANG']
        safe_env = {}

        for var in safe_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        # CLIツール固有の環境変数
        if 'EXAMPLE_API_KEY' in os.environ:
            safe_env['EXAMPLE_API_KEY'] = os.environ['EXAMPLE_API_KEY']

        return safe_env

    def _handle_command_result(self, result: subprocess.CompletedProcess) -> str:
        """コマンド結果の処理"""
        # 出力サイズの制限
        stdout = self._truncate_output(result.stdout, self.MAX_STDOUT_SIZE)
        stderr = self._truncate_output(result.stderr, self.MAX_STDERR_SIZE)

        # エラーチェック
        if result.returncode != 0:
            error_msg = stderr.strip() or "不明なエラー"

            # 認証エラーの検出
            if any(keyword in error_msg.lower() for keyword in ['auth', 'login', 'unauthorized']):
                raise AuthenticationError(f"Example CLI認証エラー: {error_msg}")

            raise ProviderError(f"Example CLIエラー (code: {result.returncode}): {error_msg}")

        # レスポンスの検証
        response = stdout.strip()
        if not response:
            raise ResponseError("空のレスポンスを受信")

        return response

    def _truncate_output(self, output: str, max_size: int) -> str:
        """出力の切り詰め"""
        if len(output) > max_size:
            truncated = output[:max_size]
            logger.warning(f"出力を切り詰め: {len(output)} -> {len(truncated)}")
            return truncated
        return output
```

### 2. セキュリティ考慮事項

```python
class SecurityMixin:
    """CLIプロバイダー用のセキュリティ機能"""

    def validate_binary_path(self, path: str) -> bool:
        """バイナリパスの検証"""
        # 絶対パスかチェック
        if not os.path.isabs(path):
            return False

        # 実行権限があるかチェック
        if not os.access(path, os.X_OK):
            return False

        # シンボリックリンクの解決と検証
        try:
            real_path = os.path.realpath(path)
            if real_path != path:
                logger.debug(f"シンボリックリンク検出: {path} -> {real_path}")
        except Exception:
            return False

        return True

    def detect_injection_attempts(self, input_text: str) -> bool:
        """インジェクション攻撃の検出"""
        dangerous_patterns = [
            r'[;&|`$]',  # シェルメタ文字
            r'\.\./',    # ディレクトリトラバーサル
            r'<script',  # スクリプトタグ
        ]

        import re
        for pattern in dangerous_patterns:
            if re.search(pattern, input_text, re.IGNORECASE):
                logger.warning(f"危険なパターンを検出: {pattern}")
                return True

        return False
```

## プロバイダーファクトリーへの登録

新しいプロバイダーを作成したら、`ProviderFactory`に登録する必要があります。

```python
# lazygit_llm/provider_factory.py

class ProviderFactory:
    """プロバイダーインスタンスの作成ファクトリー"""

    # プロバイダーマッピング
    PROVIDER_MAP = {
        # 既存プロバイダー
        "openai": ("src.api_providers.openai_provider", "OpenAIProvider"),
        "anthropic": ("src.api_providers.anthropic_provider", "AnthropicProvider"),
        "gemini": ("src.api_providers.gemini_api_provider", "GeminiAPIProvider"),
        "gcloud": ("lazygit_llm.cli_providers.gemini_cli_provider", "GeminiCLIProvider"),
        "claude-code": ("lazygit_llm.cli_providers.claude_code_provider", "ClaudeCodeProvider"),

        # 新しいプロバイダー
        "example-api": ("src.api_providers.example_provider", "ExampleProvider"),
        "example-cli": ("lazygit_llm.cli_providers.example_cli_provider", "ExampleCLIProvider"),
    }

    @staticmethod
    def create_provider(config: 'ProviderConfig') -> BaseProvider:
        """設定に基づいてプロバイダーを作成"""
        provider_name = config.provider

        if provider_name not in ProviderFactory.PROVIDER_MAP:
            raise ProviderError(f"未対応のプロバイダー: {provider_name}")

        module_path, class_name = ProviderFactory.PROVIDER_MAP[provider_name]

        try:
            # 動的インポート
            module = __import__(module_path, fromlist=[class_name])
            provider_class = getattr(module, class_name)

            # インスタンス作成
            return provider_class(config.__dict__)

        except ImportError as e:
            raise ProviderError(f"プロバイダーモジュールのインポートに失敗: {e}")
        except AttributeError as e:
            raise ProviderError(f"プロバイダークラスが見つかりません: {e}")
```

## 設定サンプル

### API型プロバイダー用設定

```yaml
# ~/.config/lazygit-llm/config.yml
provider: "example-api"
api_key: "${EXAMPLE_API_KEY}"
api_base: "https://api.example.com"
model_name: "example-model-v1"
timeout: 30
max_tokens: 100

prompt_template: |
  Generate a commit message for the following changes:

  $diff

  Keep it concise and follow conventional commits format.

additional_params:
  temperature: 0.3
  top_p: 0.9
  frequency_penalty: 0.0
```

### CLI型プロバイダー用設定

```yaml
provider: "example-cli"
model_name: "example-model"
timeout: 45
max_tokens: 150

prompt_template: |
  Based on this git diff, create a commit message:

  $diff

additional_params:
  temperature: 0.2
  max_output_length: 100
```

## テストの実装

### 1. 単体テスト

```python
# tests/test_example_provider.py

import pytest
import responses
from unittest.mock import Mock, patch

from src.api_providers.example_provider import ExampleProvider
from lazygit_llm.base_provider import ProviderError, AuthenticationError

class TestExampleProvider:

    @pytest.fixture
    def provider_config(self):
        return {
            'provider': 'example-api',
            'api_key': 'test-api-key',
            'model_name': 'example-model',
            'timeout': 30,
            'max_tokens': 100,
            'additional_params': {'temperature': 0.3}
        }

    @pytest.fixture
    def provider(self, provider_config):
        return ExampleProvider(provider_config)

    @responses.activate
    def test_generate_commit_message_success(self, provider):
        """正常なコミットメッセージ生成"""
        # APIレスポンスのモック
        responses.add(
            responses.POST,
            'https://api.example.com/chat/completions',
            json={
                'choices': [
                    {'message': {'content': 'feat: add new feature'}}
                ]
            },
            status=200
        )

        diff = "diff --git a/file.py b/file.py\n+new line"
        template = "Generate commit message: $diff"

        result = provider.generate_commit_message(diff, template)

        assert result == 'feat: add new feature'
        assert len(responses.calls) == 1

    @responses.activate
    def test_authentication_error(self, provider):
        """認証エラーのテスト"""
        responses.add(
            responses.POST,
            'https://api.example.com/chat/completions',
            json={'error': {'message': 'Invalid API key'}},
            status=401
        )

        with pytest.raises(AuthenticationError):
            provider.generate_commit_message("test diff", "template")

    def test_config_validation(self):
        """設定検証のテスト"""
        # 無効な設定
        invalid_config = {'provider': 'example-api'}

        with pytest.raises(ProviderError):
            ExampleProvider(invalid_config)
```

### 2. 統合テスト

```python
# tests/integration/test_example_integration.py

import pytest
import os
from unittest.mock import patch

from lazygit_llm.provider_factory import ProviderFactory
from lazygit_llm.config_manager import ProviderConfig

@pytest.mark.integration
class TestExampleIntegration:

    @pytest.fixture
    def config(self):
        return ProviderConfig(
            provider='example-api',
            api_key=os.getenv('EXAMPLE_API_KEY', 'test-key'),
            model_name='example-model',
            timeout=30,
            max_tokens=100,
            prompt_template='Generate: $diff',
            additional_params={'temperature': 0.3}
        )

    def test_end_to_end_generation(self, config):
        """エンドツーエンドのテスト"""
        if not os.getenv('EXAMPLE_API_KEY'):
            pytest.skip("EXAMPLE_API_KEY not set")

        provider = ProviderFactory.create_provider(config)

        test_diff = """
        diff --git a/test.py b/test.py
        index 1234567..abcdefg 100644
        --- a/test.py
        +++ b/test.py
        @@ -1,3 +1,4 @@
         def hello():
             print("Hello")
        +    print("World")
        """

        result = provider.generate_commit_message(test_diff, config.prompt_template)

        assert isinstance(result, str)
        assert len(result.strip()) > 0
        assert len(result) < 200  # 合理的な長さ
```

## デバッグとトラブルシューティング

### ログ設定

```python
import logging

# プロバイダー固有のロガー
logger = logging.getLogger(f'lazygit_llm.providers.{__name__}')

class ExampleProvider(BaseProvider):
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        logger.debug(f"リクエスト開始: model={self.model_name}, diff_size={len(diff)}")

        try:
            # 処理...
            result = "generated message"
            logger.info(f"生成成功: length={len(result)}")
            return result

        except Exception as e:
            logger.error(f"生成失敗: {e}", exc_info=True)
            raise
```

### 一般的な問題と解決方法

#### API型プロバイダー

1. **認証エラー**
   - API キーの有効性確認
   - 環境変数の設定確認
   - APIキーの権限確認

2. **タイムアウトエラー**
   - ネットワーク接続確認
   - timeout設定の調整
   - プロキシ設定の確認

3. **レート制限**
   - リトライ機能の実装
   - 使用頻度の調整
   - 複数APIキーの利用

#### CLI型プロバイダー

1. **バイナリが見つからない**
   - PATHの設定確認
   - バイナリのインストール確認
   - 権限の確認

2. **セキュリティエラー**
   - バイナリパスの検証
   - 許可リストの更新
   - 環境変数の設定

3. **コマンド実行エラー**
   - コマンド引数の確認
   - 入力データの検証
   - 環境設定の確認

## ベストプラクティス

### 1. セキュリティ

- 入力データの検証とサニタイゼーション
- API キーの安全な管理
- subprocess実行時のsell=False
- 出力サイズの制限

### 2. エラーハンドリング

- 適切な例外クラスの使用
- ユーザーフレンドリーなエラーメッセージ
- 詳細なログ出力
- リトライ機能の実装

### 3. パフォーマンス

- タイムアウト設定の適切な調整
- レスポンスサイズの制限
- 接続プールの利用
- 非同期処理の検討

### 4. 保守性

- 明確なドキュメント
- 包括的なテスト
- 設定の外部化
- バージョン互換性の考慮

---

このガイドに従って新しいプロバイダーを実装することで、LazyGit LLM Commit Generatorの機能を拡張し、より多くのLLMサービスに対応できます。
