# 🛠️ 開発者ガイド

LazyGit LLM Commit Generatorの開発・拡張に関するガイドです。

## 🚀 開発環境のセットアップ

### 前提条件

- Python 3.9以上
- Git
- 好みのコードエディタ（VS Code、PyCharm等）

### 開発用セットアップ

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd lazygit-llm-commit-generator

# 2. 仮想環境作成（推奨）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 開発用依存関係インストール
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 作成予定

# 4. 開発モードでパッケージインストール
pip install -e .

# 5. pre-commitフック設定（推奨）
pre-commit install
```

### 開発用設定ファイル

```yaml
# config/dev-config.yml
provider: "openai"
api_key: "${OPENAI_API_KEY}"
model_name: "gpt-3.5-turbo"  # 開発用は安価なモデル
timeout: 15
max_tokens: 50

# 開発用ログ設定
log_level: "DEBUG"
verbose: true

# テスト用プロンプト
prompt_template: |
  [DEV] Generate a simple commit message for: {diff}
```

## 🏗️ アーキテクチャ設計

### 設計原則

1. **単一責任の原則**: 各クラスは明確な役割を持つ
2. **オープン/クローズドの原則**: 拡張に開いて、修正に閉じている
3. **依存関係逆転の原則**: 抽象に依存し、具象に依存しない
4. **セキュリティファースト**: 全ての入力を検証・サニタイゼーション

### 主要コンポーネント

```
┌─────────────────┐    ┌─────────────────┐
│   main.py       │    │ ConfigManager   │
│ (Entry Point)   │───▶│ (Configuration) │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│ GitDiffProcessor│    │ProviderFactory  │
│ (Git Handling)  │    │ (Provider Mgmt) │
└─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│MessageFormatter │    │  BaseProvider   │
│ (Output Format) │    │   (Abstract)    │
└─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │Concrete Providers│
                    │ (OpenAI, etc.)  │
                    └─────────────────┘
```

## 🔧 新しいプロバイダーの追加

### 1. プロバイダークラスの作成

```python
# lazygit-llm/src/api_providers/custom_provider.py
from typing import Dict, Any
from ..base_provider import BaseProvider, ProviderError

class CustomProvider(BaseProvider):
    """カスタムLLMプロバイダーの実装例"""

    def __init__(self, config: Dict[str, Any]):
        """
        カスタムプロバイダーを初期化

        Args:
            config: プロバイダー設定辞書
        """
        super().__init__(config)

        # 必須設定の検証
        if 'api_key' not in config:
            raise ProviderError("APIキーが設定されていません")

        self.api_key = config['api_key']
        self.model_name = config.get('model_name', 'default-model')
        self.base_url = config.get('base_url', 'https://api.custom.com')

        # カスタムクライアントの初期化
        self._initialize_client()

    def _initialize_client(self):
        """APIクライアントを初期化"""
        # カスタムAPIクライアントのセットアップ
        pass

    def generate_commit_message(self, diff: str) -> str:
        """
        カスタムAPIを使用してコミットメッセージを生成

        Args:
            diff: Git差分文字列

        Returns:
            生成されたコミットメッセージ

        Raises:
            ProviderError: API呼び出しに失敗した場合
        """
        try:
            # プロンプトの構築
            prompt = self._build_prompt(diff)

            # API呼び出し
            response = self._call_api(prompt)

            # レスポンスの処理
            return self._extract_message(response)

        except Exception as e:
            raise ProviderError(f"コミットメッセージ生成に失敗: {e}")

    def _build_prompt(self, diff: str) -> str:
        """プロンプトを構築"""
        template = self.config.get('prompt_template',
                                  'Generate commit message for: {diff}')
        return template.format(diff=diff)

    def _call_api(self, prompt: str) -> Dict[str, Any]:
        """カスタムAPIを呼び出し"""
        # 実際のAPI呼び出しロジック
        # requests等を使用してHTTP APIを呼び出し
        pass

    def _extract_message(self, response: Dict[str, Any]) -> str:
        """APIレスポンスからメッセージを抽出"""
        # レスポンス解析ロジック
        pass

    def test_connection(self) -> bool:
        """
        カスタムAPIへの接続をテスト

        Returns:
            接続成功の場合True
        """
        try:
            # 簡単なAPI呼び出しでテスト
            # 例: ヘルスチェックエンドポイント
            return True
        except Exception:
            return False

    def supports_streaming(self) -> bool:
        """
        ストリーミング対応状況

        Returns:
            ストリーミング対応の場合True
        """
        return False  # または実装に応じてTrue
```

### 2. プロバイダーの登録

```python
# lazygit-llm/src/provider_factory.py に追加

from .api_providers.custom_provider import CustomProvider

# レジストリに登録
provider_registry.register_provider("custom", CustomProvider, "api")

