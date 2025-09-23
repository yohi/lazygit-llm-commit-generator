"""
OpenAIProviderのユニットテスト

OpenAI GPT APIを使用したコミットメッセージ生成機能をテスト。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import openai

from lazygit_llm.src.api_providers.openai_provider import OpenAIProvider
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError, ResponseError


class TestOpenAIProvider:
    """OpenAIProviderのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.config = {
            'api_key': 'test-api-key',
            'model_name': 'gpt-4',
            'timeout': 30,
            'max_tokens': 100,
            'prompt_template': 'Generate commit message: {diff}',
            'additional_params': {
                'temperature': 0.3,
                'top_p': 0.9
            }
        }

    def test_initialization_success(self):
        """正常初期化テスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            assert provider.api_key == 'test-api-key'
            assert provider.model_name == 'gpt-4'
            assert provider.timeout == 30
            assert provider.max_tokens == 100
            assert provider.client == mock_client
            mock_openai_class.assert_called_once_with(api_key='test-api-key')

    def test_initialization_missing_api_key(self):
        """APIキー不足時の初期化エラーテスト"""
        config_without_key = self.config.copy()
        del config_without_key['api_key']

        with pytest.raises(ProviderError, match="APIキーが設定されていません"):
            OpenAIProvider(config_without_key)

    def test_initialization_missing_model(self):
        """モデル名不足時の初期化エラーテスト"""
        config_without_model = self.config.copy()
        del config_without_model['model_name']

        with pytest.raises(ProviderError, match="モデル名が設定されていません"):
            OpenAIProvider(config_without_model)

    def test_initialization_openai_unavailable(self):
        """OpenAIライブラリ不可用時のテスト"""
        with patch('lazygit_llm.src.api_providers.openai_provider.OPENAI_AVAILABLE', False):
            with pytest.raises(ProviderError, match="OpenAIライブラリがインストールされていません"):
                OpenAIProvider(self.config)

    def test_generate_commit_message_success(self, sample_git_diff):
        """コミットメッセージ生成成功テスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            # モックの設定
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "feat: add new feature"

            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)
            result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add new feature"

            # API呼び出しの確認
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['model'] == 'gpt-4'
            assert call_args[1]['max_tokens'] == 100
            assert call_args[1]['temperature'] == 0.3
            assert call_args[1]['top_p'] == 0.9

    def test_generate_commit_message_empty_diff(self):
        """空の差分でのエラーテスト"""
        with patch('openai.OpenAI'):
            provider = OpenAIProvider(self.config)

            with pytest.raises(ProviderError, match="空の差分データです"):
                provider.generate_commit_message("")

    def test_generate_commit_message_authentication_error(self, sample_git_diff):
        """認証エラーテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
                message="Invalid API key",
                response=Mock(),
                body=None
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(AuthenticationError, match="OpenAI API認証エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_rate_limit_error(self, sample_git_diff):
        """レート制限エラーテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.RateLimitError(
                message="Rate limit exceeded",
                response=Mock(),
                body=None
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(ResponseError, match="OpenAI APIレート制限エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_timeout_error(self, sample_git_diff):
        """タイムアウトエラーテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.APITimeoutError(
                request=Mock()
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(TimeoutError, match="OpenAI APIタイムアウト"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_api_error(self, sample_git_diff):
        """一般的なAPIエラーテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.APIError(
                message="API Error",
                request=Mock(),
                body=None
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(ResponseError, match="OpenAI APIエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_unexpected_error(self, sample_git_diff):
        """予期しないエラーテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("Unexpected error")
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(ProviderError, match="予期しないエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_empty_response(self, sample_git_diff):
        """空のレスポンステスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = ""

            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(ResponseError, match="OpenAIから空のレスポンス"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_no_choices(self, sample_git_diff):
        """選択肢なしのレスポンステスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = []

            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with pytest.raises(ResponseError, match="OpenAIから無効なレスポンス形式"):
                provider.generate_commit_message(sample_git_diff)

    def test_build_prompt(self, sample_git_diff):
        """プロンプト構築テスト"""
        with patch('openai.OpenAI'):
            provider = OpenAIProvider(self.config)
            prompt = provider._build_prompt(sample_git_diff)

            assert sample_git_diff in prompt
            assert "Generate commit message:" in prompt

    def test_build_prompt_custom_template(self, sample_git_diff):
        """カスタムプロンプトテンプレートテスト"""
        custom_config = self.config.copy()
        custom_config['prompt_template'] = "Custom template: {diff}\nGenerate a message."

        with patch('openai.OpenAI'):
            provider = OpenAIProvider(custom_config)
            prompt = provider._build_prompt(sample_git_diff)

            assert "Custom template:" in prompt
            assert sample_git_diff in prompt
            assert "Generate a message." in prompt

    def test_extract_response_content_success(self):
        """レスポンス内容抽出成功テスト"""
        with patch('openai.OpenAI'):
            provider = OpenAIProvider(self.config)

            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "fix: resolve issue"

            result = provider._extract_response_content(mock_response)
            assert result == "fix: resolve issue"

    def test_test_connection_success(self):
        """接続テスト成功"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "test response"

            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)
            result = provider.test_connection()

            assert result is True

    def test_test_connection_failure(self):
        """接続テスト失敗"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
                message="Invalid API key",
                response=Mock(),
                body=None
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)
            result = provider.test_connection()

            assert result is False

    def test_supports_streaming(self):
        """ストリーミング対応確認テスト"""
        with patch('openai.OpenAI'):
            provider = OpenAIProvider(self.config)
            assert provider.supports_streaming() is True

    def test_generate_with_streaming(self, sample_git_diff):
        """ストリーミング対応生成テスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            # ストリーミングレスポンスのモック
            mock_client = Mock()
            mock_stream = [
                Mock(choices=[Mock(delta=Mock(content="feat:"))]),
                Mock(choices=[Mock(delta=Mock(content=" add"))]),
                Mock(choices=[Mock(delta=Mock(content=" feature"))]),
            ]

            mock_client.chat.completions.create.return_value = mock_stream
            mock_openai_class.return_value = mock_client

            # ストリーミング有効の設定
            streaming_config = self.config.copy()
            streaming_config['additional_params']['stream'] = True

            provider = OpenAIProvider(streaming_config)
            result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add feature"

            # ストリーミングが有効になっていることを確認
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['stream'] is True

    def test_retry_logic(self, sample_git_diff):
        """リトライロジックテスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()

            # 最初の2回は失敗、3回目は成功
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "feat: add retry logic"

            mock_client.chat.completions.create.side_effect = [
                openai.RateLimitError(message="Rate limit", response=Mock(), body=None),
                openai.APIError(message="Temporary error", request=Mock(), body=None),
                mock_response
            ]
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add retry logic"
            assert mock_client.chat.completions.create.call_count == 3

    def test_max_retries_exceeded(self, sample_git_diff):
        """最大リトライ回数超過テスト"""
        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = openai.RateLimitError(
                message="Rate limit",
                response=Mock(),
                body=None
            )
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                with pytest.raises(ResponseError, match="最大リトライ回数"):
                    provider.generate_commit_message(sample_git_diff)

    @pytest.mark.parametrize("model_name,expected_max_tokens", [
        ("gpt-4", 100),
        ("gpt-3.5-turbo", 100),
        ("gpt-4-turbo", 100),
    ])
    def test_different_models(self, model_name, expected_max_tokens):
        """異なるモデルでの動作テスト"""
        config = self.config.copy()
        config['model_name'] = model_name

        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(config)

            assert provider.model_name == model_name

    def test_additional_params_application(self, sample_git_diff):
        """追加パラメータの適用テスト"""
        config_with_params = self.config.copy()
        config_with_params['additional_params'] = {
            'temperature': 0.5,
            'top_p': 0.8,
            'frequency_penalty': 0.1,
            'presence_penalty': 0.2,
            'stream': False
        }

        with patch('openai.OpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock()
            mock_response.choices[0].message.content = "test: commit message"

            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_class.return_value = mock_client

            provider = OpenAIProvider(config_with_params)
            provider.generate_commit_message(sample_git_diff)

            # パラメータが正しく適用されていることを確認
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]['temperature'] == 0.5
            assert call_args[1]['top_p'] == 0.8
            assert call_args[1]['frequency_penalty'] == 0.1
            assert call_args[1]['presence_penalty'] == 0.2
            assert call_args[1]['stream'] is False