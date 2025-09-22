"""
API型LLMプロバイダーモジュール

REST API経由でLLMサービスにアクセスするプロバイダー群:
- OpenAI (GPT-4, GPT-3.5)
- Anthropic Claude API
- Google Gemini API
"""

from typing import Type
import logging
from ..base_provider import BaseProvider

logger = logging.getLogger(__name__)

# プロバイダー登録レジストリ(実装時に各プロバイダーが追加)
API_PROVIDERS: dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """
    APIプロバイダーを登録

    Args:
        name: プロバイダー名
        provider_class: プロバイダークラス
    """
    norm = name.strip().lower()
    if not norm:
        raise ValueError("provider name は空にできません")
    if not isinstance(provider_class, type) or not issubclass(provider_class, BaseProvider):
        raise TypeError("provider_class は BaseProvider のサブクラスである必要があります")
    if norm in API_PROVIDERS:
        logger.warning("API provider '%s' (正規化名: '%s') を上書き登録します", name, norm)
    API_PROVIDERS[norm] = provider_class


def get_available_providers() -> list[str]:
    """
    利用可能なAPIプロバイダー一覧を取得

    Returns:
        プロバイダー名のリスト
    """
    return sorted(API_PROVIDERS.keys())


def get_provider_class(name: str) -> Type[BaseProvider] | None:
    """名前でAPIプロバイダーのクラスを取得(見つからない場合はNone)。"""
    return API_PROVIDERS.get(name.strip().lower())


__all__ = ["API_PROVIDERS", "get_available_providers", "get_provider_class", "register_provider"]
