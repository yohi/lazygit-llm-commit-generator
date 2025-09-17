"""
CLI型LLMプロバイダーモジュール

コマンドライン経由でLLMサービスにアクセスするプロバイダー群:
- Gemini CLI (gcloud)
- Claude Code CLI (claude-code)
"""

from typing import Optional, Type
import logging
from ..base_provider import BaseProvider

logger = logging.getLogger(__name__)

# プロバイダー登録レジストリ(実装時に各プロバイダーが追加)
CLI_PROVIDERS: dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """
    CLIプロバイダーを登録

    Args:
        name: プロバイダー名
        provider_class: プロバイダークラス
    """
    norm = name.strip().lower()
    if not isinstance(provider_class, type) or not issubclass(provider_class, BaseProvider):
        raise TypeError("provider_class は BaseProvider のサブクラスである必要があります")
    if norm in CLI_PROVIDERS:
        logger.warning("CLI provider '%s' を上書き登録します", norm)
    CLI_PROVIDERS[norm] = provider_class


def get_available_providers() -> list[str]:
    """
    利用可能なCLIプロバイダー一覧を取得

    Returns:
        プロバイダー名のリスト
    """
    return sorted(CLI_PROVIDERS.keys())


def get_provider_class(name: str) -> Optional[Type[BaseProvider]]:
    """名前でCLIプロバイダーのクラスを取得（見つからない場合はNone）。"""
    return CLI_PROVIDERS.get(name.strip().lower())


# 公開シンボルを明示
__all__ = ["register_provider", "get_available_providers", "get_provider_class", "CLI_PROVIDERS"]
