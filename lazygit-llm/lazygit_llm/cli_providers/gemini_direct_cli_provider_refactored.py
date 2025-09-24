"""
Gemini Direct CLI Provider (Refactored)

リファクタリングされたGemini Direct CLIプロバイダー
- 明確な責任分離
- 改善されたエラーハンドリング
- テスト可能な設計
"""

import os
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from ..base_provider import BaseProvider, ProviderError, AuthenticationError, ProviderTimeoutError
from ..error_classifier import GeminiErrorClassifier, ErrorType
from ..security_validator import SecurityValidator

logger = logging.getLogger(__name__)


class GeminiDirectCLIProviderRefactored(BaseProvider):
    """
    リファクタリング版 Gemini Direct CLI Provider

    改善点:
    - エラー分類の明確化
    - 設定管理の統一化
    - テスト可能な設計
    - 責任の分離
    """

    PROVIDER_NAME = "gemini-cli-refactored"
    ALLOWED_BINARIES = ('gemini', 'gemini-wrapper.sh', 'gemini-wrapper-refactored.sh')

    def __init__(self, config: Dict[str, Any]):
        """
        初期化

        Args:
            config: プロバイダー設定
        """
        super().__init__(config)

        # 設定の読み込み
        self.model = config.get('model_name', 'gemini-1.5-pro')
        self.timeout = config.get('timeout', 30)
        self.api_key = config.get('api_key')

        # コンポーネントの初期化
        self.error_classifier = GeminiErrorClassifier()
        self.security_validator = SecurityValidator()

        # Geminiバイナリの検証と設定
        self.gemini_path = self._discover_gemini_binary()

        logger.info(f"Gemini CLI プロバイダー(リファクタリング版)を初期化: model={self.model}, path={self.gemini_path}")

    def generate_commit_message(self, diff_data: str, prompt_template: str) -> str:
        """
        コミットメッセージを生成

        Args:
            diff_data: Git差分データ
            prompt_template: プロンプトテンプレート

        Returns:
            str: 生成されたコミットメッセージ

        Raises:
            ProviderError: 生成に失敗した場合
            AuthenticationError: 認証に失敗した場合
            ProviderTimeoutError: タイムアウトした場合
        """
        try:
            # セキュリティ検証
            safe_diff = self.security_validator.sanitize_git_diff(diff_data)

            # プロンプト作成
            prompt = self._create_prompt(safe_diff, prompt_template)

            # Gemini CLI実行
            response = self._execute_gemini_command(prompt)

            # レスポンス検証
            if not self._validate_response(response):
                raise ProviderError("生成されたコミットメッセージが無効です")

            return response.strip()

        except subprocess.CalledProcessError as e:
            return self._handle_subprocess_error(e)
        except Exception as e:
            logger.exception("Gemini CLI実行中に予期しないエラー")
            raise ProviderError(f"予期しないエラー: {e}") from e

    def _discover_gemini_binary(self) -> str:
        """
        Geminiバイナリのパスを検出

        優先順位:
        1. 改善版ラッパースクリプト
        2. 既存ラッパースクリプト
        3. オリジナルgeminiバイナリ

        Returns:
            str: 検証済みのgeminiバイナリパス

        Raises:
            ProviderError: geminiバイナリが見つからない場合
        """
        # 候補パスの定義
        candidates = [
            "/home/y_ohi/bin/gemini-wrapper-refactored.sh",
            "/home/y_ohi/bin/gemini-wrapper.sh",
            "/home/linuxbrew/.linuxbrew/bin/gemini"
        ]

        # システムPATHから検索
        system_gemini = shutil.which('gemini')
        if system_gemini:
            candidates.insert(-1, system_gemini)

        # 各候補をチェック
        for candidate in candidates:
            if self._is_valid_gemini_binary(candidate):
                logger.info(f"Geminiバイナリを発見: {candidate}")
                return candidate

        raise ProviderError(
            "geminiコマンドが見つかりません。"
            "Gemini CLIをインストールして、PATHに追加してください。"
        )

    def _is_valid_gemini_binary(self, path: str) -> bool:
        """
        Geminiバイナリの有効性をチェック

        Args:
            path: チェックするパス

        Returns:
            bool: 有効かどうか
        """
        if not os.path.exists(path):
            return False

        if not os.access(path, os.X_OK):
            return False

        # セキュリティチェック
        binary_name = Path(path).name
        if binary_name not in self.ALLOWED_BINARIES:
            logger.warning(f"許可されていないバイナリ: {binary_name}")
            return False

        # パスの安全性チェック
        if not self._is_safe_binary_path(path):
            logger.warning(f"安全でないバイナリパス: {path}")
            return False

        return True

    def _is_safe_binary_path(self, path: str) -> bool:
        """
        バイナリパスの安全性をチェック

        Args:
            path: チェックするパス

        Returns:
            bool: 安全かどうか
        """
        # 基本的な安全性チェック
        resolved_path = Path(path).resolve()

        # 危険なパターンをチェック
        dangerous_patterns = ['.', '..', '/tmp/', '/var/tmp/']
        for pattern in dangerous_patterns:
            if pattern in str(resolved_path):
                return False

        # ホームディレクトリまたはシステムディレクトリ内かチェック
        safe_prefixes = [
            Path.home(),
            Path('/usr/'),
            Path('/home/linuxbrew/'),
        ]

        return any(
            str(resolved_path).startswith(str(prefix))
            for prefix in safe_prefixes
        )

    def _create_prompt(self, diff_data: str, template: str) -> str:
        """
        プロンプトを作成

        Args:
            diff_data: Git差分データ
            template: プロンプトテンプレート

        Returns:
            str: 作成されたプロンプト
        """
        return template.format(diff=diff_data)

    def _execute_gemini_command(self, prompt: str) -> str:
        """
        Geminiコマンドを実行

        Args:
            prompt: 実行するプロンプト

        Returns:
            str: Geminiからのレスポンス

        Raises:
            subprocess.CalledProcessError: コマンド実行が失敗した場合
        """
        # コマンド構築
        cmd = self._build_command(prompt)

        # 環境変数設定
        env = self._build_environment()

        logger.debug(f"Geminiコマンド実行: {' '.join(cmd[:3])}... (プロンプト: {len(prompt)}文字)")

        # 実行
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=env,
            check=False  # エラーハンドリングは自前で行う
        )

        # 結果の分析
        return self._analyze_result(result, cmd)

    def _build_command(self, prompt: str) -> List[str]:
        """
        実行コマンドを構築

        Args:
            prompt: プロンプト

        Returns:
            List[str]: コマンド引数リスト
        """
        cmd = [self.gemini_path]

        # モデル指定
        if self.model != 'gemini-1.5-pro':
            cmd.extend(['-m', self.model])

        # プロンプト指定
        cmd.extend(['--prompt', prompt])

        return cmd

    def _build_environment(self) -> Dict[str, str]:
        """
        実行環境を構築

        Returns:
            Dict[str, str]: 環境変数辞書
        """
        env = os.environ.copy()

        # APIキー設定
        if self.api_key:
            env['GEMINI_API_KEY'] = self.api_key
            env['GOOGLE_API_KEY'] = self.api_key
            logger.debug("APIキーが設定されています（環境変数として使用）")

        return env

    def _analyze_result(self, result: subprocess.CompletedProcess, cmd: List[str]) -> str:
        """
        実行結果を分析

        Args:
            result: subprocess実行結果
            cmd: 実行されたコマンド

        Returns:
            str: 成功時のレスポンス

        Raises:
            subprocess.CalledProcessError: 失敗時
        """
        logger.debug(f"実行結果: returncode={result.returncode}, "
                    f"stdout={len(result.stdout)}文字, stderr={len(result.stderr)}文字")

        # エラー分類
        analysis = self.error_classifier.classify_error(
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            return_code=result.returncode
        )

        logger.debug(f"エラー分析結果: {analysis.error_type.value}, 信頼度={analysis.confidence}")

        # 成功ケース
        if result.returncode == 0 or analysis.error_type == ErrorType.SUCCESS_WITH_WARNING:
            return self._handle_success_case(result, analysis)

        # エラーケース
        raise subprocess.CalledProcessError(
            result.returncode,
            cmd,
            result.stdout,
            result.stderr
        )

    def _handle_success_case(self, result: subprocess.CompletedProcess, analysis) -> str:
        """
        成功ケースを処理

        Args:
            result: subprocess実行結果
            analysis: エラー分析結果

        Returns:
            str: 処理されたレスポンス
        """
        output = result.stdout or ""

        # Gemini特有のノイズを除去
        cleaned_output = self._clean_gemini_output(output)

        if not cleaned_output.strip():
            logger.warning("出力が空です")
            return output  # オリジナルを返す

        return cleaned_output

    def _clean_gemini_output(self, output: str) -> str:
        """
        Gemini出力をクリーンアップ

        Args:
            output: 元の出力

        Returns:
            str: クリーンアップされた出力
        """
        # 除去するパターン
        noise_patterns = [
            "Loaded cached credentials.",
            "Error when talking to Gemini API",
            r"Full report available at: /tmp/.*\.json"
        ]

        lines = output.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # ノイズパターンをチェック
            is_noise = any(
                pattern in line for pattern in noise_patterns
            )

            if not is_noise:
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _handle_subprocess_error(self, error: subprocess.CalledProcessError) -> str:
        """
        subprocess.CalledProcessErrorを処理

        Args:
            error: subprocess例外

        Returns:
            str: 成功時のレスポンス（エラーでない場合）

        Raises:
            適切な例外
        """
        # エラー分析
        analysis = self.error_classifier.classify_error(
            stdout=error.stdout or "",
            stderr=error.stderr or "",
            return_code=error.returncode
        )

        logger.info(f"エラー分析: {analysis.error_type.value} (信頼度: {analysis.confidence})")

        # エラータイプ別処理
        if analysis.error_type == ErrorType.QUOTA_EXCEEDED:
            raise ProviderError(
                f"🚨 Gemini APIクォータ制限: {analysis.message}\n"
                f"💡 {analysis.suggested_action}\n"
                f"📋 詳細: {(error.stdout or '')[:200]}..."
            ) from error

        elif analysis.error_type == ErrorType.AUTHENTICATION_ERROR:
            raise AuthenticationError(
                f"🔑 Gemini CLI認証エラー: {analysis.message}\n"
                f"💡 {analysis.suggested_action}"
            ) from error

        elif analysis.error_type == ErrorType.NETWORK_ERROR:
            raise ProviderError(
                f"🌐 ネットワークエラー: {analysis.message}\n"
                f"💡 {analysis.suggested_action}"
            ) from error

        elif analysis.error_type == ErrorType.TIMEOUT_ERROR:
            raise ProviderTimeoutError(
                f"⏰ タイムアウトエラー: {analysis.message}\n"
                f"💡 {analysis.suggested_action}"
            ) from error

        else:
            # 不明なエラー
            error_details = error.stderr or error.stdout or "詳細不明"
            raise ProviderError(
                f"Gemini CLI実行エラー (終了コード: {error.returncode}): "
                f"{error_details[:200]}..."
            ) from error

    def _validate_response(self, response: str) -> bool:
        """
        レスポンスの妥当性を検証

        Args:
            response: 検証するレスポンス

        Returns:
            bool: 妥当かどうか
        """
        if not response or not response.strip():
            return False

        # 最小長チェック
        if len(response.strip()) < 3:
            return False

        # 有害なコンテンツチェック
        harmful_patterns = [
            "error", "failed", "exception", "traceback"
        ]

        response_lower = response.lower()
        if any(pattern in response_lower for pattern in harmful_patterns):
            logger.warning(f"有害パターンを検出: {response[:100]}...")
            return False

        return True