# サポートされているプロバイダーリストに追加
SUPPORTED_PROVIDERS = {
    # 既存のプロバイダー...
    'custom': {'type': 'api', 'required_fields': ['api_key', 'model_name']},
}
```

### 3. 設定例の追加

```yaml
# config/config.yml.example に追加
# Custom Provider設定例
# provider: "custom"
# api_key: "${CUSTOM_API_KEY}"
# model_name: "custom-model-v1"
# base_url: "https://api.custom.com"  # オプション
# additional_params:
#   temperature: 0.3
#   custom_param: "value"
```

### 4. テストの追加

```python
# tests/test_custom_provider.py
import pytest
from unittest.mock import Mock, patch
from lazygit_llm.api_providers.custom_provider import CustomProvider

class TestCustomProvider:
    """CustomProviderのテストクラス"""

    def setup_method(self):
        """テスト用設定"""
        self.config = {
            'api_key': 'test-key',
            'model_name': 'test-model',
            'timeout': 30,
            'max_tokens': 100
        }

    def test_initialization(self):
        """初期化テスト"""
        provider = CustomProvider(self.config)
        assert provider.api_key == 'test-key'
        assert provider.model_name == 'test-model'

    def test_missing_api_key(self):
        """APIキー不足時のエラーテスト"""
        config = self.config.copy()
        del config['api_key']

        with pytest.raises(ProviderError):
            CustomProvider(config)

    @patch('requests.post')
    def test_generate_commit_message(self, mock_post):
        """コミットメッセージ生成テスト"""
        # モックレスポンス設定
        mock_response = Mock()
        mock_response.json.return_value = {
            'message': 'feat: add new feature'
        }
        mock_post.return_value = mock_response

        provider = CustomProvider(self.config)
        result = provider.generate_commit_message("test diff")

        assert result == 'feat: add new feature'
        mock_post.assert_called_once()

    def test_supports_streaming(self):
        """ストリーミング対応テスト"""
        provider = CustomProvider(self.config)
        assert provider.supports_streaming() in [True, False]
```

## 🧪 テストの書き方

### テスト構造

```
tests/
├── __init__.py
├── conftest.py                 # pytest設定とフィクスチャ
├── test_config_manager.py      # 設定管理テスト
├── test_git_processor.py       # Git処理テスト
├── test_provider_factory.py    # プロバイダーファクトリテスト
├── test_security_validator.py  # セキュリティテスト
├── api_providers/
│   ├── test_openai_provider.py
│   ├── test_anthropic_provider.py
│   └── test_custom_provider.py
├── cli_providers/
│   ├── test_gemini_cli_provider.py
│   └── test_claude_code_provider.py
└── integration/
    └── test_end_to_end.py      # 統合テスト
