# ruff: noqa: RUF001, RUF002, RUF003
"""
包括的エラーハンドリングシステム

全プロバイダーとコンポーネントからのエラーを統一的に処理し、
ユーザーフレンドリーなエラーメッセージと回復機能を提供。
"""

import logging
import re
import sys
import traceback
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass

from .base_provider import ProviderError, AuthenticationError, TimeoutError, ResponseError
from .config_manager import ConfigError

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    CONFIGURATION = "configuration"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    PROVIDER = "provider"
    GIT = "git"
    SYSTEM = "system"
    VALIDATION = "validation"
    SECURITY = "security"


class ErrorSeverity(Enum):
    """エラー重要度"""
    CRITICAL = "critical"  # システム停止
    HIGH = "high"         # 機能停止
    MEDIUM = "medium"     # 機能制限
    LOW = "low"           # 警告


@dataclass
class ErrorInfo:
    """エラー情報の構造化"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    suggestions: List[str]
    recovery_possible: bool
    exit_code: int
    technical_details: Optional[str] = None


class ErrorHandler:
    """
    包括的エラーハンドリングクラス

    全システムコンポーネントからのエラーを分類・処理し、
    ユーザーフレンドリーなメッセージと回復提案を提供。
    """

    def __init__(self, verbose: bool = False):
        """
        エラーハンドラーを初期化

        Args:
            verbose: 詳細エラー情報を表示するかどうか
        """
        self.verbose = verbose
        self._error_registry = self._build_error_registry()  # TODO: カスタムエラーハンドラー登録機能で使用予定

    def handle_error(self, error: Exception, context: Optional[str] = None) -> ErrorInfo:
        """
        エラーを処理してErrorInfoを生成

        Args:
            error: 処理するエラー
            context: エラーの発生コンテキスト

        Returns:
            構造化されたエラー情報
        """
        error_type = type(error).__name__
        error_message = str(error)

        logger.error(f"エラーを処理中: {error_type} - {error_message}")
        if context:
            logger.error(f"コンテキスト: {context}")

        # エラータイプに基づく分類
        error_info = self._classify_error(error, error_message, context)

        # 技術的詳細を追加（verbose mode）
        if self.verbose:
            error_info.technical_details = self._get_technical_details(error)

        # ログ出力
        self._log_error(error_info, error)

        return error_info

    def handle_config_error(self, error: ConfigError) -> ErrorInfo:
        """
        設定エラーを処理

        Args:
            error: 設定エラー

        Returns:
            設定エラー情報
        """
        error_message = str(error)

        # 設定エラーの詳細分類
        if "見つかりません" in error_message or "not found" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message=f"設定ファイルエラー: {error_message}",
                user_message="設定ファイルが見つかりません",
                suggestions=[
                    "config/config.yml.example をコピーして config.yml を作成してください",
                    "設定ファイルのパスが正しいか確認してください",
                    "--config オプションで設定ファイルのパスを指定してください"
                ],
                recovery_possible=True,
                exit_code=2
            )

        elif "YAML" in error_message or "yaml" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message=f"YAML解析エラー: {error_message}",
                user_message="設定ファイルの形式が正しくありません",
                suggestions=[
                    "YAML形式が正しいか確認してください",
                    "インデントがスペースで統一されているか確認してください",
                    "特殊文字が適切にエスケープされているか確認してください",
                    "config.yml.example を参考にしてください"
                ],
                recovery_possible=True,
                exit_code=2
            )

        elif "権限" in error_message or "permission" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.MEDIUM,
                message=f"設定ファイル権限エラー: {error_message}",
                user_message="設定ファイルの権限が不適切です",
                suggestions=[
                    "chmod 600 config.yml でファイル権限を設定してください",
                    "設定ファイルの所有者が正しいか確認してください"
                ],
                recovery_possible=True,
                exit_code=2
            )

        else:
            return ErrorInfo(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                message=f"設定エラー: {error_message}",
                user_message="設定に問題があります",
                suggestions=[
                    "設定ファイルの内容を確認してください",
                    "config.yml.example と比較してください",
                    "必須項目が設定されているか確認してください"
                ],
                recovery_possible=True,
                exit_code=2
            )

    def handle_git_error(self, error: Exception) -> ErrorInfo:
        """
        Git関連エラーを処理

        Args:
            error: Gitエラー

        Returns:
            Gitエラー情報
        """
        error_message = str(error)

        if "No staged files found" in error_message:
            return ErrorInfo(
                category=ErrorCategory.GIT,
                severity=ErrorSeverity.LOW,
                message="ステージされたファイルがありません",
                user_message="ステージされたファイルがありません（No staged files found）",
                suggestions=[
                    "git add <files> でファイルをステージしてください",
                    "変更があるファイルを確認してください: git status"
                ],
                recovery_possible=True,
                exit_code=0  # 正常な状態として扱う
            )

        elif "git diff" in error_message.lower():
            return ErrorInfo(
                category=ErrorCategory.GIT,
                severity=ErrorSeverity.MEDIUM,
                message=f"Git差分処理エラー: {error_message}",
                user_message="Git差分の処理に失敗しました",
                suggestions=[
                    "Gitリポジトリ内で実行しているか確認してください",
                    "git status でリポジトリの状態を確認してください",
                    "LazyGitから正しく呼び出されているか確認してください"
                ],
                recovery_possible=True,
                exit_code=1
            )

        else:
            return ErrorInfo(
                category=ErrorCategory.GIT,
                severity=ErrorSeverity.MEDIUM,
                message=f"Gitエラー: {error_message}",
                user_message="Git関連の処理でエラーが発生しました",
                suggestions=[
                    "Gitリポジトリが正しく初期化されているか確認してください",
                    "git status でリポジトリの状態を確認してください"
                ],
                recovery_possible=True,
                exit_code=1
            )

    def handle_provider_error(self, error: Union[ProviderError, AuthenticationError, TimeoutError, ResponseError]) -> ErrorInfo:
        """
        プロバイダーエラーを処理

        Args:
            error: プロバイダーエラー

        Returns:
            プロバイダーエラー情報
        """
        error_message = str(error)

        if isinstance(error, AuthenticationError):
            return ErrorInfo(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message=f"認証エラー: {error_message}",
                user_message="LLMプロバイダーの認証に失敗しました",
                suggestions=self._get_auth_suggestions(error_message),
                recovery_possible=True,
                exit_code=3
            )

        elif isinstance(error, TimeoutError):
            return ErrorInfo(
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                message=f"タイムアウトエラー: {error_message}",
                user_message="LLMプロバイダーへの接続がタイムアウトしました",
                suggestions=[
                    "ネットワーク接続を確認してください",
                    "設定でタイムアウト値を増やしてください",
                    "しばらく時間をおいて再試行してください",
                    "別のプロバイダーを試してください"
                ],
                recovery_possible=True,
                exit_code=4
            )

        elif isinstance(error, ResponseError):
            return ErrorInfo(
                category=ErrorCategory.PROVIDER,
                severity=ErrorSeverity.MEDIUM,
                message=f"レスポンスエラー: {error_message}",
                user_message="LLMプロバイダーから無効なレスポンスを受信しました",
                suggestions=[
                    "プロンプトテンプレートを確認してください",
                    "モデル設定を確認してください",
                    "しばらく時間をおいて再試行してください",
                    "別のプロバイダーを試してください"
                ],
                recovery_possible=True,
                exit_code=5
            )

        else:  # ProviderError
            if "not found" in error_message.lower() or "見つかりません" in error_message:
                return ErrorInfo(
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.HIGH,
                    message=f"プロバイダーセットアップエラー: {error_message}",
                    user_message="LLMプロバイダーのセットアップに問題があります",
                    suggestions=self._get_setup_suggestions(error_message),
                    recovery_possible=True,
                    exit_code=6
                )

            elif "rate limit" in error_message.lower() or "quota" in error_message.lower():
                return ErrorInfo(
                    category=ErrorCategory.PROVIDER,
                    severity=ErrorSeverity.MEDIUM,
                    message=f"レート制限エラー: {error_message}",
                    user_message="LLMプロバイダーのレート制限に達しました",
                    suggestions=[
                        "しばらく時間をおいて再試行してください",
                        "APIプランを確認してください",
                        "別のプロバイダーを試してください"
                    ],
                    recovery_possible=True,
                    exit_code=7
                )

            else:
                return ErrorInfo(
                    category=ErrorCategory.PROVIDER,
                    severity=ErrorSeverity.HIGH,
                    message=f"プロバイダーエラー: {error_message}",
                    user_message="LLMプロバイダーでエラーが発生しました",
                    suggestions=[
                        "設定ファイルを確認してください",
                        "プロバイダーのドキュメントを参照してください",
                        "別のプロバイダーを試してください"
                    ],
                    recovery_possible=True,
                    exit_code=8
                )

    def handle_system_error(self, error: Exception) -> ErrorInfo:
        """
        システムエラーを処理

        Args:
            error: システムエラー

        Returns:
            システムエラー情報
        """
        error_message = str(error)

        if isinstance(error, ImportError):
            return ErrorInfo(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                message=f"依存関係エラー: {error_message}",
                user_message="必要なライブラリがインストールされていません",
                suggestions=[
                    "pip install -r requirements.txt を実行してください",
                    "Python環境が正しく設定されているか確認してください",
                    "仮想環境をアクティブにしてください"
                ],
                recovery_possible=True,
                exit_code=9
            )

        elif isinstance(error, PermissionError):
            return ErrorInfo(
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH,
                message=f"権限エラー: {error_message}",
                user_message="ファイルまたはディレクトリの権限が不足しています",
                suggestions=[
                    "ファイルの権限を確認してください",
                    "実行ユーザーの権限を確認してください",
                    "sudo を使用する必要があるか確認してください"
                ],
                recovery_possible=True,
                exit_code=10
            )

        else:
            return ErrorInfo(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                message=f"システムエラー: {error_message}",
                user_message="予期しないシステムエラーが発生しました",
                suggestions=[
                    "ログファイルを確認してください",
                    "システム管理者にお問い合わせください",
                    "GitHubで問題を報告してください"
                ],
                recovery_possible=False,
                exit_code=99
            )

    def display_error(self, error_info: ErrorInfo) -> None:
        """
        エラー情報をユーザーフレンドリーに表示

        Args:
            error_info: 表示するエラー情報
        """
        # エラーメッセージの表示
        severity_emoji = {
            ErrorSeverity.CRITICAL: "🚨",
            ErrorSeverity.HIGH: "❌",
            ErrorSeverity.MEDIUM: "⚠️",
            ErrorSeverity.LOW: "ℹ️"
        }

        emoji = severity_emoji.get(error_info.severity, "❌")
        print(f"{emoji} {error_info.user_message}", file=sys.stderr)

        # 提案の表示
        if error_info.suggestions:
            print("\n💡 解決方法:", file=sys.stderr)
            for i, suggestion in enumerate(error_info.suggestions, 1):
                print(f"  {i}. {suggestion}", file=sys.stderr)

        # 技術的詳細の表示（verbose mode）
        if self.verbose and error_info.technical_details:
            print(f"\n🔧 技術的詳細:\n{error_info.technical_details}", file=sys.stderr)

        # 回復不可能なエラーの場合
        if not error_info.recovery_possible:
            print("\n❗ このエラーは回復できません。システム管理者にお問い合わせください。", file=sys.stderr)

    def _classify_error(self, error: Exception, error_message: str, context: Optional[str]) -> ErrorInfo:
        """
        エラーを分類してErrorInfoを生成

        Args:
            error: エラーオブジェクト
            error_message: エラーメッセージ
            context: コンテキスト

        Returns:
            分類されたエラー情報
        """
        # 特定のエラータイプの処理
        if isinstance(error, ConfigError):
            return self.handle_config_error(error)
        elif isinstance(error, (ProviderError, AuthenticationError, TimeoutError, ResponseError)):
            return self.handle_provider_error(error)
        elif isinstance(error, (ImportError, PermissionError)):
            return self.handle_system_error(error)
        else:
            # メッセージとコンテキスト双方を用いてGit関連を検出
            blob = f"{error_message} {context or ''}".lower()
            if "git" in blob:
                return self.handle_git_error(error)
            else:
                return self.handle_system_error(error)

    def _get_auth_suggestions(self, error_message: str) -> List[str]:
        """認証エラー用の提案を生成"""
        suggestions = ["設定ファイルでAPIキーを確認してください"]

        if "openai" in error_message.lower():
            suggestions.extend([
                "OPENAI_API_KEY 環境変数が設定されているか確認してください",
                "OpenAI APIキーの有効性を確認してください",
                "https://platform.openai.com/api-keys でAPIキーを確認してください"
            ])
        elif "anthropic" in error_message.lower() or "claude" in error_message.lower():
            suggestions.extend([
                "ANTHROPIC_API_KEY 環境変数が設定されているか確認してください",
                "Anthropic APIキーの有効性を確認してください",
                "https://console.anthropic.com でAPIキーを確認してください"
            ])
        elif "gemini" in error_message.lower() or "google" in error_message.lower():
            suggestions.extend([
                "GOOGLE_API_KEY 環境変数が設定されているか確認してください",
                "Google AI Studio でAPIキーを確認してください",
                "gcloud auth login でGoogle Cloud認証を確認してください"
            ])

        return suggestions

    def _get_setup_suggestions(self, error_message: str) -> List[str]:
        """セットアップエラー用の提案を生成"""
        suggestions = []

        if "gcloud" in error_message.lower():
            suggestions.extend([
                "Google Cloud SDK をインストールしてください",
                "https://cloud.google.com/sdk/docs/install でインストール手順を確認してください",
                "gcloud --version でインストールを確認してください"
            ])
        elif "claude-code" in error_message.lower():
            suggestions.extend([
                "Claude Code をインストールしてください",
                "https://claude.ai/code でインストール手順を確認してください",
                "claude-code --version でインストールを確認してください"
            ])
        else:
            suggestions.extend([
                "pip install -r requirements.txt を実行してください",
                "必要な依存関係がすべてインストールされているか確認してください"
            ])

        return suggestions

    def _get_technical_details(self, error: Exception) -> str:
        """技術的詳細を取得"""
        return "".join(traceback.TracebackException.from_exception(error).format())

    def _sanitize_message(self, message: str) -> str:
        """機密情報をマスクする"""
        # APIキー、トークン等をマスク
        patterns = [
            (r'api[_-]?key[=:]\s*["\']?([^"\'\\s]+)', r'api_key=***'),
            (r'token[=:]\s*["\']?([^"\'\\s]+)', r'token=***'),
            (r'password[=:]\s*["\']?([^"\'\\s]+)', r'password=***'),
        ]
        sanitized = message
        for pattern, replacement in patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    def _log_error(self, error_info: ErrorInfo, original_error: Exception) -> None:
        """エラーをログに記録"""
        log_level = {
            ErrorSeverity.CRITICAL: logging.CRITICAL,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.LOW: logging.INFO
        }

        level = log_level.get(error_info.severity, logging.ERROR)
        sanitized = self._sanitize_message(error_info.message)
        logger.log(
            level,
            f"[{error_info.category.value}] {sanitized}",
            exc_info=original_error if self.verbose else None,
        )

        if error_info.technical_details:
            logger.debug(f"技術的詳細: {self._sanitize_message(error_info.technical_details)}")

    def _build_error_registry(self) -> Dict[str, Any]:
        """エラーレジストリを構築（将来の拡張用）"""
        return {
            "known_errors": {},
            "error_patterns": {},
            "recovery_strategies": {}
        }

    def get_exit_code(self, error: Exception) -> int:
        """
        エラーに基づいて適切な終了コードを取得

        Args:
            error: エラーオブジェクト

        Returns:
            終了コード
        """
        error_info = self.handle_error(error)
        return error_info.exit_code