"""
ベースプロバイダーインターフェース

全てのLLMプロバイダーが実装すべき共通インターフェースを定義。
API型とCLI型の両方に対応する抽象基底クラス。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from string import Template
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class BaseProvider(ABC):
    """全LLMプロバイダーの基底クラス"""

    def __init__(self, config: Dict[str, Any]):
        """
        プロバイダーを初期化

        Args:
            config: プロバイダー固有の設定情報
        """
        self.config = config
        self.timeout = config.get('timeout', 30)
        self.max_tokens = config.get('max_tokens', 100)

    @abstractmethod
    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Gitの差分からコミットメッセージを生成

        Args:
            diff: `git diff --staged`の出力
            prompt_template: LLMに送信するプロンプトテンプレート

        Returns:
            生成されたコミットメッセージ

        Raises:
            ProviderError: プロバイダー固有のエラー
            ProviderTimeoutError: タイムアウトエラー
            AuthenticationError: 認証エラー
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        プロバイダーへの接続をテスト

        Returns:
            接続が成功した場合True、失敗した場合False
        """
        pass

    def supports_streaming(self) -> bool:
        """
        ストリーミング出力をサポートするかどうか

        Returns:
            ストリーミングをサポートする場合True
        """
        return False

    def validate_config(self) -> bool:
        """
        設定情報を検証

        Returns:
            設定が有効な場合True、無効な場合False
        """
        required_fields = self.get_required_config_fields()
        for field in required_fields:
            if field not in self.config or self.config.get(field) in ("", None):
                logger.error(f"必須設定項目が不足: {field}")
                return False
        return True

    @abstractmethod
    def get_required_config_fields(self) -> list[str]:
        """
        このプロバイダーに必要な設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        pass

    def _format_prompt(self, diff: str, prompt_template: str) -> str:
        """
        プロンプトテンプレートに差分を挿入してプロンプトを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート（{diff}プレースホルダーを含む）

        Returns:
            フォーマット済みプロンプト
        """
        # 後方互換: 旧 `{diff}` を `$diff` に正規化
        if "{diff}" in prompt_template:
            prompt_template = prompt_template.replace("{diff}", "$diff")
        tmpl = Template(prompt_template)
        return tmpl.safe_substitute(diff=diff)

    def _validate_response(self, response: str) -> bool:
        """
        LLMからのレスポンスを検証

        Args:
            response: LLMからのレスポンス

        Returns:
            レスポンスが有効な場合True
        """
        if not response or not response.strip():
            return False

        # 最大長チェック（LazyGitでの表示を考慮）
        max_len = int(self.config.get("max_message_length", 500))
        if len(response) > max_len:
            logger.warning("生成されたコミットメッセージが長すぎます")
            return False

        return True


class ProviderError(Exception):
    """プロバイダー固有のエラー"""
    pass


class AuthenticationError(ProviderError):
    """認証エラー"""
    pass


class ProviderTimeoutError(ProviderError):
    """タイムアウトエラー"""
    pass


class ResponseError(ProviderError):
    """レスポンスエラー"""
    pass
