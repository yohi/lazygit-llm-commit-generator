"""
ConfigManagerのユニットテスト

設定ファイルの読み込み、環境変数解決、設定検証機能をテスト。
"""

import pytest
import os
import yaml
import tempfile
from unittest.mock import patch, mock_open
from pathlib import Path

from lazygit_llm.src.config_manager import ConfigManager, ConfigError, ProviderConfig


class TestConfigManager:
    """ConfigManagerのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.config_manager = ConfigManager()

    def test_initialization(self):
        """初期化テスト"""
        assert self.config_manager.config == {}
        assert self.config_manager._config_path is None
        assert hasattr(self.config_manager, 'security_validator')
        assert hasattr(self.config_manager, 'supported_providers')

    def test_supported_providers_structure(self):
        """サポートされているプロバイダーの構造テスト"""
        providers = self.config_manager.supported_providers

        expected_providers = ['openai', 'anthropic', 'gemini-api', 'gemini-cli', 'claude-code']
        for provider in expected_providers:
            assert provider in providers
            assert 'type' in providers[provider]
            assert 'required_fields' in providers[provider]
            assert providers[provider]['type'] in ['api', 'cli']

    def test_load_config_success(self, temp_config_file):
        """設定ファイル読み込み成功テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = type('Result', (), {'level': 'info'})()

            config = self.config_manager.load_config(temp_config_file)

            assert config['provider'] == 'openai'
            assert config['api_key'] == 'test-api-key'
            assert config['model_name'] == 'gpt-3.5-turbo'
            assert self.config_manager._config_path == temp_config_file

    def test_load_config_file_not_found(self):
        """存在しないファイルのテスト"""
        with pytest.raises(ConfigError, match="設定ファイルが見つかりません"):
            self.config_manager.load_config('/non/existent/file.yml')

    def test_load_config_malformed_yaml(self, temp_malformed_yaml_file):
        """不正なYAMLファイルのテスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = type('Result', (), {'level': 'info'})()

            with pytest.raises(ConfigError, match="YAML解析エラー"):
                self.config_manager.load_config(temp_malformed_yaml_file)

    def test_load_config_empty_file(self):
        """空のファイルのテスト"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("")
            f.flush()

        try:
            with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
                mock_check.return_value = type('Result', (), {'level': 'info'})()

                with pytest.raises(ConfigError, match="設定ファイルが空です"):
                    self.config_manager.load_config(f.name)
        finally:
            os.unlink(f.name)

    def test_load_config_permission_warning(self, temp_config_file):
        """ファイル権限警告のテスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_result = type('Result', (), {
                'level': 'warning',
                'message': 'ファイル権限が緩い',
                'recommendations': ['chmod 600 を推奨']
            })()
            mock_check.return_value = mock_result

            # 警告レベルなら処理は継続される
            config = self.config_manager.load_config(temp_config_file)
            assert config['provider'] == 'openai'

    def test_load_config_permission_danger(self, temp_config_file):
        """ファイル権限危険レベルのテスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_result = type('Result', (), {
                'level': 'danger',
                'message': 'ファイル権限が危険'
            })()
            mock_check.return_value = mock_result

            with pytest.raises(ConfigError, match="セキュリティエラー"):
                self.config_manager.load_config(temp_config_file)

    def test_environment_variable_resolution(self, monkeypatch):
        """環境変数解決テスト"""
        # 環境変数設定
        monkeypatch.setenv("TEST_API_KEY", "resolved-key")
        monkeypatch.setenv("TEST_MODEL", "resolved-model")

        config = {
            "api_key": "${TEST_API_KEY}",
            "model_name": "${TEST_MODEL}",
            "timeout": 30,
            "normal_value": "not-an-env-var"
        }

        resolved = self.config_manager._resolve_environment_variables(config)

        assert resolved['api_key'] == 'resolved-key'
        assert resolved['model_name'] == 'resolved-model'
        assert resolved['timeout'] == 30
        assert resolved['normal_value'] == 'not-an-env-var'

    def test_environment_variable_not_found(self):
        """環境変数が見つからない場合のテスト"""
        config = {"api_key": "${NON_EXISTENT_VAR}"}

        resolved = self.config_manager._resolve_environment_variables(config)

        # 解決できない場合は元の値を保持
        assert resolved['api_key'] == '${NON_EXISTENT_VAR}'

    def test_get_api_key_from_config(self, temp_config_file):
        """設定ファイルからのAPIキー取得テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check, \
             patch.object(self.config_manager.security_validator, 'validate_api_key') as mock_validate:

            mock_check.return_value = type('Result', (), {'level': 'info'})()
            mock_validate.return_value = type('Result', (), {
                'is_valid': True,
                'level': 'info',
                'message': 'Valid key',
                'recommendations': []
            })()

            self.config_manager.load_config(temp_config_file)
            api_key = self.config_manager.get_api_key('openai')

            assert api_key == 'test-api-key'

    def test_get_api_key_from_env(self, monkeypatch):
        """環境変数からのAPIキー取得テスト"""
        monkeypatch.setenv("OPENAI_API_KEY", "env-api-key")

        # 設定にAPIキーがない場合の設定
        self.config_manager.config = {'provider': 'openai'}

        with patch.object(self.config_manager.security_validator, 'validate_api_key') as mock_validate:
            mock_validate.return_value = type('Result', (), {
                'is_valid': True,
                'level': 'info',
                'message': 'Valid key',
                'recommendations': []
            })()

            api_key = self.config_manager.get_api_key('openai')
            assert api_key == 'env-api-key'

    def test_get_api_key_not_found(self):
        """APIキーが見つからない場合のテスト"""
        self.config_manager.config = {'provider': 'openai'}

        with pytest.raises(ConfigError, match="APIキーが見つかりません"):
            self.config_manager.get_api_key('openai')

    def test_get_api_key_invalid(self, temp_config_file):
        """無効なAPIキーのテスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check, \
             patch.object(self.config_manager.security_validator, 'validate_api_key') as mock_validate:

            mock_check.return_value = type('Result', (), {'level': 'info'})()
            mock_validate.return_value = type('Result', (), {
                'is_valid': False,
                'message': 'Invalid API key format'
            })()

            self.config_manager.load_config(temp_config_file)

            with pytest.raises(ConfigError, match="APIキー検証エラー"):
                self.config_manager.get_api_key('openai')

    def test_get_model_name_success(self, temp_config_file):
        """モデル名取得成功テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = type('Result', (), {'level': 'info'})()

            self.config_manager.load_config(temp_config_file)
            model_name = self.config_manager.get_model_name('openai')

            assert model_name == 'gpt-3.5-turbo'

    def test_get_model_name_not_found(self):
        """モデル名が設定されていない場合のテスト"""
        self.config_manager.config = {'provider': 'openai'}

        with pytest.raises(ConfigError, match="モデル名が設定されていません"):
            self.config_manager.get_model_name('openai')

    def test_get_prompt_template_from_config(self, temp_config_file):
        """設定からのプロンプトテンプレート取得テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = type('Result', (), {'level': 'info'})()

            self.config_manager.load_config(temp_config_file)
            template = self.config_manager.get_prompt_template()

            assert template == 'Generate commit message for: {diff}'
            assert '{diff}' in template

    def test_get_prompt_template_default(self):
        """デフォルトプロンプトテンプレート取得テスト"""
        self.config_manager.config = {'provider': 'openai'}

        template = self.config_manager.get_prompt_template()

        assert '{diff}' in template
        assert 'conventional commits' in template.lower()

    def test_get_prompt_template_missing_placeholder(self):
        """プレースホルダーがないプロンプトテンプレートのテスト"""
        self.config_manager.config = {
            'prompt_template': 'Invalid template without placeholder'
        }

        with pytest.raises(ConfigError, match="プロンプトテンプレートに{diff}プレースホルダーが含まれていません"):
            self.config_manager.get_prompt_template()

    def test_get_provider_config_api_provider(self, temp_config_file):
        """APIプロバイダー設定取得テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check, \
             patch.object(self.config_manager.security_validator, 'validate_api_key') as mock_validate:

            mock_check.return_value = type('Result', (), {'level': 'info'})()
            mock_validate.return_value = type('Result', (), {
                'is_valid': True,
                'level': 'info',
                'message': 'Valid key',
                'recommendations': []
            })()

            self.config_manager.load_config(temp_config_file)
            provider_config = self.config_manager.get_provider_config()

            assert provider_config.name == 'openai'
            assert provider_config.type == 'api'
            assert provider_config.model == 'gpt-3.5-turbo'
            assert provider_config.api_key == 'test-api-key'
            assert provider_config.timeout == 30
            assert provider_config.max_tokens == 100

    def test_get_provider_config_cli_provider(self):
        """CLIプロバイダー設定取得テスト"""
        self.config_manager.config = {
            'provider': 'gemini-cli',
            'model_name': 'gemini-1.5-pro',
            'timeout': 45,
            'max_tokens': 150
        }

        provider_config = self.config_manager.get_provider_config()

        assert provider_config.name == 'gemini-cli'
        assert provider_config.type == 'cli'
        assert provider_config.model == 'gemini-1.5-pro'
        assert provider_config.api_key is None
        assert provider_config.timeout == 45

    def test_get_provider_config_missing_provider(self):
        """プロバイダー名が設定されていない場合のテスト"""
        self.config_manager.config = {'model_name': 'test'}

        with pytest.raises(ConfigError, match="プロバイダー名が設定されていません"):
            self.config_manager.get_provider_config()

    def test_get_provider_config_unsupported_provider(self):
        """サポートされていないプロバイダーのテスト"""
        self.config_manager.config = {
            'provider': 'unsupported-provider',
            'model_name': 'test'
        }

        with pytest.raises(ConfigError, match="サポートされていないプロバイダー"):
            self.config_manager.get_provider_config()

    def test_validate_config_success(self, temp_config_file):
        """設定検証成功テスト"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check, \
             patch.object(self.config_manager, 'get_api_key') as mock_get_key:

            mock_check.return_value = type('Result', (), {'level': 'info'})()
            mock_get_key.return_value = 'valid-key'

            self.config_manager.load_config(temp_config_file)
            result = self.config_manager.validate_config()

            assert result is True

    def test_validate_config_missing_required_field(self):
        """必須フィールド不足の検証テスト"""
        self.config_manager.config = {}  # プロバイダーが不足

        result = self.config_manager.validate_config()
        assert result is False

    def test_validate_config_invalid_timeout(self):
        """無効なタイムアウト値の検証テスト"""
        self.config_manager.config = {
            'provider': 'openai',
            'model_name': 'gpt-3.5-turbo',
            'timeout': -1  # 無効な値
        }

        with patch.object(self.config_manager, 'get_api_key') as mock_get_key:
            mock_get_key.return_value = 'valid-key'
            result = self.config_manager.validate_config()

        assert result is False

    def test_validate_config_invalid_max_tokens(self):
        """無効な最大トークン数の検証テスト"""
        self.config_manager.config = {
            'provider': 'openai',
            'model_name': 'gpt-3.5-turbo',
            'timeout': 30,
            'max_tokens': 5000  # 上限を超える値
        }

        with patch.object(self.config_manager, 'get_api_key') as mock_get_key:
            mock_get_key.return_value = 'valid-key'
            result = self.config_manager.validate_config()

        assert result is False

    def test_get_supported_providers(self):
        """サポートプロバイダー一覧取得テスト"""
        providers = self.config_manager.get_supported_providers()

        assert isinstance(providers, dict)
        assert 'openai' in providers
        assert 'anthropic' in providers
        assert 'gemini-api' in providers
        assert 'gemini-cli' in providers
        assert 'claude-code' in providers

        # 元の辞書が変更されないことを確認
        providers['test'] = 'modified'
        assert 'test' not in self.config_manager.supported_providers

    def test_str_representation(self, temp_config_file):
        """文字列表現テスト（APIキーマスク）"""
        with patch.object(self.config_manager.security_validator, 'check_file_permissions') as mock_check:
            mock_check.return_value = type('Result', (), {'level': 'info'})()

            self.config_manager.load_config(temp_config_file)
            str_repr = str(self.config_manager)

            assert 'ConfigManager' in str_repr
            assert 'openai' in str_repr
            assert temp_config_file in str_repr
            # APIキーがマスクされていることを確認
            assert 'test-api-key' not in str_repr
            assert '*' in str_repr

    @pytest.mark.parametrize("provider,expected_type", [
        ('openai', 'api'),
        ('anthropic', 'api'),
        ('gemini-api', 'api'),
        ('gemini-cli', 'cli'),
        ('claude-code', 'cli'),
    ])
    def test_provider_types(self, provider, expected_type):
        """各プロバイダーのタイプ確認テスト"""
        providers = self.config_manager.supported_providers
        assert providers[provider]['type'] == expected_type