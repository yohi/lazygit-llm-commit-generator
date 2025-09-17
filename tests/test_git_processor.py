"""
GitDiffProcessorのユニットテスト

Git差分の読み取り、解析、フォーマット機能をテスト。
"""

import pytest
import sys
from unittest.mock import patch, Mock
from io import StringIO

from lazygit_llm.src.git_processor import GitDiffProcessor, DiffData, GitError


class TestGitDiffProcessor:
    """GitDiffProcessorのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.processor = GitDiffProcessor()

    def test_initialization(self):
        """初期化テスト"""
        assert self.processor.max_diff_size == 50000
        assert self.processor._cached_diff_data is None
        assert hasattr(self.processor, 'security_validator')

    def test_initialization_custom_size(self):
        """カスタムサイズでの初期化テスト"""
        custom_processor = GitDiffProcessor(max_diff_size=100000)
        assert custom_processor.max_diff_size == 100000

    def test_read_staged_diff_success(self, sample_git_diff):
        """差分読み取り成功テスト"""
        with patch('sys.stdin') as mock_stdin, \
             patch.object(self.processor.security_validator, 'sanitize_git_diff') as mock_sanitize:

            mock_stdin.read.return_value = sample_git_diff
            mock_sanitize.return_value = (sample_git_diff, type('Result', (), {
                'is_valid': True,
                'level': 'info',
                'message': 'Safe diff',
                'recommendations': []
            })())

            result = self.processor.read_staged_diff()

            assert result == sample_git_diff
            assert self.processor._cached_diff_data is not None
            assert self.processor._cached_diff_data.file_count == 1

    def test_read_staged_diff_security_error(self, sample_git_diff):
        """差分セキュリティエラーテスト"""
        with patch('sys.stdin') as mock_stdin, \
             patch.object(self.processor.security_validator, 'sanitize_git_diff') as mock_sanitize:

            mock_stdin.read.return_value = sample_git_diff
            mock_sanitize.return_value = (sample_git_diff, type('Result', (), {
                'is_valid': False,
                'level': 'danger',
                'message': 'Dangerous content detected'
            })())

            with pytest.raises(GitError, match="セキュリティエラー"):
                self.processor.read_staged_diff()

    def test_read_staged_diff_security_warning(self, sample_git_diff):
        """差分セキュリティ警告テスト"""
        with patch('sys.stdin') as mock_stdin, \
             patch.object(self.processor.security_validator, 'sanitize_git_diff') as mock_sanitize:

            mock_stdin.read.return_value = sample_git_diff
            mock_sanitize.return_value = (sample_git_diff, type('Result', (), {
                'is_valid': True,
                'level': 'warning',
                'message': 'Potential sensitive content',
                'recommendations': ['Review the content']
            })())

            result = self.processor.read_staged_diff()

            assert result == sample_git_diff
            # 警告レベルでは処理が継続される

    def test_read_staged_diff_stdin_error(self):
        """標準入力読み取りエラーテスト"""
        with patch('sys.stdin') as mock_stdin:
            mock_stdin.read.side_effect = IOError("stdin read error")

            with pytest.raises(GitError, match="差分の読み取りに失敗しました"):
                self.processor.read_staged_diff()

    def test_has_staged_changes_with_cached_data(self, sample_git_diff):
        """キャッシュされたデータでの変更確認テスト"""
        # 事前にデータを設定
        self.processor._cached_diff_data = DiffData(
            raw_diff=sample_git_diff,
            file_count=1,
            additions=5,
            deletions=0,
            files_changed=['test.py']
        )

        assert self.processor.has_staged_changes() is True

    def test_has_staged_changes_no_cached_data(self, sample_git_diff):
        """キャッシュなしでの変更確認テスト"""
        with patch.object(self.processor, 'read_staged_diff') as mock_read:
            mock_read.return_value = sample_git_diff
            self.processor._cached_diff_data = DiffData(
                raw_diff=sample_git_diff,
                file_count=1,
                additions=5,
                deletions=0,
                files_changed=['test.py']
            )

            result = self.processor.has_staged_changes()

            assert result is True
            mock_read.assert_called_once()

    def test_has_staged_changes_empty_diff(self):
        """空の差分での変更確認テスト"""
        self.processor._cached_diff_data = DiffData(
            raw_diff="",
            file_count=0,
            additions=0,
            deletions=0,
            files_changed=[]
        )

        assert self.processor.has_staged_changes() is False

    def test_has_staged_changes_read_error(self):
        """読み取りエラー時の変更確認テスト"""
        with patch.object(self.processor, 'read_staged_diff') as mock_read:
            mock_read.side_effect = GitError("Read failed")

            result = self.processor.has_staged_changes()

            assert result is False

    def test_format_diff_for_llm_success(self, sample_git_diff):
        """LLM向け差分フォーマット成功テスト"""
        formatted = self.processor.format_diff_for_llm(sample_git_diff)

        assert "Files changed: 1" in formatted
        assert "Additions: +5" in formatted
        assert "Deletions: -0" in formatted
        assert "Changed files:" in formatted
        assert "test.py" in formatted
        assert "Diff content:" in formatted

    def test_format_diff_for_llm_empty(self):
        """空の差分のLLM向けフォーマットテスト"""
        formatted = self.processor.format_diff_for_llm("")

        assert formatted == "No changes detected"

    def test_format_diff_for_llm_whitespace_only(self):
        """空白のみの差分のLLM向けフォーマットテスト"""
        formatted = self.processor.format_diff_for_llm("   \n   \n   ")

        assert formatted == "No changes detected"

    def test_format_diff_for_llm_error(self):
        """フォーマットエラー時のテスト"""
        with patch.object(self.processor, '_parse_diff') as mock_parse:
            mock_parse.side_effect = Exception("Parse error")

            result = self.processor.format_diff_for_llm("test diff")

            # エラー時は元の差分をそのまま返す
            assert result == "test diff"

    def test_get_diff_stats_with_data(self, sample_git_diff):
        """差分統計取得テスト（データあり）"""
        self.processor._cached_diff_data = DiffData(
            raw_diff=sample_git_diff,
            file_count=2,
            additions=10,
            deletions=5,
            files_changed=['file1.py', 'file2.py'],
            is_binary_change=True,
            total_lines=50
        )

        stats = self.processor.get_diff_stats()

        assert stats['file_count'] == 2
        assert stats['additions'] == 10
        assert stats['deletions'] == 5
        assert stats['files_changed'] == ['file1.py', 'file2.py']
        assert stats['has_binary_changes'] is True
        assert stats['total_lines'] == 50

    def test_get_diff_stats_no_data(self):
        """差分統計取得テスト（データなし）"""
        stats = self.processor.get_diff_stats()

        assert stats['file_count'] == 0
        assert stats['additions'] == 0
        assert stats['deletions'] == 0
        assert stats['files_changed'] == []
        assert stats['has_binary_changes'] is False
        assert stats['total_lines'] == 0

    def test_parse_diff_success(self, sample_git_diff):
        """差分解析成功テスト"""
        diff_data = self.processor._parse_diff(sample_git_diff)

        assert diff_data.file_count == 1
        assert diff_data.additions == 5
        assert diff_data.deletions == 0
        assert 'test.py' in diff_data.files_changed
        assert diff_data.is_binary_change is False
        assert diff_data.total_lines > 0

    def test_parse_diff_empty(self):
        """空の差分の解析テスト"""
        diff_data = self.processor._parse_diff("")

        assert diff_data.file_count == 0
        assert diff_data.additions == 0
        assert diff_data.deletions == 0
        assert diff_data.files_changed == []
        assert diff_data.raw_diff == ""

    def test_parse_diff_binary_files(self):
        """バイナリファイル変更の解析テスト"""
        binary_diff = """diff --git a/image.png b/image.png
