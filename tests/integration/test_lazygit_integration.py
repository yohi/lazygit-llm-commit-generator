"""
LazyGitとの統合テスト

実際のLazyGit環境での動作確認と互換性テスト。
"""

import pytest
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lazygit_llm.main import main
from lazygit_llm.src.git_processor import GitDiffProcessor
from lazygit_llm.src.message_formatter import MessageFormatter


class TestLazyGitIntegration:
    """LazyGit統合テストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.test_repo_dir = None

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        if self.test_repo_dir and os.path.exists(self.test_repo_dir):
            # テスト用リポジトリを削除
            subprocess.run(['rm', '-rf', self.test_repo_dir], check=False)

    def create_test_git_repo(self):
        """テスト用Gitリポジトリを作成"""
        self.test_repo_dir = tempfile.mkdtemp(prefix='lazygit_test_')

        # Gitリポジトリを初期化
        subprocess.run(['git', 'init'], cwd=self.test_repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=self.test_repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=self.test_repo_dir, check=True)

        # 初期ファイルを作成してコミット
        initial_file = os.path.join(self.test_repo_dir, 'README.md')
        with open(initial_file, 'w') as f:
            f.write('# Test Repository\n\nThis is a test repository.\n')

        subprocess.run(['git', 'add', 'README.md'], cwd=self.test_repo_dir, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=self.test_repo_dir, check=True)

        return self.test_repo_dir

    def create_test_changes(self, repo_dir):
        """テスト用の変更を作成"""
        # 新しいファイルを追加
        new_file = os.path.join(repo_dir, 'src', 'main.py')
        os.makedirs(os.path.dirname(new_file), exist_ok=True)
        with open(new_file, 'w') as f:
            f.write('''#!/usr/bin/env python3
"""
メインアプリケーションモジュール
"""

def main():
    """メイン関数"""
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
''')

        # 既存ファイルを変更
        readme_file = os.path.join(repo_dir, 'README.md')
        with open(readme_file, 'a') as f:
            f.write('\n## Features\n\n- New feature added\n- Bug fixes\n')

        # ファイルをステージング
        subprocess.run(['git', 'add', '.'], cwd=repo_dir, check=True)

    def test_git_diff_processing_in_repo(self):
        """実際のGitリポジトリでの差分処理テスト"""
        repo_dir = self.create_test_git_repo()
        self.create_test_changes(repo_dir)

        # Git差分を取得
        result = subprocess.run(
            ['git', 'diff', '--cached'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )

        git_diff = result.stdout
        assert len(git_diff) > 0
        assert 'src/main.py' in git_diff
        assert 'README.md' in git_diff

        # GitDiffProcessorでテスト
        processor = GitDiffProcessor()

        # 実際の差分をフォーマット
        formatted_diff = processor.format_diff_for_llm(git_diff)

        assert 'Files changed:' in formatted_diff
        assert 'src/main.py' in formatted_diff
        assert 'README.md' in formatted_diff
        assert 'Additions:' in formatted_diff

    def test_lazygit_compatible_output_format(self):
        """LazyGit互換の出力フォーマットテスト"""
        formatter = MessageFormatter()

        # LazyGitが期待する形式のメッセージをテスト
        test_messages = [
            "feat: add new user authentication system",
            "fix: resolve login validation issue\n\nThis commit fixes the validation logic for user login.",
            "docs: update API documentation\n\n- Added new endpoint descriptions\n- Updated example responses",
            "refactor: improve code structure",
        ]

        for message in test_messages:
            formatted = formatter.format_for_lazygit(message)

            # LazyGitが期待する形式であることを確認
            assert len(formatted) > 0
            assert not formatted.startswith('\n')
            assert not formatted.endswith('\n\n\n')

            # コミットメッセージの形式が正しいことを確認
            lines = formatted.split('\n')
            assert len(lines[0]) <= 72  # 第一行は72文字以内

            if len(lines) > 1 and lines[1]:  # 2行目がある場合は空行であるべき
                assert lines[1].strip() == ""

    def test_stdin_input_processing(self):
        """標準入力からの差分処理テスト（LazyGitからの入力をシミュレート）"""
        sample_diff = """diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,15 @@
