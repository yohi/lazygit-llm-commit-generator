"""
OpenAI API プロバイダー

OpenAI GPT モデルを使用してコミットメッセージを生成する。
GPT-4、GPT-3.5-turbo等のモデルに対応し、ストリーミング出力もサポート。
"""

import logging
import time
from typing import Dict, Any, Optional, Iterator

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from ..base_provider import BaseProvider, ProviderError, AuthenticationError, TimeoutError, ResponseError

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """
    OpenAI APIプロバイダー

    OpenAI GPTモデルを使用してコミットメッセージを生成する。
    API認証、エラーハンドリング、ストリーミング出力に対応。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        OpenAIプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: OpenAIライブラリが利用できない場合
            AuthenticationError: APIキーが無効な場合
        """
        super().__init__(config)

        if not OPENAI_AVAILABLE:
            raise ProviderError(
                "OpenAIライブラリがインストールされていません。"
                "pip install openai を実行してください。"
            )

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("OpenAI設定が無効です")

        # OpenAIクライアントを初期化
        self.api_key = config.get('api_key')
        self.model = config.get('model_name', 'gpt-4')

        if not self.api_key:
            raise AuthenticationError("OpenAI APIキーが設定されていません")

        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"OpenAIプロバイダーを初期化: model={self.model}")
        except Exception as e:
            raise ProviderError(f"OpenAIクライアントの初期化に失敗: {e}") from e

        # 追加設定
        self.temperature = config.get('additional_params', {}).get('temperature', 0.3)
        self.top_p = config.get('additional_params', {}).get('top_p', 1.0)
        self.max_retries = config.get('additional_params', {}).get('max_retries', 3)
        self.timeout = config.get('additional_params', {}).get('timeout', 30)
        self.max_tokens = config.get('additional_params', {}).get('max_tokens', 500)

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Git差分からコミットメッセージを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Returns:
            生成されたコミットメッセージ

        Raises:
            AuthenticationError: API認証エラー
            TimeoutError: タイムアウトエラー
            ResponseError: レスポンスエラー
            ProviderError: その他のプロバイダーエラー
        """
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        prompt = self._format_prompt(diff, prompt_template)
        logger.debug(f"OpenAI APIにリクエスト送信: model={self.model}, prompt_length={len(prompt)}")

        try:
            start_time = time.time()

            # OpenAI API呼び出し
            response = self._make_api_request(prompt)

            elapsed_time = time.time() - start_time
            logger.info(f"OpenAI API呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンスの検証
            if not self._validate_response(response):
                raise ResponseError("OpenAI APIから無効なレスポンスを受信しました")

            return response

        except openai.AuthenticationError as e:
            logger.exception("OpenAI認証エラー")
            raise AuthenticationError(f"OpenAI API認証に失敗しました: {e}") from e

        except openai.RateLimitError as e:
            logger.exception("OpenAI APIレート制限エラー")
            raise ProviderError(f"OpenAI APIレート制限に達しました: {e}") from e

        except openai.APITimeoutError as e:
            logger.exception("OpenAI APIタイムアウト")
            raise TimeoutError(f"OpenAI APIがタイムアウトしました: {e}") from e

        except openai.APIError as e:
            logger.exception("OpenAI APIエラー")
            raise ProviderError(f"OpenAI APIエラー: {e}") from e

        except Exception as e:
            logger.exception("OpenAI API呼び出し中に予期しないエラー")
            raise ProviderError(f"OpenAI API呼び出しに失敗しました: {e}") from e

    def test_connection(self) -> bool:
        """
        OpenAI APIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他の接続エラー
        """
        try:
            logger.debug("OpenAI API接続テストを開始")

            # 簡単なテストリクエストを送信
            test_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a connection test."}
                ],
                max_tokens=5,
                timeout=10
            )

            if test_response and test_response.choices:
                logger.info("OpenAI API接続テスト成功")
                return True
            else:
                logger.warning("OpenAI API接続テスト: 無効なレスポンス")
                return False

        except openai.AuthenticationError as e:
            logger.exception("OpenAI認証エラー")
            raise AuthenticationError(f"OpenAI API認証に失敗しました: {e}") from e

        except Exception as e:
            logger.exception("OpenAI API接続テストエラー")
            raise ProviderError(f"OpenAI API接続テストに失敗しました: {e}") from e

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
        logger.debug(f"OpenAI APIストリーミングリクエスト: model={self.model}")

        try:
            # ストリーミングAPI呼び出し
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                timeout=self.timeout,
                stream=True
            )

            accumulated_content = ""

            for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        accumulated_content += content
                        yield content

            # 最終的なレスポンス検証
            if not self._validate_response(accumulated_content):
                logger.warning("ストリーミングレスポンスの検証に失敗")

        except openai.AuthenticationError as e:
            logger.exception("OpenAIストリーミング認証エラー")
            raise AuthenticationError(f"OpenAI API認証に失敗しました: {e}") from e

        except Exception as e:
            logger.exception("OpenAIストリーミングエラー")
            raise ProviderError(f"OpenAIストリーミングに失敗しました: {e}") from e

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['api_key', 'model_name']

    def _make_api_request(self, prompt: str) -> str:
        """
        OpenAI APIリクエストを実行（リトライ機能付き）

        Args:
            prompt: 送信するプロンプト

        Returns:
            APIからのレスポンス

        Raises:
            各種OpenAI API例外
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    timeout=self.timeout
                )

                if response.choices and response.choices[0].message:
                    content = response.choices[0].message.content
                    if content:
                        return content.strip()

                raise ResponseError("OpenAI APIから空のレスポンスを受信しました")

            except (openai.RateLimitError, openai.APITimeoutError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # 指数バックオフ
                    logger.warning(f"OpenAI APIエラー、{wait_time}秒後にリトライ({attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(wait_time)
                else:
                    raise e

            except Exception as e:
                # リトライしないエラー
                raise e

        # すべてのリトライが失敗した場合
        if last_exception:
            raise last_exception
        else:
            raise ProviderError("OpenAI APIリクエストがすべて失敗しました")

    def _get_supported_models(self) -> list[str]:
        """
        サポートされているモデル一覧を取得

        Returns:
            サポートされているモデル名のリスト
        """
        return [
            'gpt-4',
            'gpt-4-turbo-preview',
            'gpt-4-1106-preview',
            'gpt-3.5-turbo',
            'gpt-3.5-turbo-1106',
            'gpt-3.5-turbo-16k'
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """
        現在のモデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'provider': 'openai',
            'model': self.model,
            'supports_streaming': True,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'supported_models': self._get_supported_models()
        }