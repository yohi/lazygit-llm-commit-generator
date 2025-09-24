"""
Gemini Direct CLI プロバイダーのテスト
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from lazygit_llm.cli_providers.gemini_direct_cli_provider import GeminiDirectCLIProvider
from lazygit_llm.base_provider import ProviderError, AuthenticationError, ProviderTimeoutError, ResponseError


@pytest.fixture
def sample_config():
    """テスト用設定"""
    return {
        'provider': 'gemini-cli',
        'model_name': 'gemini-1.5-pro',
        'timeout': 30,
        'max_tokens': 100,
        'additional_params': {
            'temperature': 0.3,
            'api_key': 'test-api-key'
        }
    }


@pytest.fixture
def sample_git_diff():
    """テスト用Git差分"""
    return """--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,4 @@
 def main():
+    print("Hello, World!")
     pass
"""


class TestGeminiDirectCLIProvider:
    """Gemini Direct CLI プロバイダーのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.provider = None

    def teardown_method(self):
        """各テストメソッドの後に実行"""
        self.provider = None

    @patch('shutil.which')
    def test_init_success(self, mock_which, sample_config):
        """初期化成功テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'

        provider = GeminiDirectCLIProvider(sample_config)

        assert provider.model == 'gemini-1.5-pro'
        assert provider.temperature == 0.3
        assert provider.api_key == 'test-api-key'
        assert provider.gemini_path == '/usr/local/bin/gemini'

    @patch('shutil.which')
    def test_init_gemini_not_found(self, mock_which, sample_config):
        """geminiコマンドが見つからない場合のテスト"""
        mock_which.return_value = None

        with pytest.raises(ProviderError, match="geminiコマンドが見つかりません"):
            GeminiDirectCLIProvider(sample_config)

    @patch('shutil.which')
    def test_init_invalid_binary(self, mock_which, sample_config):
        """無効なバイナリの場合のテスト"""
        mock_which.return_value = '/usr/bin/malicious'

        with pytest.raises(ProviderError, match="許可されていないバイナリ"):
            GeminiDirectCLIProvider(sample_config)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_success(self, mock_run, mock_which, sample_config, sample_git_diff):
        """コミットメッセージ生成成功テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="feat: add hello world message\n",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        result = provider.generate_commit_message(sample_git_diff, prompt_template)

        assert result == "feat: add hello world message"
        mock_run.assert_called_once()

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_with_prefix_cleanup(self, mock_run, mock_which, sample_config, sample_git_diff):
        """プレフィックス付きレスポンスのクリーンアップテスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Commit message: feat: add hello world message\n",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        result = provider.generate_commit_message(sample_git_diff, prompt_template)

        assert result == "feat: add hello world message"

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_with_markdown_cleanup(self, mock_run, mock_which, sample_config, sample_git_diff):
        """マークダウンコードブロックのクリーンアップテスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="```\nfeat: add hello world message\n```",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        result = provider.generate_commit_message(sample_git_diff, prompt_template)

        assert result == "feat: add hello world message"

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_timeout(self, mock_run, mock_which, sample_config, sample_git_diff):
        """タイムアウトエラーテスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.side_effect = subprocess.TimeoutExpired('gemini', 30)

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        with pytest.raises(ProviderTimeoutError):
            provider.generate_commit_message(sample_git_diff, prompt_template)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_auth_error(self, mock_run, mock_which, sample_config, sample_git_diff):
        """認証エラーテスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.side_effect = subprocess.CalledProcessError(1, 'gemini', "Authentication failed")

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        with pytest.raises(AuthenticationError):
            provider.generate_commit_message(sample_git_diff, prompt_template)

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_generate_commit_message_empty_response(self, mock_run, mock_which, sample_config, sample_git_diff):
        """空のレスポンステスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        prompt_template = "Generate commit message: {diff}"

        with pytest.raises(ResponseError, match="Geminiからの無効なレスポンス"):
            provider.generate_commit_message(sample_git_diff, prompt_template)

    @patch('shutil.which')
    @patch('tempfile.NamedTemporaryFile')
    @patch('subprocess.run')
    @patch('os.unlink')
    def test_execute_with_tempfile(self, mock_unlink, mock_run, mock_tempfile, mock_which, sample_config):
        """大きなプロンプトのファイル経由実行テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'

        # 一時ファイルのモック
        mock_file = MagicMock()
        mock_file.name = '/tmp/test.txt'
        mock_tempfile.return_value.__enter__.return_value = mock_file

        mock_run.return_value = Mock(
            returncode=0,
            stdout="feat: large prompt response\n",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        large_prompt = "x" * 10000  # 8KBを超える大きなプロンプト

        result = provider._execute_gemini_command(large_prompt)

        assert result == "feat: large prompt response\n"
        mock_tempfile.assert_called_once()
        mock_file.write.assert_called_once_with(large_prompt)
        mock_unlink.assert_called_once_with('/tmp/test.txt')

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_execute_with_args(self, mock_run, mock_which, sample_config):
        """小さなプロンプトのコマンド引数実行テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="feat: small prompt response\n",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)
        small_prompt = "Generate commit message"

        result = provider._execute_gemini_command(small_prompt)

        assert result == "feat: small prompt response\n"
        # コマンド引数に --prompt が含まれることを確認
        call_args = mock_run.call_args[0][0]
        assert '--prompt' in call_args
        assert small_prompt in call_args

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_test_connection_success(self, mock_run, mock_which, sample_config):
        """接続テスト成功"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.return_value = Mock(
            returncode=0,
            stdout="OK\n",
            stderr=""
        )

        provider = GeminiDirectCLIProvider(sample_config)

        assert provider.test_connection() is True

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_test_connection_timeout(self, mock_run, mock_which, sample_config):
        """接続テストタイムアウト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        mock_run.side_effect = subprocess.TimeoutExpired('gemini', 10)

        provider = GeminiDirectCLIProvider(sample_config)

        with pytest.raises(ProviderTimeoutError):
            provider.test_connection()

    @patch('shutil.which')
    def test_get_model_info(self, mock_which, sample_config):
        """モデル情報取得テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'

        provider = GeminiDirectCLIProvider(sample_config)
        info = provider.get_model_info()

        assert info['provider'] == 'gemini-cli'
        assert info['model'] == 'gemini-1.5-pro'
        assert info['temperature'] == 0.3
        assert info['cli_path'] == '/usr/local/bin/gemini'

    @patch('shutil.which')
    def test_get_required_config_fields(self, mock_which, sample_config):
        """必須設定項目取得テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'

        provider = GeminiDirectCLIProvider(sample_config)
        required_fields = provider.get_required_config_fields()

        assert required_fields == ['model_name']

    @patch('shutil.which')
    def test_validate_config_success(self, mock_which, sample_config):
        """設定検証成功テスト"""
        mock_which.return_value = '/usr/local/bin/gemini'

        provider = GeminiDirectCLIProvider(sample_config)

        assert provider.validate_config() is True

    def test_validate_config_invalid_model_name(self, sample_config):
        """無効なモデル名の設定検証テスト"""
        sample_config['model_name'] = ""

        with patch('shutil.which', return_value='/usr/local/bin/gemini'):
            provider = GeminiDirectCLIProvider(sample_config)
            assert provider.validate_config() is False

    def test_validate_config_invalid_timeout(self, sample_config):
        """無効なタイムアウトの設定検証テスト"""
        sample_config['timeout'] = -1

        with patch('shutil.which', return_value='/usr/local/bin/gemini'):
            provider = GeminiDirectCLIProvider(sample_config)
            assert provider.validate_config() is False

    @patch('shutil.which')
    def test_clean_response_various_formats(self, mock_which, sample_config):
        """様々な形式のレスポンスクリーンアップテスト"""
        mock_which.return_value = '/usr/local/bin/gemini'
        provider = GeminiDirectCLIProvider(sample_config)

        # 引用符付きレスポンス
        assert provider._clean_response('"feat: add feature"') == "feat: add feature"
        assert provider._clean_response("'feat: add feature'") == "feat: add feature"

        # プレフィックス付きレスポンス
        assert provider._clean_response("Commit message: feat: add feature") == "feat: add feature"
        assert provider._clean_response("Here's a commit message: feat: add feature") == "feat: add feature"

        # 前後の空白
        assert provider._clean_response("  feat: add feature  ") == "feat: add feature"

    def test_response_validation(self, sample_config):
        """レスポンス検証テスト"""
        with patch('shutil.which', return_value='/usr/local/bin/gemini'):
            provider = GeminiDirectCLIProvider(sample_config)

            # 有効なレスポンス
            assert provider._validate_response("feat: add feature") is True

            # 無効なレスポンス
            assert provider._validate_response("") is False
            assert provider._validate_response("   ") is False
            assert provider._validate_response("x" * (provider.MAX_STDOUT_SIZE + 1)) is False
