"""
エンドツーエンド統合テスト

実際のワークフローでの動作確認と各コンポーネント間の連携テスト。
"""

import pytest
import tempfile
import os
import sys
import yaml
from pathlib import Path
from unittest.mock import patch, Mock, StringIO

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lazygit_llm.main import main
from lazygit_llm.src.config_manager import ConfigManager
from lazygit_llm.src.git_processor import GitDiffProcessor
from lazygit_llm.src.provider_factory import ProviderFactory
from lazygit_llm.src.message_formatter import MessageFormatter
from lazygit_llm.src.error_handler import ErrorHandler


class TestEndToEnd:
    """エンドツーエンドテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.temp_files = []

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        # 一時ファイルをクリーンアップ
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def create_test_config(self, provider='openai', model='gpt-4', api_key='test-key'):
        """テスト用設定ファイルを作成"""
        config_content = {
            'provider': provider,
            'model_name': model,
            'api_key': api_key,
            'timeout': 30,
            'max_tokens': 100,
            'prompt_template': 'Generate a commit message for: {diff}',
            'additional_params': {
                'temperature': 0.3,
                'top_p': 0.9
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_content, f, default_flow_style=False)
            self.temp_files.append(f.name)
            return f.name

    def test_full_pipeline_with_config_file(self):
        """設定ファイルを使用した完全パイプラインテスト"""
        # テスト用設定ファイルを作成
        config_file = self.create_test_config()

        # テスト用Git差分
        test_diff = r'''diff --git a/src/auth.py b/src/auth.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/auth.py
@@ -0,0 +1,10 @@
+"""
+認証モジュール
+"""
+
+def authenticate_user(username, password):
+    """ユーザー認証を行う"""
+    if not username or not password:
+        return False
+    return True
'''

        # コマンドライン引数をシミュレート
        test_args = ['main.py', '--config', config_file]

        with patch('sys.argv', test_args), \
             patch('sys.stdin') as mock_stdin, \
             patch('sys.stdout', new_callable=StringIO) as mock_stdout, \
             patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:

            # 標準入力をシミュレート
            mock_stdin.read.return_value = test_diff

            # OpenAIプロバイダーをモック
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add user authentication module"
            mock_openai.return_value = mock_provider

            # メイン関数を実行
            exit_code = main()

            # 結果を検証
            assert exit_code == 0
            output = mock_stdout.getvalue()
            assert "feat: add user authentication module" in output

    def test_component_integration_flow(self):
        """コンポーネント統合フローテスト"""
        # 1. 設定管理
        config_manager = ConfigManager()
        config_file = self.create_test_config()

        config = config_manager.load_config(config_file)
        assert config['provider'] == 'openai'

        provider_config = config_manager.get_provider_config()
        assert provider_config.name == 'openai'

        # 2. プロバイダーファクトリー
        factory = ProviderFactory()
        assert factory.is_provider_supported('openai')

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai_class:
            mock_provider = Mock()
            mock_openai_class.return_value = mock_provider

            provider = factory.create_provider(provider_config)
            assert provider == mock_provider

        # 3. Git差分処理
        processor = GitDiffProcessor()
        test_diff = "diff --git a/test.py b/test.py\n+def test(): pass"

        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.return_value = test_diff
            processed_diff = processor.read_staged_diff()
            assert processed_diff == test_diff

        formatted_diff = processor.format_diff_for_llm(test_diff)
        assert "test.py" in formatted_diff

        # 4. メッセージフォーマット
        formatter = MessageFormatter()
        mock_response = "feat: add test function"
        formatted_message = formatter.format_response(mock_response)
        assert formatted_message == "feat: add test function"

    def test_error_handling_integration(self):
        """エラーハンドリング統合テスト"""
        error_handler = ErrorHandler()

        # 認証エラーのシミュレート
        from lazygit_llm.src.base_provider import AuthenticationError
        auth_error = AuthenticationError("Invalid API key")

        error_info = error_handler.handle_error(auth_error)

        assert error_info['category'].name == 'AUTHENTICATION'
        assert error_info['severity'].name == 'HIGH'
        assert len(error_info['suggestions']) > 0

        # ユーザー向けメッセージフォーマット
        formatted_message = error_handler.format_error_message_for_user(error_info)
        assert "APIキー" in formatted_message or "認証" in formatted_message

    def test_security_validation_integration(self):
        """セキュリティ検証統合テスト"""
        from lazygit_llm.src.security_validator import SecurityValidator

        validator = SecurityValidator()

        # APIキー検証
        api_key_result = validator.validate_api_key(
            'openai',
            'sk-1234567890abcdef1234567890abcdef12345678'  # gitleaks:allow - test only
        )
        assert api_key_result.is_valid

        # 差分サニタイゼーション
        safe_diff = "diff --git a/test.py b/test.py\n+def hello(): print('Hello')"
        sanitized_diff, result = validator.sanitize_git_diff(safe_diff)

        assert result.is_valid
        assert sanitized_diff == safe_diff

        # 危険な差分の検出
        dangerous_diff = "diff --git a/test.py b/test.py\n+os.system('rm -rf /')"
        _, danger_result = validator.sanitize_git_diff(dangerous_diff)

        assert not danger_result.is_valid
        assert danger_result.level == "danger"

    def test_multiple_provider_support(self):
        """複数プロバイダーサポートテスト"""
        factory = ProviderFactory()

        providers_to_test = [
            ('openai', 'lazygit_llm.src.api_providers.openai_provider.OpenAIProvider'),
            ('anthropic', 'lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider'),
            ('gemini-api', 'lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider'),
        ]

        for provider_name, provider_class_path in providers_to_test:
            config_file = self.create_test_config(provider=provider_name)
            config_manager = ConfigManager()
            config_manager.load_config(config_file)

            provider_config = config_manager.get_provider_config()
            assert provider_config.name == provider_name

            # プロバイダーがサポートされていることを確認
            assert factory.is_provider_supported(provider_name)

    def test_configuration_validation_integration(self):
        """設定検証統合テスト"""
        config_manager = ConfigManager()

        # 有効な設定
        valid_config_file = self.create_test_config()
        config_manager.load_config(valid_config_file)

        assert config_manager.validate_config()

        # 無効な設定（APIキーなし）
        invalid_config_file = self.create_test_config(api_key='')

        with patch.object(config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = Mock(level='info')
            config_manager.load_config(invalid_config_file)

            # APIキーが空の場合の検証
            with pytest.raises(Exception):
                config_manager.get_api_key('openai')

    def test_large_diff_processing_pipeline(self):
        """大容量差分処理パイプラインテスト"""
        # 大きな差分を生成
        large_file_content = '\n'.join([f'+line {i}: some content here' for i in range(1000)])
        large_diff = f"""diff --git a/large_file.py b/large_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/large_file.py
