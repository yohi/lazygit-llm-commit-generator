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
    ALLOWED_BINARIES: ClassVar[tuple[str, ...]] = ('gemini', 'gemini-wrapper.sh')
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
            # まずstdoutとstderrを結合してチェック
            combined_output = f"{stdout_output}\n{stderr_output}".lower()

            # クォータ制限の改善された検出
            if any(keyword in combined_output for keyword in ["quota exceeded", "429", "rate limit", "クォータ制限", "フォールバック"]):
                # ラッパースクリプトからのフォールバック情報があれば、それを利用
                if "フォールバック成功" in stderr_output or "フォールバック成功" in stdout_output:
                    logger.info("ラッパースクリプトによるフォールバック処理が検出されました")
                    # フォールバック成功時でも終了コード1の場合は、実際のGeminiエラーを確認
                    if stdout_output.strip():
                        return stdout_output.strip()  # Geminiからの実際の回答を返す
                raise ProviderError(f"⚠️ Gemini APIクォータ制限: 1日あたりのリクエスト制限に達しました\n🔄 自動フォールバック機能が利用可能です（gemini-wrapper使用時）\n💡 明日再試行するか、別のプロバイダー（openai、anthropic）をご利用ください") from e
            elif "authentication" in combined_output or "api key" in combined_output:
                raise AuthenticationError("🔑 Gemini CLI認証エラー: APIキーまたは認証設定を確認してください") from e
            elif any(keyword in combined_output for keyword in ["network", "connection", "connectivity"]):
                raise ProviderError(f"🌐 ネットワーク接続エラー: {stderr_output}\n📡 インターネット接続を確認してください") from e
            elif any(keyword in combined_output for keyword in ["timeout", "timed out"]):
                raise ProviderTimeoutError(f"⏰ Gemini APIタイムアウト: {stderr_output}\n⚙️ 設定ファイルでtimeout値を増やしてください") from e
            # Gemini CLIの一般的なエラー（改善）
            elif "error when talking to gemini api" in combined_output:
                if stdout_output.strip():
                    # stdoutに有効な内容があれば、それを返す（クォータエラー後のフォールバック成功）
                    logger.warning("Gemini APIエラーが発生しましたが、有効なレスポンスが得られました")
                    return stdout_output.strip()
                raise ProviderError(f"🤖 Gemini API通信エラー: APIサービスとの通信に失敗しました\n📋 詳細: {stdout_output}\n💡 しばらく待ってから再試行してください") from e
            elif e.returncode == 1 and not stdout_output.strip():
                # 標準出力が空で終了コード1の場合のみ認証エラーとする
                raise AuthenticationError("🔑 Gemini CLI認証エラー: 認証情報を確認してください") from e
            else:
                error_msg = stderr_output or stdout_output or "不明なエラー"
                raise ProviderError(f"Gemini CLI実行エラー (終了コード: {e.returncode}): {error_msg}") from e
        except Exception as e:
            logger.exception("Gemini CLI実行中に予期しないエラー")
            raise ProviderError(f"Gemini CLI予期しないエラー: {e}") from e

    def _verify_gemini_binary(self) -> str:
        """
        geminiバイナリのパスを検証（ラッパースクリプト優先）

        Returns:
            検証済みのgeminiバイナリパス

        Raises:
            ProviderError: geminiコマンドが見つからない場合
        """
        # 1. ラッパースクリプトを最優先で検索
        wrapper_path = Path.home() / "bin" / "gemini-wrapper.sh"
        if wrapper_path.exists() and wrapper_path.is_file():
            # ラッパースクリプトが実行可能かチェック
            if os.access(wrapper_path, os.X_OK):
                logger.info(f"改善されたgeminiラッパースクリプトを使用: {wrapper_path}")
                return str(wrapper_path)
            else:
                logger.warning(f"ラッパースクリプトが実行可能ではありません: {wrapper_path}")

        # 2. 標準のgeminiコマンドを検索
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

        logger.debug(f"標準geminiバイナリを使用: {gemini_path}")
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

        # プロンプト指定（--prompt を使用）
        cmd.extend(['--prompt', prompt])

        # 環境変数設定（APIキーがある場合）
        env = os.environ.copy()
        if self.api_key:
            env['GEMINI_API_KEY'] = self.api_key
            env['GOOGLE_API_KEY'] = self.api_key

        logger.debug(f"小さなプロンプト({len(prompt)}bytes)をコマンド引数で実行")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False
        )

        # デバッグログを追加
        logger.debug(f"subprocess結果: returncode={result.returncode}, stdout_length={len(result.stdout) if result.stdout else 0}, stderr_length={len(result.stderr) if result.stderr else 0}")
        logger.debug(f"stdout内容: {result.stdout[:200] if result.stdout else 'None'}...")
        logger.debug(f"stderr内容: {result.stderr[:200] if result.stderr else 'None'}...")

        # "Error when talking to Gemini API"メッセージがあっても、有効なコンテンツがstdoutにある場合は成功とみなす
        if result.returncode != 0:
            stdout_content = result.stdout.strip() if result.stdout else ""
            stderr_content = result.stderr.strip() if result.stderr else ""

            # Gemini CLIの「Error when talking to Gemini API」はクォータ制限を示すことが多い
            if "Error when talking to Gemini API" in stdout_content:
                logger.info("Gemini APIエラーメッセージを検出: クォータ制限の可能性があります")
                # エラーメッセージ部分を除去して、実際のコンテンツがあるかチェック
                cleaned_output = stdout_content.replace("Error when talking to Gemini API", "").strip()
                lines = [line for line in cleaned_output.split('\n') if line.strip() and not line.startswith('Loaded cached credentials') and not 'Full report available' in line]

                if lines:
                    logger.warning(f"Gemini APIエラーがありましたが、有効なコンテンツも取得できました: {' '.join(lines)[:100]}...")
                    return '\n'.join(lines)
                else:
                    # 有効なコンテンツがない場合はクォータエラーとして処理
                    logger.info("有効なコンテンツが見つからないため、クォータエラーとして処理します")
                    raise ProviderError(f"🚨 Gemini APIクォータ制限: 1日あたりのリクエスト制限に達しました\n💡 明日再試行するか、別のプロバイダー（openai、anthropic）をご利用ください\n📋 詳細: {stdout_content[:200]}...") from e

            # より詳細なエラー情報を提供
            stderr_msg = stderr_content or "不明なエラー"
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