index 1234567..abcdef0 100644
Binary files a/image.png and b/image.png differ"""

        diff_data = self.processor._parse_diff(binary_diff)

        assert diff_data.is_binary_change is True
        assert 'image.png' in diff_data.files_changed

    def test_parse_diff_complex(self):
        """複雑な差分の解析テスト"""
        complex_diff = """diff --git a/file1.py b/file1.py
index 1234567..abcdef0 100644
--- a/file1.py
+++ b/file1.py
@@ -1,3 +1,5 @@
 import os
+import sys

 def main():
+    print("Hello")
     pass
-    return

diff --git a/file2.py b/file2.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/file2.py
@@ -0,0 +1,2 @@
+def test():
+    return True"""

        diff_data = self.processor._parse_diff(complex_diff)

        assert diff_data.file_count == 2
        assert diff_data.additions == 4  # +import sys, +print("Hello"), +def test():, +return True
        assert diff_data.deletions == 1  # -return
        assert 'file1.py' in diff_data.files_changed
        assert 'file2.py' in diff_data.files_changed

    def test_parse_diff_alternative_format(self):
        """代替形式の差分解析テスト"""
        alt_diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,3 @@
 line1
+line2
 line3"""

        diff_data = self.processor._parse_diff(alt_diff)

        assert diff_data.file_count == 1
        assert 'test.py' in diff_data.files_changed
        assert diff_data.additions == 1

    def test_filter_diff_content(self):
        """差分内容フィルタリングテスト"""
        diff_with_binary = """diff --git a/test.py b/test.py
+added line
Binary files a/image.png and b/image.png differ
+another line"""

        filtered = self.processor._filter_diff_content(diff_with_binary)

        assert "(Binary file changed)" in filtered
        assert "Binary files a/image.png and b/image.png differ" not in filtered
        assert "+added line" in filtered
        assert "+another line" in filtered

    def test_filter_diff_content_long_lines(self):
        """長い行のフィルタリングテスト"""
        long_line = "+" + "a" * 250  # 200文字を超える長い行
        diff_with_long_line = f"""diff --git a/test.py b/test.py
+short line
{long_line}
+another short line"""

        filtered = self.processor._filter_diff_content(diff_with_long_line)

        assert "+short line" in filtered
        assert "+another short line" in filtered
        # 長い行は切り詰められる
        assert "..." in filtered
        assert len([line for line in filtered.split('\n') if len(line) > 200]) == 0

    def test_filter_diff_content_empty_changes(self):
        """空白のみの変更のフィルタリングテスト"""
        diff_with_empty = """diff --git a/test.py b/test.py
+line with content
+
-
-
+another line"""

        filtered = self.processor._filter_diff_content(diff_with_empty)

        assert "+line with content" in filtered
        assert "+another line" in filtered
        # 空白のみの変更行はスキップされる
        lines = filtered.split('\n')
        empty_changes = [line for line in lines if line in ['+', '-', '+   ', '-   ']]
        assert len(empty_changes) == 0

    def test_truncate_diff_within_limit(self, sample_git_diff):
        """制限内の差分の切り詰めテスト"""
        result = self.processor._truncate_diff(sample_git_diff)

        # 制限内なのでそのまま返される
        assert result == sample_git_diff

    def test_truncate_diff_exceeds_limit(self):
        """制限を超える差分の切り詰めテスト"""
        large_diff = "a" * (self.processor.max_diff_size + 1000)
        result = self.processor._truncate_diff(large_diff)

        assert len(result.encode('utf-8')) <= self.processor.max_diff_size + 100  # メッセージ分の余裕
        assert "... (diff truncated due to size limit)" in result

    def test_validate_diff_format_valid(self, sample_git_diff):
        """有効な差分フォーマットの検証テスト"""
        assert self.processor.validate_diff_format(sample_git_diff) is True

    def test_validate_diff_format_minimal_valid(self):
        """最小限の有効な差分フォーマットテスト"""
        minimal_diff = "+added line"
        assert self.processor.validate_diff_format(minimal_diff) is True

    def test_validate_diff_format_with_headers(self):
        """ヘッダー付きの有効な差分フォーマットテスト"""
        diff_with_headers = """--- a/file.py
+++ b/file.py
@@ -1,1 +1,2 @@
 existing line
+new line"""
        assert self.processor.validate_diff_format(diff_with_headers) is True

    def test_validate_diff_format_empty(self):
        """空の差分の検証テスト"""
        assert self.processor.validate_diff_format("") is False
        assert self.processor.validate_diff_format("   ") is False
        assert self.processor.validate_diff_format(None) is False

    def test_validate_diff_format_no_changes(self):
        """変更がない差分の検証テスト"""
        no_changes_diff = "file content without + or - markers"
        assert self.processor.validate_diff_format(no_changes_diff) is False

    @pytest.mark.parametrize("diff_content,expected_files,expected_additions,expected_deletions", [
        # 単一ファイル追加
        ("diff --git a/new.py b/new.py\n+def new():\n+    pass", 1, 2, 0),
        # 単一ファイル削除
        ("diff --git a/old.py b/old.py\n-def old():\n-    pass", 1, 0, 2),
        # 複数ファイル
        ("diff --git a/a.py b/a.py\n+line\ndiff --git a/b.py b/b.py\n-line", 2, 1, 1),
        # ファイル名変更
        ("diff --git a/old.py b/new.py\n+changed", 1, 1, 0),
    ])
    def test_parse_diff_various_scenarios(self, diff_content, expected_files, expected_additions, expected_deletions):
        """様々なシナリオでの差分解析テスト"""
        diff_data = self.processor._parse_diff(diff_content)

        assert diff_data.file_count == expected_files
        assert diff_data.additions == expected_additions
        assert diff_data.deletions == expected_deletions

    def test_cached_diff_data_isolation(self):
        """キャッシュデータの分離テスト"""
        stats1 = self.processor.get_diff_stats()
        stats1['files_changed'].append('test_file')

        # 元のキャッシュデータが変更されていないことを確認
        stats2 = self.processor.get_diff_stats()
        assert 'test_file' not in stats2['files_changed']