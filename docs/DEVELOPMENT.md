# LazyGit LLM Commit Generator - 開発者ガイド

## 🏗 開発環境セットアップ

### 前提条件

- **Python**: 3.9以上 (推奨: 3.11+)
- **Git**: 2.0以上
- **LazyGit**: 0.35以上 (テスト用)

### 開発環境構築

```bash
# プロジェクトをクローン
git clone https://github.com/yohi/lazygit-llm-commit-generator.git
cd lazygit-llm-commit-generator

# 仮想環境作成
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 開発用依存関係をインストール
pip install -r requirements.txt
pip install -e .  # 開発モードでインストール
```

### 開発ツール設定

```bash
# コード品質ツール
pip install black flake8 mypy pytest-cov

# pre-commitフック設定
pip install pre-commit
pre-commit install

# VS Code/PyCharm設定
cp .vscode/settings.json.example .vscode/settings.json
```

## 📁 プロジェクト構造

```
lazygit-llm-commit-generator/
├── 📦 setup.py                    # パッケージ設定
├── 📄 requirements.txt            # 依存関係
├── 🧪 pytest.ini                 # テスト設定
├── 📋 MANIFEST.in                 # パッケージング設定
├── 📚 docs/                       # ドキュメント
│   ├── API_REFERENCE.md          # API仕様書
│   ├── USER_GUIDE.md             # ユーザーガイド
│   └── DEVELOPMENT.md            # 開発者ガイド
├── 🔧 lazygit-llm/               # メインパッケージ
│   ├── lazygit_llm/              # コア実装
│   │   ├── main.py               # エントリーポイント
│   │   ├── config_manager.py     # 設定管理
│   │   ├── git_processor.py      # Git操作
│   │   ├── provider_factory.py   # プロバイダー工場
│   │   ├── message_formatter.py  # メッセージ整形
│   │   └── base_provider.py      # ベースクラス
│   ├── src/                      # プロバイダー実装
│   │   ├── api_providers/        # API系プロバイダー
│   │   │   ├── openai_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── gemini_api_provider.py
│   │   ├── cli_providers/        # CLI系プロバイダー
│   │   │   ├── claude_code_provider.py
│   │   │   └── gemini_cli_provider.py
│   │   ├── error_handler.py      # エラーハンドリング
│   │   └── security_validator.py # セキュリティ検証
│   ├── config/                   # 設定ファイル例
│   │   └── config.yml.example    # 設定テンプレート
│   └── tests/                    # テストスイート
│       ├── unit/                 # 単体テスト
│       ├── integration/          # 統合テスト
│       └── performance/          # パフォーマンステスト
└── 🚀 scripts/                   # ユーティリティスクリプト
    ├── install.py                # インストールスクリプト
    ├── validate_system.py        # システム検証
    └── test_packaging.sh         # パッケージングテスト
```

## 🎯 開発フロー

### 1. 機能開発

```bash
# フィーチャーブランチを作成
git checkout -b feature/new-provider

# 実装
# - コードを書く
# - テストを書く
# - ドキュメントを更新

# テスト実行
python -m pytest tests/

# コード品質チェック
black lazygit-llm/
flake8 lazygit-llm/
mypy lazygit-llm/

# コミット・プッシュ
git add .
git commit -m "feat: add new provider support"
git push origin feature/new-provider
```

### 2. コード品質基準

#### Python スタイル

```python
# Google Style Docstring
def generate_commit_message(self, diff: str, prompt_template: str) -> str:
    """
    Git差分からコミットメッセージを生成

    Args:
        diff: `git diff --staged`の出力
        prompt_template: LLMに送信するプロンプトテンプレート

    Returns:
        生成されたコミットメッセージ

    Raises:
        ProviderError: プロバイダー固有のエラー
        AuthenticationError: 認証失敗
    """
```

#### 型ヒント

```python
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

def load_config(self, config_path: Union[str, Path]) -> Dict[str, Any]:
    """型ヒントを適切に使用"""
```

#### エラーハンドリング

```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Specific error occurred: {e}")
    raise ProviderError(f"Operation failed: {e}") from e
except Exception as e:
    logger.exception("Unexpected error")
    raise ProviderError(f"Unexpected error: {e}") from e
```

## 🔌 プロバイダー開発

### 新しいプロバイダーの追加

#### 1. ベースクラスを継承

```python
# src/api_providers/new_provider.py
from typing import Dict, Any
from ..base_provider import BaseProvider, ProviderError

class NewProvider(BaseProvider):
    """新しいLLMプロバイダー"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.endpoint = config.get('endpoint', 'https://api.example.com')

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """コミットメッセージ生成の実装"""
        try:
            prompt = prompt_template.replace('{diff}', diff)
            response = self._call_api(prompt)
            return self._extract_message(response)
        except Exception as e:
            raise ProviderError(f"Message generation failed: {e}")

    def test_connection(self) -> bool:
        """接続テストの実装"""
        try:
            response = self._call_api("test")
            return response.status_code == 200
        except:
            return False

    def _call_api(self, prompt: str) -> Any:
        """API呼び出し（プライベートメソッド）"""
        # 実装詳細
        pass

    def _extract_message(self, response: Any) -> str:
        """レスポンスからメッセージ抽出"""
        # 実装詳細
        pass
```

