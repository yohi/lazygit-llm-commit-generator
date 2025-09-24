"""
メインエントリーポイントのユニットテスト

main.pyの統合機能、コマンドライン引数処理、エラーハンドリングをテスト。
"""

import pytest
import sys
import argparse
from unittest.mock import Mock, patch, StringIO
from contextlib import redirect_stdout, redirect_stderr

from lazygit_llm.main import main, setup_logging, parse_arguments, handle_commit_generation
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError


class TestMain:
    """メイン機能のテストクラス"""

    def test_parse_arguments_default(self):
        """デフォルト引数解析テスト"""
        with patch('sys.argv', ['main.py']):
            args = parse_arguments()

            assert args.config is None
            assert args.provider is None
            assert args.model is None
            assert args.verbose is False
            assert args.debug is False
            assert args.test_connection is False
            assert args.timeout == 30

    def test_parse_arguments_with_config(self):
        """設定ファイル指定の引数解析テスト"""
        test_args = ['main.py', '--config', '/path/to/config.yml']

        with patch('sys.argv', test_args):
            args = parse_arguments()

            assert args.config == '/path/to/config.yml'

    def test_parse_arguments_with_provider(self):
        """プロバイダー指定の引数解析テスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args):
            args = parse_arguments()

            assert args.provider == 'openai'
            assert args.model == 'gpt-4'

    def test_parse_arguments_verbose_debug(self):
        """詳細・デバッグフラグの引数解析テスト"""
        test_args = ['main.py', '--verbose', '--debug']

        with patch('sys.argv', test_args):
            args = parse_arguments()

            assert args.verbose is True
            assert args.debug is True

    def test_parse_arguments_test_connection(self):
        """接続テストフラグの引数解析テスト"""
        test_args = ['main.py', '--test-connection']

        with patch('sys.argv', test_args):
            args = parse_arguments()

            assert args.test_connection is True

    def test_parse_arguments_timeout(self):
        """タイムアウト設定の引数解析テスト"""
        test_args = ['main.py', '--timeout', '60']

        with patch('sys.argv', test_args):
            args = parse_arguments()

            assert args.timeout == 60

    def test_setup_logging_default(self):
        """デフォルトログ設定テスト"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging(verbose=False, debug=False)

            mock_config.assert_called_once()
            call_args = mock_config.call_args[1]
            assert call_args['level'] == 30  # logging.WARNING

    def test_setup_logging_verbose(self):
        """詳細ログ設定テスト"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging(verbose=True, debug=False)

            mock_config.assert_called_once()
            call_args = mock_config.call_args[1]
            assert call_args['level'] == 20  # logging.INFO

    def test_setup_logging_debug(self):
        """デバッグログ設定テスト"""
        with patch('logging.basicConfig') as mock_config:
            setup_logging(verbose=False, debug=True)

            mock_config.assert_called_once()
            call_args = mock_config.call_args[1]
            assert call_args['level'] == 10  # logging.DEBUG

    def test_handle_commit_generation_success(self, sample_git_diff):
        """コミットメッセージ生成成功テスト"""
        mock_processor = Mock()
        mock_processor.read_staged_diff.return_value = sample_git_diff
        mock_processor.format_diff_for_llm.return_value = sample_git_diff

        mock_provider = Mock()
        mock_provider.generate_commit_message.return_value = "feat: add new feature"

        mock_formatter = Mock()
        mock_formatter.format_response.return_value = "feat: add new feature"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            result = handle_commit_generation(mock_processor, mock_provider, mock_formatter)

            assert result == 0
            output = mock_stdout.getvalue()
            assert "feat: add new feature" in output

    def test_handle_commit_generation_no_changes(self):
        """変更なしの場合のテスト"""
        mock_processor = Mock()
        mock_processor.has_staged_changes.return_value = False

        mock_provider = Mock()
        mock_formatter = Mock()

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = handle_commit_generation(mock_processor, mock_provider, mock_formatter)

            assert result == 1
            error_output = mock_stderr.getvalue()
            assert "ステージされた変更" in error_output

    def test_handle_commit_generation_provider_error(self, sample_git_diff):
        """プロバイダーエラーの場合のテスト"""
        mock_processor = Mock()
        mock_processor.read_staged_diff.return_value = sample_git_diff
        mock_processor.format_diff_for_llm.return_value = sample_git_diff

        mock_provider = Mock()
        mock_provider.generate_commit_message.side_effect = ProviderError("Provider failed")

        mock_formatter = Mock()

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = handle_commit_generation(mock_processor, mock_provider, mock_formatter)

            assert result == 1
            error_output = mock_stderr.getvalue()
            assert "エラー" in error_output

    def test_handle_commit_generation_authentication_error(self, sample_git_diff):
        """認証エラーの場合のテスト"""
        mock_processor = Mock()
        mock_processor.read_staged_diff.return_value = sample_git_diff
        mock_processor.format_diff_for_llm.return_value = sample_git_diff

        mock_provider = Mock()
        mock_provider.generate_commit_message.side_effect = AuthenticationError("Auth failed")

        mock_formatter = Mock()

        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            result = handle_commit_generation(mock_processor, mock_provider, mock_formatter)

            assert result == 1
            error_output = mock_stderr.getvalue()
            assert "認証" in error_output or "APIキー" in error_output

    def test_main_success_with_config_file(self, temp_config_file, sample_git_diff):
        """設定ファイル使用の成功テスト"""
        test_args = ['main.py', '--config', temp_config_file]

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter_class, \
             patch('lazygit_llm.src.config_manager.ConfigManager') as mock_config_class:

            # モックの設定
            mock_processor = Mock()
            mock_processor.has_staged_changes.return_value = True
            mock_processor.read_staged_diff.return_value = sample_git_diff
            mock_processor.format_diff_for_llm.return_value = sample_git_diff
            mock_processor_class.return_value = mock_processor

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add new feature"
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_formatter = Mock()
            mock_formatter.format_response.return_value = "feat: add new feature"
            mock_formatter_class.return_value = mock_formatter

            mock_config = Mock()
            mock_config.load_config.return_value = {}
            mock_config.get_provider_config.return_value = Mock()
            mock_config_class.return_value = mock_config

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = main()

                assert result == 0
                output = mock_stdout.getvalue()
                assert "feat: add new feature" in output

    def test_main_success_with_command_line_args(self, sample_git_diff):
        """コマンドライン引数使用の成功テスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter_class, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):

            # モックの設定
            mock_processor = Mock()
            mock_processor.has_staged_changes.return_value = True
            mock_processor.read_staged_diff.return_value = sample_git_diff
            mock_processor.format_diff_for_llm.return_value = sample_git_diff
            mock_processor_class.return_value = mock_processor

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add new feature"
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_formatter = Mock()
            mock_formatter.format_response.return_value = "feat: add new feature"
            mock_formatter_class.return_value = mock_formatter

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = main()

                assert result == 0
                output = mock_stdout.getvalue()
                assert "feat: add new feature" in output

    def test_main_test_connection_success(self, temp_config_file):
        """接続テスト成功"""
        test_args = ['main.py', '--config', temp_config_file, '--test-connection']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.config_manager.ConfigManager') as mock_config_class:

            mock_provider = Mock()
            mock_provider.test_connection.return_value = True
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_config = Mock()
            mock_config.load_config.return_value = {}
            mock_config.get_provider_config.return_value = Mock()
            mock_config_class.return_value = mock_config

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = main()

                assert result == 0
                output = mock_stdout.getvalue()
                assert "接続テスト成功" in output

    def test_main_test_connection_failure(self, temp_config_file):
        """接続テスト失敗"""
        test_args = ['main.py', '--config', temp_config_file, '--test-connection']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.config_manager.ConfigManager') as mock_config_class:

            mock_provider = Mock()
            mock_provider.test_connection.return_value = False
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_config = Mock()
            mock_config.load_config.return_value = {}
            mock_config.get_provider_config.return_value = Mock()
            mock_config_class.return_value = mock_config

            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                error_output = mock_stderr.getvalue()
                assert "接続テスト失敗" in error_output

    def test_main_missing_config_and_provider(self):
        """設定もプロバイダーも指定されていない場合のエラーテスト"""
        test_args = ['main.py']

        with patch('sys.argv', test_args):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                error_output = mock_stderr.getvalue()
                assert "設定ファイル" in error_output or "プロバイダー" in error_output

    def test_main_missing_api_key(self):
        """APIキー不足の場合のエラーテスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args):
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                error_output = mock_stderr.getvalue()
                assert "APIキー" in error_output

    def test_main_keyboard_interrupt(self, sample_git_diff):
        """キーボード割り込みの処理テスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):

            mock_processor = Mock()
            mock_processor.has_staged_changes.side_effect = KeyboardInterrupt()
            mock_processor_class.return_value = mock_processor

            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                error_output = mock_stderr.getvalue()
                assert "中断" in error_output

    def test_main_unexpected_error(self, sample_git_diff):
        """予期しないエラーの処理テスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):

            mock_processor = Mock()
            mock_processor.has_staged_changes.side_effect = RuntimeError("Unexpected error")
            mock_processor_class.return_value = mock_processor

            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                error_output = mock_stderr.getvalue()
                assert "予期しないエラー" in error_output

    def test_main_verbose_logging(self, temp_config_file, sample_git_diff):
        """詳細ログ出力のテスト"""
        test_args = ['main.py', '--config', temp_config_file, '--verbose']

        with patch('sys.argv', test_args), \
             patch('logging.basicConfig') as mock_log_config, \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter_class, \
             patch('lazygit_llm.src.config_manager.ConfigManager') as mock_config_class:

            # モックの設定
            mock_processor = Mock()
            mock_processor.has_staged_changes.return_value = True
            mock_processor.read_staged_diff.return_value = sample_git_diff
            mock_processor.format_diff_for_llm.return_value = sample_git_diff
            mock_processor_class.return_value = mock_processor

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add new feature"
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_formatter = Mock()
            mock_formatter.format_response.return_value = "feat: add new feature"
            mock_formatter_class.return_value = mock_formatter

            mock_config = Mock()
            mock_config.load_config.return_value = {}
            mock_config.get_provider_config.return_value = Mock()
            mock_config_class.return_value = mock_config

            result = main()

            assert result == 0
            # 詳細ログが有効になっていることを確認
            mock_log_config.assert_called_once()
            call_args = mock_log_config.call_args[1]
            assert call_args['level'] == 20  # logging.INFO

    def test_main_debug_logging(self, temp_config_file, sample_git_diff):
        """デバッグログ出力のテスト"""
        test_args = ['main.py', '--config', temp_config_file, '--debug']

        with patch('sys.argv', test_args), \
             patch('logging.basicConfig') as mock_log_config, \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter_class, \
             patch('lazygit_llm.src.config_manager.ConfigManager') as mock_config_class:

            # モックの設定
            mock_processor = Mock()
            mock_processor.has_staged_changes.return_value = True
            mock_processor.read_staged_diff.return_value = sample_git_diff
            mock_processor.format_diff_for_llm.return_value = sample_git_diff
            mock_processor_class.return_value = mock_processor

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add new feature"
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_formatter = Mock()
            mock_formatter.format_response.return_value = "feat: add new feature"
            mock_formatter_class.return_value = mock_formatter

            mock_config = Mock()
            mock_config.load_config.return_value = {}
            mock_config.get_provider_config.return_value = Mock()
            mock_config_class.return_value = mock_config

            result = main()

            assert result == 0
            # デバッグログが有効になっていることを確認
            mock_log_config.assert_called_once()
            call_args = mock_log_config.call_args[1]
            assert call_args['level'] == 10  # logging.DEBUG

    @pytest.mark.parametrize("provider,model,env_var", [
        ('openai', 'gpt-4', 'OPENAI_API_KEY'),
        ('anthropic', 'claude-3-5-sonnet-20241022', 'ANTHROPIC_API_KEY'),
        ('gemini', 'gemini-1.5-pro', 'GOOGLE_API_KEY'),
    ])
    def test_main_different_providers(self, provider, model, env_var, sample_git_diff):
        """異なるプロバイダーでのメイン機能テスト"""
        test_args = ['main.py', '--provider', provider, '--model', model]

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.message_formatter.MessageFormatter') as mock_formatter_class, \
             patch.dict('os.environ', {env_var: 'test-key'}):

            # モックの設定
            mock_processor = Mock()
            mock_processor.has_staged_changes.return_value = True
            mock_processor.read_staged_diff.return_value = sample_git_diff
            mock_processor.format_diff_for_llm.return_value = sample_git_diff
            mock_processor_class.return_value = mock_processor

            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = f"{provider}: add new feature"
            mock_factory = Mock()
            mock_factory.create_provider.return_value = mock_provider
            mock_factory_class.return_value = mock_factory

            mock_formatter = Mock()
            mock_formatter.format_response.return_value = f"{provider}: add new feature"
            mock_formatter_class.return_value = mock_formatter

            with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = main()

                assert result == 0
                output = mock_stdout.getvalue()
                assert f"{provider}: add new feature" in output

    def test_error_handling_integration(self, sample_git_diff):
        """エラーハンドリング統合テスト"""
        test_args = ['main.py', '--provider', 'openai', '--model', 'gpt-4']

        with patch('sys.argv', test_args), \
             patch('lazygit_llm.src.git_processor.GitDiffProcessor') as mock_processor_class, \
             patch('lazygit_llm.src.provider_factory.ProviderFactory') as mock_factory_class, \
             patch('lazygit_llm.src.error_handler.ErrorHandler') as mock_error_handler_class, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):

            # エラーハンドラーのモック
            mock_error_handler = Mock()
            mock_error_handler.handle_error.return_value = {
                'user_message': 'テストエラーメッセージ',
                'suggestions': ['提案1', '提案2']
            }
            mock_error_handler.format_error_message_for_user.return_value = 'フォーマット済みエラーメッセージ'
            mock_error_handler_class.return_value = mock_error_handler

            # プロセッサーでエラーを発生させる
            mock_processor = Mock()
            mock_processor.has_staged_changes.side_effect = TimeoutError("Timeout occurred")
            mock_processor_class.return_value = mock_processor

            mock_factory = Mock()
            mock_factory_class.return_value = mock_factory

            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main()

                assert result == 1
                # エラーハンドラーが呼び出されていることを確認
                mock_error_handler.handle_error.assert_called_once()
                mock_error_handler.format_error_message_for_user.assert_called_once()

    def test_help_message_display(self):
        """ヘルプメッセージ表示テスト"""
        test_args = ['main.py', '--help']

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    parse_arguments()

                    output = mock_stdout.getvalue()
                    assert "usage:" in output
                    assert "--config" in output
                    assert "--provider" in output