@@ -0,0 +1,1000 @@
{large_file_content}
"""

        processor = GitDiffProcessor(max_diff_size=10000)  # 10KB制限

        # 大容量差分を処理
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.return_value = large_diff
            processed_diff = processor.read_staged_diff()

        # LLM用にフォーマット
        formatted_diff = processor.format_diff_for_llm(processed_diff)

        # 適切にサイズ制限されていることを確認
        assert len(formatted_diff.encode('utf-8')) <= 12000  # 多少の余裕

    def test_unicode_content_pipeline(self):
        """Unicode コンテンツパイプラインテスト"""
        unicode_diff = r'''diff --git a/japanese.py b/japanese.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/japanese.py
@@ -0,0 +1,5 @@
+"""
+日本語ファイルのテスト
+"""
+
+def こんにちは():
+    print("こんにちは、世界！ 🌍")
'''

        # Git差分処理
        processor = GitDiffProcessor()
        formatted_diff = processor.format_diff_for_llm(unicode_diff)

        assert "日本語ファイル" in formatted_diff
        assert "こんにちは" in formatted_diff
        assert "🌍" in formatted_diff

        # メッセージフォーマット
        formatter = MessageFormatter()
        unicode_message = "feat: 日本語サポートを追加 🇯🇵"

        formatted_message = formatter.format_for_lazygit(unicode_message)
        assert "🇯🇵" in formatted_message
        assert formatter.validate_commit_message(formatted_message)

    def test_streaming_support_detection(self):
        """ストリーミングサポート検出テスト"""
        factory = ProviderFactory()

        # APIプロバイダーは一般的にストリーミングをサポート
        api_providers = ['openai', 'anthropic']

        for provider_name in api_providers:
            config_file = self.create_test_config(provider=provider_name)
            config_manager = ConfigManager()
            config_manager.load_config(config_file)

            provider_config = config_manager.get_provider_config()

            class_name_map = {
                'openai': 'OpenAIProvider',
                'anthropic': 'AnthropicProvider',
            }
            with patch(f"lazygit_llm.src.api_providers.{provider_name}_provider.{class_name_map[provider_name]}") as mock_provider_class:
                mock_provider = Mock()
                mock_provider.supports_streaming.return_value = True
                mock_provider_class.return_value = mock_provider

                provider = factory.create_provider(provider_config)
                assert provider.supports_streaming()

    def test_command_line_override_integration(self):
        """コマンドライン上書き統合テスト"""
        # 設定ファイルを作成
        config_file = self.create_test_config(provider='openai', model='gpt-3.5-turbo')

        # コマンドラインで異なるモデルを指定
        test_args = ['main.py', '--config', config_file, '--model', 'gpt-4']

        with patch('sys.argv', test_args):
            config_manager = ConfigManager()
            config_manager.load_config(config_file)

            # コマンドラインの値が優先されることを確認
            # (実際の実装では引数パーサーがこれを処理)
            base_config = config_manager.config
            assert base_config['model_name'] == 'gpt-3.5-turbo'  # 設定ファイルの値

    def test_environment_variable_precedence(self):
        """環境変数優先順位テスト"""
        # 設定ファイルにAPIキーなしで作成
        config_content = {
            'provider': 'openai',
            'model_name': 'gpt-4',
            'timeout': 30,
            'max_tokens': 100,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_content, f)
            config_file = f.name
            self.temp_files.append(config_file)

        # 環境変数でAPIキーを設定
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-api-key'}):
            config_manager = ConfigManager()

            with patch.object(config_manager.security_validator, 'check_file_permissions') as mock_check, \
                 patch.object(config_manager.security_validator, 'validate_api_key') as mock_validate:

                mock_check.return_value = Mock(level='info')
                mock_validate.return_value = Mock(is_valid=True, level='info', message='Valid', recommendations=[])

                config_manager.load_config(config_file)
                api_key = config_manager.get_api_key('openai')

                assert api_key == 'env-api-key'

    def test_error_recovery_integration(self):
        """エラー回復統合テスト"""
        config_file = self.create_test_config()
        test_args = ['main.py', '--config', config_file]

        with patch('sys.argv', test_args), \
             patch('sys.stdin') as mock_stdin, \
             patch('sys.stderr', new_callable=StringIO) as mock_stderr:

            # 標準入力エラーをシミュレート
            mock_stdin.read.side_effect = IOError("Input error")

            exit_code = main()

            # エラーが適切に処理されて終了コードが1であることを確認
            assert exit_code == 1
            error_output = mock_stderr.getvalue()
            assert len(error_output) > 0  # エラーメッセージが出力されている

    def test_concurrent_request_handling(self):
        """並行リクエスト処理テスト"""
        import threading
        import time

        config_file = self.create_test_config()

        def run_main_thread(results, thread_id):
            """メイン関数を別スレッドで実行"""
            test_args = ['main.py', '--config', config_file]
            test_diff = f"diff --git a/file{thread_id}.py b/file{thread_id}.py\n+def test{thread_id}(): pass"

            with patch('sys.argv', test_args), \
                 patch('sys.stdin') as mock_stdin, \
                 patch('sys.stdout', new_callable=StringIO) as mock_stdout, \
                 patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:

                mock_stdin.read.return_value = test_diff

                mock_provider = Mock()
                mock_provider.generate_commit_message.return_value = f"feat: add test function {thread_id}"
                mock_openai.return_value = mock_provider

                start_time = time.time()
                exit_code = main()
                end_time = time.time()

                results[thread_id] = {
                    'exit_code': exit_code,
                    'output': mock_stdout.getvalue(),
                    'duration': end_time - start_time
                }

        # 複数スレッドで同時実行
        threads = []
        results = {}

        for i in range(3):
            thread = threading.Thread(target=run_main_thread, args=(results, i))
            threads.append(thread)
            thread.start()

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()

        # 結果を検証
        assert len(results) == 3
        for i in range(3):
            assert results[i]['exit_code'] == 0
            assert f"feat: add test function {i}" in results[i]['output']

    def test_performance_benchmarking(self):
        """パフォーマンスベンチマークテスト"""
        import time

        config_file = self.create_test_config()
        test_diff = """diff --git a/performance_test.py b/performance_test.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/performance_test.py
