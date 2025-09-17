"""
MessageFormatterのユニットテスト

LLMレスポンスのクリーニングとフォーマット機能をテスト。
"""

import pytest
from lazygit_llm.src.message_formatter import MessageFormatter


class TestMessageFormatter:
    """MessageFormatterのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.formatter = MessageFormatter()

    def test_initialization(self):
        """初期化テスト"""
        assert self.formatter.max_message_length == 500

    def test_initialization_custom_length(self):
        """カスタム長さでの初期化テスト"""
        custom_formatter = MessageFormatter(max_message_length=200)
        assert custom_formatter.max_message_length == 200

    def test_format_response_success(self):
        """レスポンスフォーマット成功テスト"""
        raw_response = "feat: add new feature to handle user authentication"
        result = self.formatter.format_response(raw_response)

        assert result == "feat: add new feature to handle user authentication"

    def test_format_response_empty(self):
        """空のレスポンステスト"""
        with pytest.raises(ValueError, match="空のレスポンスです"):
            self.formatter.format_response("")

    def test_format_response_with_artifacts(self):
        """LLMアーティファクト付きレスポンステスト"""
        raw_response = "Here's your commit message:\n\nfeat: add new feature\n\nThis should be concise."
        result = self.formatter.format_response(raw_response)

        assert "Here's your commit message:" not in result
        assert "feat: add new feature" in result

    def test_format_response_too_long(self):
        """長すぎるレスポンステスト"""
        long_response = "feat: " + "very long description " * 50  # 500文字超過
        result = self.formatter.format_response(long_response)

        assert len(result) <= self.formatter.max_message_length

    def test_format_response_invalid_format(self):
        """無効なフォーマットのレスポンステスト"""
        invalid_response = "\x00\x01\x02"  # 制御文字
        result = self.formatter.format_response(invalid_response)

        # 無効な文字は除去される
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result

    def test_clean_llm_response_basic(self):
        """基本的なLLMレスポンスクリーニングテスト"""
        response = "  feat: add new feature  "
        result = self.formatter.clean_llm_response(response)

        assert result == "feat: add new feature"

    def test_clean_llm_response_empty(self):
        """空のレスポンスクリーニングテスト"""
        result = self.formatter.clean_llm_response("")
        assert result == ""

    def test_clean_llm_response_with_artifacts(self):
        """アーティファクト付きレスポンスクリーニングテスト"""
        response = "Here is your commit message:\n\nfeat: add authentication\n\nNo additional text needed."
        result = self.formatter.clean_llm_response(response)

        assert "Here is your commit message:" not in result
        assert "No additional text needed." not in result
        assert "feat: add authentication" in result

    def test_clean_llm_response_multiple_newlines(self):
        """複数改行のクリーニングテスト"""
        response = "feat: add feature\n\n\n\nWith description\n\n\n\nAnd more text"
        result = self.formatter.clean_llm_response(response)

        # 3つ以上の連続改行は2つに正規化される
        assert "\n\n\n" not in result
        assert "feat: add feature\n\nWith description\n\nAnd more text" == result

    def test_clean_llm_response_multiple_spaces(self):
        """複数スペースのクリーニングテスト"""
        response = "feat:    add     feature    with    spaces"
        result = self.formatter.clean_llm_response(response)

        # 2つ以上の連続スペースは1つに正規化される
        assert "    " not in result
        assert "feat: add feature with spaces" == result

    def test_format_for_lazygit_basic(self):
        """LazyGit基本フォーマットテスト"""
        message = "feat: add new feature"
        result = self.formatter.format_for_lazygit(message)

        assert result == "feat: add new feature"

    def test_format_for_lazygit_empty(self):
        """空メッセージのLazyGitフォーマットテスト"""
        result = self.formatter.format_for_lazygit("")
        assert result == ""

    def test_format_for_lazygit_trailing_newlines(self):
        """末尾改行の除去テスト"""
        message = "feat: add new feature\n\n\n"
        result = self.formatter.format_for_lazygit(message)

        assert result == "feat: add new feature"

    def test_format_for_lazygit_multiline(self):
        """複数行メッセージのLazyGitフォーマットテスト"""
        message = "feat: add new feature\n\nThis is a detailed description\nof the new feature"
        result = self.formatter.format_for_lazygit(message)

        # 内部の改行は保持される
        assert "feat: add new feature\n\nThis is a detailed description\nof the new feature" == result

    def test_validate_commit_message_valid(self):
        """有効なコミットメッセージの検証テスト"""
        valid_messages = [
            "feat: add new feature",
            "fix: resolve authentication issue",
            "docs: update installation guide",
            "feat(auth): add OAuth2 support",
        ]

        for message in valid_messages:
            assert self.formatter.validate_commit_message(message) is True

    def test_validate_commit_message_invalid(self):
        """無効なコミットメッセージの検証テスト"""
        invalid_messages = [
            "",  # 空
            "   ",  # 空白のみ
            "ab",  # 短すぎる
            "a" * 600,  # 長すぎる
            "feat: add feature\n\n\n\n\n\nToo many lines",  # 行数が多すぎる
            "feat: add \x00\x01 feature",  # 制御文字
        ]

        for message in invalid_messages:
            assert self.formatter.validate_commit_message(message) is False

    def test_validate_message_format_length_boundary(self):
        """メッセージ長境界テスト"""
        # 境界値のテスト
        exactly_max = "a" * self.formatter.max_message_length
        too_long = "a" * (self.formatter.max_message_length + 1)

        assert self.formatter.validate_message_format(exactly_max) is True
        assert self.formatter.validate_message_format(too_long) is False

    def test_validate_message_format_line_count(self):
        """行数制限テスト"""
        # 5行ちょうど
        five_lines = "line1\nline2\nline3\nline4\nline5"
        # 6行（制限超過）
        six_lines = "line1\nline2\nline3\nline4\nline5\nline6"

        assert self.formatter.validate_message_format(five_lines) is True
        assert self.formatter.validate_message_format(six_lines) is False

    def test_remove_llm_artifacts(self):
        """LLMアーティファクト除去の詳細テスト"""
        test_cases = [
            # 前置きパターン
            ("Here is your commit message: feat: add feature", "feat: add feature"),
            ("Here's the commit message: fix: resolve issue", "fix: resolve issue"),
            ("Based on the diff: docs: update readme", "docs: update readme"),
            ("Looking at the changes: style: format code", "style: format code"),
            ("I would suggest: test: add unit tests", "test: add unit tests"),

            # 後置きパターン
            ("feat: add feature\nNo additional text.", "feat: add feature"),
            ("fix: resolve issue\n以上です。", "fix: resolve issue"),
            ("docs: update guide\n以下の通りです。", "docs: update guide"),

            # コミットメッセージラベル
            ("commit message: feat: add feature", "feat: add feature"),
            ("コミットメッセージ: fix: resolve issue", "fix: resolve issue"),
        ]

        for input_text, expected in test_cases:
            result = self.formatter._remove_llm_artifacts(input_text)
            assert expected in result, f"Failed for input: {input_text}"

    def test_truncate_message_within_limit(self):
        """制限内メッセージの切り詰めテスト"""
        short_message = "feat: add feature"
        result = self.formatter._truncate_message(short_message)

        assert result == short_message

    def test_truncate_message_exceeds_limit(self):
        """制限超過メッセージの切り詰めテスト"""
        long_message = "feat: " + "very long description " * 100
        result = self.formatter._truncate_message(long_message)

        assert len(result) <= self.formatter.max_message_length
        assert "..." in result

    def test_truncate_message_preserves_meaning(self):
        """意味を保持した切り詰めテスト"""
        long_message = "feat: add authentication system with OAuth2 support " * 20
        result = self.formatter._truncate_message(long_message)

        # 冒頭の重要な部分は保持される
        assert "feat: add authentication" in result
        assert len(result) <= self.formatter.max_message_length

    def test_clean_message_comprehensive(self):
        """包括的メッセージクリーニングテスト"""
        messy_message = """
        Here's your commit message:

        feat: add user authentication

        This commit adds OAuth2 support
        with Google and GitHub providers.

        No additional text.
        """

        result = self.formatter.clean_message(messy_message)

        # アーティファクト除去
        assert "Here's your commit message:" not in result
        assert "No additional text." not in result

        # 核心部分は保持
        assert "feat: add user authentication" in result
        assert "OAuth2 support" in result

    def test_error_handling(self):
        """エラーハンドリングテスト"""
        with pytest.raises(ValueError):
            self.formatter.format_response(None)

        with pytest.raises(ValueError):
            self.formatter.format_response("")

        # 無効な入力でもクラッシュしない
        result = self.formatter.clean_llm_response(None)
        assert result == ""

    @pytest.mark.parametrize("input_message,expected_valid", [
        ("feat: add new feature", True),
        ("fix: resolve bug in auth", True),
        ("docs: update README", True),
        ("", False),
        ("x", False),  # 短すぎる
        ("a" * 1000, False),  # 長すぎる
        ("line1\nline2\nline3\nline4\nline5\nline6", False),  # 行数過多
    ])
    def test_validation_matrix(self, input_message, expected_valid):
        """検証マトリックステスト"""
        result = self.formatter.validate_commit_message(input_message)
        assert result == expected_valid

    def test_format_response_with_warning(self):
        """警告付きフォーマットテスト"""
        # 無効な形式だが処理は継続される
        response = "ab"  # 短すぎるが例外は発生しない

        with pytest.raises(ValueError, match="無効なメッセージ形式"):
            self.formatter.format_response(response)

    def test_japanese_content_handling(self):
        """日本語コンテンツの処理テスト"""
        japanese_response = "機能: 新しい認証システムを追加"
        result = self.formatter.format_response(japanese_response)

        assert result == "機能: 新しい認証システムを追加"
        assert self.formatter.validate_commit_message(result) is True

    def test_unicode_content_handling(self):
        """Unicode文字の処理テスト"""
        unicode_response = "feat: add emoji support 🚀✨"
        result = self.formatter.format_response(unicode_response)

        assert "🚀" in result
        assert "✨" in result
        assert self.formatter.validate_commit_message(result) is True