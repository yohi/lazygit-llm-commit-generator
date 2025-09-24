"""
Google Gemini API プロバイダー

Google Gemini モデルを使用してコミットメッセージを生成する。
Gemini 1.5 Pro, Flash等のモデルに対応し、安全設定の制御もサポート。
"""

import logging
import time
from typing import Dict, Any, Optional, List

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from ..base_provider import BaseProvider, ProviderError, AuthenticationError, TimeoutError, ResponseError

logger = logging.getLogger(__name__)


class GeminiAPIProvider(BaseProvider):
    """
    Google Gemini APIプロバイダー

    Google Geminiモデルを使用してコミットメッセージを生成する。
    API認証、安全設定、エラーハンドリングに対応。
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Gemini APIプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: Geminiライブラリが利用できない場合
            AuthenticationError: APIキーが無効な場合
        """
        super().__init__(config)

        if not GEMINI_AVAILABLE:
            raise ProviderError(
                "Google Generative AIライブラリがインストールされていません。"
                "pip install google-generativeai を実行してください。"
            )

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Gemini API設定が無効です")

        # Gemini APIクライアントを初期化
        self.api_key = config.get('api_key')
        self.model_name = config.get('model_name', 'gemini-2.5-pro')

        if not self.api_key:
            raise AuthenticationError("Gemini APIキーが設定されていません")

        try:
            # Gemini APIを設定
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"Gemini APIプロバイダーを初期化: model={self.model_name}")
        except Exception as e:
            raise ProviderError(f"Gemini APIクライアントの初期化に失敗: {e}")

        # 追加設定
        additional_params = config.get('additional_params', {})
        self.temperature = additional_params.get('temperature', 0.3)
        self.top_p = additional_params.get('top_p', 1.0)
        self.top_k = additional_params.get('top_k', 32)
        self.max_retries = additional_params.get('max_retries', 3)

        # 安全設定
        self.safety_settings = self._configure_safety_settings(additional_params)

        # 生成設定
        self.generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
            top_p=self.top_p,
            top_k=self.top_k,
            max_output_tokens=self.max_tokens,
        )

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
        logger.debug(f"Gemini APIにリクエスト送信: model={self.model_name}, prompt_length={len(prompt)}")

        try:
            start_time = time.time()

            # Gemini API呼び出し
            response = self._make_api_request(prompt)

            elapsed_time = time.time() - start_time
            logger.info(f"Gemini API呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンスの検証
            if not self._validate_response(response):
                raise ResponseError("Gemini APIから無効なレスポンスを受信しました")

            return response

        except Exception as e:
            logger.exception("Gemini API呼び出し中にエラー")
            # Gemini固有のエラーハンドリング
            if "API_KEY_INVALID" in str(e) or "authentication" in str(e).lower():
                raise AuthenticationError(f"Gemini API認証に失敗しました: {e}") from e
            elif "quota" in str(e).lower() or "rate" in str(e).lower():
                raise ProviderError(f"Gemini APIクォータまたはレート制限に達しました: {e}") from e
            elif "timeout" in str(e).lower():
                raise TimeoutError(f"Gemini APIがタイムアウトしました: {e}") from e
            else:
                raise ProviderError(f"Gemini API呼び出しに失敗しました: {e}") from e

    def test_connection(self) -> bool:
        """
        Gemini APIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他の接続エラー
        """
        try:
            logger.debug("Gemini API接続テストを開始")

            # 簡単なテストリクエストを送信
            test_generation_config = genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=5,
            )

            test_response = self.model.generate_content(
                "Hello, this is a connection test.",
                generation_config=test_generation_config,
                safety_settings=self.safety_settings
            )

            if test_response and test_response.text:
                logger.info("Gemini API接続テスト成功")
                return True
            else:
                logger.warning("Gemini API接続テスト: 無効なレスポンス")
                return False

        except Exception as e:
            logger.exception("Gemini API接続テストエラー")
            if "API_KEY_INVALID" in str(e) or "authentication" in str(e).lower():
                raise AuthenticationError(f"Gemini API認証に失敗しました: {e}") from e
            else:
                raise ProviderError(f"Gemini API接続テストに失敗しました: {e}") from e

    def supports_streaming(self) -> bool:
        """
        ストリーミング出力をサポートするかどうか

        Returns:
            Gemini APIはストリーミングをサポート
        """
        return True

    def generate_commit_message_stream(self, diff: str, prompt_template: str):
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
        logger.debug(f"Gemini APIストリーミングリクエスト: model={self.model_name}")

        stream = None
        try:
            # ストリーミングAPI呼び出し
            stream = self.model.generate_content(
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=True
            )

            accumulated_content = ""

            for chunk in stream:
                if chunk.text:
                    content = chunk.text
                    accumulated_content += content
                    yield content

            # 最終的なレスポンス検証
            if not accumulated_content.strip():
                raise ProviderError("Gemini APIから空のレスポンスを受信しました")

            if not self._validate_response(accumulated_content):
                logger.warning("ストリーミングレスポンスの検証に失敗")

        except (GeneratorExit, KeyboardInterrupt):
            # 中断シグナルは即座に再発生
            raise
        except Exception as e:
            logger.exception("Geminiストリーミングエラー")
            if "API_KEY_INVALID" in str(e) or "authentication" in str(e).lower():
                raise AuthenticationError(f"Gemini API認証に失敗しました: {e}") from e
            elif "quota" in str(e).lower() or "rate" in str(e).lower():
                raise ProviderError(f"Gemini APIクォータまたはレート制限に達しました: {e}") from e
            elif "timeout" in str(e).lower():
                raise TimeoutError(f"Gemini APIがタイムアウトしました: {e}") from e
            else:
                raise ProviderError(f"Geminiストリーミングに失敗しました: {e}") from e
        finally:
            # ストリームリソースの清理
            if stream and hasattr(stream, 'close'):
                try:
                    stream.close()
                except Exception:
                    pass  # 清理エラーは無視

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['api_key', 'model_name']

    def _make_api_request(self, prompt: str) -> str:
        """
        Gemini APIリクエストを実行（リトライ機能付き）

        Args:
            prompt: 送信するプロンプト

        Returns:
            APIからのレスポンス

        Raises:
            各種Gemini API例外
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )

                if response and response.text:
                    return response.text.strip()

                raise ResponseError("Gemini APIから空のレスポンスを受信しました")

            except Exception as e:
                last_exception = e
                # レート制限やタイムアウトの場合はリトライ
                if any(keyword in str(e).lower() for keyword in ['rate', 'quota', 'timeout']):
                    if attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt  # 指数バックオフ
                        logger.warning(f"Gemini APIエラー、{wait_time}秒後にリトライ（{attempt + 1}/{self.max_retries}）: {e}")
                        time.sleep(wait_time)
                    else:
                        raise e
                else:
                    # リトライしないエラー
                    raise e

        # すべてのリトライが失敗した場合
        if last_exception:
            raise last_exception
        else:
            raise ProviderError("Gemini APIリクエストがすべて失敗しました")

    def _configure_safety_settings(self, additional_params: Dict[str, Any]) -> Dict[HarmCategory, HarmBlockThreshold]:
        """
        Geminiの安全設定を構成

        Args:
            additional_params: 追加パラメータ

        Returns:
            安全設定の辞書
        """
        # デフォルトの安全設定（比較的緩い設定）
        default_safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # 設定ファイルからの安全設定を適用
        safety_config = additional_params.get('safety_settings', [])
        if safety_config:
            try:
                custom_safety_settings = {}
                for setting in safety_config:
                    category = setting.get('category')
                    threshold = setting.get('threshold')

                    # カテゴリの変換
                    harm_category = self._parse_harm_category(category)
                    harm_threshold = self._parse_harm_threshold(threshold)

                    if harm_category and harm_threshold:
                        custom_safety_settings[harm_category] = harm_threshold

                if custom_safety_settings:
                    logger.info("カスタム安全設定を適用")
                    return custom_safety_settings

            except Exception as e:
                logger.warning(f"カスタム安全設定の解析に失敗、デフォルトを使用: {e}")

        return default_safety_settings

    def _parse_harm_category(self, category: str) -> Optional[HarmCategory]:
        """文字列からHarmCategoryを解析"""
        category_map = {
            'HARM_CATEGORY_HARASSMENT': HarmCategory.HARM_CATEGORY_HARASSMENT,
            'HARM_CATEGORY_HATE_SPEECH': HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            'HARM_CATEGORY_SEXUALLY_EXPLICIT': HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            'HARM_CATEGORY_DANGEROUS_CONTENT': HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        }
        return category_map.get(category)

    def _parse_harm_threshold(self, threshold: str) -> Optional[HarmBlockThreshold]:
        """文字列からHarmBlockThresholdを解析"""
        threshold_map = {
            'BLOCK_NONE': HarmBlockThreshold.BLOCK_NONE,
            'BLOCK_LOW_AND_ABOVE': HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            'BLOCK_MEDIUM_AND_ABOVE': HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            'BLOCK_ONLY_HIGH': HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
        return threshold_map.get(threshold)

    def _get_supported_models(self) -> list[str]:
        """
        サポートされているモデル一覧を取得

        Returns:
            サポートされているモデル名のリスト
        """
        return [
            # 最新GA版(2025年)
            'gemini-2.5-pro',
            'gemini-2.5-flash',
            'gemini-2.5-flash-lite',  # プレビュー版
            # 既存モデル(フォールバック)
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-1.0-pro',
            'gemini-pro'
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """
        現在のモデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'provider': 'gemini',
            'model': self.model_name,
            'supports_streaming': True,
            'max_output_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'safety_settings_enabled': bool(self.safety_settings),
            'supported_models': self._get_supported_models()
        }
