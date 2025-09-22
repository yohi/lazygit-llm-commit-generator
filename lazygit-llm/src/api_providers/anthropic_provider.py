"""
Anthropic Claude API プロバイダー

Anthropic Claude モデルを使用してコミットメッセージを生成する。
Claude-3 Opus, Sonnet, Haiku等のモデルに対応し、ストリーミング出力もサポート。
"""

import logging
import time
from typing import Dict, Any, Optional, Iterator

try:
    import anthropic
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from ..base_provider import BaseProvider, ProviderError, AuthenticationError, TimeoutError, ResponseError

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """
    Anthropic Claude APIプロバイダー

    Anthropic Claudeモデルを使用してコミットメッセージを生成する。
    API認証、エラーハンドリング、ストリーミング出力に対応。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Anthropicプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: Anthropicライブラリが利用できない場合
            AuthenticationError: APIキーが無効な場合
        """
        super().__init__(config)

        if not ANTHROPIC_AVAILABLE:
            raise ProviderError(
                "Anthropicライブラリがインストールされていません。"
                "pip install anthropic を実行してください。"
            )

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Anthropic設定が無効です")

        # Anthropicクライアントを初期化
        self.api_key = config.get('api_key')
        self.model = config.get('model_name', 'claude-opus-4-1-20250805')

        if not self.api_key:
            raise AuthenticationError("Anthropic APIキーが設定されていません")

        try:
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"Anthropicプロバイダーを初期化: model={self.model}")
        except Exception as e:
            raise ProviderError(f"Anthropicクライアントの初期化に失敗: {e}") from e

        # 追加設定(Claudeは max_tokens_to_sample を使用)
        additional_params = config.get('additional_params', {})
        self.max_tokens_to_sample = additional_params.get('max_tokens_to_sample', self.max_tokens)
        self.temperature = additional_params.get('temperature', 0.3)
        self.top_p = additional_params.get('top_p', 1.0)
        self.max_retries = additional_params.get('max_retries', 3)


    def test_connection(self) -> bool:
        """
        Anthropic APIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他の接続エラー
        """
        try:
            logger.debug("Anthropic API接続テストを開始")

            # 簡単なテストリクエストを送信
            test_response = self.client.messages.create(
                model=self.model,
                max_tokens=5,
                messages=[
                    {"role": "user", "content": "Hello, this is a connection test."}
                ]
            )

            if test_response and test_response.content:
                logger.info("Anthropic API接続テスト成功")
                return True
            else:
                logger.warning("Anthropic API接続テスト: 無効なレスポンス")
                return False

        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropic認証エラー: {e}")
            raise AuthenticationError(f"Anthropic API認証に失敗しました: {e}") from e

        except Exception as e:
            logger.error(f"Anthropic API接続テストエラー: {e}")
            raise ProviderError(f"Anthropic API接続テストに失敗しました: {e}") from e

    def supports_streaming(self) -> bool:
        """
        ストリーミング出力をサポートするかどうか

        Returns:
            ストリーミングをサポートする場合True
        """
        return True

    def generate_commit_message_stream(self, diff: str, prompt_template: str) -> Iterator[str]:
        """
        ストリーミングでコミットメッセージを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Yields:
            生成されたテキストのチャンク

        Raises:
            AuthenticationError: API認証エラー
            TimeoutError: タイムアウトエラー
            ProviderError: その他のプロバイダーエラー
        """
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        prompt = self._format_prompt(diff, prompt_template)
        logger.debug(f"Anthropic APIストリーミングリクエスト: model={self.model}")

        try:
            # ストリーミングAPI呼び出し
            stream = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_to_sample,
                temperature=self.temperature,
                top_p=self.top_p,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            accumulated_content = ""

            for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        content = event.delta.text
                        accumulated_content += content
                        yield content

            # 最終的なレスポンス検証
            if not self._validate_response(accumulated_content):
                logger.warning("ストリーミングレスポンスの検証に失敗")

        except anthropic.AuthenticationError as e:
            logger.error(f"Anthropicストリーミング認証エラー: {e}")
            raise AuthenticationError(f"Anthropic API認証に失敗しました: {e}") from e

        except Exception as e:
            logger.error(f"Anthropicストリーミングエラー: {e}")
            raise ProviderError(f"Anthropicストリーミングに失敗しました: {e}") from e

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['api_key', 'model_name']

    def _make_api_request(self, prompt: str) -> str:
        """
        Anthropic APIリクエストを実行(リトライ機能付き)

        Args:
            prompt: 送信するプロンプト

        Returns:
            APIからのレスポンス

        Raises:
            各種Anthropic API例外
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens_to_sample,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    messages=[{"role": "user", "content": prompt}]
                )

                if response.content and len(response.content) > 0:
                    # Claude APIは content がリスト形式
                    content_block = response.content[0]
                    if hasattr(content_block, 'text'):
                        return content_block.text.strip()

                raise ResponseError("Anthropic APIから空のレスポンスを受信しました")

            except (anthropic.RateLimitError, anthropic.APITimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    logger.warning(f"Anthropic APIエラー、{wait_time}秒後にリトライ({attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    raise

            except Exception as e:
                # リトライしないエラー
                raise

        # すべてのリトライが失敗した場合
        if last_exception:
            raise last_exception
        else:
            raise ProviderError("Anthropic APIリクエストがすべて失敗しました")

    def _get_supported_models(self) -> list[str]:
        """
        サポートされているモデル一覧を取得

        Returns:
            サポートされているモデル名のリスト
        """
        return [
            # 最新モデル(2025年リリース)
            'claude-opus-4-1-20250805',
            'claude-opus-4-20250514',
            'claude-sonnet-4-20250514',
            'claude-3-7-sonnet-20250219',
            'claude-3-7-sonnet-latest',  # エイリアス
            # 既存モデル
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022',
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307',
            'claude-2.1',
            'claude-2.0',
            'claude-instant-1.2'
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """
        現在のモデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'provider': 'anthropic',
            'model': self.model,
            'supports_streaming': True,
            'max_tokens_to_sample': self.max_tokens_to_sample,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'supported_models': self._get_supported_models()
        }

    def _format_prompt_for_claude(self, prompt: str) -> str:
        """
        Claude向けにプロンプトを最適化

        Args:
            prompt: 基本プロンプト

        Returns:
            Claude向けに最適化されたプロンプト
        """
        # Claudeは明確な指示と構造化された入力を好む
        optimized_prompt = f"""Please analyze the following git diff and generate a concise, descriptive commit message.

Instructions:
- Generate only the commit message, no additional explanation
- Follow conventional commit format if possible (type: description)
- Keep it concise but descriptive
- Focus on what was changed and why

Git diff:
{prompt}

Commit message:"""

        return optimized_prompt

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Git差分からコミットメッセージを生成(Claude最適化版)

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Returns:
            生成されたコミットメッセージ
        """
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        # 基本プロンプトを作成
        basic_prompt = self._format_prompt(diff, prompt_template)

        # Claude向けに最適化
        optimized_prompt = self._format_prompt_for_claude(basic_prompt)

        logger.debug(f"Anthropic APIにリクエスト送信: model={self.model}, prompt_length={len(optimized_prompt)}")

        try:
            start_time = time.time()

            # Anthropic API呼び出し
            response = self._make_api_request_optimized(optimized_prompt)

            elapsed_time = time.time() - start_time
            logger.info(f"Anthropic API呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンスの検証
            if not self._validate_response(response):
                raise ResponseError("Anthropic APIから無効なレスポンスを受信しました")

            return response

        except Exception as e:
            # エラーハンドリングは既存のメソッドと同様
            logger.error(f"Anthropic API呼び出しエラー: {e}")
            raise

    def _make_api_request_optimized(self, prompt: str) -> str:
        """
        最適化されたAnthropic APIリクエスト

        Args:
            prompt: 最適化されたプロンプト

        Returns:
            APIからのレスポンス
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens_to_sample,
                temperature=self.temperature,
                top_p=self.top_p,
                messages=[{"role": "user", "content": prompt}]
            )

            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    return content_block.text.strip()

            raise ResponseError("Anthropic APIから空のレスポンスを受信しました")

        except Exception as e:
            raise ProviderError(f"Anthropic APIリクエストに失敗: {e}") from e