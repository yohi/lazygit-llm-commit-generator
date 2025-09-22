"""
プロバイダーファクトリーモジュール

設定に基づいてLLMプロバイダーのインスタンスを作成する。
"""

import logging
from typing import Dict, Any
from collections.abc import Mapping
from lazygit_llm.base_provider import BaseProvider
from lazygit_llm.api_providers import get_provider_class as get_api_provider_class
from lazygit_llm.cli_providers import get_provider_class as get_cli_provider_class

logger = logging.getLogger(__name__)


class ProviderFactory:
    """プロバイダーファクトリークラス"""

    def create_provider(self, config: Mapping[str, Any]) -> BaseProvider:
        """
        設定に基づいてプロバイダーを作成する

        Args:
            config: 設定辞書

        Returns:
            作成されたプロバイダーインスタンス

        Raises:
            TypeError: provider設定が辞書でない
            ValueError: 不正な設定
            RuntimeError: プロバイダーの作成に失敗
        """
        provider_config = config.get('provider', {})

        if not isinstance(provider_config, dict):
            raise TypeError("provider設定が辞書ではありません")

        provider_name = str(provider_config.get('name', '')).strip()
        if not provider_name:
            raise ValueError("provider.name が設定されていません")

        provider_type = str(provider_config.get('type', '')).strip().lower()
        provider_class = None

        if not provider_type:
            # type 未指定時は name から自動判別
            api_cls = get_api_provider_class(provider_name)
            cli_cls = get_cli_provider_class(provider_name)

            if api_cls and cli_cls:
                raise ValueError(
                    f"プロバイダー名 '{provider_name}' は API/CLI の両方で見つかりました。"
                    "provider.type を 'api' または 'cli' で明示してください。"
                )
            if api_cls:
                provider_type, provider_class = 'api', api_cls
            elif cli_cls:
                provider_type, provider_class = 'cli', cli_cls
            else:
                available_api = ", ".join(self._get_available_api_providers())
                available_cli = ", ".join(self._get_available_cli_providers())
                raise ValueError(
                    f"プロバイダー名 '{provider_name}' が見つからず、typeも未指定です。\n"
                    f"利用可能なAPIプロバイダー: {available_api}\n"
                    f"利用可能なCLIプロバイダー: {available_cli}"
                )
        else:
            # type 明示時の既存処理
            if provider_type == 'api':
                provider_class = get_api_provider_class(provider_name)
            elif provider_type == 'cli':
                provider_class = get_cli_provider_class(provider_name)
            else:
                raise ValueError(f"サポートされていないプロバイダータイプ: {provider_type}")

        if not provider_class:
            available_api = ", ".join(self._get_available_api_providers())
            available_cli = ", ".join(self._get_available_cli_providers())
            raise ValueError(
                f"プロバイダー '{provider_name}' (type: {provider_type}) が見つかりません。\n"
                f"利用可能なAPIプロバイダー: {available_api}\n"
                f"利用可能なCLIプロバイダー: {available_cli}"
            )

        # プロバイダーインスタンスを作成
        try:
            provider = provider_class(provider_config)
            logger.info("プロバイダーを作成しました: %s (%s)", provider_name, provider_type)
            return provider
        except Exception as e:
            logger.exception("プロバイダーの作成に失敗")
            raise RuntimeError(f"プロバイダー '{provider_name}' の作成に失敗しました: {e}") from e

    def _get_available_api_providers(self) -> list:
        """
        利用可能なAPIプロバイダーの一覧を取得する

        Returns:
            APIプロバイダー名のリスト
        """
        try:
            from lazygit_llm.api_providers import get_available_providers
            return get_available_providers()
        except Exception:
            logger.warning("api_providers モジュールの読み込みに失敗", exc_info=True)
            return []

    def _get_available_cli_providers(self) -> list:
        """
        利用可能なCLIプロバイダーの一覧を取得する

        Returns:
            CLIプロバイダー名のリスト
        """
        try:
            from lazygit_llm.cli_providers import get_available_providers
            return get_available_providers()
        except Exception:
            logger.warning("cli_providers モジュールの読み込みに失敗", exc_info=True)
            return []

    def list_available_providers(self) -> Dict[str, list]:
        """
        利用可能な全プロバイダーを取得する

        Returns:
            プロバイダータイプ別のリスト辞書
        """
        return {
            'api': sorted(self._get_available_api_providers()),
            'cli': sorted(self._get_available_cli_providers()),
        }
