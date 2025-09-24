"""
SecurityValidatorのユニットテスト

セキュリティ検証機能（APIキー検証、差分サニタイゼーション、権限チェック）をテスト。
"""

import pytest
import os
import tempfile
import stat
from unittest.mock import patch, Mock

from lazygit_llm.src.security_validator import SecurityValidator, SecurityCheckResult, ValidationResult


class TestSecurityValidator:
    """SecurityValidatorのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.validator = SecurityValidator()

    def test_initialization(self):
        """初期化テスト"""
        assert hasattr(self.validator, 'api_key_patterns')
        assert hasattr(self.validator, 'sensitive_patterns')
        assert hasattr(self.validator, 'dangerous_patterns')

    def test_validate_api_key_openai_valid(self):
        """OpenAI APIキー有効性テスト"""
        valid_keys = [
            "sk-1234567890abcdef1234567890abcdef12345678",  # gitleaks:allow - test only
            "sk-proj-1234567890abcdef1234567890abcdef1234567890abcdef",  # gitleaks:allow - test only
        ]

        for key in valid_keys:
            result = self.validator.validate_api_key("openai", key)
            assert result.is_valid is True
            assert result.level == "info"

    def test_validate_api_key_openai_invalid(self):
        """OpenAI APIキー無効性テスト"""
        invalid_keys = [
            "invalid-key",
            "sk-short",
            "wrongprefix-1234567890abcdef1234567890abcdef12345678",
            "",
            "sk-",
        ]

        for key in invalid_keys:
            result = self.validator.validate_api_key("openai", key)
            assert result.is_valid is False

    def test_validate_api_key_anthropic_valid(self):
        """Anthropic APIキー有効性テスト"""
        valid_keys = [
            "sk-ant-api03-1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef-1234567890abcdef",
            "sk-ant-api03-" + "a" * 95,  # 有効な長さ
        ]

        for key in valid_keys:
            result = self.validator.validate_api_key("anthropic", key)
            assert result.is_valid is True
            assert result.level == "info"

    def test_validate_api_key_anthropic_invalid(self):
        """Anthropic APIキー無効性テスト"""
        invalid_keys = [
            "invalid-key",
            "sk-ant-short",
            "wrong-prefix-1234567890abcdef",
            "",
            "sk-ant-api03-",
        ]

        for key in invalid_keys:
            result = self.validator.validate_api_key("anthropic", key)
            assert result.is_valid is False

    def test_validate_api_key_google_valid(self):
        """Google APIキー有効性テスト"""
        valid_keys = [
            "AIza" + "a" * 35,  # 39文字  # gitleaks:allow - test only
            "AIza1234567890abcdef1234567890abcdef123",  # gitleaks:allow - test only
        ]

        for key in valid_keys:
            result = self.validator.validate_api_key("google", key)
            assert result.is_valid is True
            assert result.level == "info"

    def test_validate_api_key_google_invalid(self):
        """Google APIキー無効性テスト"""
        invalid_keys = [
            "invalid-key",
            "AIza123",  # 短すぎる
            "wrong-prefix1234567890abcdef1234567890",
            "",
            "AIza",
        ]

        for key in invalid_keys:
            result = self.validator.validate_api_key("google", key)
            assert result.is_valid is False

    def test_validate_api_key_unsupported_provider(self):
        """サポートされていないプロバイダーのテスト"""
        result = self.validator.validate_api_key("unsupported", "any-key")

        assert result.is_valid is False
        assert "サポートされていない" in result.message

    def test_validate_api_key_exposed_warning(self):
        """露出の可能性があるAPIキーの警告テスト"""
        # 一般的でない文字列で、露出の可能性をテスト
        suspicious_key = "sk-1234567890abcdef1234567890abcdef12345678"  # gitleaks:allow - test only

        result = self.validator.validate_api_key("openai", suspicious_key)

        # 基本的には有効だが、推奨事項が含まれる場合がある
        assert result.is_valid is True
        assert len(result.recommendations) > 0

    def test_sanitize_git_diff_clean(self, sample_git_diff):
        """クリーンな差分のサニタイゼーションテスト"""
        sanitized, result = self.validator.sanitize_git_diff(sample_git_diff)

        assert result.is_valid is True
        assert result.level == "info"
        assert sanitized == sample_git_diff  # 変更されない

    def test_sanitize_git_diff_with_secrets(self):
        """機密情報を含む差分のサニタイゼーションテスト"""
        diff_with_secrets = """diff --git a/config.py b/config.py
