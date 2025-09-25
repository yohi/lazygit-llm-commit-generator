"""
Gemini Native CLI プロバイダー

ローカルのgeminiコマンドを使用してGeminiモデルにアクセスする。
厳格なセキュリティ制御に従い、subprocess実行時の安全性を確保。
"""

import subprocess
import logging
import os
import shutil
from typing import Dict, Any, Optional, List, ClassVar
from pathlib import Path

from lazygit_llm.base_provider import BaseProvider, ProviderError, AuthenticationError, ProviderTimeoutError, ResponseError

logger = logging.getLogger(__name__)


class GeminiNativeCLIProvider(BaseProvider):
    """
    Gemini Native CLIプロバイダー

    ローカルのgeminiコマンドを使用してGeminiモデルにアクセス。
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
        Gemini Native CLIプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: geminiコマンドが利用できない場合
        """
        super().__init__(config)

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Gemini Native CLI設定が無効です")

        self.model = config.get('model_name', 'gemini-1.5-pro')

        # 追加設定
        additional_params = config.get('additional_params', {})
        self.temperature = additional_params.get('temperature', 0.3)

        # セキュリティ設定
        cfg_timeout = int(config.get('timeout', self.DEFAULT_TIMEOUT))
        self.cli_timeout = min(max(cfg_timeout, 1), self.MAX_TIMEOUT)

        # geminiバイナリの検証
        self.gemini_path = self._verify_gemini_binary()

        logger.info(f"Gemini Native CLIプロバイダーを初期化: model={self.model}, gemini_path={self.gemini_path}")

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
            prompt = prompt_template.replace('$diff', diff)

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
            raise ProviderTimeoutError("Gemini Native CLIタイムアウト") from e
        except Exception as e:
            logger.exception("予期しないエラーが発生: %s", e)
            raise ProviderError(f"Gemini Native CLIエラー: {e}") from e

    def test_connection(self) -> bool:
        """
        Geminiコマンドへの接続をテスト

        Returns:
            接続が成功した場合True、失敗した場合False
        """
        try:
            test_response = self._execute_gemini_command("Hello", timeout=15)
            return bool(test_response and test_response.strip())
        except Exception as e:
            logger.warning("Gemini接続テスト失敗: %s", e)
            return False

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト（gemini-nativeは最小限の設定）
        """
        return []  # model_nameは任意

    def _verify_gemini_binary(self) -> str:
        """
        geminiバイナリの存在と安全性を検証

        Returns:
            検証されたgeminiバイナリのパス

        Raises:
            ProviderError: geminiバイナリが見つからない、または安全でない場合
        """
        gemini_path = shutil.which('gemini')
        if not gemini_path:
            raise ProviderError(
                "geminiコマンドが見つかりません。Gemini CLIをインストールしてください。"
            )

        # パスの安全性チェック
        if not self._is_safe_binary_path(gemini_path):
            raise ProviderError(f"geminiバイナリパスが安全ではありません: {gemini_path}")

        # バイナリの実行可能性チェック
        if not os.access(gemini_path, os.X_OK):
            raise ProviderError(f"geminiバイナリが実行可能ではありません: {gemini_path}")

        logger.debug("geminiバイナリを検証: %s", gemini_path)
        return gemini_path

    def _sanitize_command_for_logging(self, cmd: list) -> str:
        """
        ログ出力用にコマンドラインを安全にサニタイズ

        Args:
            cmd: コマンドライン引数のリスト

        Returns:
            サニタイズされたコマンド文字列
        """
        if not cmd:
            return ""

        sanitized = [cmd[0]]  # バイナリパスは保持

        for i, arg in enumerate(cmd[1:], 1):
            if arg == '-p' and i + 1 < len(cmd):
                # プロンプト引数をマスク
                next_arg = cmd[i + 1] if i + 1 < len(cmd) else ""
                if next_arg == '-':
                    sanitized.extend(['-p', '-'])  # stdin経由は安全
                elif len(next_arg) > 50:  # 長いプロンプトはマスク
                    sanitized.extend(['-p', '[REDACTED_PROMPT]'])
                else:
                    # 短い引数は最初の20文字のみ表示
                    sanitized.extend(['-p', f"{next_arg[:20]}..."])
                break  # -p の次の引数も処理したのでスキップ
            elif i > 1 and cmd[i-1] == '-p':
                # 上記で処理済みなのでスキップ
                continue
            elif len(arg) > 100:
                # 100文字以上の長い引数はマスク
                sanitized.append('[LONG_ARGUMENT]')
            else:
                sanitized.append(arg)

        return ' '.join(sanitized)

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

        # ARG_MAX制限対策: 大きなプロンプトは常にstdin経由
        prompt_size = len(prompt.encode('utf-8'))
        use_stdin = prompt_size > 8192  # 8KB以上は確実にstdin経由

        if use_stdin:
            logger.debug(f"大きなプロンプト({prompt_size}bytes)をstdin経由で処理")
            # コマンド構築（stdinでプロンプトを渡す）
            cmd = [self.gemini_path, '--prompt', '-']  # '-'でstdinを意味する
        else:
            # 小さなプロンプトはコマンド引数経由（互換性のため）
            cmd = [self.gemini_path, '--prompt', prompt]

        try:
            # 機密情報を含む可能性のあるコマンドをサニタイズしてログ出力
            logger.debug("Geminiコマンド実行: %s", self._sanitize_command_for_logging(cmd))

            # セキュアなsubprocess実行
            if use_stdin:
                # stdin経由でプロンプト送信（大きなプロンプト用）
                result = subprocess.run(
                    cmd,
                    input=prompt,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,  # セキュリティのためshell=False
                    cwd=None,     # 作業ディレクトリを制限
                    env=self._create_safe_environment()
                )
            else:
                # コマンド引数経由（小さなプロンプト用）
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,  # セキュリティのためshell=False
                    cwd=None,     # 作業ディレクトリを制限
                    env=self._create_safe_environment()
                )

            # 出力サイズの制限チェック
            if len(result.stdout) > self.MAX_STDOUT_SIZE:
                logger.warning("Gemini出力が制限サイズを超過")
                raise ProviderError("Gemini出力が大きすぎます")

            if len(result.stderr) > self.MAX_STDERR_SIZE:
                logger.warning("Geminiエラー出力が制限サイズを超過")

            # コマンドの終了コードをチェック
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "不明なエラー"
                logger.error("Geminiコマンドが失敗 (code: %d): %s", result.returncode, error_msg)

                # 認証関連エラーの判定
                if 'auth' in error_msg.lower() or 'credential' in error_msg.lower():
                    raise AuthenticationError(f"Gemini認証エラー: {error_msg}")

                raise ProviderError(f"Geminiコマンド実行エラー: {error_msg}")

            return result.stdout

        except subprocess.TimeoutExpired:
            logger.error("geminiコマンドがタイムアウトしました（%d秒）", timeout)
            raise ProviderTimeoutError("geminiコマンドがタイムアウトしました") from None
        except (AuthenticationError, ProviderTimeoutError, ProviderError):
            raise
        except Exception as e:
            if isinstance(e, (AuthenticationError, ProviderTimeoutError, ProviderError)):
                raise
            logger.exception("geminiコマンド実行中にエラー")
            raise ProviderError(f"geminiコマンド実行失敗: {e}") from e

    def _validate_response(self, response: str) -> bool:
        """
        Geminiレスポンスの妥当性を検証

        Args:
            response: 検証するレスポンス

        Returns:
            レスポンスが有効な場合True、無効な場合False
        """
        if not response or not response.strip():
            logger.warning("Geminiから空のレスポンス")
            return False

        # 最小長チェック
        if len(response.strip()) < 3:
            logger.warning("Geminiレスポンスが短すぎます: %s", response.strip())
            return False

        return True

    def _clean_response(self, response: str) -> str:
        """
        Geminiレスポンスをクリーンアップ

        Args:
            response: クリーンアップするレスポンス

        Returns:
            クリーンアップされたレスポンス
        """
        # 基本的なクリーンアップ
        cleaned = response.strip()

        # Gemini特有の不要な出力を除去
        # "Loaded cached credentials." などのログメッセージを除去
        lines = cleaned.split('\n')
        content_lines = []

        for line in lines:
            line = line.strip()
            # システムメッセージっぽい行をスキップ
            if (line.startswith('Loaded cached credentials') or
                line.startswith('Error executing tool') or
                line.startswith('Tool "') or
                line.startswith('Did you mean one of:') or
                not line):
                continue
            content_lines.append(line)

        # 最初の有効な行をコミットメッセージとして返す
        if content_lines:
            return content_lines[0]

        return cleaned

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
            'LANG',
            'LC_ALL',
            'NO_COLOR'
        ]

        safe_env = {}
        for var in safe_vars:
            if var in os.environ:
                if var in ('LANG', 'LC_ALL'):
                    safe_env[var] = os.environ.get(var, 'C.UTF-8')
                elif var == 'NO_COLOR':
                    safe_env[var] = '1'
                else:
                    safe_env[var] = os.environ[var]

        # セキュリティのため、明示的にシェル関連の環境変数を除去
        excluded_vars = ['SHELL', 'PS1', 'PS2']
        for var in excluded_vars:
            safe_env.pop(var, None)

        # 文字化け防止: 最低限UTF-8ロケールを保証
        safe_env.setdefault('LC_ALL', 'C.UTF-8')

        return safe_env

    def _is_safe_binary_path(self, path: str) -> bool:
        """
        バイナリパスの安全性をチェック

        Args:
            path: チェックするパス

        Returns:
            安全な場合True、危険な場合False
        """
        try:
            # パスの正規化
            normalized_path = Path(path).resolve()

            # 危険なパスパターンをチェック
            dangerous_patterns = [
                '/tmp/', '/var/tmp/', '/dev/', '/proc/',
                '..', '~', '$'
            ]

            path_str = str(normalized_path)
            return not any(pattern in path_str for pattern in dangerous_patterns)

        except Exception:
            logger.warning("パス安全性チェック中にエラー: %s", path)
            return False
