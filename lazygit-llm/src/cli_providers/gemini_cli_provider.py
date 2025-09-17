"""
Gemini CLI プロバイダー

Google Cloud SDK (gcloud) を使用してGemini モデルにアクセスする。
厳格なセキュリティ制御に従い、subprocess実行時の安全性を確保。
"""

import subprocess
import shlex
import logging
import time
import os
import hashlib
from typing import Dict, Any, Optional, List
from pathlib import Path

from ..base_provider import BaseProvider, ProviderError, AuthenticationError, TimeoutError, ResponseError

logger = logging.getLogger(__name__)


class GeminiCLIProvider(BaseProvider):
    """
    Gemini CLIプロバイダー

    Google Cloud SDK (gcloud) を使用してGeminiモデルにアクセス。
    セキュリティ要件に従った安全なsubprocess実行を実装。
    """

    # セキュリティ設定
    ALLOWED_BINARIES = ['gcloud']
    MAX_STDOUT_SIZE = 1024 * 1024  # 1MB
    MAX_STDERR_SIZE = 1024 * 1024  # 1MB
    DEFAULT_TIMEOUT = 30  # 30秒
    MAX_TIMEOUT = 300     # 5分（設定可能な最大値）

    def __init__(self, config: Dict[str, Any]):
        """
        Gemini CLIプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: gcloudコマンドが利用できない場合
        """
        super().__init__(config)

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Gemini CLI設定が無効です")

        self.model = config.get('model_name', 'gemini-1.5-pro')

        # 追加設定
        additional_params = config.get('additional_params', {})
        self.project_id = additional_params.get('project_id')
        self.location = additional_params.get('location', 'us-central1')
        self.temperature = additional_params.get('temperature', 0.3)
        self.max_output_tokens = additional_params.get('max_output_tokens', self.max_tokens)

        # セキュリティ設定
        self.cli_timeout = min(config.get('timeout', self.DEFAULT_TIMEOUT), self.MAX_TIMEOUT)

        # gcloudバイナリの検証
        self.gcloud_path = self._verify_gcloud_binary()

        logger.info(f"Gemini CLIプロバイダーを初期化: model={self.model}, gcloud_path={self.gcloud_path}")

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Git差分からコミットメッセージを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Returns:
            生成されたコミットメッセージ

        Raises:
            AuthenticationError: gcloud認証エラー
            TimeoutError: タイムアウトエラー
            ResponseError: レスポンスエラー
            ProviderError: その他のプロバイダーエラー
        """
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        prompt = self._format_prompt(diff, prompt_template)
        logger.debug(f"Gemini CLIにリクエスト送信: model={self.model}, prompt_length={len(prompt)}")

        try:
            start_time = time.time()

            # gcloudコマンドを実行
            response = self._execute_gcloud_command(prompt)

            elapsed_time = time.time() - start_time
            logger.info(f"Gemini CLI呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンスの検証
            if not self._validate_response(response):
                raise ResponseError("Gemini CLIから無効なレスポンスを受信しました")

            return response

        except Exception as e:
            logger.error(f"Gemini CLI呼び出し中にエラー: {e}")
            # エラーの分類
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['authentication', 'login', 'credentials']):
                raise AuthenticationError(f"gcloud認証エラー: {e}")
            elif 'timeout' in error_str:
                raise TimeoutError(f"Gemini CLIタイムアウト: {e}")
            elif any(keyword in error_str for keyword in ['not found', 'command not found']):
                raise ProviderError(f"gcloudコマンドが見つかりません: {e}")
            else:
                raise ProviderError(f"Gemini CLI呼び出しに失敗しました: {e}")

    def test_connection(self) -> bool:
        """
        Gemini CLIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他の接続エラー
        """
        try:
            logger.debug("Gemini CLI接続テストを開始")

            # 簡単なテストプロンプトで接続確認
            test_prompt = "Hello, this is a connection test."
            response = self._execute_gcloud_command(test_prompt, max_output_tokens=5)

            if response and response.strip():
                logger.info("Gemini CLI接続テスト成功")
                return True
            else:
                logger.warning("Gemini CLI接続テスト: 空のレスポンス")
                return False

        except AuthenticationError:
            # 認証エラーは再発生
            raise
        except Exception as e:
            logger.error(f"Gemini CLI接続テストエラー: {e}")
            raise ProviderError(f"Gemini CLI接続テストに失敗しました: {e}")

    def supports_streaming(self) -> bool:
        """
        ストリーミング出力をサポートするかどうか

        Returns:
            CLIプロバイダーはストリーミングをサポートしない
        """
        return False

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['model_name']

    def _verify_gcloud_binary(self) -> str:
        """
        gcloudバイナリの存在と安全性を検証

        Returns:
            検証されたgcloudバイナリのパス

        Raises:
            ProviderError: gcloudが見つからない、または安全でない場合
        """
        # PATH内でgcloudを検索
        gcloud_path = None

        # 明示的なパスのリスト（優先順位順）
        explicit_paths = [
            '/usr/bin/gcloud',
            '/usr/local/bin/gcloud',
            '/opt/google-cloud-sdk/bin/gcloud',
            '/snap/bin/gcloud'
        ]

        # 明示的なパスを最初にチェック
        for path in explicit_paths:
            if Path(path).is_file() and os.access(path, os.X_OK):
                gcloud_path = path
                break

        # 明示的なパスで見つからない場合、PATHを検索
        if not gcloud_path:
            try:
                result = subprocess.run(
                    ['which', 'gcloud'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if result.returncode == 0 and result.stdout.strip():
                    candidate_path = result.stdout.strip()
                    if os.access(candidate_path, os.X_OK):
                        gcloud_path = candidate_path
            except Exception as e:
                logger.debug(f"PATH検索中にエラー: {e}")

        if not gcloud_path:
            raise ProviderError(
                "gcloudコマンドが見つかりません。Google Cloud SDKをインストールしてください。\n"
                "インストール手順: https://cloud.google.com/sdk/docs/install"
            )

        # バイナリの検証
        self._verify_binary_security(gcloud_path)

        logger.debug(f"gcloudバイナリを検証: {gcloud_path}")
        return gcloud_path

    def _verify_binary_security(self, binary_path: str) -> None:
        """
        バイナリのセキュリティを検証

        Args:
            binary_path: 検証するバイナリのパス

        Raises:
            ProviderError: セキュリティ検証に失敗した場合
        """
        try:
            # ファイルの存在確認
            if not Path(binary_path).is_file():
                raise ProviderError(f"バイナリファイルが存在しません: {binary_path}")

            # 実行権限確認
            if not os.access(binary_path, os.X_OK):
                raise ProviderError(f"バイナリに実行権限がありません: {binary_path}")

            # パスの正規化（シンボリックリンクの解決）
            resolved_path = str(Path(binary_path).resolve())

            # 危険なパスのチェック
            dangerous_patterns = ['/tmp/', '/var/tmp/', '..']
            for pattern in dangerous_patterns:
                if pattern in resolved_path:
                    raise ProviderError(f"危険なパスが検出されました: {resolved_path}")

            logger.debug(f"バイナリセキュリティ検証完了: {resolved_path}")

        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"バイナリセキュリティ検証エラー: {e}")

    def _execute_gcloud_command(self, prompt: str, max_output_tokens: Optional[int] = None) -> str:
        """
        gcloudコマンドを安全に実行

        Args:
            prompt: Geminiに送信するプロンプト
            max_output_tokens: 最大出力トークン数

        Returns:
            Geminiからのレスポンス

        Raises:
            ProviderError: コマンド実行エラー
            AuthenticationError: 認証エラー
            TimeoutError: タイムアウトエラー
        """
        # 入力の検証とサニタイゼーション
        sanitized_prompt = self._sanitize_input(prompt)

        # 出力トークン数の設定
        output_tokens = max_output_tokens or self.max_output_tokens

        # コマンド引数の構築（安全な方法）
        cmd_args = [
            self.gcloud_path,
            'ai',
            'generative-models',
            'generate-text',
            f'--model={self.model}',
            f'--prompt={sanitized_prompt}',
            f'--max-output-tokens={output_tokens}',
            f'--temperature={self.temperature}',
            '--format=value(predictions[0].content)',
            '--quiet'
        ]

        # プロジェクトIDが設定されている場合は追加
        if self.project_id:
            cmd_args.extend([f'--project={self.project_id}'])

        # リージョンが設定されている場合は追加
        if self.location:
            cmd_args.extend([f'--region={self.location}'])

        # 安全な環境変数の設定
        safe_env = self._create_safe_environment()

        try:
            logger.debug(f"gcloudコマンド実行: {' '.join(cmd_args[:3])}... (引数は安全にマスク)")

            # subprocess実行（セキュリティ要件に準拠）
            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=self.cli_timeout,
                env=safe_env,
                shell=False,  # 重要: shell=False を使用
                check=False
            )

            # stdout/stderrのサイズ制限
            stdout = self._truncate_output(result.stdout, self.MAX_STDOUT_SIZE, "stdout")
            stderr = self._truncate_output(result.stderr, self.MAX_STDERR_SIZE, "stderr")

            # エラーチェック
            if result.returncode != 0:
                error_msg = stderr.strip() or "不明なエラー"

                # 認証エラーの検出
                if any(keyword in error_msg.lower() for keyword in ['login', 'authentication', 'credentials']):
                    raise AuthenticationError(f"gcloud認証が必要です: {error_msg}")

                # その他のエラー
                raise ProviderError(f"gcloudコマンドが失敗しました (exit code: {result.returncode}): {error_msg}")

            # レスポンスの処理
            response = stdout.strip()
            if not response:
                raise ResponseError("gcloudから空のレスポンスを受信しました")

            # 安全メタデータのみログ出力（内容は記録しない）
            logger.info(f"gcloudコマンド成功: exit_code={result.returncode}, response_length={len(response)}")

            return response

        except subprocess.TimeoutExpired:
            logger.error(f"gcloudコマンドがタイムアウトしました: {self.cli_timeout}秒")
            raise TimeoutError(f"gcloudコマンドがタイムアウトしました（{self.cli_timeout}秒）")

        except Exception as e:
            if isinstance(e, (AuthenticationError, TimeoutError, ProviderError)):
                raise
            logger.error(f"gcloudコマンド実行中に予期しないエラー: {e}")
            raise ProviderError(f"gcloudコマンド実行に失敗しました: {e}")

    def _sanitize_input(self, input_text: str) -> str:
        """
        入力テキストをサニタイゼーション

        Args:
            input_text: サニタイゼーション対象のテキスト

        Returns:
            サニタイゼーション済みテキスト
        """
        if not input_text:
            return ""

        # 基本的なサニタイゼーション
        sanitized = input_text.strip()

        # 危険な文字の除去
        dangerous_chars = ['`', '$', '\\', '|', '&', ';', '(', ')', '<', '>']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # 長さ制限
        max_prompt_length = 50000  # 50KB制限
        if len(sanitized) > max_prompt_length:
            sanitized = sanitized[:max_prompt_length]
            logger.warning(f"プロンプトが長すぎるため切り詰めました: {len(input_text)} -> {len(sanitized)}")

        return sanitized

    def _create_safe_environment(self) -> Dict[str, str]:
        """
        安全な環境変数を作成

        Returns:
            最小限の安全な環境変数辞書
        """
        # 必要最小限の環境変数のみ継承
        safe_vars = [
            'PATH',
            'HOME',
            'USER',
            'GOOGLE_APPLICATION_CREDENTIALS',
            'CLOUDSDK_CORE_PROJECT',
            'CLOUDSDK_COMPUTE_REGION',
            'CLOUDSDK_COMPUTE_ZONE'
        ]

        safe_env = {}
        for var in safe_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        # セキュリティのため、明示的にシェル関連の環境変数を除去
        excluded_vars = ['SHELL', 'PS1', 'PS2']
        for var in excluded_vars:
            safe_env.pop(var, None)

        return safe_env

    def _truncate_output(self, output: str, max_size: int, output_type: str) -> str:
        """
        出力を指定サイズで切り詰め

        Args:
            output: 出力テキスト
            max_size: 最大サイズ（バイト）
            output_type: 出力タイプ（ログ用）

        Returns:
            切り詰められた出力
        """
        if not output:
            return ""

        output_bytes = output.encode('utf-8')
        if len(output_bytes) <= max_size:
            return output

        # 切り詰め処理
        truncated_bytes = output_bytes[:max_size]
        truncated_text = truncated_bytes.decode('utf-8', errors='ignore')

        logger.warning(f"{output_type}出力をサイズ制限により切り詰めました: {len(output_bytes)} -> {len(truncated_bytes)} bytes")

        return truncated_text + f"\n... ({output_type} truncated due to size limit)"

    def get_model_info(self) -> Dict[str, Any]:
        """
        現在のモデル情報を取得

        Returns:
            モデル情報の辞書
        """
        return {
            'provider': 'gemini-cli',
            'model': self.model,
            'supports_streaming': False,
            'max_output_tokens': self.max_output_tokens,
            'temperature': self.temperature,
            'project_id': self.project_id,
            'location': self.location,
            'gcloud_path': self.gcloud_path,
            'timeout': self.cli_timeout,
            'security_features': [
                'subprocess_shell_false',
                'input_sanitization',
                'output_size_limits',
                'safe_environment',
                'binary_verification'
            ]
        }