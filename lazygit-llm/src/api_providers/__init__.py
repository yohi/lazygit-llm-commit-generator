"""
API型LLMプロバイダーモジュール

REST API経由でLLMサービスにアクセスするプロバイダー群：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic Claude API
- Google Gemini API
"""

from typing import Dict, Type
from ..base_provider import BaseProvider

# プロバイダー登録レジストリ（実装時に各プロバイダーが追加）
API_PROVIDERS: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """
    APIプロバイダーを登録

    Args:
        name: プロバイダー名
        provider_class: プロバイダークラス
    """
    API_PROVIDERS[name] = provider_class


def get_available_providers() -> list[str]:
    """
    利用可能なAPIプロバイダー一覧を取得

    Returns:
        プロバイダー名のリスト
    """
    return list(API_PROVIDERS.keys())