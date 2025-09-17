"""
プロバイダーファクトリーシステム

LLMプロバイダーの動的な生成と管理を行う。
API型とCLI型の両方に対応し、設定に基づいて適切なプロバイダーを選択する。
"""

import logging
from typing import Dict, Any, Type, Optional, List
from abc import ABC, abstractmethod

from .base_provider import BaseProvider, ProviderError
from .config_manager import ProviderConfig

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    プロバイダー登録システム

    利用可能なプロバイダーを管理し、動的な登録・取得機能を提供。
    """

    def __init__(self):
        """プロバイダーレジストリを初期化"""
        self._api_providers: Dict[str, Type[BaseProvider]] = {}
        self._cli_providers: Dict[str, Type[BaseProvider]] = {}

    def register_api_provider(self, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        APIプロバイダーを登録

        Args:
            name: プロバイダー名
            provider_class: プロバイダークラス

        Raises:
            ValueError: プロバイダー名が無効または既に登録済みの場合
        """
        if not name or not isinstance(name, str):
            raise ValueError("プロバイダー名は有効な文字列である必要があります")

        if name in self._api_providers:
            logger.warning(f"APIプロバイダーが既に登録されています（上書き）: {name}")

        self._api_providers[name] = provider_class
        logger.debug(f"APIプロバイダーを登録: {name}")

    def register_cli_provider(self, name: str, provider_class: Type[BaseProvider]) -> None:
        """
        CLIプロバイダーを登録

        Args:
            name: プロバイダー名
            provider_class: プロバイダークラス

        Raises:
            ValueError: プロバイダー名が無効または既に登録済みの場合
        """
        if not name or not isinstance(name, str):
            raise ValueError("プロバイダー名は有効な文字列である必要があります")

        if name in self._cli_providers:
            logger.warning(f"CLIプロバイダーが既に登録されています（上書き）: {name}")

        self._cli_providers[name] = provider_class
        logger.debug(f"CLIプロバイダーを登録: {name}")

    def get_api_provider(self, name: str) -> Optional[Type[BaseProvider]]:
        """
        APIプロバイダークラスを取得

        Args:
            name: プロバイダー名

        Returns:
            プロバイダークラス、見つからない場合はNone
        """
        return self._api_providers.get(name)

    def get_cli_provider(self, name: str) -> Optional[Type[BaseProvider]]:
        """
        CLIプロバイダークラスを取得

        Args:
            name: プロバイダー名

        Returns:
            プロバイダークラス、見つからない場合はNone
        """
        return self._cli_providers.get(name)

    def get_all_providers(self) -> Dict[str, str]:
        """
        全プロバイダーの一覧を取得

        Returns:
            プロバイダー名とタイプ（api/cli）の辞書
        """
        all_providers = {}

        for name in self._api_providers.keys():
            all_providers[name] = 'api'

        for name in self._cli_providers.keys():
            all_providers[name] = 'cli'

        return all_providers

    def list_api_providers(self) -> List[str]:
        """
        APIプロバイダー一覧を取得

        Returns:
            APIプロバイダー名のリスト
        """
        return list(self._api_providers.keys())

    def list_cli_providers(self) -> List[str]:
        """
        CLIプロバイダー一覧を取得

        Returns:
            CLIプロバイダー名のリスト
        """
        return list(self._cli_providers.keys())