#### 2. プロバイダーを登録

```python
# src/api_providers/__init__.py
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_api_provider import GeminiAPIProvider
from .new_provider import NewProvider  # 追加

PROVIDER_CLASSES = {
    'openai': OpenAIProvider,
    'anthropic': AnthropicProvider,
    'gemini-api': GeminiAPIProvider,
    'new-provider': NewProvider,  # 追加
}

def get_provider_class(provider_name: str):
    """プロバイダークラスを取得"""
    if provider_name not in PROVIDER_CLASSES:
        available = ', '.join(PROVIDER_CLASSES.keys())
        raise ValueError(f"Unknown provider: {provider_name}. Available: {available}")
    return PROVIDER_CLASSES[provider_name]
```

#### 3. 設定例を追加

```yaml
# lazygit-llm/config/config.yml.example に追加
# --- New Provider設定例 ---
# provider: "new-provider"
# model_name: "new-model"
# api_key: "${NEW_PROVIDER_API_KEY}"
# endpoint: "https://api.newprovider.com/v1"
# additional_params:
#   custom_param: "value"
```

#### 4. テストを追加

```python
# tests/unit/test_new_provider.py
import pytest
from unittest.mock import Mock, patch
from lazygit_llm.src.api_providers.new_provider import NewProvider

class TestNewProvider:
    def test_init(self):
        config = {
            'api_key': 'test-key',
            'endpoint': 'https://test.com'
        }
        provider = NewProvider(config)
        assert provider.api_key == 'test-key'
        assert provider.endpoint == 'https://test.com'

    @patch('requests.post')
    def test_generate_commit_message(self, mock_post):
        mock_response = Mock()
        mock_response.json.return_value = {'message': 'feat: add new feature'}
        mock_post.return_value = mock_response

        provider = NewProvider({'api_key': 'test'})
        result = provider.generate_commit_message('diff content', 'template')

        assert result == 'feat: add new feature'
        mock_post.assert_called_once()
```

## 🧪 テスト戦略

### テスト構造

```
tests/
├── unit/                     # 単体テスト
│   ├── test_config_manager.py
│   ├── test_git_processor.py
│   ├── test_provider_factory.py
│   └── test_providers/
│       ├── test_openai_provider.py
│       └── test_anthropic_provider.py
├── integration/              # 統合テスト
│   ├── test_end_to_end.py
│   └── test_provider_integration.py
├── performance/              # パフォーマンステスト
│   └── test_performance.py
└── conftest.py              # 共通フィクスチャ
```

### テスト実行

```bash
# 全テスト実行
python -m pytest tests/

# 特定のテストのみ
python -m pytest tests/unit/test_config_manager.py

# カバレッジ付き実行
python -m pytest tests/ --cov=lazygit_llm --cov-report=html

# マーカー別実行
python -m pytest tests/ -m "unit"           # 単体テストのみ
python -m pytest tests/ -m "integration"    # 統合テストのみ
python -m pytest tests/ -m "not slow"       # 遅いテストを除外
```

### モック戦略

```python
# API呼び出しをモック
@patch('openai.OpenAI')
def test_openai_provider(self, mock_openai):
    mock_client = Mock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="feat: add feature"))]
    )

    provider = OpenAIProvider({'api_key': 'test'})
    result = provider.generate_commit_message('diff', 'template')

    assert result == "feat: add feature"

# 環境変数をモック
@patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
def test_config_with_env_vars(self):
    config = ConfigManager()
    config.load_config('test-config.yml')
    assert config.config['api_key'] == 'test-key'
```

## 🔒 セキュリティガイドライン

### 機密情報の取り扱い

```python
# ❌ 悪い例: ログに機密情報を出力
logger.info(f"Using API key: {api_key}")

# ✅ 良い例: 機密情報をマスク
logger.info(f"Using API key: {api_key[:8]}{'*' * 20}")

# ✅ セキュリティバリデーター使用
from .security_validator import SecurityValidator

def log_safe(self, message: str) -> str:
    """セキュアなログ出力"""
    return SecurityValidator.mask_sensitive_data(message)
```

### 入力検証

```python
def validate_diff(self, diff: str) -> str:
    """Git diff内容を検証"""
    if not diff or not isinstance(diff, str):
        raise ValueError("Invalid diff content")

    # 異常に大きな差分を拒否
    if len(diff) > 1024 * 1024:  # 1MB
        raise ValueError("Diff content too large")

    # 不正なパスを検出
    if any(path in diff for path in ['../', '~/', '/etc/']):
        raise ValueError("Suspicious path detected in diff")

    return diff
```

### APIキー管理

```python
class ConfigManager:
    def _expand_env_vars(self, value: str) -> str:
        """環境変数を安全に展開"""
        if not isinstance(value, str):
            return value

        # ${VAR_NAME} 形式の環境変数を展開
        pattern = r'\${([A-Z_]+)}'
        def replace_env(match):
            env_name = match.group(1)
            env_value = os.environ.get(env_name)
            if env_value is None:
                raise ValueError(f"Environment variable not set: {env_name}")
            return env_value

        return re.sub(pattern, replace_env, value)
```