```

### テスト用フィクスチャ

```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_config_file():
    """一時的な設定ファイルを作成"""
    config_content = """
provider: "openai"
api_key: "test-key"
model_name: "gpt-3.5-turbo"
timeout: 30
max_tokens: 100
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(config_content)
        f.flush()
        yield f.name

    # クリーンアップ
    Path(f.name).unlink()

@pytest.fixture
def sample_git_diff():
    """サンプルのGit差分"""
    return """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..ed708ec
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+def hello():
+    print("Hello, World!")
+    return True
"""

@pytest.fixture
def mock_provider_config():
    """テスト用プロバイダー設定"""
    return {
        'name': 'test-provider',
        'type': 'api',
        'model': 'test-model',
        'api_key': 'test-key',
        'timeout': 30,
        'max_tokens': 100,
        'additional_params': {}
    }
```

### ユニットテストの例

```python
# tests/test_config_manager.py
import pytest
from lazygit_llm.config_manager import ConfigManager, ConfigError

class TestConfigManager:
    """ConfigManagerのテストクラス"""

    def test_load_config_success(self, temp_config_file):
        """設定ファイル読み込み成功テスト"""
        manager = ConfigManager()
        config = manager.load_config(temp_config_file)

        assert config['provider'] == 'openai'
        assert config['api_key'] == 'test-key'

    def test_load_config_file_not_found(self):
        """存在しないファイルのテスト"""
        manager = ConfigManager()

        with pytest.raises(ConfigError, match="設定ファイルが見つかりません"):
            manager.load_config('/non/existent/file.yml')

    def test_validate_config_success(self, temp_config_file):
        """設定検証成功テスト"""
        manager = ConfigManager()
        manager.load_config(temp_config_file)

        assert manager.validate_config() is True

    def test_environment_variable_resolution(self, monkeypatch):
        """環境変数解決テスト"""
        monkeypatch.setenv("TEST_API_KEY", "resolved-key")

        config = {"api_key": "${TEST_API_KEY}"}
        manager = ConfigManager()
        resolved = manager._resolve_environment_variables(config)

        assert resolved['api_key'] == 'resolved-key'
```

### 統合テストの例

```python
# tests/integration/test_end_to_end.py
import pytest
from unittest.mock import patch, Mock
from lazygit_llm.main import main

class TestEndToEnd:
    """エンドツーエンドテスト"""

    @patch('sys.stdin')
    @patch('lazygit_llm.config_manager.ConfigManager.load_config')
    @patch('lazygit_llm.api_providers.openai_provider.OpenAIProvider.generate_commit_message')
    def test_full_workflow(self, mock_generate, mock_load_config, mock_stdin):
        """完全なワークフローテスト"""
        # モック設定
        mock_stdin.read.return_value = "test diff content"
        mock_load_config.return_value = {
            'provider': 'openai',
            'api_key': 'test-key',
            'model_name': 'gpt-3.5-turbo'
        }
        mock_generate.return_value = "feat: add new feature"

        # 実行
        with patch('sys.argv', ['main.py', '--config', 'test.yml']):
            result = main()

        # 検証
        assert result == 0
        mock_generate.assert_called_once()
```

## 🔍 コード品質

### Linting設定

```bash
# .flake8
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv
ignore = E203,W503

# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py39']

[tool.isort]
profile = "black"
line_length = 100

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### pre-commitフック

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.10.1
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.942
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.1.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### 実行コマンド

```bash
# コード整形
black lazygit-llm/
isort lazygit-llm/

# Linting
flake8 lazygit-llm/
mypy lazygit-llm/

# テスト実行
pytest tests/ -v
pytest tests/ --cov=lazygit_llm --cov-report=html

# 全チェック実行
pre-commit run --all-files
```

## 📦 パッケージング・リリース

### バージョニング

セマンティックバージョニング（SemVer）を使用：

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

### リリースプロセス

```bash
# 1. バージョン更新
# setup.py と __init__.py でバージョンを更新

# 2. 変更履歴更新
# CHANGELOG.md に変更内容を記録

# 3. テスト実行
pytest tests/ --cov=lazygit_llm

# 4. パッケージビルド
python setup.py sdist bdist_wheel

# 5. PyPIアップロード（テスト環境）
twine upload --repository testpypi dist/*

# 6. 本番環境アップロード
twine upload dist/*

# 7. Gitタグ作成
git tag v1.0.0
git push origin v1.0.0
```

## 🐛 デバッグ

### ログ設定

```python
# 開発用ログ設定
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### デバッグ用ツール

```bash
# 対話的デバッグ
python -m pdb lazygit-llm/src/main.py

# プロファイリング
python -m cProfile -o profile.stats lazygit-llm/src/main.py
python -c "import pstats; pstats.Stats('profile.stats').sort_stats('cumulative').print_stats()"

# メモリ使用量チェック
pip install memory-profiler
python -m memory_profiler lazygit-llm/src/main.py
```

## 📚 ドキュメント

### ドキュメント更新

```bash
# API ドキュメント生成（sphinx使用）
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs/
sphinx-build docs/ docs/_build/

# README更新
# 新機能追加時は README.md を更新

# CHANGELOG更新
# リリース時に CHANGELOG.md を更新
```

### コメント・ドックストリング

```python
def generate_commit_message(self, diff: str) -> str:
    """
    Git差分からコミットメッセージを生成

    このメソッドは設定されたLLMプロバイダーを使用して、
    提供されたGit差分からコミットメッセージを生成します。

    Args:
        diff (str): Git差分文字列。git diff --stagedの出力を想定

    Returns:
        str: 生成されたコミットメッセージ

    Raises:
        ProviderError: LLMプロバイダーでエラーが発生した場合
        TimeoutError: APIのタイムアウトが発生した場合
        AuthenticationError: API認証に失敗した場合

    Example:
        >>> provider = OpenAIProvider(config)
        >>> diff = "diff --git a/file.py..."
        >>> message = provider.generate_commit_message(diff)
        >>> print(message)
        "feat: add new feature for user authentication"

    Note:
        このメソッドは非同期実行には対応していません。
        大容量の差分（50KB以上）は自動的に切り詰められます。
    """
    pass
```

## 🤝 コントリビューション

### プルリクエストガイドライン

1. **機能ブランチ作成**
   ```bash
   git checkout -b feature/new-provider
   ```

2. **変更実装**
   - 小さく、焦点を絞った変更
   - 適切なテストの追加
   - ドキュメントの更新

3. **コード品質チェック**
   ```bash
   pre-commit run --all-files
   pytest tests/
   ```

4. **プルリクエスト作成**
   - 明確なタイトルと説明
   - 関連するIssueの参照
   - スクリーンショット（UI変更の場合）

### Issue報告

バグ報告や機能要望は以下の情報を含めてください：

- **環境情報**: OS、Pythonバージョン、依存関係
- **再現手順**: 具体的なステップ
- **期待される動作**: 何が起こるべきか
- **実際の動作**: 何が起こったか
- **ログ**: エラーメッセージやログ

---

開発にご参加いただき、ありがとうございます！質問があれば、GitHubのDiscussionsでお気軽にお尋ねください。