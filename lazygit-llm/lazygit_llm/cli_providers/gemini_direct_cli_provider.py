"""
Gemini CLI プロバイダー（ダイレクト gemini コマンド使用）

ローカルの gemini コマンドを直接使用してGeminiモデルにアクセスする。
厳格なセキュリティ制御に従い、subprocess実行時の安全性を確保。
"""

import subprocess
import logging
import os
import shutil
import json
import tempfile
from typing import Dict, Any, Optional, List, ClassVar
from pathlib import Path

from lazygit_llm.base_provider import BaseProvider, ProviderError, AuthenticationError, ProviderTimeoutError, ResponseError

logger = logging.getLogger(__name__)


class GeminiDirectCLIProvider(BaseProvider):
    """
    Gemini CLI プロバイダー（gemini コマンド直接使用）

    ローカルの gemini コマンドを使用してGeminiモデルにアクセス。
    セキュリティ要件に従った安全なsubprocess実行を実装。
    """

    # セキュリティ設定
    ALLOWED_BINARIES: ClassVar[tuple[str, ...]] = ('gemini',)
    MAX_STDOUT_SIZE: ClassVar[int] = 1024 * 1024  # 1MB
    MAX_STDERR_SIZE: ClassVar[int] = 1024 * 1024  # 1MB
    DEFAULT_TIMEOUT: ClassVar[int] = 30  # 30秒
    MAX_TIMEOUT: ClassVar[int] = 300     # 5分（設定可能な最大値）

    def __init__(self, config: Dict[str, Any]):
        """
        Gemini CLI プロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: geminiコマンドが利用できない場合
        """
        super().__init__(config)

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Gemini CLI設定が無効です")

        self.model = config.get('model_name', 'gemini-1.5-pro')

        # 追加設定
        additional_params = config.get('additional_params', {})
        self.temperature = additional_params.get('temperature', 0.3)
        self.max_output_tokens = additional_params.get('max_output_tokens', self.max_tokens)

        # APIキーはオプション（geminiコマンドが認証済みの場合は不要）
        self.api_key = additional_params.get('api_key') or config.get('api_key')
        if self.api_key:
            logger.debug("APIキーが設定されています（環境変数として使用）")
        else:
            logger.debug("APIキーなし - geminiコマンドの認証情報を使用します")

        # セキュリティ設定
        cfg_timeout = int(config.get('timeout', self.DEFAULT_TIMEOUT))
        self.cli_timeout = min(max(cfg_timeout, 1), self.MAX_TIMEOUT)

        # geminiバイナリの検証
        self.gemini_path = self._verify_gemini_binary()

        logger.info(f"Gemini CLI プロバイダーを初期化: model={self.model}, gemini_path={self.gemini_path}")

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Git差分からコミットメッセージを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Returns:
            生成されたコミットメッセージ

        Raises:
            AuthenticationError: Gemini認証エラー
            ProviderTimeoutError: タイムアウトエラー
            ResponseError: レスポンス形式エラー
            ProviderError: その他のプロバイダーエラー
        """
        try:
            # プロンプトに差分を組み込み
            prompt = prompt_template.replace('{diff}', diff).replace('$diff', diff)

            # Geminiコマンドを実行
            response = self._execute_gemini_command(prompt)

            # レスポンスの検証とクリーンアップ
            if not self._validate_response(response):
                raise ResponseError("Geminiからの無効なレスポンス")

            return self._clean_response(response)

        except (AuthenticationError, ProviderTimeoutError, ResponseError, ProviderError):
            raise
        except subprocess.TimeoutExpired as e:
            logger.error("Geminiコマンドがタイムアウト: %s", e)
            raise ProviderTimeoutError(
                f"Gemini Direct CLIタイムアウト (制限時間: {self.cli_timeout}秒)\n"
                "ネットワーク接続を確認するか、設定ファイルでtimeout値を増やしてください"
            ) from e
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr if e.stderr else ""
            stdout_output = e.stdout if e.stdout else ""
            logger.error("Geminiコマンド実行エラー: returncode=%s, stderr=%s", e.returncode, stderr_output)

            # エラーの種類に応じた詳細なメッセージ
            if "quota exceeded" in stderr_output.lower() or "429" in stderr_output or "rate limit" in stderr_output.lower():
                raise ProviderError(f"Gemini APIクォータ制限: 1日あたりのリクエスト制限に達しました\n明日再試行するか、別のプロバイダー（openai、anthropic）をご利用ください") from e
            elif "authentication" in stderr_output.lower() or "api key" in stderr_output.lower():
                raise AuthenticationError("Gemini CLI認証エラー: APIキーまたは認証設定を確認してください") from e
            elif "network" in stderr_output.lower() or "connection" in stderr_output.lower() or "connectivity" in stderr_output.lower():
                raise ProviderError(f"ネットワーク接続エラー: {stderr_output}\nインターネット接続を確認してください") from e
            elif "timeout" in stderr_output.lower() or "timed out" in stderr_output.lower():
                raise ProviderTimeoutError(f"Gemini APIタイムアウト: {stderr_output}\n設定ファイルでtimeout値を増やしてください") from e
            elif e.returncode == 1:
                raise AuthenticationError("Gemini CLI認証エラー: 認証情報を確認してください") from e
            else:
                error_msg = stderr_output or stdout_output or "不明なエラー"
                raise ProviderError(f"Gemini CLI実行エラー (終了コード: {e.returncode}): {error_msg}") from e
        except Exception as e:
            logger.exception("Gemini CLI実行中に予期しないエラー")
            raise ProviderError(f"Gemini CLI予期しないエラー: {e}") from e

    def _verify_gemini_binary(self) -> str:
        """
        geminiバイナリのパスを検証

        Returns:
            検証済みのgeminiバイナリパス

        Raises:
            ProviderError: geminiコマンドが見つからない場合
        """
        gemini_path = shutil.which('gemini')
        if not gemini_path:
            raise ProviderError(
                "geminiコマンドが見つかりません。"
                "gemini CLIをインストールして、PATHに追加してください。"
            )

        # セキュリティ検証: 許可されたバイナリ名のみ
        binary_name = Path(gemini_path).name
        if binary_name not in self.ALLOWED_BINARIES:
            raise ProviderError(f"許可されていないバイナリ: {binary_name}")

        logger.debug(f"geminiバイナリを検証: {gemini_path}")
        return gemini_path

    def _execute_gemini_command(self, prompt: str, timeout: Optional[int] = None) -> str:
        """
        geminiコマンドを安全に実行

        Args:
            prompt: 送信するプロンプト
            timeout: タイムアウト秒数（未指定時はデフォルト値を使用）

        Returns:
            Geminiからのレスポンス

        Raises:
            subprocess.TimeoutExpired: タイムアウト
            ProviderError: 実行エラー
        """
        if timeout is None:
            timeout = self.cli_timeout

        # 大きなプロンプトはファイル経由で処理
        prompt_size = len(prompt.encode('utf-8'))
        use_tempfile = prompt_size > 8192  # 8KB以上はファイル経由

        if use_tempfile:
            return self._execute_with_tempfile(prompt, timeout)
        else:
            return self._execute_with_args(prompt, timeout)

    def _execute_with_tempfile(self, prompt: str, timeout: int) -> str:
        """一時ファイルを使用してgeminiコマンドを実行"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
            temp_file.write(prompt)
            temp_file_path = temp_file.name

        try:
            # このgemini CLIの場合、ファイル経由ではなくstdin経由を使用
            cmd = [self.gemini_path]

            # モデル指定（--modelまたは-mオプション）
            if self.model != 'gemini-1.5-pro':
                cmd.extend(['-m', self.model])

            # 環境変数設定（APIキーがある場合）
            env = os.environ.copy()
            if self.api_key:
                env['GEMINI_API_KEY'] = self.api_key
                env['GOOGLE_API_KEY'] = self.api_key
                env['OPENAI_API_KEY'] = self.api_key  # このgemini CLIがOpenAIも使用する可能性

            logger.debug(f"大きなプロンプト({len(prompt)}bytes)をstdin経由で実行")

            result = subprocess.run(
                cmd,
                input=prompt,  # stdin経由でプロンプト送信
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                check=False
            )

            if result.returncode != 0:
                # より詳細なエラー情報を提供
                stderr_msg = result.stderr.strip() if result.stderr else "不明なエラー"
                logger.error(f"geminiコマンド実行失敗: returncode={result.returncode}, stderr={stderr_msg}")
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

            return result.stdout

        finally:
            # 一時ファイルを削除
            try:
                os.unlink(temp_file_path)
            except OSError:
                pass

    def _execute_with_args(self, prompt: str, timeout: int) -> str:
        """コマンド引数でgeminiコマンドを実行"""
        # このgemini CLIの実際の引数構造に合わせて構築
        cmd = [self.gemini_path]

        # モデル指定（--modelまたは-mオプション）
        if self.model != 'gemini-1.5-pro':
            cmd.extend(['-m', self.model])

        # プロンプト指定（--promptまたは-pオプション、非推奨だが動作する）
        cmd.extend(['-p', prompt])

        # 環境変数設定（APIキーがある場合）
        env = os.environ.copy()
        if self.api_key:
            env['GEMINI_API_KEY'] = self.api_key
            env['GOOGLE_API_KEY'] = self.api_key
            env['OPENAI_API_KEY'] = self.api_key  # このgemini CLIがOpenAIも使用する可能性

        logger.debug(f"小さなプロンプト({len(prompt)}bytes)をコマンド引数で実行")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False
        )

        if result.returncode != 0:
            # より詳細なエラー情報を提供
            stderr_msg = result.stderr.strip() if result.stderr else "不明なエラー"
            logger.error(f"geminiコマンド実行失敗: returncode={result.returncode}, stderr={stderr_msg}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

        return result.stdout

    def _validate_response(self, response: str) -> bool:
        """
        Geminiレスポンスの基本検証

        Args:
            response: Geminiからのレスポンス

        Returns:
            レスポンスが有効な場合True
        """
        if not response or not response.strip():
            logger.warning("空のレスポンスを受信")
            return False

        # レスポンスサイズ制限
        if len(response) > self.MAX_STDOUT_SIZE:
            logger.warning(f"レスポンスサイズが制限を超過: {len(response)} > {self.MAX_STDOUT_SIZE}")
            return False

        return True

    def _clean_response(self, response: str) -> str:
        """
        Geminiレスポンスをクリーンアップ

        Args:
            response: 生のレスポンス

        Returns:
            クリーンアップされたレスポンス
        """
        # 前後の空白を削除
        cleaned = response.strip()

        # 一般的な不要プレフィックスを削除
        prefixes_to_remove = [
            "Commit message:",
            "Here's a commit message:",
            "Suggested commit message:",
            "The commit message is:",
            "Commit:",
        ]

        for prefix in prefixes_to_remove:
            if cleaned.lower().startswith(prefix.lower()):
                cleaned = cleaned[len(prefix):].strip()

        # マークダウンコードブロックを削除
        if cleaned.startswith('```') and cleaned.endswith('```'):
            lines = cleaned.split('\n')
            if len(lines) > 2:
                cleaned = '\n'.join(lines[1:-1]).strip()

        # 引用符を削除
        if ((cleaned.startswith('"') and cleaned.endswith('"')) or
            (cleaned.startswith("'") and cleaned.endswith("'"))):
            cleaned = cleaned[1:-1].strip()

        return cleaned

    def test_connection(self) -> bool:
        """
        Gemini CLIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他のエラー
        """
        try:
            # シンプルなテストプロンプトで接続を確認
            test_prompt = "Hello, respond with 'OK' only."
            response = self._execute_gemini_command(test_prompt, timeout=10)

            if response and response.strip():
                logger.info("Gemini CLI接続テスト成功")
                return True
            else:
                logger.error("Gemini CLI接続テスト失敗: 空のレスポンス")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Gemini CLI接続テストがタイムアウト")
            raise ProviderTimeoutError(
                f"Gemini CLI接続テストタイムアウト (制限時間: {self.cli_timeout}秒)\n"
                "ネットワーク接続を確認するか、設定ファイルでtimeout値を増やしてください"
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                raise AuthenticationError("Gemini CLI認証エラー")
            else:
                raise ProviderError(f"Gemini CLI接続テストエラー (code: {e.returncode})")
        except Exception as e:
            logger.exception("Gemini CLI接続テスト中に予期しないエラー")
            raise ProviderError(f"Gemini CLI接続テスト予期しないエラー: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """
        モデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'provider': 'gemini-cli',
            'model': self.model,
            'supports_streaming': False,
            'max_output_tokens': self.max_output_tokens,
            'temperature': self.temperature,
            'cli_path': self.gemini_path,
            'timeout': self.cli_timeout
        }

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['model_name']

    def validate_config(self) -> bool:
        """
        プロバイダー設定を検証

        Returns:
            設定が有効な場合True
        """
        # 基本設定の検証
        if not super().validate_config():
            return False

        # モデル名の検証
        model_name = self.config.get('model_name', '')
        if not model_name or not isinstance(model_name, str):
            logger.error("有効なmodel_nameが設定されていません")
            return False

        # タイムアウト設定の検証
        timeout = self.config.get('timeout', self.DEFAULT_TIMEOUT)
        try:
            timeout_int = int(timeout)
            if timeout_int <= 0 or timeout_int > self.MAX_TIMEOUT:
                logger.error(f"無効なタイムアウト設定: {timeout}")
                return False
        except (ValueError, TypeError):
            logger.error(f"タイムアウト設定が数値ではありません: {timeout}")
            return False

        return True
