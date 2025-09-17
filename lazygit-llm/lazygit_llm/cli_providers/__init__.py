"""
CLI型LLMプロバイダーモジュール

コマンドライン経由でLLMサービスにアクセスするプロバイダー群:
- Gemini CLI (gcloud)
- Claude Code CLI (claude-code)
"""

from typing import Dict, Type
import logging
from ..base_provider import BaseProvider

logger = logging.getLogger(__name__)

# プロバイダー登録レジストリ（実装時に各プロバイダーが追加）
CLI_PROVIDERS: Dict[str, Type[BaseProvider]] = {}


def register_provider(name: str, provider_class: Type[BaseProvider]) -> None:
    """
    CLIプロバイダーを登録

    Args:
        name: プロバイダー名
        provider_class: プロバイダークラス
    """
    if name in CLI_PROVIDERS:
        logger.warning("CLI provider '%s' を上書き登録します", name)
    CLI_PROVIDERS[name] = provider_class


def get_available_providers() -> list[str]:
    """
    利用可能なCLIプロバイダー一覧を取得

    Returns:
        プロバイダー名のリスト
    """
    return list(CLI_PROVIDERS.keys())
