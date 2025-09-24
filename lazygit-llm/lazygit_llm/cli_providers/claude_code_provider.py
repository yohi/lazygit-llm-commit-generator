"""
Claude Code CLI プロバイダー

Anthropic Claude Code CLI を使用してClaude モデルにアクセスする。
厳格なセキュリティ制御に従い、subprocess実行時の安全性を確保。
"""

import subprocess
import logging
import time
import os
import shutil
from typing import Dict, Any, Optional, List, ClassVar
from pathlib import Path

from lazygit_llm.base_provider import BaseProvider, ProviderError, AuthenticationError, ProviderTimeoutError, ResponseError

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(BaseProvider):
    """
    Claude Code CLIプロバイダー

    Anthropic Claude Code CLI を使用してClaudeモデルにアクセス。
    セキュリティ要件に従った安全なsubprocess実行を実装。
    """

    # セキュリティ設定
    ALLOWED_BINARIES: ClassVar[tuple[str, ...]] = ('claude-code', 'claude')
    MAX_STDOUT_SIZE: ClassVar[int] = 2 * 1024 * 1024  # 2MB（Claudeの長い出力に対応）
    MAX_STDERR_SIZE: ClassVar[int] = 1024 * 1024      # 1MB
    DEFAULT_TIMEOUT: ClassVar[int] = 45  # 45秒（Claudeは処理が重い場合がある）
    MAX_TIMEOUT: ClassVar[int] = 600     # 10分（設定可能な最大値）

    def __init__(self, config: Dict[str, Any]):
        """
        Claude Code CLIプロバイダーを初期化

        Args:
            config: プロバイダー設定

        Raises:
            ProviderError: claude-codeコマンドが利用できない場合
        """
        # デフォルト値を設定してからsuper().__init__を呼び出し
        config.setdefault('model_name', 'claude-3-5-sonnet-20241022')
        config.setdefault('additional_params', {})
        
        super().__init__(config)

        # 設定の検証
        if not self.validate_config():
            raise ProviderError("Claude Code CLI設定が無効です")

        self.model = config['model_name']

        # 追加設定
        additional_params = config['additional_params']
        self.temperature = additional_params.get('temperature', 0.3)
        self.max_output_tokens = additional_params.get('max_output_tokens', self.max_tokens)

        # タイムアウト値を安全に変換
        try:
            timeout_value = int(config.get('timeout', self.DEFAULT_TIMEOUT))
        except (ValueError, TypeError):
            timeout_value = self.DEFAULT_TIMEOUT
        
        self.cli_timeout = min(timeout_value, self.MAX_TIMEOUT)

        # claude-codeバイナリの検証
        self.claude_code_path = self._verify_claude_code_binary()

        logger.info(f"Claude Code CLIプロバイダーを初期化: model={self.model}, claude_code_path={self.claude_code_path}")

    def generate_commit_message(self, diff: str, prompt_template: str) -> str:
        """
        Git差分からコミットメッセージを生成

        Args:
            diff: Git差分
            prompt_template: プロンプトテンプレート

        Returns:
            生成されたコミットメッセージ

        Raises:
            AuthenticationError: Claude Code認証エラー
            ProviderTimeoutError: タイムアウトエラー
            ResponseError: レスポンスエラー
            ProviderError: その他のプロバイダーエラー
        """
        if not diff or not diff.strip():
            raise ProviderError("空の差分が提供されました")

        # プロンプトテンプレートの検証
        if not isinstance(prompt_template, str) or not prompt_template.strip():
            raise ProviderError("無効なプロンプトテンプレートが提供されました")

        prompt = prompt_template.replace('$diff', diff)
        logger.debug(f"Claude Code CLIにリクエスト送信: model={self.model}, prompt_length={len(prompt)}")

        try:
            start_time = time.time()

            # claude-codeコマンドを実行
            response = self._execute_claude_code_command(prompt)

            elapsed_time = time.time() - start_time
            logger.info(f"Claude Code CLI呼び出し完了: {elapsed_time:.2f}秒")

            # レスポンスの検証（最小限）
            if not response or not response.strip():
                raise ResponseError("Claude Code CLIから無効なレスポンスを受信しました")

            return response

        except (AuthenticationError, ProviderTimeoutError, ResponseError, ProviderError):
            raise
        except Exception as e:
            logger.exception("Claude Code CLI呼び出し中にエラー")
            # エラーの分類
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ['authentication', 'login', 'auth', 'unauthorized']):
                raise AuthenticationError("Claude Code認証エラー") from e
            elif 'timeout' in error_str:
                raise ProviderTimeoutError("Claude Code CLIタイムアウト") from e
            elif any(keyword in error_str for keyword in ['not found', 'command not found']):
                raise ProviderError("claude-codeコマンドが見つかりません") from e
            elif any(keyword in error_str for keyword in ['rate limit', 'quota', 'limit exceeded']):
                raise ProviderError("Claude Code APIレート制限") from e
            else:
                raise ProviderError("Claude Code CLI呼び出しに失敗しました") from e

    def test_connection(self) -> bool:
        """
        Claude Code CLIへの接続をテスト

        Returns:
            接続が成功した場合True

        Raises:
            AuthenticationError: 認証エラー
            ProviderError: その他の接続エラー
        """
        try:
            logger.debug("Claude Code CLI接続テストを開始")

            # 簡単なテストプロンプトで接続確認
            test_prompt = "Hello, this is a connection test. Please respond with just 'OK'."
            response = self._execute_claude_code_command(test_prompt, test_mode=True)

            if response and 'ok' in response.strip().lower():
                logger.info("Claude Code CLI接続テスト成功")
                return True
            else:
                logger.warning("Claude Code CLI接続テスト: 空のレスポンス")
                return False

        except AuthenticationError:
            # 認証エラーは再発生
            raise
        except Exception as e:
            logger.error(f"Claude Code CLI接続テストエラー: {e}")
            raise ProviderError(f"Claude Code CLI接続テストに失敗しました: {e}")

    def supports_streaming(self) -> bool:
        """
        ストリーミング出力をサポートするかどうか

        Returns:
            Claude Code CLIはストリーミングをサポートしない（通常のCLI呼び出しのため）
        """
        return False

    def get_required_config_fields(self) -> list[str]:
        """
        必須設定項目のリストを返す

        Returns:
            必須設定項目のリスト
        """
        return ['model_name']

    def _verify_claude_code_binary(self) -> str:
        """
        claude-codeバイナリの存在と安全性を検証

        Returns:
            検証されたclaude-codeバイナリのパス

        Raises:
            ProviderError: claude-codeが見つからない、または安全でない場合
        """
        # 候補となるバイナリ名
        binary_candidates = ['claude-code', 'claude']

        # 明示的なパスのリスト（優先順位順）
        explicit_paths = [
            '/usr/local/bin/claude-code',
            '/usr/bin/claude-code',
            '/opt/claude-code/bin/claude-code',
            '/usr/local/bin/claude',
            '/usr/bin/claude'
        ]

        claude_code_path = None

        # 明示的なパスを最初にチェック
        for path in explicit_paths:
            if Path(path).is_file() and os.access(path, os.X_OK):
                claude_code_path = path
                break

        # 明示的なパスで見つからない場合、PATHを検索
        if not claude_code_path:
            for binary_name in binary_candidates:
                candidate = shutil.which(binary_name)
                if candidate and os.access(candidate, os.X_OK):
                    claude_code_path = candidate
                    break

        if not claude_code_path:
            raise ProviderError(
                "claude-codeコマンドが見つかりません。Claude Codeをインストールしてください。\n"
                "インストール手順: https://claude.ai/code"
            )

        # バイナリの検証
        self._verify_binary_security(claude_code_path)

        logger.debug(f"claude-codeバイナリを検証: {claude_code_path}")
        return claude_code_path

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
            resolved = Path(binary_path).resolve()
            resolved_path = str(resolved)

            # 許可バイナリ名の確認
            if os.path.basename(resolved_path) not in self.ALLOWED_BINARIES:
                raise ProviderError(f"許可されていないバイナリ名です: {resolved_path}")

            # 危険なパスのチェック
            dangerous_patterns = ['/tmp/', '/var/tmp/']
            for pattern in dangerous_patterns:
                if pattern in resolved_path:
                    raise ProviderError(f"危険なパスが検出されました: {resolved_path}")

            logger.debug(f"バイナリセキュリティ検証完了: {resolved_path}")

        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"バイナリセキュリティ検証エラー: {e}")

    def _detect_binary_and_build_args(self) -> list[str]:
        """
        Claude Code CLIバイナリを検出し、適切なコマンド引数を構築

        Returns:
            適切なCLIフラグを含むコマンド引数リスト

        Raises:
            ProviderError: バイナリ検出またはフラグ検証エラー
        """
        # バイナリパスから実際のコマンド名を取得
        binary_name = os.path.basename(self.claude_code_path)
        
        # 基本のコマンド引数
        base_args = [self.claude_code_path]
        
        try:
            # --helpでサポートされているフラグを確認
            help_result = subprocess.run(
                [self.claude_code_path, '--help'],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False
            )
            
            help_output = help_result.stdout + help_result.stderr
            logger.debug(f"Claude Code CLI ヘルプ出力を確認: {binary_name}")
            
        except subprocess.TimeoutExpired:
            logger.warning("Claude Code CLI --help がタイムアウト、デフォルトフラグを使用")
            help_output = ""
        except Exception as e:
            logger.warning(f"Claude Code CLI --help 実行エラー: {e}, デフォルトフラグを使用")
            help_output = ""
        
        # フラグの可用性を確認
        flags = {
            'print_flag': None,      # 非対話モード: -p, --print
            'output_format': None,   # 出力形式: --output-format
            'model_flag': None       # モデル指定: --model
        }
        
        help_lower = help_output.lower()
        
        # 非対話モードフラグの検出
        if '-p, --print' in help_lower or '--print' in help_lower:
            flags['print_flag'] = '--print'
        elif '-p' in help_lower:
            flags['print_flag'] = '-p'
        
        # 出力形式フラグの検出
        if '--output-format' in help_lower:
            flags['output_format'] = 'text'  # text/json/stream-json
        
        # モデルフラグの検出
        if '--model' in help_lower:
            flags['model_flag'] = True
        
        # コマンド引数の構築
        cmd_args = base_args.copy()
        
        # chatコマンドが利用可能かチェック（claude-codeの場合）
        if 'chat' in help_lower or binary_name in ['claude-code']:
            cmd_args.append('chat')
        
        # モデル指定
        if flags['model_flag']:
            cmd_args.extend(['--model', self.model])
        
        # 非対話モード
        if flags['print_flag']:
            cmd_args.append(flags['print_flag'])
        
        # 出力形式（利用可能な場合）
        if flags['output_format']:
            cmd_args.extend(['--output-format', flags['output_format']])
        
        logger.debug(f"構築されたコマンド引数: {' '.join(cmd_args[:4])}... (プロンプトはstdin経由)")
        return cmd_args

    def _execute_claude_code_command(self, prompt: str, test_mode: bool = False) -> str:
        """
        claude-codeコマンドを安全に実行

        Args:
            prompt: Claudeに送信するプロンプト
            test_mode: テストモードかどうか

        Returns:
            Claudeからのレスポンス

        Raises:
            ProviderError: コマンド実行エラー
            AuthenticationError: 認証エラー
            ProviderTimeoutError: タイムアウトエラー
        """
        # 入力の検証とサニタイゼーション
        sanitized_prompt = self._sanitize_input(prompt)

        # 動的にバイナリを検出してコマンド引数を構築
        try:
            cmd_args = self._detect_binary_and_build_args()
        except Exception as e:
            logger.warning(f"動的フラグ検出に失敗、フォールバックを使用: {e}")
            # フォールバック: 基本的なコマンド引数
            cmd_args = [
                self.claude_code_path,
                '--model', self.model,
                '--print'  # 非対話モードの一般的なフラグ
            ]
            
            # chatサブコマンドが必要かチェック
            binary_name = os.path.basename(self.claude_code_path)
            if binary_name in ['claude-code']:
                cmd_args.insert(1, 'chat')

        # 安全な環境変数の設定
        safe_env = self._create_safe_environment()

        try:
            logger.debug(f"claude-codeコマンド実行: {' '.join(cmd_args[:3])}... (プロンプトはstdin経由)")

            # subprocess実行（セキュリティ要件に準拠）
            result = subprocess.run(
                cmd_args,
                input=sanitized_prompt,  # プロンプトをstdinに渡す
                capture_output=True,
                text=True,
                encoding='utf-8',  # 明示的にエンコーディングを指定
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
                if any(keyword in error_msg.lower() for keyword in ['login', 'authentication', 'auth', 'unauthorized']):
                    raise AuthenticationError(f"Claude Code認証が必要です: {error_msg}")

                # レート制限エラーの検出
                if any(keyword in error_msg.lower() for keyword in ['rate limit', 'quota', 'limit exceeded']):
                    raise ProviderError(f"Claude Code APIレート制限に達しました: {error_msg}")

                # その他のエラー
                raise ProviderError(f"claude-codeコマンドが失敗しました (exit code: {result.returncode}): {error_msg}")

            # レスポンスの処理
            response = stdout.strip()
            if not response:
                raise ResponseError("claude-codeから空のレスポンスを受信しました")

            # 安全メタデータのみログ出力（内容は記録しない）
            logger.info(f"claude-codeコマンド成功: exit_code={result.returncode}, response_length={len(response)}")

            return response

        except subprocess.TimeoutExpired as e:
            logger.exception("claude-codeコマンドがタイムアウトしました: %s 秒", self.cli_timeout)
            raise ProviderTimeoutError("claude-codeコマンドがタイムアウトしました") from e

        except Exception as e:
            if isinstance(e, (AuthenticationError, ProviderTimeoutError, ProviderError)):
                raise
            logger.exception("claude-codeコマンド実行中に予期しないエラー")
            raise ProviderError("claude-codeコマンド実行に失敗しました") from e

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

        # シェル未使用のため制御文字に限定
        dangerous_chars = ['\x00']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # 長さ制限（Claudeは長いコンテキストを扱えるため、より大きな制限）
        max_prompt_length = 100000  # 100KB制限
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
            'CLAUDE_API_KEY',
            'ANTHROPIC_API_KEY',
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
            'provider': 'claude-code',
            'model': self.model,
            'supports_streaming': False,
            'max_output_tokens': self.max_output_tokens,
            'temperature': self.temperature,
            'claude_code_path': self.claude_code_path,
            'timeout': self.cli_timeout,
            'security_features': [
                'subprocess_shell_false',
                'input_sanitization',
                'output_size_limits',
                'safe_environment',
                'binary_verification',
                'enhanced_auth_detection'
            ]
        }