## 📊 パフォーマンス最適化

### プロファイリング

```python
# tests/performance/test_performance.py
import time
import pytest
from memory_profiler import profile

class TestPerformance:
    @pytest.mark.performance
    def test_response_time(self):
        """レスポンス時間をテスト"""
        provider = OpenAIProvider({'api_key': 'test'})

        start_time = time.time()
        result = provider.generate_commit_message('small diff', 'template')
        end_time = time.time()

        response_time = end_time - start_time
        assert response_time < 10.0  # 10秒以内

    @profile
    def test_memory_usage(self):
        """メモリ使用量をプロファイル"""
        provider = OpenAIProvider({'api_key': 'test'})
        for i in range(100):
            provider.generate_commit_message(f'diff {i}', 'template')
```

### キャッシュ戦略

```python
from functools import lru_cache
from typing import Dict, Any

class ProviderFactory:
    def __init__(self):
        self._provider_cache: Dict[str, BaseProvider] = {}

    @lru_cache(maxsize=128)
    def _get_cached_config(self, config_hash: str) -> Dict[str, Any]:
        """設定をキャッシュ"""
        # 実装
        pass

    def create_provider(self, config: Dict[str, Any]) -> BaseProvider:
        """プロバイダーをキャッシュして再利用"""
        config_key = self._get_config_key(config)

        if config_key not in self._provider_cache:
            self._provider_cache[config_key] = self._create_new_provider(config)

        return self._provider_cache[config_key]
```

## 🚀 リリース管理

### バージョニング

[Semantic Versioning](https://semver.org/) に従う：

- **MAJOR**: 互換性のない変更
- **MINOR**: 後方互換性のある機能追加
- **PATCH**: 後方互換性のあるバグ修正

```bash
# バージョン更新
# setup.py の version を更新
version="1.1.0"

# タグ作成
git tag -a v1.1.0 -m "Release version 1.1.0"
git push origin v1.1.0
```

### リリースチェックリスト

#### リリース前

- [ ] 全テストがパス
- [ ] コードカバレッジ >= 80%
- [ ] ドキュメント更新済み
- [ ] CHANGELOGを更新
- [ ] セキュリティ監査完了

#### リリース作業

```bash
# 1. 最終テスト
python -m pytest tests/ --cov=lazygit_llm

# 2. パッケージビルド
python setup.py sdist bdist_wheel

# 3. パッケージ検証
python verify_packaging.py

# 4. TestPyPIにアップロード
twine upload --repository testpypi dist/*

# 5. テスト環境で検証
pip install --index-url https://test.pypi.org/simple/ lazygit-llm-commit-generator

# 6. 本番PyPIにアップロード
twine upload dist/*
```

#### リリース後

- [ ] GitHub Releaseを作成
- [ ] ドキュメントサイトを更新
- [ ] アナウンス記事の投稿

## 🛠 デバッグガイド

### ログレベル設定

```python
# 開発時のログ設定
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# 特定モジュールのログレベルを調整
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('openai').setLevel(logging.INFO)
```

### デバッグ用ツール

```python
# デバッグ用プロバイダー
class DebugProvider(BaseProvider):
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        logger.debug(f"Diff length: {len(diff)}")
        logger.debug(f"Template: {prompt_template[:100]}...")

        # 実際のAPI呼び出しをスキップしてテスト用メッセージを返す
        return "debug: test commit message"

    def test_connection(self) -> bool:
        return True
```

### プロファイリングツール

```bash
# メモリプロファイル
pip install memory-profiler
python -m memory_profiler main.py

# 実行時間プロファイル
python -m cProfile -o profile.prof main.py
python -c "import pstats; pstats.Stats('profile.prof').sort_stats('cumulative').print_stats(10)"
```

## 🤝 コントリビューションガイド

### Pull Request プロセス

1. **Issue作成**: 機能要求やバグ報告
2. **フォーク**: プロジェクトをフォーク
3. **ブランチ作成**: `feature/`, `bugfix/`, `docs/` プレフィックス使用
4. **実装**: コード変更とテスト追加
5. **テスト**: 全テストがパスすることを確認
6. **PR作成**: 詳細な説明とテスト結果を含める
7. **レビュー**: コードレビューを受ける
8. **マージ**: 承認後にマージ

### コードレビューチェックリスト

#### 機能面
- [ ] 要件を満たしている
- [ ] エッジケースを考慮している
- [ ] エラーハンドリングが適切
- [ ] パフォーマンスへの影響が最小

#### コード品質
- [ ] 可読性が高い
- [ ] 適切なコメント・ドキュメント
- [ ] DRY原則に従っている
- [ ] SOLID原則に従っている

#### テスト
- [ ] 十分なテストカバレッジ
- [ ] 適切なテストケース
- [ ] モックが適切に使われている

#### セキュリティ
- [ ] 機密情報が適切に保護されている
- [ ] 入力検証が実装されている
- [ ] SQLインジェクション等の脆弱性がない

---

**開発を楽しんでください！ 🚀**