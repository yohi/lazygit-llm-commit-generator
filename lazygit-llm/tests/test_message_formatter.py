"""
MessageFormatterクラスの包括的なテストモジュール

メッセージの整形、検証、長さ制限などの機能をテストする。
"""

import pytest
from unittest.mock import patch
from lazygit_llm.message_formatter import MessageFormatter


class TestMessageFormatter:
    """MessageFormatterクラスのテスト"""

    @pytest.fixture
    def formatter(self, mock_logger):
        """テスト用のMessageFormatterインスタンス"""
        return MessageFormatter(max_length=50, default_message="feat: Update project")

    @pytest.fixture
    def mock_logger(self):
        """モックされたロガー"""
        with patch('lazygit_llm.message_formatter.logger') as mock:
            yield mock

    # format_responseのテスト
    def test_format_response_empty_input_returns_default_and_logs_warning(self, formatter, mock_logger):
        """空入力の場合、デフォルトを返し警告をログ出力"""
        result = formatter.format_response("")
        assert result == "feat: Update project"
        mock_logger.warning.assert_called_once()

    def test_format_response_whitespace_input_returns_default_and_logs_warning(self, formatter, mock_logger):
        """空白のみの入力の場合、デフォルトを返し警告をログ出力"""
        result = formatter.format_response("   \n\t  ")
        assert result == "feat: Update project"
        mock_logger.warning.assert_called_once()

    def test_format_response_normal_flow(self, formatter):
        """正常なフローのテスト"""
        input_msg = "Add new feature for user authentication"
        result = formatter.format_response(input_msg)
        assert result == "Add new feature for user authentication"
        assert len(result) <= formatter.max_length

    def test_format_response_with_code_blocks(self, formatter):
        """コードブロックを含む入力の処理"""
        input_msg = """```python
def hello():
    return "world"
```
Add hello function"""
        result = formatter.format_response(input_msg)
        assert "```" not in result
        assert "Add hello function" in result

    # _clean_messageのテスト
    @pytest.mark.parametrize("input_text,expected", [
        ("  hello world  ", "hello world"),
        ("hello\n\n\nworld", "hello\nworld"),
        ("hello\tworld", "hello world"),
        ("hello   multiple   spaces", "hello multiple spaces"),
        ("  \t  mixed\n\n\nwhitespace  \t  ", "mixed\nwhitespace"),
    ])
    def test_clean_message_trim_and_normalize(self, formatter, input_text, expected):
        """trim、改行の統合、タブ->スペース、複数スペースの処理"""
        result = formatter._clean_message(input_text)
        assert result == expected

    def test_clean_message_crlf_normalization(self, formatter):
        """CRLF正規化のテスト"""
        input_text = "line1\r\nline2\rline3\nline4"
        result = formatter._clean_message(input_text)
        expected = "line1\nline2\nline3\nline4"
        assert result == expected

    # _extract_commit_messageのテスト
    def test_extract_commit_message_remove_code_blocks(self, formatter):
        """コードブロックの削除"""
        input_msg = """Here's the commit:
```bash
git add .
```
Added new files"""
        result = formatter._extract_commit_message(input_msg)
        assert "```" not in result
        assert "git add ." not in result
        assert "Added new files" in result

    @pytest.mark.parametrize("input_text,expected", [
        ("Commit message: Add new feature", "Add new feature"),
        ("commit message: fix bug", "fix bug"),
        ("COMMIT MESSAGE: update docs", "update docs"),
        ("Generated commit message: refactor code", "refactor code"),
        ("Here is your commit message: test update", "test update"),
        ("Suggested message: improve performance", "improve performance"),
    ])
    def test_extract_commit_message_strip_common_prefixes_case_insensitive(self, formatter, input_text, expected):
        """一般的なプレフィックスの大文字小文字無視での削除"""
        result = formatter._extract_commit_message(input_text)
        assert result == expected

    @pytest.mark.parametrize("input_text,expected", [
        ('"Add new feature"', "Add new feature"),
        ("'Fix bug in parser'", "Fix bug in parser"),
        ('`Update documentation`', "Update documentation"),
        ('"""Triple quoted message"""', "Triple quoted message"),
        ("'Mixed quotes\"", "Mixed quotes"),
    ])
    def test_extract_commit_message_remove_surrounding_quotes(self, formatter, input_text, expected):
        """周囲の引用符の削除"""
        result = formatter._extract_commit_message(input_text)
        assert result == expected

    def test_extract_commit_message_pick_first_line(self, formatter):
        """最初の行を選択"""
        input_text = """Add authentication system
        
This commit adds a new authentication system
with JWT tokens and user management."""
        result = formatter._extract_commit_message(input_text)
        assert result == "Add authentication system"

    def test_extract_commit_message_pick_first_sentence_as_fallback(self, formatter):
        """フォールバックとして最初の文を選択"""
        input_text = "Add authentication system. This includes JWT support. Also user management."
        result = formatter._extract_commit_message(input_text)
        assert result == "Add authentication system."

    # _apply_length_limitのテスト
    def test_apply_length_limit_no_op_when_under_max(self, formatter):
        """最大長未満の場合は何もしない"""
        input_text = "Short message"
        result = formatter._apply_length_limit(input_text)
        assert result == input_text

    def test_apply_length_limit_truncation_at_boundary(self, formatter, mock_logger):
        """境界での切り詰め"""
        # 50文字の制限に対して53文字の入力
        input_text = "This is a very long commit message that exceeds max"  # 53文字
        result = formatter._apply_length_limit(input_text)
        assert len(result) <= formatter.max_length
        assert result.endswith("...")
        mock_logger.warning.assert_called_once()

    def test_apply_length_limit_word_boundary_behavior(self, formatter):
        """単語境界での切り詰め動作"""
        # 境界近くに空白がある場合、単語境界で切り詰める
        input_text = "This is a long message with space near boundary point"
        result = formatter._apply_length_limit(input_text)
        assert result.endswith("...")
        # 単語の途中で切れていないことを確認（省略記号の前の文字が英数字でないことを確認）
        import re
        char_before_ellipsis = result[-4]  # "..."の前の文字
        assert not re.match(r'\w', char_before_ellipsis), "単語の途中で切り詰められています"
        assert len(result) <= formatter.max_length

    def test_apply_length_limit_punctuation_trimming_and_ellipsis(self, formatter):
        """句読点の除去と省略記号の追加"""
        input_text = "This is a very long commit message that ends with punctuation,."
        result = formatter._apply_length_limit(input_text)
        assert result.endswith("...")
        # 省略記号の前に句読点がないことを確認
        before_ellipsis = result[:-3].rstrip()
        assert not before_ellipsis.endswith(('.', ',', '!', '?', ';', ':'))

    def test_apply_length_limit_ensures_logger_warning_emitted(self, formatter, mock_logger):
        """長さ制限適用時に警告ログが出力されることを確認"""
        long_text = "A" * 100  # 制限を大幅に超える
        formatter._apply_length_limit(long_text)
        mock_logger.warning.assert_called_once()
        # 警告メッセージに長さ情報が含まれることを確認
        call_args = mock_logger.warning.call_args[0]
        assert "切り詰めました" in call_args[0]

    # validate_messageのテスト
    def test_validate_message_empty_input(self, formatter):
        """空入力の検証"""
        assert not formatter.validate_message("")
        assert not formatter.validate_message("   ")

    def test_validate_message_short_input(self, formatter):
        """短すぎる入力の検証"""
        assert not formatter.validate_message("ab")  # 3文字未満
        assert formatter.validate_message("abc")     # 3文字以上

    @pytest.mark.parametrize("invalid_char", [
        "\x00",  # NULL
        "\x01",  # SOH
        "\x02",  # STX
        "\x1f",  # Unit Separator
    ])
    def test_validate_message_invalid_control_chars(self, formatter, invalid_char):
        """不正な制御文字の検出"""
        message = f"Valid message{invalid_char}with control char"
        assert not formatter.validate_message(message)

    @pytest.mark.parametrize("valid_char", [
        "\n",    # 改行（許可）
        "\t",    # タブ（許可）
    ])
    def test_validate_message_valid_control_chars(self, formatter, valid_char):
        """有効な制御文字の許可"""
        message = f"Valid message{valid_char}with allowed char"
        assert formatter.validate_message(message)

    def test_validate_message_normal_text(self, formatter):
        """正常なテキストの検証"""
        assert formatter.validate_message("This is a normal commit message")
        assert formatter.validate_message("fix: resolve issue with parser")

    # 統合テスト
    def test_format_response_integration_with_long_complex_input(self, formatter, mock_logger):
        """長くて複雑な入力での統合テスト"""
        complex_input = '''
        ```python
        def complex_function():
            return "test"
        ```

        Commit message: "Add a very long and complex commit message that includes code blocks, quotes, and exceeds the maximum length limit to test the complete pipeline"

        This is additional text that should be ignored.
        '''

        result = formatter.format_response(complex_input)

        # 結果の検証
        assert isinstance(result, str)
        assert len(result) <= formatter.max_length
        assert "```" not in result
        assert result.startswith("Add a very long")
        assert result.endswith("...")
        # トリミング時の警告が出ていること
        assert mock_logger.warning.called

    def test_format_response_with_multiple_processing_steps(self, formatter):
        """複数の処理ステップを含む統合テスト"""
        input_text = """  
        GENERATED COMMIT MESSAGE: 'Fix\t\tthe   authentication\n\n\nbug   in\tuser\nlogin'  
        """
        
        result = formatter.format_response(input_text)
        
        # 各ステップが適用されていることを確認
        assert result == "Fix the authentication bug in user login"
        assert "GENERATED COMMIT MESSAGE:" not in result
        assert "'" not in result
        assert "\t" not in result
        assert "   " not in result

    def test_format_response_edge_case_only_code_block(self, formatter, mock_logger):
        """コードブロックのみの入力（エッジケース）"""
        input_text = """```bash
git add .
git commit -m "test"
```"""
        
        result = formatter.format_response(input_text)
        
        # デフォルトメッセージが返されることを確認
        assert result == formatter.default_message
        mock_logger.warning.assert_called()

    # パラメタ化されたテスト - エッジケース
    @pytest.mark.parametrize("test_input,expected_type,should_warn", [
        ("", str, True),                    # 空文字列
        ("   \n\t  ", str, True),           # 空白のみ
        ("a", str, False),                  # 最小有効文字
        ("Normal message", str, False),     # 正常
        ("x" * 100, str, True),            # 長すぎる（警告）
    ])
    def test_format_response_parametrized_edge_cases(self, formatter, mock_logger, test_input, expected_type, should_warn):
        """エッジケースのパラメタ化テスト"""
        result = formatter.format_response(test_input)
        
        assert isinstance(result, expected_type)
        assert len(result) > 0
        assert len(result) <= formatter.max_length
        
        if should_warn:
            assert mock_logger.warning.called
        
    def test_custom_max_length_and_default_message(self):
        """カスタム設定でのテスト"""
        custom_formatter = MessageFormatter(max_length=20, default_message="Custom default")
        
        # 長いメッセージの切り詰め
        long_msg = "This is a very long message that exceeds 20 characters"
        result = custom_formatter.format_response(long_msg)
        assert len(result) <= 20
        assert result.endswith("...")
        
        # 空入力でカスタムデフォルト
        result = custom_formatter.format_response("")
        assert result == "Custom default"


if __name__ == "__main__":
    # 簡単なテスト実行例
    formatter = MessageFormatter()
    
    print("=== MessageFormatter Test Examples ===")
    
    # 基本テスト
    test_cases = [
        ("", "Empty input"),
        ("   ", "Whitespace only"),  
        ("Add new feature", "Normal message"),
        ("x" * 100, "Long message"),
        ('Commit message: "Add feature"', "With prefix and quotes"),
        ("```\ncode\n```\nAdd function", "With code block"),
    ]
    
    for test_input, description in test_cases:
        result = formatter.format_response(test_input)
        print(f"{description:20} -> '{result}' (len: {len(result)})")
    
    print("\n=== Validation Tests ===")
    validation_cases = [
        ("", "Empty"),
        ("ab", "Too short"),
        ("abc", "Minimum length"),
        ("Normal message", "Valid"),
        ("Bad\x00message", "With null char"),
        ("Good\nmessage", "With newline"),
    ]
    
    for test_input, description in validation_cases:
        is_valid = formatter.validate_message(test_input)
        print(f"{description:15} -> {is_valid}")
    
    print("\nAll example tests completed!")