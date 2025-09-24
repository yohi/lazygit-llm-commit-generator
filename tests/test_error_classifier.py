"""
エラー分類器のテストスイート
"""

import pytest
import unittest
from unittest.mock import patch, MagicMock

# プロジェクトのパスを追加
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lazygit-llm'))

from lazygit_llm.error_classifier import GeminiErrorClassifier, ErrorType, ErrorAnalysisResult


class TestGeminiErrorClassifier(unittest.TestCase):
    """GeminiErrorClassifierのテストクラス"""

    def setUp(self):
        """テスト前の準備"""
        self.classifier = GeminiErrorClassifier()

    def test_quota_exceeded_detection(self):
        """クォータ制限エラーの検出テスト"""
        test_cases = [
            "429 Too Many Requests",
            "Quota exceeded for quota metric",
            "rate limit exceeded",
            "RESOURCE_EXHAUSTED",
            "Error when talking to Gemini API"
        ]

        for test_case in test_cases:
            with self.subTest(error_text=test_case):
                result = self.classifier.classify_error(
                    stdout=test_case,
                    stderr="",
                    return_code=1
                )
                self.assertEqual(result.error_type, ErrorType.QUOTA_EXCEEDED)
                self.assertGreater(result.confidence, 0.6)
                self.assertTrue(result.is_retryable)

    def test_authentication_error_detection(self):
        """認証エラーの検出テスト"""
        test_cases = [
            "401 Unauthorized",
            "403 Forbidden",
            "authentication failed",
            "invalid api key"
        ]

        for test_case in test_cases:
            with self.subTest(error_text=test_case):
                result = self.classifier.classify_error(
                    stdout=test_case,
                    stderr="",
                    return_code=1
                )
                self.assertEqual(result.error_type, ErrorType.AUTHENTICATION_ERROR)
                self.assertGreater(result.confidence, 0.6)
                self.assertFalse(result.is_retryable)

    def test_network_error_detection(self):
        """ネットワークエラーの検出テスト"""
        test_cases = [
            "network error",
            "connection failed",
            "connectivity issue",
            "dns resolution failed"
        ]

        for test_case in test_cases:
            with self.subTest(error_text=test_case):
                result = self.classifier.classify_error(
                    stdout=test_case,
                    stderr="",
                    return_code=1
                )
                self.assertEqual(result.error_type, ErrorType.NETWORK_ERROR)
                self.assertTrue(result.is_retryable)

    def test_timeout_error_detection(self):
        """タイムアウトエラーの検出テスト"""
        test_cases = [
            "timeout exceeded",
            "request timed out",
            "connection timeout"
        ]

        for test_case in test_cases:
            with self.subTest(error_text=test_case):
                result = self.classifier.classify_error(
                    stdout=test_case,
                    stderr="",
                    return_code=1
                )
                self.assertEqual(result.error_type, ErrorType.TIMEOUT_ERROR)
                self.assertTrue(result.is_retryable)

    def test_success_case(self):
        """成功ケースのテスト"""
        result = self.classifier.classify_error(
            stdout="Generated commit message: feat: add new feature",
            stderr="",
            return_code=0
        )
        self.assertEqual(result.error_type, ErrorType.SUCCESS_WITH_WARNING)
        self.assertEqual(result.confidence, 1.0)
        self.assertFalse(result.is_retryable)

    def test_success_with_warning(self):
        """警告付き成功のテスト"""
        result = self.classifier.classify_error(
            stdout="feat: add feature\nError when talking to Gemini API",
            stderr="warning: deprecated method",
            return_code=0
        )
        self.assertEqual(result.error_type, ErrorType.SUCCESS_WITH_WARNING)
        self.assertGreater(result.confidence, 0.8)

    def test_auth_error_not_quota(self):
        """認証エラー（クォータエラーでない）のテスト"""
        # 認証エラーのみ
        result = self.classifier.classify_error(
            stdout="401 authentication failed",
            stderr="",
            return_code=1
        )
        self.assertEqual(result.error_type, ErrorType.AUTHENTICATION_ERROR)

        # クォータエラーも含む場合（優先度：クォータエラー > 認証エラー）
        result = self.classifier.classify_error(
            stdout="401 authentication failed\n429 quota exceeded",
            stderr="",
            return_code=1
        )
        self.assertEqual(result.error_type, ErrorType.QUOTA_EXCEEDED)

    def test_confidence_calculation(self):
        """信頼度計算のテスト"""
        # 単一マッチ
        result = self.classifier.classify_error(
            stdout="429 Too Many Requests",
            stderr="",
            return_code=1
        )
        self.assertGreaterEqual(result.confidence, 0.6)

        # 複数マッチ
        result = self.classifier.classify_error(
            stdout="429 Too Many Requests\nQuota exceeded\nrate limit",
            stderr="",
            return_code=1
        )
        self.assertGreater(result.confidence, 0.8)

    def test_special_cases(self):
        """特別なケースのテスト"""
        special_cases = {
            "Error when talking to Gemini API": ErrorType.QUOTA_EXCEEDED,
            "Fallback to Flash model failed": ErrorType.QUOTA_EXCEEDED,
            "Loaded cached credentials": ErrorType.SUCCESS_WITH_WARNING
        }

        for special_text, expected_type in special_cases.items():
            with self.subTest(special_text=special_text):
                result = self.classifier.classify_error(
                    stdout=special_text,
                    stderr="",
                    return_code=1 if expected_type != ErrorType.SUCCESS_WITH_WARNING else 0
                )
                self.assertEqual(result.error_type, expected_type)

    def test_unknown_error(self):
        """不明なエラーのテスト"""
        result = self.classifier.classify_error(
            stdout="Some unknown error occurred",
            stderr="",
            return_code=1
        )
        self.assertEqual(result.error_type, ErrorType.UNKNOWN_ERROR)
        self.assertEqual(result.confidence, 0.5)

    def test_user_friendly_message(self):
        """ユーザーフレンドリーメッセージのテスト"""
        result = ErrorAnalysisResult(
            error_type=ErrorType.QUOTA_EXCEEDED,
            confidence=0.9,
            message="クォータ制限",
            suggested_action="明日再試行",
            is_retryable=True,
            technical_details={"return_code": 1}
        )

        message = self.classifier.get_user_friendly_message(result)

        self.assertIn("🎯", message)  # 高信頼度インジケーター
        self.assertIn("クォータ制限", message)
        self.assertIn("明日再試行", message)
        self.assertIn("再試行可能: はい", message)
        self.assertIn("終了コード 1", message)


class TestErrorAnalysisResult(unittest.TestCase):
    """ErrorAnalysisResultのテストクラス"""

    def test_error_analysis_result_creation(self):
        """ErrorAnalysisResult作成のテスト"""
        result = ErrorAnalysisResult(
            error_type=ErrorType.QUOTA_EXCEEDED,
            confidence=0.8,
            message="Test message",
            suggested_action="Test action",
            is_retryable=True,
            technical_details={"key": "value"}
        )

        self.assertEqual(result.error_type, ErrorType.QUOTA_EXCEEDED)
        self.assertEqual(result.confidence, 0.8)
        self.assertEqual(result.message, "Test message")
        self.assertEqual(result.suggested_action, "Test action")
        self.assertTrue(result.is_retryable)
        self.assertEqual(result.technical_details["key"], "value")


if __name__ == '__main__':
    # テスト実行
    unittest.main(verbosity=2)
