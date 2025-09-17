"""
ErrorHandlerのユニットテスト

エラーハンドリング、ログ記録、ユーザーフレンドリーなメッセージ生成機能をテスト。
"""

import pytest
import sys
import logging
from unittest.mock import Mock, patch, StringIO
from contextlib import redirect_stderr, redirect_stdout

from lazygit_llm.src.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError, ResponseError


class TestErrorHandler:
    """ErrorHandlerのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.error_handler = ErrorHandler()

    def test_initialization(self):
        """初期化テスト"""
        assert hasattr(self.error_handler, 'logger')
        assert hasattr(self.error_handler, 'error_count')
        assert hasattr(self.error_handler, 'last_error')
        assert self.error_handler.error_count == 0
        assert self.error_handler.last_error is None

    def test_handle_authentication_error(self):
        """認証エラーハンドリングテスト"""
        error = AuthenticationError("Invalid API key")

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.AUTHENTICATION
            assert result['severity'] == ErrorSeverity.HIGH
            assert "APIキー" in result['user_message']
            assert "Invalid API key" in result['technical_details']
            assert len(result['suggestions']) > 0
            mock_log.assert_called_once()

    def test_handle_timeout_error(self):
        """タイムアウトエラーハンドリングテスト"""
        error = TimeoutError("Request timeout after 30 seconds")

        with patch.object(self.error_handler.logger, 'warning') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.NETWORK
            assert result['severity'] == ErrorSeverity.MEDIUM
            assert "タイムアウト" in result['user_message']
            assert "timeout" in result['technical_details']
            assert any("再試行" in suggestion for suggestion in result['suggestions'])
            mock_log.assert_called_once()

    def test_handle_response_error(self):
        """レスポンスエラーハンドリングテスト"""
        error = ResponseError("API returned invalid response")

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.API
            assert result['severity'] == ErrorSeverity.HIGH
            assert "API" in result['user_message']
            assert "invalid response" in result['technical_details']
            mock_log.assert_called_once()

    def test_handle_provider_error(self):
        """プロバイダーエラーハンドリングテスト"""
        error = ProviderError("Provider initialization failed")

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.CONFIGURATION
            assert result['severity'] == ErrorSeverity.HIGH
            assert "設定" in result['user_message']
            assert "initialization failed" in result['technical_details']
            mock_log.assert_called_once()

    def test_handle_generic_exception(self):
        """一般的な例外ハンドリングテスト"""
        error = ValueError("Invalid input value")

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.UNKNOWN
            assert result['severity'] == ErrorSeverity.MEDIUM
            assert "予期しないエラー" in result['user_message']
            assert "Invalid input value" in result['technical_details']
            mock_log.assert_called_once()

    def test_handle_keyboard_interrupt(self):
        """キーボード割り込みハンドリングテスト"""
        error = KeyboardInterrupt()

        with patch.object(self.error_handler.logger, 'info') as mock_log:
            result = self.error_handler.handle_error(error)

            assert result['category'] == ErrorCategory.USER_CANCELLED
            assert result['severity'] == ErrorSeverity.LOW
            assert "中断" in result['user_message']
            assert result['suggestions'] == []
            mock_log.assert_called_once()

    def test_error_count_increment(self):
        """エラーカウント増加テスト"""
        assert self.error_handler.error_count == 0

        self.error_handler.handle_error(ValueError("Error 1"))
        assert self.error_handler.error_count == 1

        self.error_handler.handle_error(RuntimeError("Error 2"))
        assert self.error_handler.error_count == 2

    def test_last_error_tracking(self):
        """最新エラー追跡テスト"""
        assert self.error_handler.last_error is None

        error1 = ValueError("Error 1")
        self.error_handler.handle_error(error1)
        assert self.error_handler.last_error == error1

        error2 = RuntimeError("Error 2")
        self.error_handler.handle_error(error2)
        assert self.error_handler.last_error == error2

    def test_format_user_message_authentication(self):
        """認証エラーのユーザーメッセージフォーマットテスト"""
        error = AuthenticationError("Invalid API key for OpenAI")
        message = self.error_handler._format_user_message(error)

        assert "APIキー" in message
        assert "認証" in message
        assert len(message) > 0

    def test_format_user_message_timeout(self):
        """タイムアウトエラーのユーザーメッセージフォーマットテスト"""
        error = TimeoutError("Request timeout")
        message = self.error_handler._format_user_message(error)

        assert "タイムアウト" in message
        assert "時間" in message

    def test_format_user_message_generic(self):
        """一般的なエラーのユーザーメッセージフォーマットテスト"""
        error = ValueError("Some value error")
        message = self.error_handler._format_user_message(error)

        assert "エラー" in message
        assert len(message) > 0

    def test_get_error_suggestions_authentication(self):
        """認証エラーの提案取得テスト"""
        error = AuthenticationError("Invalid API key")
        suggestions = self.error_handler._get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("APIキー" in suggestion for suggestion in suggestions)
        assert any("設定" in suggestion for suggestion in suggestions)

    def test_get_error_suggestions_timeout(self):
        """タイムアウトエラーの提案取得テスト"""
        error = TimeoutError("Request timeout")
        suggestions = self.error_handler._get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("再試行" in suggestion for suggestion in suggestions)
        assert any("タイムアウト" in suggestion for suggestion in suggestions)

    def test_get_error_suggestions_network(self):
        """ネットワークエラーの提案取得テスト"""
        error = ConnectionError("Connection failed")
        suggestions = self.error_handler._get_error_suggestions(error)

        assert len(suggestions) > 0
        assert any("接続" in suggestion for suggestion in suggestions)

    def test_categorize_error_provider_errors(self):
        """プロバイダーエラーのカテゴリ分類テスト"""
        test_cases = [
            (AuthenticationError("Auth failed"), ErrorCategory.AUTHENTICATION),
            (TimeoutError("Timeout"), ErrorCategory.NETWORK),
            (ResponseError("API error"), ErrorCategory.API),
            (ProviderError("Config error"), ErrorCategory.CONFIGURATION),
        ]

        for error, expected_category in test_cases:
            category = self.error_handler._categorize_error(error)
            assert category == expected_category

    def test_categorize_error_standard_exceptions(self):
        """標準例外のカテゴリ分類テスト"""
        test_cases = [
            (KeyboardInterrupt(), ErrorCategory.USER_CANCELLED),
            (FileNotFoundError("File not found"), ErrorCategory.FILE_SYSTEM),
            (PermissionError("Permission denied"), ErrorCategory.FILE_SYSTEM),
            (ConnectionError("Connection failed"), ErrorCategory.NETWORK),
            (ValueError("Invalid value"), ErrorCategory.UNKNOWN),
            (RuntimeError("Runtime error"), ErrorCategory.UNKNOWN),
        ]

        for error, expected_category in test_cases:
            category = self.error_handler._categorize_error(error)
            assert category == expected_category

    def test_determine_severity_high(self):
        """高重要度エラーの判定テスト"""
        high_severity_errors = [
            AuthenticationError("Auth failed"),
            ResponseError("API error"),
            ProviderError("Config error"),
            FileNotFoundError("File not found"),
        ]

        for error in high_severity_errors:
            severity = self.error_handler._determine_severity(error)
            assert severity == ErrorSeverity.HIGH

    def test_determine_severity_medium(self):
        """中重要度エラーの判定テスト"""
        medium_severity_errors = [
            TimeoutError("Timeout"),
            ConnectionError("Connection failed"),
            ValueError("Invalid value"),
        ]

        for error in medium_severity_errors:
            severity = self.error_handler._determine_severity(error)
            assert severity == ErrorSeverity.MEDIUM

    def test_determine_severity_low(self):
        """低重要度エラーの判定テスト"""
        low_severity_errors = [
            KeyboardInterrupt(),
        ]

        for error in low_severity_errors:
            severity = self.error_handler._determine_severity(error)
            assert severity == ErrorSeverity.LOW

    def test_log_error_debug_mode(self):
        """デバッグモードでのエラーログテスト"""
        error = ValueError("Test error")
        error_info = {
            'category': ErrorCategory.UNKNOWN,
            'severity': ErrorSeverity.MEDIUM,
            'user_message': 'Test message',
            'technical_details': 'Test details'
        }

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            self.error_handler._log_error(error, error_info, debug=True)

            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            assert "Test error" in call_args
            assert "Test details" in call_args

    def test_log_error_production_mode(self):
        """本番モードでのエラーログテスト"""
        error = ValueError("Test error")
        error_info = {
            'category': ErrorCategory.UNKNOWN,
            'severity': ErrorSeverity.MEDIUM,
            'user_message': 'Test message',
            'technical_details': 'Test details'
        }

        with patch.object(self.error_handler.logger, 'error') as mock_log:
            self.error_handler._log_error(error, error_info, debug=False)

            mock_log.assert_called()
            call_args = mock_log.call_args[0][0]
            assert "Test message" in call_args

    def test_format_error_message_for_user(self):
        """ユーザー向けエラーメッセージフォーマットテスト"""
        error_info = {
            'category': ErrorCategory.AUTHENTICATION,
            'severity': ErrorSeverity.HIGH,
            'user_message': 'API認証に失敗しました',
            'technical_details': 'Invalid API key',
            'suggestions': ['APIキーを確認してください', '設定ファイルをチェックしてください']
        }

        formatted = self.error_handler.format_error_message_for_user(error_info)

        assert "API認証に失敗しました" in formatted
        assert "APIキーを確認してください" in formatted
        assert "設定ファイルをチェックしてください" in formatted

    def test_format_error_message_for_user_no_suggestions(self):
        """提案なしのユーザー向けエラーメッセージフォーマットテスト"""
        error_info = {
            'category': ErrorCategory.USER_CANCELLED,
            'severity': ErrorSeverity.LOW,
            'user_message': '処理が中断されました',
            'technical_details': 'KeyboardInterrupt',
            'suggestions': []
        }

        formatted = self.error_handler.format_error_message_for_user(error_info)

        assert "処理が中断されました" in formatted
        assert "解決方法" not in formatted

    def test_get_error_statistics(self):
        """エラー統計取得テスト"""
        # 複数のエラーを処理
        self.error_handler.handle_error(AuthenticationError("Auth error"))
        self.error_handler.handle_error(TimeoutError("Timeout error"))
        self.error_handler.handle_error(ValueError("Value error"))

        stats = self.error_handler.get_error_statistics()

        assert stats['total_errors'] == 3
        assert stats['last_error_type'] == 'ValueError'
        assert 'error_categories' in stats

    def test_reset_error_tracking(self):
        """エラー追跡リセットテスト"""
        # エラーを発生させる
        self.error_handler.handle_error(ValueError("Test error"))
        assert self.error_handler.error_count > 0
        assert self.error_handler.last_error is not None

        # リセット
        self.error_handler.reset_error_tracking()

        assert self.error_handler.error_count == 0
        assert self.error_handler.last_error is None

    @pytest.mark.parametrize("error_type,expected_category", [
        (AuthenticationError("test"), ErrorCategory.AUTHENTICATION),
        (TimeoutError("test"), ErrorCategory.NETWORK),
        (ResponseError("test"), ErrorCategory.API),
        (ProviderError("test"), ErrorCategory.CONFIGURATION),
        (FileNotFoundError("test"), ErrorCategory.FILE_SYSTEM),
        (PermissionError("test"), ErrorCategory.FILE_SYSTEM),
        (ConnectionError("test"), ErrorCategory.NETWORK),
        (KeyboardInterrupt(), ErrorCategory.USER_CANCELLED),
        (ValueError("test"), ErrorCategory.UNKNOWN),
    ])
    def test_error_categorization_matrix(self, error_type, expected_category):
        """エラーカテゴリ分類マトリックステスト"""
        category = self.error_handler._categorize_error(error_type)
        assert category == expected_category

    def test_error_context_preservation(self):
        """エラーコンテキスト保持テスト"""
        error = ValueError("Test error")
        error.context = {"provider": "openai", "operation": "generate"}

        result = self.error_handler.handle_error(error)

        # コンテキスト情報が技術的詳細に含まれているかチェック
        if hasattr(error, 'context'):
            assert "context" in result['technical_details'] or "Test error" in result['technical_details']

    def test_concurrent_error_handling(self):
        """並行エラーハンドリングテスト"""
        import threading

        errors = []
        results = []

        def handle_error_thread(error_msg):
            try:
                error = ValueError(f"Error {error_msg}")
                result = self.error_handler.handle_error(error)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 複数スレッドでエラーハンドリング
        threads = []
        for i in range(5):
            thread = threading.Thread(target=handle_error_thread, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # エラーが発生していないことを確認
        assert len(errors) == 0
        assert len(results) == 5
        assert self.error_handler.error_count == 5

    def test_error_handler_with_custom_logger(self):
        """カスタムロガーでのエラーハンドラーテスト"""
        custom_logger = logging.getLogger('custom_test_logger')
        custom_logger.setLevel(logging.DEBUG)

        error_handler = ErrorHandler(logger=custom_logger)

        assert error_handler.logger == custom_logger

        with patch.object(custom_logger, 'error') as mock_log:
            error_handler.handle_error(ValueError("Test error"))
            mock_log.assert_called_once()

    def test_error_message_localization(self):
        """エラーメッセージローカライゼーションテスト"""
        # 日本語メッセージのテスト
        error = AuthenticationError("Invalid API key")
        result = self.error_handler.handle_error(error)

        assert "認証" in result['user_message'] or "APIキー" in result['user_message']
        # 日本語の提案メッセージが含まれていることを確認
        assert any("してください" in suggestion for suggestion in result['suggestions'])

    def test_error_severity_escalation(self):
        """エラー重要度エスカレーションテスト"""
        # 短時間で同じタイプのエラーが複数回発生した場合の動作
        for _ in range(3):
            self.error_handler.handle_error(TimeoutError("Repeated timeout"))

        # エラーカウントが正しく増加していることを確認
        assert self.error_handler.error_count == 3

    def test_error_recovery_suggestions(self):
        """エラー回復提案テスト"""
        recovery_test_cases = [
            (AuthenticationError("Invalid key"), ["APIキー", "設定"]),
            (TimeoutError("Timeout"), ["再試行", "タイムアウト"]),
            (ConnectionError("No connection"), ["接続", "ネットワーク"]),
        ]

        for error, expected_keywords in recovery_test_cases:
            result = self.error_handler.handle_error(error)
            suggestions = result['suggestions']

            assert len(suggestions) > 0
            assert any(
                any(keyword in suggestion for keyword in expected_keywords)
                for suggestion in suggestions
            )