+"""
+認証モジュール
+"""
+
+def authenticate_user(username, password):
+    """ユーザー認証を行う"""
+    if not username or not password:
+        return False
+
+    # 実際の認証ロジックをここに実装
+    return True
+
+def get_user_permissions(user_id):
+    """ユーザーの権限を取得"""
+    return ['read', 'write']
"""

        processor = GitDiffProcessor()

        # 標準入力をシミュレート
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.return_value = sample_diff

            diff_content = processor.read_staged_diff()

            assert diff_content == sample_diff
            assert processor.has_staged_changes()

            # LLM用フォーマット
            formatted = processor.format_diff_for_llm(diff_content)
            assert 'src/auth.py' in formatted
            assert 'new file' in formatted

    def test_commit_message_validation_for_lazygit(self):
        """LazyGit向けコミットメッセージ検証テスト"""
        formatter = MessageFormatter()

        # LazyGitで使用可能なメッセージ形式
        valid_messages = [
            "feat: add OAuth2 authentication",
            "fix: resolve memory leak in parser",
            "docs: update installation guide",
            "style: format code according to PEP8",
            "refactor: extract common utilities",
            "test: add unit tests for validator",
            "chore: update dependencies",
        ]

        for message in valid_messages:
            assert formatter.validate_commit_message(message)
            formatted = formatter.format_for_lazygit(message)

            # LazyGitのコミットウィンドウで表示される形式
            assert len(formatted.split('\n')[0]) <= 72
            assert not formatted.endswith('\n')

    def test_environment_variable_integration(self):
        """環境変数を使用したLazyGit統合テスト"""
        test_env = {
            'OPENAI_API_KEY': 'sk-test1234567890abcdef1234567890abcdef12345678',
            'LAZYGIT_LLM_PROVIDER': 'openai',
            'LAZYGIT_LLM_MODEL': 'gpt-3.5-turbo',
        }

        with patch.dict('os.environ', test_env):
            # 環境変数が正しく読み取られることを確認
            assert os.environ.get('OPENAI_API_KEY') == test_env['OPENAI_API_KEY']
            assert os.environ.get('LAZYGIT_LLM_PROVIDER') == 'openai'
            assert os.environ.get('LAZYGIT_LLM_MODEL') == 'gpt-3.5-turbo'

    @pytest.mark.slow
    def test_full_lazygit_workflow_simulation(self):
        """完全なLazyGitワークフローシミュレーション"""
        repo_dir = self.create_test_git_repo()
        self.create_test_changes(repo_dir)

        # LazyGitが呼び出すコマンドをシミュレート
        # 1. Git差分を取得
        diff_result = subprocess.run(
            ['git', 'diff', '--cached'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )

        git_diff = diff_result.stdout

        # 2. 差分処理
        processor = GitDiffProcessor()

        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.return_value = git_diff

            processed_diff = processor.read_staged_diff()
            formatted_diff = processor.format_diff_for_llm(processed_diff)

            # 3. メッセージフォーマット
            formatter = MessageFormatter()

            # 模擬LLMレスポンス
            mock_llm_response = "feat: add main application module and update documentation"

            formatted_message = formatter.format_for_lazygit(mock_llm_response)

            # 4. 結果検証
            assert len(formatted_message) > 0
            assert formatter.validate_commit_message(formatted_message)
            assert 'feat:' in formatted_message

    def test_lazygit_custom_config_integration(self):
        """LazyGit用カスタム設定統合テスト"""
        custom_config = """
provider: openai
model_name: gpt-4
timeout: 45
max_tokens: 150
prompt_template: |
  Based on the following git diff, generate a concise commit message following conventional commits format:

  {diff}

  Focus on the primary change and use appropriate type (feat, fix, docs, style, refactor, test, chore).