+password = "secret123"
+api_key = "sk-1234567890abcdef"  # gitleaks:allow - test only
+database_url = "postgresql://user:pass@host:5432/db"
 normal_line = "safe content"
+email = "user@example.com"
+phone = "123-456-7890"
"""

        sanitized, result = self.validator.sanitize_git_diff(diff_with_secrets)

        assert result.is_valid is True
        assert result.level == "warning"
        assert "機密情報" in result.message

        # 機密情報が除去または置換されていることを確認
        assert "secret123" not in sanitized
        assert "sk-1234567890abcdef" not in sanitized  # gitleaks:allow - test only
        assert "user:pass@host" not in sanitized
        assert "user@example.com" not in sanitized
        assert "123-456-7890" not in sanitized

        # 安全なコンテンツは保持されている
        assert "normal_line" in sanitized
        assert "safe content" in sanitized

    def test_sanitize_git_diff_dangerous_patterns(self):
        """危険なパターンを含む差分のサニタイゼーションテスト"""
        dangerous_diff = """diff --git a/script.py b/script.py
+import subprocess
+subprocess.call("rm -rf /", shell=True)
+eval(user_input)
+exec(malicious_code)
 safe_code = "normal operation"
"""

        _, result = self.validator.sanitize_git_diff(dangerous_diff)

        assert result.is_valid is False  # 危険なパターンで無効
        assert result.level == "danger"
        assert "危険" in result.message

    def test_sanitize_git_diff_binary_content(self):
        """バイナリコンテンツの検出テスト"""
        binary_diff = "diff --git a/file.py b/file.py\n" + "\x00\x01\x02" + "normal text"

        sanitized, result = self.validator.sanitize_git_diff(binary_diff)

        assert result.is_valid is True
        # バイナリコンテンツが適切に処理される
        assert "\x00\x01\x02" not in sanitized

    def test_sanitize_git_diff_large_content(self):
        """大容量コンテンツのテスト"""
        large_diff = "+" + "a" * 200000  # 200KB

        _, result = self.validator.sanitize_git_diff(large_diff)

        assert result.is_valid is False
        assert result.level == "warning"
        assert "サイズが大きすぎます" in result.message

    def test_check_file_permissions_secure(self):
        """安全なファイル権限のテスト"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp.flush()

            # 600 (rw-------) に設定
            os.chmod(tmp.name, 0o600)

            try:
                result = self.validator.check_file_permissions(tmp.name)

                assert result.is_valid is True
                assert result.level == "info"
            finally:
                os.unlink(tmp.name)

    def test_check_file_permissions_too_permissive(self):
        """権限が緩すぎるファイルのテスト"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp.flush()

            # 644 (rw-r--r--) に設定
            os.chmod(tmp.name, 0o644)

            try:
                result = self.validator.check_file_permissions(tmp.name)

                assert result.level == "warning"
                assert "他のユーザー" in result.message
                assert "chmod 600" in result.recommendations[0]
            finally:
                os.unlink(tmp.name)

    def test_check_file_permissions_world_writable(self):
        """誰でも書き込み可能なファイルのテスト"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp.flush()

            # 666 (rw-rw-rw-) に設定
            os.chmod(tmp.name, 0o666)

            try:
                result = self.validator.check_file_permissions(tmp.name)

                assert result.level == "danger"
                assert "他のユーザーが書き込み可能" in result.message
            finally:
                os.unlink(tmp.name)

    def test_check_file_permissions_nonexistent(self):
        """存在しないファイルのテスト"""
        result = self.validator.check_file_permissions("/nonexistent/file")

        assert result.is_valid is False
        assert "存在しません" in result.message

    def test_validate_input_size_within_limit(self):
        """制限内のサイズのテスト"""
        content = "a" * 1000  # 1KB
        result = self.validator.validate_input_size(content, max_size=10000)

        assert result.is_valid is True
        assert result.level == "info"

    def test_validate_input_size_exceeds_limit(self):
        """制限を超えるサイズのテスト"""
        content = "a" * 10000  # 10KB
        result = self.validator.validate_input_size(content, max_size=5000)

        assert result.is_valid is False
        assert result.level == "warning"
        assert "サイズ制限" in result.message

    def test_validate_input_size_empty(self):
        """空の入力のテスト"""
        result = self.validator.validate_input_size("")

        assert result.is_valid is True
        assert result.level == "info"

    def test_check_binary_content_clean(self):
        """クリーンなテキストのバイナリチェック"""
        clean_text = "This is normal text with unicode: こんにちは"
        result = self.validator._check_binary_content(clean_text)

        assert result.is_valid is True

    def test_check_binary_content_with_binary(self):
        """バイナリコンテンツのチェック"""
        binary_text = "Normal text" + "\x00\x01\x02\x03" + "more text"
        result = self.validator._check_binary_content(binary_text)

        assert result.is_valid is False
        assert "バイナリコンテンツ" in result.message

    def test_sanitize_sensitive_info_passwords(self):
        """パスワード情報のサニタイゼーション"""
        text_with_password = """
password = "mypassword123"
PASSWORD: secretvalue
db_password="another_secret"
"""
        sanitized = self.validator._sanitize_sensitive_info(text_with_password)

        assert "mypassword123" not in sanitized
        assert "secretvalue" not in sanitized
        assert "another_secret" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_sensitive_info_api_keys(self):
        """APIキー情報のサニタイゼーション"""
        text_with_keys = """
api_key = "sk-1234567890abcdef"  # gitleaks:allow - test only
OPENAI_API_KEY=sk-proj-abcdef1234567890  # gitleaks:allow - test only
google_api_key: AIza1234567890abcdef  # gitleaks:allow - test only
"""
        sanitized = self.validator._sanitize_sensitive_info(text_with_keys)

        assert "sk-1234567890abcdef" not in sanitized  # gitleaks:allow - test only
        assert "sk-proj-abcdef1234567890" not in sanitized  # gitleaks:allow - test only
        assert "AIza1234567890abcdef" not in sanitized  # gitleaks:allow - test only
        assert "[REDACTED]" in sanitized

    def test_sanitize_sensitive_info_urls(self):
        """URL内の機密情報のサニタイゼーション"""
        text_with_urls = """
database_url = "postgresql://user:password@host:5432/db"
redis_url = "redis://user:secret@localhost:6379"
"""
        sanitized = self.validator._sanitize_sensitive_info(text_with_urls)

        assert "user:password@host" not in sanitized
        assert "user:secret@localhost" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_detect_dangerous_patterns_shell_injection(self):
        """シェルインジェクションの検出"""
        dangerous_text = """
import subprocess
subprocess.call("rm -rf /", shell=True)
os.system(user_input)
"""
        patterns = self.validator._detect_dangerous_patterns(dangerous_text)

        assert len(patterns) > 0
        assert any("shell=True" in str(pattern) for pattern in patterns)

    def test_detect_dangerous_patterns_code_execution(self):
        """コード実行の検出"""
        dangerous_text = """
eval(user_input)
exec(malicious_code)
__import__('os').system('bad')
"""
        patterns = self.validator._detect_dangerous_patterns(dangerous_text)

        assert len(patterns) > 0
        assert any("eval" in str(pattern) for pattern in patterns)

    def test_detect_dangerous_patterns_safe_code(self):
        """安全なコードの検出テスト"""
        safe_text = """
def hello_world():
    print("Hello, World!")
    return True

class TestClass:
    def __init__(self):
        self.value = 42
"""
        patterns = self.validator._detect_dangerous_patterns(safe_text)

        assert len(patterns) == 0

    @pytest.mark.parametrize("provider,key,expected_valid", [
        ("openai", "sk-1234567890abcdef1234567890abcdef12345678", True),  # gitleaks:allow - test only
        ("openai", "invalid", False),
        ("anthropic", "sk-ant-api03-" + "a" * 95, True),
        ("anthropic", "invalid", False),
        ("google", "AIza" + "a" * 35, True),
        ("google", "invalid", False),
        ("gemini", "AIza" + "a" * 35, True),  # Google alias
        ("unknown", "any-key", False),
    ])
    def test_api_key_validation_matrix(self, provider, key, expected_valid):
        """APIキー検証のマトリックステスト"""
        result = self.validator.validate_api_key(provider, key)
        assert result.is_valid == expected_valid

    def test_security_check_result_dataclass(self):
        """SecurityCheckResultデータクラステスト"""
        result = SecurityCheckResult(
            is_valid=True,
            level="info",
            message="Test message",
            recommendations=["Recommendation 1", "Recommendation 2"]
        )

        assert result.is_valid is True
        assert result.level == "info"
        assert result.message == "Test message"
        assert len(result.recommendations) == 2

    def test_validation_result_dataclass(self):
        """ValidationResultデータクラステスト"""
        result = ValidationResult(
            is_valid=False,
            level="danger",
            message="Validation failed",
            recommendations=["Fix this issue"]
        )

        assert result.is_valid is False
        assert result.level == "danger"
        assert result.message == "Validation failed"
        assert len(result.recommendations) == 1