class ProviderFactory:
    """
    プロバイダーファクトリークラス

    設定に基づいて適切なLLMプロバイダーを生成する。
    API型とCLI型の自動判別と、プロバイダーの動的ロードに対応。
    """

    def __init__(self):
        """プロバイダーファクトリーを初期化"""
        self.registry = ProviderRegistry()
        self._initialized = False

    def create_provider(self, config: Dict[str, Any]) -> BaseProvider:
        """
        設定に基づいてプロバイダーを生成

        Args:
            config: プロバイダー設定（ConfigManagerからの設定）

        Returns:
            生成されたプロバイダーインスタンス

        Raises:
            ProviderError: プロバイダーの生成に失敗した場合
        """
        if not self._initialized:
            self._initialize_providers()

        # 設定の基本検証
        if not config or 'provider' not in config:
            raise ProviderError("プロバイダー設定が無効です")

        provider_name = config['provider']
        provider_type = self._detect_provider_type(provider_name)

        logger.info(f"プロバイダーを生成: {provider_name} (type: {provider_type})")

        try:
            if provider_type == 'api':
                return self._create_api_provider(provider_name, config)
            elif provider_type == 'cli':
                return self._create_cli_provider(provider_name, config)
            else:
                raise ProviderError(f"不明なプロバイダータイプ: {provider_type}")

        except Exception as e:
            logger.error(f"プロバイダー生成エラー: {e}")
            raise ProviderError(f"プロバイダーの生成に失敗しました（{provider_name}）: {e}")

    def get_supported_providers(self) -> List[str]:
        """
        サポートされているプロバイダー一覧を取得

        Returns:
            サポートされているプロバイダー名のリスト
        """
        if not self._initialized:
            self._initialize_providers()

        all_providers = self.registry.get_all_providers()
        return list(all_providers.keys())

    def is_provider_available(self, provider_name: str) -> bool:
        """
        指定されたプロバイダーが利用可能かチェック

        Args:
            provider_name: プロバイダー名

        Returns:
            利用可能な場合True
        """
        if not self._initialized:
            self._initialize_providers()

        provider_type = self._detect_provider_type(provider_name)
        if provider_type == 'api':
            return self.registry.get_api_provider(provider_name) is not None
        elif provider_type == 'cli':
            return self.registry.get_cli_provider(provider_name) is not None
        return False

    def _initialize_providers(self) -> None:
        """
        利用可能なプロバイダーを初期化

        動的にプロバイダーモジュールをロードして登録する。
        """
        logger.debug("プロバイダーの初期化を開始")

        # APIプロバイダーの登録
        self._register_api_providers()

        # CLIプロバイダーの登録
        self._register_cli_providers()

        self._initialized = True
        logger.info("プロバイダーの初期化完了")

    def _register_api_providers(self) -> None:
        """APIプロバイダーを動的に登録"""
        api_provider_configs = [
            ('openai', 'api_providers.openai_provider', 'OpenAIProvider'),
            ('anthropic', 'api_providers.anthropic_provider', 'AnthropicProvider'),
            ('gemini-api', 'api_providers.gemini_api_provider', 'GeminiAPIProvider'),
        ]

        for provider_name, module_name, class_name in api_provider_configs:
            try:
                # 動的にモジュールをインポート
                module = __import__(f"src.{module_name}", fromlist=[class_name])
                provider_class = getattr(module, class_name)
                self.registry.register_api_provider(provider_name, provider_class)
                logger.debug(f"APIプロバイダーを登録: {provider_name}")
            except ImportError as e:
                logger.warning(f"APIプロバイダーのロードに失敗（スキップ）: {provider_name} - {e}")
            except AttributeError as e:
                logger.warning(f"APIプロバイダークラスが見つかりません（スキップ）: {class_name} - {e}")

    def _register_cli_providers(self) -> None:
        """CLIプロバイダーを動的に登録"""
        cli_provider_configs = [
            ('gemini-cli', 'cli_providers.gemini_cli_provider', 'GeminiCLIProvider'),
            ('claude-code', 'cli_providers.claude_code_provider', 'ClaudeCodeProvider'),
        ]

        for provider_name, module_name, class_name in cli_provider_configs:
            try:
                # 動的にモジュールをインポート
                module = __import__(f"src.{module_name}", fromlist=[class_name])
                provider_class = getattr(module, class_name)
                self.registry.register_cli_provider(provider_name, provider_class)
                logger.debug(f"CLIプロバイダーを登録: {provider_name}")
            except ImportError as e:
                logger.warning(f"CLIプロバイダーのロードに失敗（スキップ）: {provider_name} - {e}")
            except AttributeError as e:
                logger.warning(f"CLIプロバイダークラスが見つかりません（スキップ）: {class_name} - {e}")

    def _detect_provider_type(self, provider_name: str) -> str:
        """
        プロバイダー名からタイプ（api/cli）を自動判別

        Args:
            provider_name: プロバイダー名

        Returns:
            プロバイダータイプ（'api' または 'cli'）

        Raises:
            ProviderError: 不明なプロバイダーの場合
        """
        # プロバイダータイプの判別表
        provider_types = {
            'openai': 'api',
            'anthropic': 'api',
            'gemini-api': 'api',
            'gemini-cli': 'cli',
            'claude-code': 'cli',
        }

        provider_type = provider_types.get(provider_name)
        if not provider_type:
            raise ProviderError(f"サポートされていないプロバイダー: {provider_name}")

        return provider_type

    def _create_api_provider(self, provider_name: str, config: Dict[str, Any]) -> BaseProvider:
        """
        APIプロバイダーを生成

        Args:
            provider_name: プロバイダー名
            config: 設定

        Returns:
            APIプロバイダーインスタンス

        Raises:
            ProviderError: プロバイダーの生成に失敗した場合
        """
        provider_class = self.registry.get_api_provider(provider_name)
        if not provider_class:
            raise ProviderError(f"APIプロバイダーが見つかりません: {provider_name}")

        # 必須パラメータの確認
        if 'api_key' not in config:
            raise ProviderError(f"APIプロバイダーにはapi_keyが必要です: {provider_name}")

        if 'model_name' not in config:
            raise ProviderError(f"APIプロバイダーにはmodel_nameが必要です: {provider_name}")

        # プロバイダーインスタンスを生成
        try:
            return provider_class(config)
        except Exception as e:
            raise ProviderError(f"APIプロバイダーの初期化に失敗: {provider_name} - {e}")

    def _create_cli_provider(self, provider_name: str, config: Dict[str, Any]) -> BaseProvider:
        """
        CLIプロバイダーを生成

        Args:
            provider_name: プロバイダー名
            config: 設定

        Returns:
            CLIプロバイダーインスタンス

        Raises:
            ProviderError: プロバイダーの生成に失敗した場合
        """
        provider_class = self.registry.get_cli_provider(provider_name)
        if not provider_class:
            raise ProviderError(f"CLIプロバイダーが見つかりません: {provider_name}")

        # 必須パラメータの確認
        if 'model_name' not in config:
            raise ProviderError(f"CLIプロバイダーにはmodel_nameが必要です: {provider_name}")

        # プロバイダーインスタンスを生成
        try:
            return provider_class(config)
        except Exception as e:
            raise ProviderError(f"CLIプロバイダーの初期化に失敗: {provider_name} - {e}")

    def test_provider_connection(self, provider_name: str, config: Dict[str, Any]) -> bool:
        """
        プロバイダーの接続をテスト

        Args:
            provider_name: プロバイダー名
            config: 設定

        Returns:
            接続が成功した場合True

        Raises:
            ProviderError: テストに失敗した場合
        """
        try:
            provider = self.create_provider(config)
            return provider.test_connection()
        except Exception as e:
            logger.error(f"プロバイダー接続テストエラー: {provider_name} - {e}")
            raise ProviderError(f"接続テストに失敗しました: {provider_name} - {e}")

    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """
        プロバイダーの詳細情報を取得

        Args:
            provider_name: プロバイダー名

        Returns:
            プロバイダー情報の辞書
        """
        if not self._initialized:
            self._initialize_providers()

        try:
            provider_type = self._detect_provider_type(provider_name)
            is_available = self.is_provider_available(provider_name)

            return {
                'name': provider_name,
                'type': provider_type,
                'available': is_available,
                'requires_api_key': provider_type == 'api'
            }
        except ProviderError:
            return {
                'name': provider_name,
                'type': 'unknown',
                'available': False,
                'requires_api_key': False
            }