additional_params:
  temperature: 0.3
  top_p: 0.9
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as config_file:
            config_file.write(custom_config)
            config_file.flush()

            # 設定ファイルが存在することを確認
            assert os.path.exists(config_file.name)

            # 設定ファイルの内容を検証
            with open(config_file.name, 'r') as f:
                content = f.read()
                assert 'provider: openai' in content
                assert 'conventional commits' in content

            # クリーンアップ
            os.unlink(config_file.name)

    def test_exit_code_handling_for_lazygit(self):
        """LazyGit用終了コード処理テスト"""
        # 成功ケース
        test_args_success = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args_success), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):

            # 成功シナリオのモック
            mock_processor_instance = Mock()
            mock_processor_instance.has_staged_changes.return_value = True
            mock_processor_instance.read_staged_diff.return_value = "test diff"
            mock_processor_instance.format_diff_for_llm.return_value = "formatted diff"
            mock_processor.return_value = mock_processor_instance

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: test commit"
            mock_factory_instance = Mock()
            mock_factory_instance.create_provider.return_value = mock_provider
            mock_factory.return_value = mock_factory_instance

            mock_formatter_instance = Mock()
            mock_formatter_instance.format_response.return_value = "feat: test commit"
            mock_formatter.return_value = mock_formatter_instance

            with patch('sys.stdout'):
                exit_code = main()
                assert exit_code == 0  # LazyGitが期待する成功コード

        # 失敗ケース
        test_args_failure = ['main.py', '--provider', 'invalid-provider']

        with patch('sys.argv', test_args_failure):
            with patch('sys.stderr'):
                exit_code = main()
                assert exit_code == 1  # LazyGitが期待する失敗コード

    def test_binary_file_handling_in_lazygit_context(self):
        """LazyGitコンテキストでのバイナリファイル処理テスト"""
        binary_diff = """diff --git a/assets/logo.png b/assets/logo.png
new file mode 100644
index 0000000..1234567
Binary files /dev/null and b/assets/logo.png differ
diff --git a/src/main.py b/src/main.py
new file mode 100644
index 0000000..abcdef0
--- /dev/null
+++ b/src/main.py
@@ -0,0 +1,3 @@
+def main():
+    print("Hello, World!")
+    return 0
"""

        processor = GitDiffProcessor()

        # バイナリファイルを含む差分を処理
        formatted = processor.format_diff_for_llm(binary_diff)

        # バイナリファイルが適切に処理されていることを確認
        assert '(Binary file changed)' in formatted
        assert 'Binary files' not in formatted  # 元のバイナリメッセージは除去される
        assert 'src/main.py' in formatted  # テキストファイルは保持される
        assert 'def main():' in formatted

    def test_large_diff_handling_for_lazygit(self):
        """LazyGit用大容量差分処理テスト"""
        # 大きな差分を生成
        large_diff_content = "+" + "very long line content " * 1000
        large_diff = f"""diff --git a/large_file.txt b/large_file.txt
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/large_file.txt
@@ -0,0 +1 @@
{large_diff_content}
"""

        processor = GitDiffProcessor(max_diff_size=5000)  # 5KB制限

        # 大容量差分を処理
        formatted = processor.format_diff_for_llm(large_diff)

        # 適切に切り詰められていることを確認
        assert len(formatted.encode('utf-8')) <= 5100  # 多少の余裕を持たせる
        assert '... (diff truncated due to size limit)' in formatted or len(formatted) < len(large_diff)

    def test_unicode_handling_in_lazygit(self):
        """LazyGitでのUnicode文字処理テスト"""
        unicode_diff = """diff --git a/docs/README.md b/docs/README.md
index 1234567..abcdef0 100644
--- a/docs/README.md
+++ b/docs/README.md
@@ -1,3 +1,6 @@
 # プロジェクト概要

 このプロジェクトは...
+
+## 新機能 🚀
+- 認証システムの改善 ✨
"""

        processor = GitDiffProcessor()
        formatter = MessageFormatter()

        # Unicode文字を含む差分を処理
        formatted_diff = processor.format_diff_for_llm(unicode_diff)

        # Unicode文字が保持されていることを確認
        assert '新機能' in formatted_diff
        assert '🚀' in formatted_diff
        assert '✨' in formatted_diff

        # Unicode文字を含むコミットメッセージを処理
        unicode_message = "feat: 新しい認証システムを追加 🔐"
        formatted_message = formatter.format_for_lazygit(unicode_message)

        assert '🔐' in formatted_message
        assert formatter.validate_commit_message(formatted_message)

    def test_lazygit_config_file_integration(self):
        """LazyGit設定ファイル統合テスト"""
        lazygit_config = {
            'git': {
                'commitMessage': {
                    'autoGenerate': True,
                    'llmCommand': 'python -m lazygit_llm --provider openai --model gpt-4'
                }
            }
        }

        # LazyGitが期待する設定形式であることを確認
        assert 'git' in lazygit_config
        assert 'commitMessage' in lazygit_config['git']
        assert 'llmCommand' in lazygit_config['git']['commitMessage']

        # コマンドラインが正しい形式であることを確認
        command = lazygit_config['git']['commitMessage']['llmCommand']
        assert 'python -m lazygit_llm' in command
        assert '--provider openai' in command
        assert '--model gpt-4' in command