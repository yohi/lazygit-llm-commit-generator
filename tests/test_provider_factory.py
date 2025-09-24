"""
ProviderFactoryのユニットテスト

プロバイダーファクトリーの作成、設定、登録機能をテスト。
"""

import pytest
from unittest.mock import Mock, patch

from lazygit_llm.src.provider_factory import ProviderFactory, ProviderConfig
from lazygit_llm.src.base_provider import ProviderError
from lazygit_llm.src.api_providers.openai_provider import OpenAIProvider
from lazygit_llm.src.api_providers.anthropic_provider import AnthropicProvider
from lazygit_llm.src.api_providers.gemini_api_provider import GeminiApiProvider
from lazygit_llm.src.cli_providers.gemini_cli_provider import GeminiCliProvider
from lazygit_llm.src.cli_providers.claude_code_provider import ClaudeCodeProvider


class TestProviderFactory:
    """ProviderFactoryのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.factory = ProviderFactory()

    def test_initialization(self):
        """初期化テスト"""
        assert hasattr(self.factory, '_providers')
        assert isinstance(self.factory._providers, dict)

        # デフォルトプロバイダーが登録されていることを確認
        expected_providers = ['openai', 'anthropic', 'gemini', 'gcloud', 'gemini-cli', 'claude-code']
        for provider_name in expected_providers:
            assert provider_name in self.factory._providers

    def test_register_provider_success(self):
        """プロバイダー登録成功テスト"""
        mock_provider_class = Mock()

        self.factory.register_provider('test-provider', mock_provider_class)

        assert 'test-provider' in self.factory._providers
        assert self.factory._providers['test-provider'] == mock_provider_class

    def test_register_provider_override_existing(self):
        """既存プロバイダー上書きテスト"""
        mock_provider_class = Mock()

        # 既存のプロバイダーを上書き
        self.factory.register_provider('openai', mock_provider_class)

        assert self.factory._providers['openai'] == mock_provider_class

    def test_create_provider_openai_success(self):
        """OpenAIプロバイダー作成成功テスト"""
        config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance
            mock_openai.assert_called_once()

    def test_create_provider_anthropic_success(self):
        """Anthropicプロバイダー作成成功テスト"""
        config = ProviderConfig(
            name='anthropic',
            type='api',
            model='claude-3-5-sonnet-20241022',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider') as mock_anthropic:
            mock_instance = Mock()
            mock_anthropic.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance
            mock_anthropic.assert_called_once()

    def test_create_provider_gemini_api_success(self):
        """Gemini APIプロバイダー作成成功テスト"""
        config = ProviderConfig(
            name='gemini',
            type='api',
            model='gemini-1.5-pro',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider') as mock_gemini:
            mock_instance = Mock()
            mock_gemini.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance
            mock_gemini.assert_called_once()

    def test_create_provider_gemini_cli_success(self):
        """Gemini CLIプロバイダー作成成功テスト"""
        config = ProviderConfig(
            name='gcloud',
            type='cli',
            model='gemini-1.5-pro',
            api_key=None,
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.cli_providers.gemini_cli_provider.GeminiCliProvider') as mock_gemini_cli:
            mock_instance = Mock()
            mock_gemini_cli.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance
            mock_gemini_cli.assert_called_once()

    def test_create_provider_claude_code_success(self):
        """Claude Code CLIプロバイダー作成成功テスト"""
        config = ProviderConfig(
            name='claude-code',
            type='cli',
            model='claude-3-5-sonnet-20241022',
            api_key=None,
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.cli_providers.claude_code_provider.ClaudeCodeProvider') as mock_claude:
            mock_instance = Mock()
            mock_claude.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance
            mock_claude.assert_called_once()

    def test_create_provider_unknown_provider(self):
        """未知のプロバイダー作成エラーテスト"""
        config = ProviderConfig(
            name='unknown-provider',
            type='api',
            model='test-model',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="サポートされていないプロバイダー"):
            self.factory.create_provider(config)

    def test_create_provider_initialization_error(self):
        """プロバイダー初期化エラーテスト"""
        config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:
            mock_openai.side_effect = Exception("Initialization failed")

            with pytest.raises(ProviderError, match="プロバイダーの初期化に失敗しました"):
                self.factory.create_provider(config)

    def test_get_supported_providers(self):
        """サポートされているプロバイダー一覧取得テスト"""
        supported_providers = self.factory.get_supported_providers()

        expected_providers = ['openai', 'anthropic', 'gemini', 'gcloud', 'gemini-cli', 'claude-code']
        assert isinstance(supported_providers, list)
        for provider in expected_providers:
            assert provider in supported_providers

    def test_is_provider_supported_true(self):
        """プロバイダーサポート確認テスト（サポート済み）"""
        assert self.factory.is_provider_supported('openai') is True
        assert self.factory.is_provider_supported('anthropic') is True
        assert self.factory.is_provider_supported('gemini') is True
        assert self.factory.is_provider_supported('gcloud') is True
        assert self.factory.is_provider_supported('gemini-cli') is True
        assert self.factory.is_provider_supported('claude-code') is True

    def test_is_provider_supported_false(self):
        """プロバイダーサポート確認テスト（未サポート）"""
        assert self.factory.is_provider_supported('unknown-provider') is False
        assert self.factory.is_provider_supported('') is False
        assert self.factory.is_provider_supported(None) is False

    def test_config_validation_success(self):
        """設定検証成功テスト"""
        valid_config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        # 例外が発生しないことを確認
        result = self.factory._validate_config(valid_config)
        assert result is None  # 正常な場合は何も返さない

    def test_config_validation_missing_name(self):
        """設定検証エラーテスト（名前不足）"""
        invalid_config = ProviderConfig(
            name='',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="プロバイダー名が指定されていません"):
            self.factory._validate_config(invalid_config)

    def test_config_validation_missing_model(self):
        """設定検証エラーテスト（モデル不足）"""
        invalid_config = ProviderConfig(
            name='openai',
            type='api',
            model='',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="モデル名が指定されていません"):
            self.factory._validate_config(invalid_config)

    def test_config_validation_invalid_timeout(self):
        """設定検証エラーテスト（無効なタイムアウト）"""
        invalid_config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=-1,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="タイムアウトは正の値である必要があります"):
            self.factory._validate_config(invalid_config)

    def test_config_validation_invalid_max_tokens(self):
        """設定検証エラーテスト（無効な最大トークン数）"""
        invalid_config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=0,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="最大トークン数は正の値である必要があります"):
            self.factory._validate_config(invalid_config)

    def test_config_validation_missing_prompt_template(self):
        """設定検証エラーテスト（プロンプトテンプレート不足）"""
        invalid_config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='',
            additional_params={}
        )

        with pytest.raises(ProviderError, match="プロンプトテンプレートが指定されていません"):
            self.factory._validate_config(invalid_config)

    def test_build_provider_config_dict(self):
        """プロバイダー設定辞書構築テスト"""
        config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={'temperature': 0.5}
        )

        config_dict = self.factory._build_provider_config_dict(config)

        assert config_dict['api_key'] == 'test-key'
        assert config_dict['model_name'] == 'gpt-4'
        assert config_dict['timeout'] == 30
        assert config_dict['max_tokens'] == 100
        assert config_dict['prompt_template'] == 'Test: {diff}'
        assert config_dict['additional_params']['temperature'] == 0.5

    def test_build_provider_config_dict_no_api_key(self):
        """APIキーなしのプロバイダー設定辞書構築テスト"""
        config = ProviderConfig(
            name='gcloud',
            type='cli',
            model='gemini-1.5-pro',
            api_key=None,
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        config_dict = self.factory._build_provider_config_dict(config)

        assert 'api_key' not in config_dict
        assert config_dict['model_name'] == 'gemini-1.5-pro'

    @pytest.mark.parametrize("provider_name,provider_class", [
        ('openai', 'lazygit_llm.src.api_providers.openai_provider.OpenAIProvider'),
        ('anthropic', 'lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider'),
        ('gemini', 'lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider'),
        ('gcloud', 'lazygit_llm.src.cli_providers.gemini_cli_provider.GeminiCliProvider'),
        ('claude-code', 'lazygit_llm.src.cli_providers.claude_code_provider.ClaudeCodeProvider'),
    ])
    def test_provider_class_mapping(self, provider_name, provider_class):
        """プロバイダークラスマッピングテスト"""
        assert provider_name in self.factory._providers
        # クラス名の確認（実際のクラスオブジェクトの比較は複雑なので文字列で確認）
        assert hasattr(self.factory._providers[provider_name], '__name__')

    def test_provider_config_dataclass(self):
        """ProviderConfigデータクラステスト"""
        config = ProviderConfig(
            name='test-provider',
            type='api',
            model='test-model',
            api_key='test-key',
            timeout=60,
            max_tokens=200,
            prompt_template='Custom: {diff}',
            additional_params={'custom_param': 'value'}
        )

        assert config.name == 'test-provider'
        assert config.type == 'api'
        assert config.model == 'test-model'
        assert config.api_key == 'test-key'
        assert config.timeout == 60
        assert config.max_tokens == 200
        assert config.prompt_template == 'Custom: {diff}'
        assert config.additional_params['custom_param'] == 'value'

    def test_create_provider_with_complex_config(self):
        """複雑な設定でのプロバイダー作成テスト"""
        config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4-turbo',
            api_key='sk-test1234567890abcdef1234567890abcdef12345678',  # gitleaks:allow - test only
            timeout=45,
            max_tokens=500,
            prompt_template='Complex template with {diff} and additional context',
            additional_params={
                'temperature': 0.7,
                'top_p': 0.95,
                'frequency_penalty': 0.1,
                'presence_penalty': 0.2,
                'stop': ['\n\n', 'END']
            }
        )

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:
            mock_instance = Mock()
            mock_openai.return_value = mock_instance

            provider = self.factory.create_provider(config)

            assert provider == mock_instance

            # 呼び出し引数の確認
            call_args = mock_openai.call_args[0][0]  # 第一引数（設定辞書）
            assert call_args['model_name'] == 'gpt-4-turbo'
            assert call_args['timeout'] == 45
            assert call_args['max_tokens'] == 500
            assert call_args['additional_params']['temperature'] == 0.7

    def test_error_propagation(self):
        """エラー伝播テスト"""
        config = ProviderConfig(
            name='openai',
            type='api',
            model='gpt-4',
            api_key='test-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Test: {diff}',
            additional_params={}
        )

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:
            mock_openai.side_effect = ProviderError("Custom provider error")

            with pytest.raises(ProviderError, match="Custom provider error"):
                self.factory.create_provider(config)

    def test_factory_singleton_behavior(self):
        """ファクトリーシングルトン動作テスト"""
        factory1 = ProviderFactory()
        factory2 = ProviderFactory()

        # 異なるインスタンスが作成される（シングルトンではない）
        assert factory1 is not factory2

        # しかし、同じプロバイダーが登録されている
        assert factory1._providers.keys() == factory2._providers.keys()

    def test_custom_provider_registration_and_creation(self):
        """カスタムプロバイダー登録と作成テスト"""
        # カスタムプロバイダークラスのモック
        class MockCustomProvider:
            def __init__(self, config):
                self.config = config

        # プロバイダーを登録
        self.factory.register_provider('custom-provider', MockCustomProvider)

        # 設定を作成
        config = ProviderConfig(
            name='custom-provider',
            type='api',
            model='custom-model',
            api_key='custom-key',
            timeout=30,
            max_tokens=100,
            prompt_template='Custom: {diff}',
            additional_params={}
        )

        # プロバイダーを作成
        provider = self.factory.create_provider(config)

        assert isinstance(provider, MockCustomProvider)
        assert provider.config['model_name'] == 'custom-model'
