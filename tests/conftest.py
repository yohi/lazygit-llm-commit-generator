"""
pytest設定ファイルと共通フィクスチャ

テスト実行時の設定とテスト間で共有するフィクスチャを定義。
"""

import pytest
import tempfile
import yaml
import os
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Dict, Any

# テスト用のサンプルデータ
SAMPLE_GIT_DIFF = """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..ed708ec
--- /dev/null
+++ b/test.py
@@ -0,0 +1,5 @@
+def hello_world():
+    print("Hello, World!")
+    return True
+
+# Test comment
"""

SAMPLE_CONFIG = {
    'provider': 'openai',
    'api_key': 'test-api-key',
    'model_name': 'gpt-3.5-turbo',
    'timeout': 30,
    'max_tokens': 100,
    'prompt_template': 'Generate commit message for: {diff}',
    'additional_params': {
        'temperature': 0.3,
        'top_p': 0.9
    }
}


@pytest.fixture
def sample_git_diff():
    """サンプルGit差分データ"""
    return SAMPLE_GIT_DIFF


@pytest.fixture
def sample_config():
    """サンプル設定データ"""
    return SAMPLE_CONFIG.copy()


@pytest.fixture
def temp_config_file():
    """一時的な設定ファイルを作成"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(SAMPLE_CONFIG, f)
        f.flush()
        yield f.name

    # クリーンアップ
    os.unlink(f.name)


@pytest.fixture
def temp_invalid_config_file():
    """無効な設定ファイルを作成（テスト用）"""
    invalid_config = """
provider: invalid_provider
api_key:
model_name:
timeout: -1
max_tokens: 0
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(invalid_config)
        f.flush()
        yield f.name

    # クリーンアップ
    os.unlink(f.name)


@pytest.fixture
def temp_malformed_yaml_file():
    """構文エラーのあるYAMLファイルを作成"""
    malformed_yaml = """
provider: openai
api_key: test
  invalid: indentation
model_name: gpt-3.5-turbo
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(malformed_yaml)
        f.flush()
        yield f.name

    # クリーンアップ
    os.unlink(f.name)


@pytest.fixture
def mock_provider_config():
    """テスト用プロバイダー設定"""
    from lazygit_llm.src.config_manager import ProviderConfig

    return ProviderConfig(
        name='test-provider',
        type='api',
        model='test-model',
        api_key='test-key',
        timeout=30,
        max_tokens=100,
        additional_params={}
    )


@pytest.fixture
def mock_openai_response():
    """OpenAI APIレスポンスのモック"""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message = Mock()
    mock_response.choices[0].message.content = "feat: add new test feature"
    return mock_response


@pytest.fixture
def mock_anthropic_response():
    """Anthropic APIレスポンスのモック"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "fix: resolve authentication issue"
    return mock_response


@pytest.fixture
def mock_gemini_response():
    """Gemini APIレスポンスのモック"""
    mock_response = Mock()
    mock_response.text = "docs: update configuration guide"
    return mock_response


@pytest.fixture
def mock_subprocess_success():
    """成功するsubprocess実行のモック"""
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "refactor: improve error handling"
    mock_result.stderr = ""
    return mock_result


@pytest.fixture
def mock_subprocess_failure():
    """失敗するsubprocess実行のモック"""
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Command execution failed"
    return mock_result


@pytest.fixture
def mock_stdin_diff():
    """標準入力からのGit差分をモック"""
    return patch('sys.stdin', Mock(read=Mock(return_value=SAMPLE_GIT_DIFF)))


@pytest.fixture
def mock_empty_stdin():
    """空の標準入力をモック"""
    return patch('sys.stdin', Mock(read=Mock(return_value="")))


@pytest.fixture
def clean_environment():
    """テスト用にクリーンな環境変数を提供"""
    # テスト関連の環境変数をバックアップ
    original_env = {}
    test_env_vars = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
        'GOOGLE_API_KEY',
        'LAZYGIT_LLM_CONFIG'
    ]

    for var in test_env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]

    yield

    # 環境変数を復元
    for var, value in original_env.items():
        os.environ[var] = value


@pytest.fixture(scope="session")
def test_project_root():
    """テストプロジェクトのルートディレクトリ"""
    return Path(__file__).parent.parent


@pytest.fixture
def captured_logs(caplog):
    """ログ出力をキャプチャ"""
    return caplog


# pytest設定
def pytest_configure(config):
    """pytest設定"""
    # カスタムマーカーを登録
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as requiring API access"
    )


def pytest_collection_modifyitems(config, items):
    """テスト収集後の処理"""
    # APIテストをスキップする設定
    if config.getoption("--no-api"):
        skip_api = pytest.mark.skip(reason="--no-api option given")
        for item in items:
            if "api" in item.keywords:
                item.add_marker(skip_api)


def pytest_addoption(parser):
    """コマンドラインオプションを追加"""
    parser.addoption(
        "--no-api",
        action="store_true",
        default=False,
        help="Skip tests that require API access"
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests"
    )