"""
Git差分処理システム

標準入力からGitの差分データを読み取り、LLM向けにフォーマットする。
LazyGitとの統合でステージされた変更の検証も行う。
"""

import sys
import re
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from io import StringIO

logger = logging.getLogger(__name__)


@dataclass
class DiffData:
    """Git差分データの構造化表現"""
    raw_diff: str
    file_count: int
    additions: int
    deletions: int
    files_changed: List[str] = field(default_factory=list)
    is_binary_change: bool = False
    total_lines: int = 0


class GitError(Exception):
    """Git処理関連のエラー"""
    pass


class GitDiffProcessor:
    """
    Git差分処理クラス

    標準入力からgit diffの出力を読み取り、解析してLLM向けにフォーマットする。
    LazyGitとの統合において、ステージされた変更の有無を確認する機能も提供。
    """

    def __init__(self, max_diff_size: int = 50000):
        """
        Git差分プロセッサーを初期化

        Args:
            max_diff_size: 処理する差分の最大サイズ（バイト）
        """
        self.max_diff_size = max_diff_size
        self._cached_diff_data: Optional[DiffData] = None

    def read_staged_diff(self) -> str:
        """
        標準入力からステージされた変更の差分を読み取り

        この関数はLazyGitから `git diff --staged` の出力を
        標準入力経由で受け取ることを想定している。

        Returns:
            読み取られた差分データ（文字列）

        Raises:
            GitError: 差分の読み取りに失敗した場合
        """
        try:
            logger.debug("標準入力からGit差分を読み取り開始")

            # 標準入力から差分データを読み取り
            diff_content = sys.stdin.read()

            # サイズ制限チェック
            if len(diff_content.encode('utf-8')) > self.max_diff_size:
                logger.warning(f"差分サイズが上限を超過: {len(diff_content)} > {self.max_diff_size}")
                # 差分を切り詰める
                diff_content = self._truncate_diff(diff_content)

            # 差分データをキャッシュ用に解析
            self._cached_diff_data = self._parse_diff(diff_content)

            logger.info(f"Git差分読み取り完了: {self._cached_diff_data.file_count}ファイル, "
                       f"{self._cached_diff_data.additions}+/{self._cached_diff_data.deletions}-")

            return diff_content

        except Exception as e:
            logger.error(f"Git差分読み取りエラー: {e}")
            raise GitError(f"差分の読み取りに失敗しました: {e}")

    def has_staged_changes(self) -> bool:
        """
        ステージされた変更があるかどうかを確認

        Returns:
            ステージされた変更がある場合True、ない場合False
        """
        if self._cached_diff_data is None:
            # まだ差分を読み取っていない場合は読み取りを試行
            try:
                self.read_staged_diff()
            except GitError:
                return False

        # 空の差分または実質的な変更がない場合はFalse
        if not self._cached_diff_data or not self._cached_diff_data.raw_diff.strip():
            return False

        # ファイル数または変更行数で判定
        return (self._cached_diff_data.file_count > 0 or
                self._cached_diff_data.additions > 0 or
                self._cached_diff_data.deletions > 0)

    def format_diff_for_llm(self, diff: str) -> str:
        """
        差分データをLLM向けにフォーマット

        Args:
            diff: 元の差分データ

        Returns:
            LLM向けにフォーマットされた差分データ
        """
        if not diff or not diff.strip():
            return "No changes detected"

        try:
            # 差分を解析
            diff_data = self._parse_diff(diff)

            # フォーマット済み差分を構築
            formatted_lines = []

            # ヘッダー情報を追加
            formatted_lines.append(f"Files changed: {diff_data.file_count}")
            formatted_lines.append(f"Additions: +{diff_data.additions}")
            formatted_lines.append(f"Deletions: -{diff_data.deletions}")
            formatted_lines.append("")

            # 変更されたファイル一覧
            if diff_data.files_changed:
                formatted_lines.append("Changed files:")
                for file_path in diff_data.files_changed:
                    formatted_lines.append(f"  - {file_path}")
                formatted_lines.append("")

            # 実際の差分内容（フィルタリング済み）
            filtered_diff = self._filter_diff_content(diff)
            if filtered_diff:
                formatted_lines.append("Diff content:")
                formatted_lines.append(filtered_diff)

            return "\n".join(formatted_lines)

        except Exception as e:
            logger.error(f"差分フォーマットエラー: {e}")
            # エラーが発生した場合は元の差分をそのまま返す
            return diff

    def get_diff_stats(self) -> Dict[str, Any]:
        """
        キャッシュされた差分統計情報を取得

        Returns:
            差分統計情報の辞書
        """
        if self._cached_diff_data is None:
            return {
                'file_count': 0,
                'additions': 0,
                'deletions': 0,
                'files_changed': [],
                'has_binary_changes': False,
                'total_lines': 0
            }

        return {
            'file_count': self._cached_diff_data.file_count,
            'additions': self._cached_diff_data.additions,
            'deletions': self._cached_diff_data.deletions,
            'files_changed': self._cached_diff_data.files_changed.copy(),
            'has_binary_changes': self._cached_diff_data.is_binary_change,
            'total_lines': self._cached_diff_data.total_lines
        }

    def _parse_diff(self, diff_content: str) -> DiffData:
        """
        差分内容を解析してDiffDataオブジェクトを生成

        Args:
            diff_content: 差分内容

        Returns:
            解析されたDiffDataオブジェクト
        """
        if not diff_content:
            return DiffData(raw_diff="", file_count=0, additions=0, deletions=0)

        # 基本統計を初期化
        file_count = 0
        additions = 0
        deletions = 0
        files_changed = []
        is_binary_change = False
        total_lines = len(diff_content.splitlines())

        try:
            # ファイル変更の検出（diff --git a/file b/file パターン）
            file_patterns = re.findall(r'^diff --git a/(.+?) b/(.+?)$', diff_content, re.MULTILINE)
            for old_file, new_file in file_patterns:
                file_count += 1
                # 新しいファイル名を使用（リネームの場合は新しい名前）
                if new_file not in files_changed:
                    files_changed.append(new_file)

            # 追加/削除行数の計算（+/- で始まる行をカウント）
            lines = diff_content.splitlines()
            for line in lines:
                # バイナリファイルの変更を検出
                if "Binary files" in line and "differ" in line:
                    is_binary_change = True
                    continue

                # 差分の内容行のみカウント（ヘッダーやメタデータは除外）
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1

            # ファイル数が0の場合、他の方法で検出を試行
            if file_count == 0:
                # --- a/file +++ b/file パターンも確認
                alt_file_patterns = re.findall(r'^--- a/(.+?)$', diff_content, re.MULTILINE)
                if alt_file_patterns:
                    file_count = len(set(alt_file_patterns))
                    files_changed = list(set(alt_file_patterns))

            logger.debug(f"差分解析結果: {file_count}ファイル, {additions}+/{deletions}-, バイナリ: {is_binary_change}")

        except Exception as e:
            logger.warning(f"差分解析中にエラー（処理続行）: {e}")

        return DiffData(
            raw_diff=diff_content,
            file_count=file_count,
            additions=additions,
            deletions=deletions,
            files_changed=files_changed,
            is_binary_change=is_binary_change,
            total_lines=total_lines
        )

    def _filter_diff_content(self, diff: str) -> str:
        """
        LLM向けに差分内容をフィルタリング

        Args:
            diff: 元の差分内容

        Returns:
            フィルタリングされた差分内容
        """
        if not diff:
            return ""

        filtered_lines = []
        lines = diff.splitlines()

        for line in lines:
            # バイナリファイルの変更行はスキップ
            if "Binary files" in line and "differ" in line:
                filtered_lines.append("(Binary file changed)")
                continue

            # 非常に長い行は切り詰める
            if len(line) > 200:
                line = line[:197] + "..."

            # 空白のみの変更行は情報を簡略化
            if line.startswith('+') or line.startswith('-'):
                if not line[1:].strip():
                    continue  # 空白のみの変更はスキップ

            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _truncate_diff(self, diff: str) -> str:
        """
        差分が大きすぎる場合に切り詰める

        Args:
            diff: 元の差分

        Returns:
            切り詰められた差分
        """
        if len(diff.encode('utf-8')) <= self.max_diff_size:
            return diff

        # バイト単位で切り詰める
        truncated = diff.encode('utf-8')[:self.max_diff_size].decode('utf-8', errors='ignore')

        # 最後に改行を追加して切り詰めメッセージを付加
        return truncated + "\n\n... (diff truncated due to size limit)"

    def validate_diff_format(self, diff: str) -> bool:
        """
        差分フォーマットの妥当性を検証

        Args:
            diff: 検証する差分

        Returns:
            フォーマットが有効な場合True
        """
        if not diff or not diff.strip():
            return False

        # 基本的なGit差分フォーマットの存在確認
        has_diff_header = 'diff --git' in diff
        has_file_header = ('---' in diff and '+++' in diff)
        has_changes = ('+' in diff or '-' in diff)

        # 最低限の条件: ファイルヘッダーまたは変更内容が存在
        return has_file_header or has_changes or has_diff_header