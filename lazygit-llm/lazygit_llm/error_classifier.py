"""
Gemini CLIエラー分類器

このモジュールは、Gemini CLIからの出力を分析し、
エラーの種類を適切に分類する機能を提供します。
"""

import re
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """エラータイプの定義"""
    QUOTA_EXCEEDED = "quota_exceeded"
    AUTHENTICATION_ERROR = "authentication_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT = "rate_limit"
    UNKNOWN_ERROR = "unknown_error"
    SUCCESS_WITH_WARNING = "success_with_warning"


@dataclass
class ErrorAnalysisResult:
    """エラー分析結果"""
    error_type: ErrorType
    confidence: float  # 0.0-1.0
    message: str
    suggested_action: str
    technical_details: Optional[Dict[str, Any]] = None
    is_retryable: bool = False


class GeminiErrorClassifier:
    """Gemini CLIエラー分類器"""

    # エラーパターン定義
    ERROR_PATTERNS = {
        ErrorType.QUOTA_EXCEEDED: [
            r"429.*Too Many Requests",
            r"Quota exceeded",
            r"rate limit.*exceeded",
            r"quota metric.*exceeded",
            r"RESOURCE_EXHAUSTED",
            r"rateLimitExceeded"
        ],
        ErrorType.AUTHENTICATION_ERROR: [
            r"401.*Unauthorized",
            r"403.*Forbidden",
            r"authentication.*failed",
            r"invalid.*api.*key",
            r"unauthorized.*access"
        ],
        ErrorType.NETWORK_ERROR: [
            r"network.*error",
            r"connection.*failed",
            r"connectivity.*issue",
            r"dns.*resolution.*failed",
            r"socket.*error"
        ],
        ErrorType.TIMEOUT_ERROR: [
            r"timeout.*exceeded",
            r"request.*timed.*out",
            r"connection.*timeout",
            r"read.*timeout"
        ]
    }

    # 特別な処理が必要なケース
    SPECIAL_CASES = {
        "Error when talking to Gemini API": ErrorType.QUOTA_EXCEEDED,
        "Fallback to Flash model failed": ErrorType.QUOTA_EXCEEDED,
        "Loaded cached credentials": ErrorType.SUCCESS_WITH_WARNING
    }

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def classify_error(self,
                      stdout: str = "",
                      stderr: str = "",
                      return_code: int = 0) -> ErrorAnalysisResult:
        """
        エラーを分類する

        Args:
            stdout: 標準出力
            stderr: 標準エラー出力
            return_code: 終了コード

        Returns:
            ErrorAnalysisResult: 分析結果
        """
        combined_output = f"{stdout}\n{stderr}".lower()

        # 成功ケース
        if return_code == 0:
            return self._analyze_success_case(stdout, stderr)

        # 特別なケースの確認
        special_result = self._check_special_cases(stdout, stderr)
        if special_result:
            return special_result

        # パターンマッチングによる分類
        for error_type, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, combined_output, re.IGNORECASE):
                    confidence = self._calculate_confidence(pattern, combined_output)
                    return self._create_result(
                        error_type,
                        confidence,
                        stdout,
                        stderr,
                        return_code
                    )

        # 認証エラーの特別チェック（クォータエラーでない場合のみ）
        if self._is_auth_error_not_quota(combined_output):
            return self._create_result(
                ErrorType.AUTHENTICATION_ERROR,
                0.8,
                stdout,
                stderr,
                return_code
            )

        # 不明なエラー
        return self._create_result(
            ErrorType.UNKNOWN_ERROR,
            0.5,
            stdout,
            stderr,
            return_code
        )

    def _analyze_success_case(self, stdout: str, stderr: str) -> ErrorAnalysisResult:
        """成功ケースの分析"""
        combined_output = f"{stdout}\n{stderr}"

        # 警告付き成功の検出
        if any(warning in combined_output for warning in [
            "Error when talking to Gemini API",
            "Fallback to Flash model failed",
            "warning", "Warning"
        ]):
            return ErrorAnalysisResult(
                error_type=ErrorType.SUCCESS_WITH_WARNING,
                confidence=0.9,
                message="処理は成功しましたが、警告が発生しています",
                suggested_action="出力内容を確認し、必要に応じて対処してください",
                is_retryable=False,
                technical_details={
                    "stdout_length": len(stdout),
                    "stderr_length": len(stderr),
                    "has_warnings": True
                }
            )

        # 正常成功
        return ErrorAnalysisResult(
            error_type=ErrorType.SUCCESS_WITH_WARNING,  # 実際は成功だが、統一的に扱う
            confidence=1.0,
            message="処理が正常に完了しました",
            suggested_action="特にアクションは必要ありません",
            is_retryable=False
        )

    def _check_special_cases(self, stdout: str, stderr: str) -> Optional[ErrorAnalysisResult]:
        """特別なケースをチェック"""
        combined_output = f"{stdout}\n{stderr}"

        for special_text, error_type in self.SPECIAL_CASES.items():
            if special_text in combined_output:
                return self._create_result(error_type, 0.95, stdout, stderr, 1)

        return None

    def _is_auth_error_not_quota(self, combined_output: str) -> bool:
        """認証エラー（クォータエラーではない）かチェック"""
        has_auth_indicators = any(indicator in combined_output for indicator in [
            "401", "403", "authentication", "api key"
        ])

        has_quota_indicators = any(indicator in combined_output for indicator in [
            "429", "quota", "rate limit", "resource_exhausted"
        ])

        return has_auth_indicators and not has_quota_indicators

    def _calculate_confidence(self, pattern: str, text: str) -> float:
        """パターンマッチの信頼度を計算"""
        matches = len(re.findall(pattern, text, re.IGNORECASE))
        base_confidence = min(0.9, 0.6 + (matches * 0.1))

        # 複数の関連パターンがマッチした場合は信頼度を上げる
        if matches > 1:
            base_confidence = min(0.95, base_confidence + 0.1)

        return base_confidence

    def _create_result(self,
                      error_type: ErrorType,
                      confidence: float,
                      stdout: str,
                      stderr: str,
                      return_code: int) -> ErrorAnalysisResult:
        """ErrorAnalysisResultを作成"""

        # エラータイプ別のメッセージと推奨アクション
        messages = {
            ErrorType.QUOTA_EXCEEDED: {
                "message": "Gemini APIのクォータ制限に達しました",
                "action": "24時間待機するか、別のプロバイダーを使用してください",
                "retryable": True
            },
            ErrorType.AUTHENTICATION_ERROR: {
                "message": "API認証に失敗しました",
                "action": "APIキーの設定を確認してください",
                "retryable": False
            },
            ErrorType.NETWORK_ERROR: {
                "message": "ネットワーク接続に問題があります",
                "action": "インターネット接続を確認してください",
                "retryable": True
            },
            ErrorType.TIMEOUT_ERROR: {
                "message": "リクエストがタイムアウトしました",
                "action": "しばらく待ってから再試行してください",
                "retryable": True
            },
            ErrorType.UNKNOWN_ERROR: {
                "message": "不明なエラーが発生しました",
                "action": "ログを確認し、必要に応じてサポートに連絡してください",
                "retryable": False
            }
        }

        error_info = messages.get(error_type, messages[ErrorType.UNKNOWN_ERROR])

        return ErrorAnalysisResult(
            error_type=error_type,
            confidence=confidence,
            message=error_info["message"],
            suggested_action=error_info["action"],
            is_retryable=error_info["retryable"],
            technical_details={
                "return_code": return_code,
                "stdout_length": len(stdout),
                "stderr_length": len(stderr),
                "has_stdout": bool(stdout.strip()),
                "has_stderr": bool(stderr.strip())
            }
        )

    def get_user_friendly_message(self, result: ErrorAnalysisResult) -> str:
        """ユーザーフレンドリーなメッセージを生成"""
        confidence_indicator = "🎯" if result.confidence > 0.8 else "🤔" if result.confidence > 0.6 else "❓"

        message = f"{confidence_indicator} **{result.message}**\n"
        message += f"**推奨アクション**: {result.suggested_action}\n"

        if result.is_retryable:
            message += "🔄 **再試行可能**: はい\n"
        else:
            message += "⛔ **再試行可能**: いいえ\n"

        if result.technical_details:
            message += f"📋 **技術情報**: 終了コード {result.technical_details.get('return_code', 'N/A')}\n"

        return message
