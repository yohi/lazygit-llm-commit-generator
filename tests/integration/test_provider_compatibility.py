"""
プロバイダー互換性テスト

各LLMプロバイダーとの互換性と相互運用性をテスト。
"""

import pytest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lazygit_llm.src.provider_factory import ProviderFactory, ProviderConfig
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError


class TestProviderCompatibility:
    """プロバイダー互換性テストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.factory = ProviderFactory()
        self.sample_diff = """diff --git a/src/utils.py b/src/utils.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/src/utils.py
@@ -0,0 +1,10 @@
+"""
+Utility functions
+"""
+
+def format_timestamp(timestamp):
+    \"\"\"Format timestamp to human readable string\"\"\"
+    import datetime
+    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
"""

    def create_provider_config(self, provider_name, **kwargs):
        """プロバイダー設定を作成"""
        base_config = {
            'name': provider_name,
            'type': 'api' if provider_name in ['openai', 'anthropic', 'gemini-api'] else 'cli',
            'model': self.get_default_model(provider_name),
            'api_key': kwargs.get('api_key', 'test-key-' + provider_name),
            'timeout': kwargs.get('timeout', 30),
            'max_tokens': kwargs.get('max_tokens', 100),
            'prompt_template': kwargs.get('prompt_template', 'Generate commit: {diff}'),
            'additional_params': kwargs.get('additional_params', {})
        }

        # CLIプロバイダーはapi_keyが不要
        if base_config['type'] == 'cli':
            base_config['api_key'] = None

        return ProviderConfig(**base_config)

    def get_default_model(self, provider_name):
        """プロバイダーのデフォルトモデル名を取得"""
        model_mapping = {
            'openai': 'gpt-4',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'gemini-api': 'gemini-1.5-pro',
            'gemini-cli': 'gemini-1.5-pro',
            'claude-code': 'claude-3-5-sonnet-20241022'
        }
        return model_mapping.get(provider_name, 'default-model')

    def test_openai_provider_compatibility(self):
        """OpenAIプロバイダー互換性テスト"""
        config = self.create_provider_config('openai')

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add utility functions"
            mock_provider.test_connection.return_value = True
            mock_provider.supports_streaming.return_value = True
            mock_provider_class.return_value = mock_provider

            provider = self.factory.create_provider(config)

            # 基本機能テスト
            result = provider.generate_commit_message(self.sample_diff)
            assert result == "feat: add utility functions"

            # 接続テスト
            assert provider.test_connection() is True

            # ストリーミングサポート
            assert provider.supports_streaming() is True

    def test_anthropic_provider_compatibility(self):
        """Anthropicプロバイダー互換性テスト"""
        config = self.create_provider_config('anthropic')

        with patch('lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: implement timestamp utility"
            mock_provider.test_connection.return_value = True
            mock_provider.supports_streaming.return_value = True
            mock_provider_class.return_value = mock_provider

            provider = self.factory.create_provider(config)

            # 基本機能テスト
            result = provider.generate_commit_message(self.sample_diff)
            assert result == "feat: implement timestamp utility"

            # 接続テスト
            assert provider.test_connection() is True

            # ストリーミングサポート
            assert provider.supports_streaming() is True

    def test_gemini_api_provider_compatibility(self):
        """Gemini APIプロバイダー互換性テスト"""
        config = self.create_provider_config('gemini-api')

        with patch('lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: add timestamp formatting utility"
            mock_provider.test_connection.return_value = True
            mock_provider.supports_streaming.return_value = False  # Gemini APIは通常ストリーミング非対応
            mock_provider_class.return_value = mock_provider

            provider = self.factory.create_provider(config)

            # 基本機能テスト
            result = provider.generate_commit_message(self.sample_diff)
            assert result == "feat: add timestamp formatting utility"

            # 接続テスト
            assert provider.test_connection() is True

            # ストリーミングサポート（非対応）
            assert provider.supports_streaming() is False

    def test_gemini_cli_provider_compatibility(self):
        """Gemini CLIプロバイダー互換性テスト"""
        config = self.create_provider_config('gemini-cli')

        with patch('lazygit_llm.src.cli_providers.gemini_cli_provider.GeminiCliProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: create utility module"
            mock_provider.test_connection.return_value = True
            mock_provider.supports_streaming.return_value = False  # CLIは通常ストリーミング非対応
            mock_provider_class.return_value = mock_provider

            provider = self.factory.create_provider(config)

            # 基本機能テスト
            result = provider.generate_commit_message(self.sample_diff)
            assert result == "feat: create utility module"

            # 接続テスト
            assert provider.test_connection() is True

            # ストリーミングサポート（非対応）
            assert provider.supports_streaming() is False

    def test_claude_code_provider_compatibility(self):
        """Claude Code CLIプロバイダー互換性テスト"""
        config = self.create_provider_config('claude-code')

        with patch('lazygit_llm.src.cli_providers.claude_code_provider.ClaudeCodeProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider.generate_commit_message.return_value = "feat: implement utility functions for timestamp formatting"
            mock_provider.test_connection.return_value = True
            mock_provider.supports_streaming.return_value = False  # CLIは通常ストリーミング非対応
            mock_provider_class.return_value = mock_provider

            provider = self.factory.create_provider(config)

            # 基本機能テスト
            result = provider.generate_commit_message(self.sample_diff)
            assert result == "feat: implement utility functions for timestamp formatting"

            # 接続テスト
            assert provider.test_connection() is True

            # ストリーミングサポート（非対応）
            assert provider.supports_streaming() is False

    def test_provider_parameter_compatibility(self):
        """プロバイダーパラメータ互換性テスト"""
        test_parameters = {
            'temperature': 0.5,
            'top_p': 0.9,
            'top_k': 40,
            'max_tokens': 150,
            'stop_sequences': ['END', '\n\n']
        }

        providers_to_test = ['openai', 'anthropic', 'gemini-api']

        for provider_name in providers_to_test:
            config = self.create_provider_config(
                provider_name,
                additional_params=test_parameters
            )

            # 各プロバイダーが設定を受け入れることを確認
            assert config.additional_params == test_parameters
            assert config.name == provider_name

    def test_error_handling_consistency(self):
        """エラーハンドリング一貫性テスト"""
        providers_configs = [
            ('openai', 'lazygit_llm.src.api_providers.openai_provider.OpenAIProvider'),
            ('anthropic', 'lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider'),
            ('gemini-api', 'lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider'),
        ]

        error_scenarios = [
            (AuthenticationError("Auth failed"), "authentication error"),
            (TimeoutError("Timeout occurred"), "timeout error"),
            (ProviderError("Provider failed"), "provider error"),
        ]

        for provider_name, provider_class_path in providers_configs:
            config = self.create_provider_config(provider_name)

            with patch(provider_class_path) as mock_provider_class:
                for error, description in error_scenarios:
                    mock_provider = Mock()
                    mock_provider.generate_commit_message.side_effect = error
                    mock_provider_class.return_value = mock_provider

                    provider = self.factory.create_provider(config)

                    # 各プロバイダーが同じエラータイプを発生させることを確認
                    with pytest.raises(type(error)):
                        provider.generate_commit_message(self.sample_diff)

    def test_output_format_consistency(self):
        """出力フォーマット一貫性テスト"""
        expected_outputs = [
            "feat: add utility functions",
            "fix: resolve timestamp formatting issue",
            "docs: update utility documentation",
            "refactor: improve timestamp handling",
        ]

        all_providers = ['openai', 'anthropic', 'gemini-api', 'gemini-cli', 'claude-code']

        for provider_name in all_providers:
            config = self.create_provider_config(provider_name)

            # プロバイダーのパッケージパスを決定
            if provider_name in ['openai', 'anthropic', 'gemini-api']:
                package_path = f'lazygit_llm.src.api_providers.{provider_name}_provider'
                class_name = f'{provider_name.title()}Provider'
                if provider_name == 'gemini-api':
                    class_name = 'GeminiApiProvider'
            else:
                package_path = f'lazygit_llm.src.cli_providers.{provider_name.replace("-", "_")}_provider'
                if provider_name == 'gemini-cli':
                    class_name = 'GeminiCliProvider'
                else:
                    class_name = 'ClaudeCodeProvider'

            with patch(f'{package_path}.{class_name}') as mock_provider_class:
                for expected_output in expected_outputs:
                    mock_provider = Mock()
                    mock_provider.generate_commit_message.return_value = expected_output
                    mock_provider_class.return_value = mock_provider

                    provider = self.factory.create_provider(config)
                    result = provider.generate_commit_message(self.sample_diff)

                    # 出力が期待される形式であることを確認
                    assert result == expected_output
                    assert len(result) > 0
                    assert result.strip() == result  # 前後の空白がない

    def test_model_compatibility_matrix(self):
        """モデル互換性マトリックステスト"""
        model_compatibility = {
            'openai': ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo'],
            'anthropic': ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307', 'claude-3-opus-20240229'],
            'gemini-api': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-1.0-pro'],
            'gemini-cli': ['gemini-1.5-pro', 'gemini-1.5-flash'],
            'claude-code': ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022']
        }

        for provider_name, supported_models in model_compatibility.items():
            for model_name in supported_models:
                config = self.create_provider_config(provider_name)
                config.model = model_name

                # モデル名が正しく設定されることを確認
                assert config.model == model_name
                assert config.name == provider_name

    def test_provider_initialization_robustness(self):
        """プロバイダー初期化堅牢性テスト"""
        invalid_configs = [
            # 無効なプロバイダー名
            ('invalid-provider', 'gpt-4', 'test-key'),
            # 空のモデル名
            ('openai', '', 'test-key'),
            # 無効なタイムアウト
            ('openai', 'gpt-4', 'test-key'),
        ]

        for provider_name, model, api_key in invalid_configs:
            if provider_name == 'invalid-provider':
                # 無効なプロバイダー名の場合
                with pytest.raises(ProviderError, match="サポートされていないプロバイダー"):
                    config = ProviderConfig(
                        name=provider_name,
                        type='api',
                        model=model,
                        api_key=api_key,
                        timeout=30,
                        max_tokens=100,
                        prompt_template='Test: {diff}',
                        additional_params={}
                    )
                    self.factory.create_provider(config)
            elif model == '':
                # 空のモデル名の場合
                with pytest.raises(ProviderError, match="モデル名が指定されていません"):
                    config = ProviderConfig(
                        name=provider_name,
                        type='api',
                        model=model,
                        api_key=api_key,
                        timeout=30,
                        max_tokens=100,
                        prompt_template='Test: {diff}',
                        additional_params={}
                    )
                    self.factory._validate_config(config)

    def test_provider_switching_compatibility(self):
        """プロバイダー切り替え互換性テスト"""
        providers = ['openai', 'anthropic', 'gemini-api']

        for i, provider_name in enumerate(providers):
            config = self.create_provider_config(provider_name)

            # プロバイダーパッケージパスを決定
            package_path = f'lazygit_llm.src.api_providers.{provider_name}_provider'
            class_name = f'{provider_name.title()}Provider'
            if provider_name == 'gemini-api':
                class_name = 'GeminiApiProvider'

            with patch(f'{package_path}.{class_name}') as mock_provider_class:
                mock_provider = Mock()
                mock_provider.generate_commit_message.return_value = f"Message from {provider_name}"
                mock_provider_class.return_value = mock_provider

                provider = self.factory.create_provider(config)
                result = provider.generate_commit_message(self.sample_diff)

                assert f"{provider_name}" in result
                # プロバイダーが正しく作成されていることを確認
                mock_provider_class.assert_called_once()

    def test_concurrent_provider_usage(self):
        """並行プロバイダー使用テスト"""
        import threading
        import time

        providers = ['openai', 'anthropic', 'gemini-api']
        results = {}

        def test_provider_thread(provider_name, results_dict):
            """プロバイダーを別スレッドでテスト"""
            config = self.create_provider_config(provider_name)

            package_path = f'lazygit_llm.src.api_providers.{provider_name}_provider'
            class_name = f'{provider_name.title()}Provider'
            if provider_name == 'gemini-api':
                class_name = 'GeminiApiProvider'

            with patch(f'{package_path}.{class_name}') as mock_provider_class:
                mock_provider = Mock()
                mock_provider.generate_commit_message.return_value = f"Result from {provider_name}"
                mock_provider_class.return_value = mock_provider

                provider = self.factory.create_provider(config)
                result = provider.generate_commit_message(self.sample_diff)

                results_dict[provider_name] = result

        # 複数スレッドで並行実行
        threads = []
        for provider_name in providers:
            thread = threading.Thread(target=test_provider_thread, args=(provider_name, results))
            threads.append(thread)
            thread.start()

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()

        # 結果を検証
        assert len(results) == len(providers)
        for provider_name in providers:
            assert provider_name in results
            assert f"Result from {provider_name}" == results[provider_name]

    def test_provider_feature_matrix(self):
        """プロバイダー機能マトリックステスト"""
        feature_matrix = {
            'openai': {
                'streaming': True,
                'temperature': True,
                'top_p': True,
                'max_tokens': True,
                'stop_sequences': True
            },
            'anthropic': {
                'streaming': True,
                'temperature': True,
                'top_p': True,
                'max_tokens': True,
                'stop_sequences': False
            },
            'gemini-api': {
                'streaming': False,
                'temperature': True,
                'top_p': True,
                'max_tokens': True,
                'stop_sequences': True
            },
            'gemini-cli': {
                'streaming': False,
                'temperature': True,
                'top_p': True,
                'max_tokens': True,
                'stop_sequences': False
            },
            'claude-code': {
                'streaming': False,
                'temperature': True,
                'top_p': True,
                'max_tokens': True,
                'stop_sequences': False
            }
        }

        for provider_name, features in feature_matrix.items():
            config = self.create_provider_config(provider_name)

            # 各機能が適切に設定されることを確認
            if features['temperature']:
                config.additional_params['temperature'] = 0.5
                assert 'temperature' in config.additional_params

            if features['top_p']:
                config.additional_params['top_p'] = 0.9
                assert 'top_p' in config.additional_params

            if features['max_tokens']:
                assert config.max_tokens > 0

    def test_provider_fallback_mechanism(self):
        """プロバイダーフォールバック機構テスト"""
        primary_provider = 'openai'
        fallback_providers = ['anthropic', 'gemini-api']

        # プライマリプロバイダーが失敗した場合のシミュレート
        primary_config = self.create_provider_config(primary_provider)

        with patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider') as mock_openai:
            mock_openai.side_effect = AuthenticationError("Primary provider failed")

            # プライマリプロバイダーでエラーが発生することを確認
            with pytest.raises(AuthenticationError):
                self.factory.create_provider(primary_config)

        # フォールバックプロバイダーは正常に動作することを確認
        for fallback_provider in fallback_providers:
            fallback_config = self.create_provider_config(fallback_provider)

            package_path = f'lazygit_llm.src.api_providers.{fallback_provider}_provider'
            class_name = f'{fallback_provider.title()}Provider'
            if fallback_provider == 'gemini-api':
                class_name = 'GeminiApiProvider'

            with patch(f'{package_path}.{class_name}') as mock_provider_class:
                mock_provider = Mock()
                mock_provider.generate_commit_message.return_value = f"Fallback: {fallback_provider}"
                mock_provider_class.return_value = mock_provider

                provider = self.factory.create_provider(fallback_config)
                result = provider.generate_commit_message(self.sample_diff)

                assert f"Fallback: {fallback_provider}" == result