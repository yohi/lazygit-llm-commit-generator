"""
プロバイダーファクトリーモジュール

設定に基づいてLLMプロバイダーのインスタンスを作成する。
"""

import logging
from typing import Dict, Any
from collections.abc import Mapping
from difflib import get_close_matches
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

        if not isinstance(provider_config, Mapping):
            raise TypeError("provider設定がマッピングではありません")
        # provider 実装は dict を前提とする可能性があるため実体化
        provider_config = dict(provider_config)

        provider_name = str(provider_config.get('name', '')).strip()
        if not provider_name:
            raise ValueError("provider.name が設定されていません")

        provider_type = str(provider_config.get('type', '')).strip().lower()
        provider_class = None

        if not provider_type:
            # type 未指定時は設定から自動判別を試行
            detected_type = self._detect_provider_type(provider_config)
            if detected_type:
                provider_type = detected_type
                logger.info("設定から自動判別したプロバイダータイプ: %s", provider_type)
            else:
                # 設定からの判別が困難な場合は name から判別
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
                    available_api = self._get_available_api_providers()
                    available_cli = self._get_available_cli_providers()
                    all_providers = available_api + available_cli
                    suggest = get_close_matches(provider_name, all_providers, n=3, cutoff=0.6)
                    hint = f"\n候補: {', '.join(suggest)}" if suggest else ""
                    raise ValueError(
                        f"プロバイダー名 '{provider_name}' が見つからず、typeも未指定です。\n"
                        f"利用可能なAPIプロバイダー: {', '.join(available_api)}\n"
                        f"利用可能なCLIプロバイダー: {', '.join(available_cli)}{hint}"
                    )

        # provider_type が決定された場合のクラス解決（明示指定または自動判別）
        if provider_type and not provider_class:
            if provider_type == 'api':
                provider_class = get_api_provider_class(provider_name)
            elif provider_type == 'cli':
                provider_class = get_cli_provider_class(provider_name)
            else:
                raise ValueError(f"サポートされていないプロバイダータイプ: {provider_type}")

        if not provider_class:
            available_api = self._get_available_api_providers()
            available_cli = self._get_available_cli_providers()
            all_providers = available_api + available_cli
            suggest = get_close_matches(provider_name, all_providers, n=3, cutoff=0.6)
            hint = f"\n候補: {', '.join(suggest)}" if suggest else ""
            raise ValueError(
                f"プロバイダー '{provider_name}' (type: {provider_type or 'auto'}) が見つかりません。\n"
                f"利用可能なAPIプロバイダー: {', '.join(available_api)}\n"
                f"利用可能なCLIプロバイダー: {', '.join(available_cli)}{hint}"
            )

        # プロバイダーインスタンスを作成
        try:
            provider = provider_class(provider_config)
            logger.info("プロバイダーを作成しました: %s (%s)", provider_name, provider_type)
            return provider
        except Exception as e:
            logger.exception("プロバイダーの作成に失敗")
            raise RuntimeError(f"プロバイダー '{provider_name}' の作成に失敗しました: {e}") from e

    def _detect_provider_type(self, config: Dict[str, Any]) -> str:
        """
        設定からプロバイダータイプを自動判別する

        Args:
            config: プロバイダー設定辞書

        Returns:
            判別されたプロバイダータイプ ('api' または 'cli')、判別不可能な場合は空文字

        Note:
            API型の特徴的キーとCLI型の特徴的キーを検出し、
            両方存在する場合はAPI優先で判別する
        """
        # API型プロバイダーの特徴的な設定キー
        api_signature_keys = {
            'api_key', 'endpoint', 'base_url', 'token', 'url',
            'api_url', 'access_token', 'auth_token', 'key'
        }

        # CLI型プロバイダーの特徴的な設定キー
        cli_signature_keys = {
            'cli_path', 'command', 'binary', 'args',
            'executable', 'path', 'cmd', 'binary_path'
        }

        has_api_config = any(key in config for key in api_signature_keys)
        has_cli_config = any(key in config for key in cli_signature_keys)

        if has_api_config and has_cli_config:
            logger.warning("API/CLI両方の設定が検出されました。APIタイプを優先します")
            return 'api'
        elif has_api_config:
            logger.debug("API型設定を検出: %s", [k for k in api_signature_keys if k in config])
            return 'api'
        elif has_cli_config:
            logger.debug("CLI型設定を検出: %s", [k for k in cli_signature_keys if k in config])
            return 'cli'
        else:
            logger.debug("プロバイダータイプを自動判別できませんでした")
            return ''

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