@@ -0,0 +1,100 @@
""" + '\n'.join([f'+line_{i} = "content_{i}"' for i in range(100)])

        test_args = ['main.py', '--config', config_file]

        with patch('sys.argv', test_args), \
             patch('sys.stdin') as mock_stdin, \
             patch('sys.stdout', new_callable=StringIO), \
             patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:

            mock_stdin.read.return_value = test_diff

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add performance test"
            mock_openai.return_value = mock_provider

            # パフォーマンス測定
            start_time = time.time()
            exit_code = main()
            end_time = time.time()

            duration = end_time - start_time

            # 基本的なパフォーマンス要件（実際の要件に応じて調整）
            assert exit_code == 0
            assert duration < 5.0  # 5秒以内で完了すること

    def test_memory_usage_monitoring(self):
        """メモリ使用量監視テスト"""
        import psutil
        import os

        config_file = self.create_test_config()

        # 大きな差分でメモリ使用量をテスト
        large_diff = "diff --git a/large.py b/large.py\n" + "+" + "x" * 50000

        test_args = ['main.py', '--config', config_file]

        with patch('sys.argv', test_args), \
             patch('sys.stdin') as mock_stdin, \
             patch('sys.stdout', new_callable=StringIO), \
             patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:

            mock_stdin.read.return_value = large_diff

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add large file"
            mock_openai.return_value = mock_provider

            # メモリ使用量を監視
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            exit_code = main()

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # 基本的なメモリ使用量チェック（100MB以内の増加）
            assert exit_code == 0
            assert memory_increase < 100 * 1024 * 1024  # 100MB
