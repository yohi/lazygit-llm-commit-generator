"""
AnthropicProviderのユニットテスト

Anthropic Claude APIを使用したコミットメッセージ生成機能をテスト。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import anthropic

from lazygit_llm.src.api_providers.anthropic_provider import AnthropicProvider
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError, ResponseError


class TestAnthropicProvider:
    """AnthropicProviderのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.config = {
            'api_key': 'sk-ant-api03-test-api-key-1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef-1234567890abcdef',
            'model_name': 'claude-3-5-sonnet-20241022',
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
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            assert provider.api_key == self.config['api_key']
            assert provider.model_name == 'claude-3-5-sonnet-20241022'
            assert provider.timeout == 30
            assert provider.max_tokens == 100
            assert provider.client == mock_client
            mock_anthropic_class.assert_called_once_with(api_key=self.config['api_key'])

    def test_initialization_missing_api_key(self):
        """APIキー不足時の初期化エラーテスト"""
        config_without_key = self.config.copy()
        del config_without_key['api_key']

        with pytest.raises(ProviderError, match="APIキーが設定されていません"):
            AnthropicProvider(config_without_key)

    def test_initialization_missing_model(self):
        """モデル名不足時の初期化エラーテスト"""
        config_without_model = self.config.copy()
        del config_without_model['model_name']

        with pytest.raises(ProviderError, match="モデル名が設定されていません"):
            AnthropicProvider(config_without_model)

    def test_initialization_anthropic_unavailable(self):
        """Anthropicライブラリ不可用時のテスト"""
        with patch('lazygit_llm.src.api_providers.anthropic_provider.ANTHROPIC_AVAILABLE', False):
            with pytest.raises(ProviderError, match="Anthropicライブラリがインストールされていません"):
                AnthropicProvider(self.config)

    def test_generate_commit_message_success(self, sample_git_diff):
        """コミットメッセージ生成成功テスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # モックの設定
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "feat: add new feature"

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)
            result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add new feature"

            # API呼び出しの確認
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['model'] == 'claude-3-5-sonnet-20241022'
            assert call_args[1]['max_tokens'] == 100
            assert call_args[1]['temperature'] == 0.3
            assert call_args[1]['top_p'] == 0.9

    def test_generate_commit_message_empty_diff(self):
        """空の差分でのエラーテスト"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(self.config)

            with pytest.raises(ProviderError, match="空の差分データです"):
                provider.generate_commit_message("")

    def test_generate_commit_message_authentication_error(self, sample_git_diff):
        """認証エラーテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.AuthenticationError(
                message="Invalid API key",
                response=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(AuthenticationError, match="Anthropic API認証エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_rate_limit_error(self, sample_git_diff):
        """レート制限エラーテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.RateLimitError(
                message="Rate limit exceeded",
                response=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ResponseError, match="Anthropic APIレート制限エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_timeout_error(self, sample_git_diff):
        """タイムアウトエラーテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.APITimeoutError(
                request=Mock()
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(TimeoutError, match="Anthropic APIタイムアウト"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_api_error(self, sample_git_diff):
        """一般的なAPIエラーテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.APIError(
                message="API Error",
                request=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ResponseError, match="Anthropic APIエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_unexpected_error(self, sample_git_diff):
        """予期しないエラーテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = Exception("Unexpected error")
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ProviderError, match="予期しないエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_empty_response(self, sample_git_diff):
        """空のレスポンステスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = ""

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ResponseError, match="Anthropicから空のレスポンス"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_no_content(self, sample_git_diff):
        """コンテンツなしのレスポンステスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = []

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ResponseError, match="Anthropicから無効なレスポンス形式"):
                provider.generate_commit_message(sample_git_diff)

    def test_build_prompt(self, sample_git_diff):
        """プロンプト構築テスト"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(self.config)
            prompt = provider._build_prompt(sample_git_diff)

            assert sample_git_diff in prompt
            assert "Generate commit message:" in prompt

    def test_build_prompt_custom_template(self, sample_git_diff):
        """カスタムプロンプトテンプレートテスト"""
        custom_config = self.config.copy()
        custom_config['prompt_template'] = "Custom template: {diff}\nGenerate a message."

        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(custom_config)
            prompt = provider._build_prompt(sample_git_diff)

            assert "Custom template:" in prompt
            assert sample_git_diff in prompt
            assert "Generate a message." in prompt

    def test_extract_response_content_success(self):
        """レスポンス内容抽出成功テスト"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(self.config)

            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "fix: resolve issue"

            result = provider._extract_response_content(mock_response)
            assert result == "fix: resolve issue"

    def test_test_connection_success(self):
        """接続テスト成功"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "test response"

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)
            result = provider.test_connection()

            assert result is True

    def test_test_connection_failure(self):
        """接続テスト失敗"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.AuthenticationError(
                message="Invalid API key",
                response=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)
            result = provider.test_connection()

            assert result is False

    def test_supports_streaming(self):
        """ストリーミング対応確認テスト"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(self.config)
            assert provider.supports_streaming() is True

    def test_generate_with_streaming(self, sample_git_diff):
        """ストリーミング対応生成テスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            # ストリーミングレスポンスのモック
            mock_client = Mock()
            mock_stream = [
                Mock(event='content_block_delta', delta=Mock(text="feat:")),
                Mock(event='content_block_delta', delta=Mock(text=" add")),
                Mock(event='content_block_delta', delta=Mock(text=" feature")),
                Mock(event='message_stop'),
            ]

            mock_client.messages.create.return_value = mock_stream
            mock_anthropic_class.return_value = mock_client

            # ストリーミング有効の設定
            streaming_config = self.config.copy()
            streaming_config['additional_params']['stream'] = True

            provider = AnthropicProvider(streaming_config)
            result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add feature"

            # ストリーミングが有効になっていることを確認
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['stream'] is True

    def test_retry_logic(self, sample_git_diff):
        """リトライロジックテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()

            # 最初の2回は失敗、3回目は成功
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "feat: add retry logic"

            mock_client.messages.create.side_effect = [
                anthropic.RateLimitError(message="Rate limit", response=Mock(), body=None),
                anthropic.APIError(message="Temporary error", request=Mock(), body=None),
                mock_response
            ]
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add retry logic"
            assert mock_client.messages.create.call_count == 3

    def test_max_retries_exceeded(self, sample_git_diff):
        """最大リトライ回数超過テスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_client.messages.create.side_effect = anthropic.RateLimitError(
                message="Rate limit",
                response=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                with pytest.raises(ResponseError, match="最大リトライ回数"):
                    provider.generate_commit_message(sample_git_diff)

    @pytest.mark.parametrize("model_name,expected_max_tokens", [
        ("claude-3-5-sonnet-20241022", 100),
        ("claude-3-haiku-20240307", 100),
        ("claude-3-opus-20240229", 100),
    ])
    def test_different_models(self, model_name, expected_max_tokens):
        """異なるモデルでの動作テスト"""
        config = self.config.copy()
        config['model_name'] = model_name

        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(config)

            assert provider.model_name == model_name

    def test_additional_params_application(self, sample_git_diff):
        """追加パラメータの適用テスト"""
        config_with_params = self.config.copy()
        config_with_params['additional_params'] = {
            'temperature': 0.5,
            'top_p': 0.8,
            'top_k': 40,
            'stream': False
        }

        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "test: commit message"

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(config_with_params)
            provider.generate_commit_message(sample_git_diff)

            # パラメータが正しく適用されていることを確認
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['temperature'] == 0.5
            assert call_args[1]['top_p'] == 0.8
            assert call_args[1]['top_k'] == 40
            assert call_args[1]['stream'] is False

    def test_build_messages_structure(self, sample_git_diff):
        """メッセージ構造構築テスト"""
        with patch('anthropic.Anthropic'):
            provider = AnthropicProvider(self.config)
            messages = provider._build_messages(sample_git_diff)

            assert len(messages) == 1
            assert messages[0]['role'] == 'user'
            assert 'content' in messages[0]
            assert sample_git_diff in messages[0]['content']

    def test_anthropic_specific_error_handling(self, sample_git_diff):
        """Anthropic固有のエラーハンドリングテスト"""
        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()

            # Anthropic固有のエラー
            mock_client.messages.create.side_effect = anthropic.BadRequestError(
                message="Invalid request",
                response=Mock(),
                body=None
            )
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(self.config)

            with pytest.raises(ResponseError, match="Anthropic APIエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_system_message_handling(self, sample_git_diff):
        """システムメッセージの処理テスト"""
        config_with_system = self.config.copy()
        config_with_system['system_message'] = "You are a helpful assistant for git commits."

        with patch('anthropic.Anthropic') as mock_anthropic_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock()]
            mock_response.content[0].text = "feat: add system message support"

            mock_client.messages.create.return_value = mock_response
            mock_anthropic_class.return_value = mock_client

            provider = AnthropicProvider(config_with_system)
            provider.generate_commit_message(sample_git_diff)

            # システムメッセージが適用されていることを確認
            call_args = mock_client.messages.create.call_args
            assert 'system' in call_args[1]
            assert call_args[1]['system'] == "You are a helpful assistant for git commits."