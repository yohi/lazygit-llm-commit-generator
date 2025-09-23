"""
Git差分処理システム

標準入力からGitの差分データを読み取り、LLM向けにフォーマットする。
LazyGitとの統合でステージされた変更の検証も行う。
また、subprocess経由でのgitコマンド実行による差分取得もサポートする。
"""

import sys
import re
import logging
import subprocess
import shutil
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from io import StringIO
from collections import OrderedDict
import threading
from concurrent.futures import ThreadPoolExecutor

from .security_validator import SecurityValidator

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
    パフォーマンス最適化として、キャッシュ機能と並行処理をサポート。
    subprocess経由でのgitコマンド実行による差分取得もサポート。
    """

    def __init__(self, max_diff_size: int = 50000, enable_parallel_processing: bool = True):
        """
        Git差分プロセッサーを初期化

        Args:
            max_diff_size: 処理する差分の最大サイズ（バイト）
            enable_parallel_processing: 並行処理を有効にするかどうか
        """
        self.max_diff_size = max_diff_size
        self.enable_parallel_processing = enable_parallel_processing
        self._cached_diff_data: Optional[DiffData] = None
        self._processing_cache: "OrderedDict[str, str]" = OrderedDict()
        self._cache_lock = threading.Lock()
        self._cache_maxsize = 128
        self.security_validator = SecurityValidator()

        # 並行処理用のThreadPoolExecutor（オンデマンド作成）
        self._executor = None

    def _get_executor(self) -> Optional[ThreadPoolExecutor]:
        """ThreadPoolExecutorを取得（必要時に作成）"""
        if not self.enable_parallel_processing:
            return None

        with self._cache_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=2)
            return self._executor

    def read_staged_diff(self) -> str:
        """
        標準入力またはgitコマンド経由でステージされた変更の差分を読み取り

        この関数はLazyGitから `git diff --staged` の出力を
        標準入力経由で受け取ることを想定している。
        標準入力が利用できない場合は、gitコマンドを直接実行する。

        Returns:
            読み取られた差分データ(文字列)

        Raises:
            GitError: 差分の読み取りに失敗した場合
        """
        try:
            logger.debug("Git差分を読み取り開始")

            # 標準入力からの読み取りを試行(サイズ上限を考慮)
            diff_content = None
            if not sys.stdin.isatty():
                try:
                    raw = sys.stdin.buffer.read(self.max_diff_size + 1)
                    diff_content = raw.decode('utf-8', errors='ignore')
                    if len(raw) > self.max_diff_size:
                        diff_content = self._truncate_diff(diff_content)
                    logger.debug("標準入力からGit差分を読み取り")
                except Exception:
                    logger.exception("標準入力からの読み取りに失敗、gitコマンドを使用")
                    diff_content = None

            # 標準入力が利用できない場合はgitコマンドを実行
            if diff_content is None:
                diff_content = self._read_diff_via_git()

            # セキュリティバリデーターで差分をサニタイゼーション
            sanitized_diff, security_result = self.security_validator.sanitize_git_diff(diff_content)

            if not security_result.is_valid:
                logger.error(f"差分セキュリティチェック失敗: {security_result.message}")
                raise GitError(f"セキュリティエラー: {security_result.message}")

            if security_result.level == "warning":
                logger.warning(f"差分セキュリティ警告: {security_result.message}")
                for rec in security_result.recommendations:
                    logger.warning(f"推奨: {rec}")

            diff_content = sanitized_diff

            # サイズ制限チェック
            byte_len = len(diff_content.encode('utf-8'))
            if byte_len > self.max_diff_size:
                logger.warning(f"差分サイズが上限を超過: {byte_len} > {self.max_diff_size}")
                # 差分を切り詰める
                diff_content = self._truncate_diff(diff_content)

            # 差分データをキャッシュ用に解析
            self._cached_diff_data = self._parse_diff(diff_content)

            logger.info(f"Git差分読み取り完了: {self._cached_diff_data.file_count}ファイル, "
                       f"{self._cached_diff_data.additions}+/{self._cached_diff_data.deletions}-")

            return diff_content

        except Exception as e:
            logger.exception("Git差分読み取りエラー")
            raise GitError("差分の読み取りに失敗しました") from e

    def _read_diff_via_git(self) -> str:
        """
        gitコマンド経由でステージ済みの差分を取得する

        Returns:
            Git差分の文字列

        Raises:
            GitError: gitコマンド実行エラー
        """
        try:
            git_cmd = shutil.which('git')
            if not git_cmd:
                raise FileNotFoundError("git not found in PATH")
            result = subprocess.run(
                [git_cmd, 'diff', '--cached'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                error_msg = f"git diff --cached が失敗しました (exit={result.returncode}): {result.stderr}"
                logger.exception(error_msg)
                raise GitError(error_msg)

            diff_output = result.stdout.strip()
            logger.debug("gitコマンド経由でGit差分を取得しました (%d文字)", len(diff_output))

            return diff_output

        except subprocess.TimeoutExpired as err:
            error_msg = "git diff --cached がタイムアウトしました"
            logger.exception(error_msg)
            raise GitError(error_msg) from err
        except FileNotFoundError as err:
            error_msg = "gitコマンドが見つかりません"
            logger.exception(error_msg)
            raise GitError(error_msg) from err

    def has_staged_changes(self) -> bool:
        """
        ステージされた変更があるかどうかを確認

        subprocess経由でgit diff --cached --quietを実行して確認する

        Returns:
            ステージされた変更がある場合True、ない場合False
        """
        try:
            git_cmd = shutil.which('git')
            if not git_cmd:
                raise FileNotFoundError("git not found in PATH")
            result = subprocess.run(
                [git_cmd, 'diff', '--cached', '--quiet'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # git diff --quiet の終了コードを正確に判定
            ret = result.returncode
            if ret == 0:
                logger.debug("ステージ済み変更チェック: False")
                return False
            if ret == 1:
                logger.debug("ステージ済み変更チェック: True")
                return True
            logger.warning("git diff --cached --quiet 非想定終了コード: %d; stderr=%s",
                           ret, (result.stderr or '').strip())
            return False

        except subprocess.TimeoutExpired:
            logger.exception("git diff --cached --quiet がタイムアウトしました")
            return False
        except FileNotFoundError:
            logger.exception("gitコマンドが見つかりません")
            return False
        except Exception:
            logger.exception("ステージ済み変更のチェックに失敗")
            return False

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
            # サイズを強制的に制限
            diff = self._truncate_diff(diff)
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

            # 実際の差分内容(フィルタリング済み)
            filtered_diff = self._filter_diff_content(diff)
            if filtered_diff:
                formatted_lines.append("Diff content:")
                formatted_lines.append(filtered_diff)

            return "\n".join(formatted_lines)

        except Exception:
            logger.exception("差分フォーマットエラー")
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

    def get_repository_status(self) -> dict:
        """
        リポジトリの状態を取得する

        Returns:
            リポジトリの状態辞書
        """
        try:
            git_cmd = shutil.which('git')
            if not git_cmd:
                raise FileNotFoundError("git not found in PATH")
            # ブランチ名を取得
            branch_result = subprocess.run(
                [git_cmd, 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=10
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

            # ステージ済み/未ステージファイル数を取得
            status_result = subprocess.run(
                [git_cmd, 'status', '--porcelain'],
                capture_output=True,
                text=True,
                timeout=10
            )

            staged_files = 0
            unstaged_files = 0

            if status_result.returncode == 0:
                for line in status_result.stdout.splitlines():
                    if not line or len(line) < 2:
                        continue
                    # 無視ファイルは "!!" で始まる
                    if line.startswith('!!'):
                        continue
                    staged_char = line[0]
                    unstaged_char = line[1]
                    if staged_char not in (' ', '?'):
                        staged_files += 1
                    if unstaged_char != ' ':
                        unstaged_files += 1

            return {
                'current_branch': current_branch,
                'staged_files': staged_files,
                'unstaged_files': unstaged_files
            }

        except Exception:
            logger.exception("リポジトリ状態の取得に失敗")
            return {
                'current_branch': "unknown",
                'staged_files': 0,
                'unstaged_files': 0
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
            # ファイル変更の検出(diff --git a/file b/file パターン)
            file_patterns = re.findall(r'^diff --git a/(.+?) b/(.+?)$', diff_content, re.MULTILINE)
            for _old_file, new_file in file_patterns:
                # /dev/null を除外し、重複をチェック
                if new_file != '/dev/null' and new_file not in files_changed:
                    files_changed.append(new_file)
                    file_count += 1

            # GIT binary patch の検出
            if re.search(r'^\s*GIT binary patch\b', diff_content, re.MULTILINE):
                is_binary_change = True

            # 追加/削除行数の計算(+/- で始まる行をカウント)
            lines = diff_content.splitlines()
            for line in lines:
                # バイナリファイルの変更を検出
                if "Binary files" in line and "differ" in line:
                    is_binary_change = True
                    continue

                # 差分の内容行のみカウント(ヘッダーやメタデータは除外)
                if line.startswith('+') and not line.startswith('+++'):
                    additions += 1
                elif line.startswith('-') and not line.startswith('---'):
                    deletions += 1

            # ファイル数が0の場合、他の方法で検出を試行
            if file_count == 0:
                # --- a/file と +++ b/file パターンも確認(/dev/null を除外)
                alt_old = re.findall(r'^--- a/(.+?)$', diff_content, re.MULTILINE)
                alt_new = re.findall(r'^\+\+\+ b/(.+?)$', diff_content, re.MULTILINE)
                files = {p for p in (alt_old + alt_new) if p != '/dev/null'}
                if files:
                    file_count = len(files)
                    files_changed = list(files)

            logger.debug(f"差分解析結果: {file_count}ファイル, {additions}+/{deletions}-, バイナリ: {is_binary_change}")

        except Exception as e:
            logger.warning(f"差分解析中にエラー(処理続行): {e}")

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

        # バイト単位で切り詰める（UTF-8/改行境界を優先）
        buf = diff.encode('utf-8')[:self.max_diff_size]
        truncated = buf.decode('utf-8', errors='ignore')
        nl = truncated.rfind('\n')
        if nl != -1:
            truncated = truncated[:nl + 1]
        return truncated + "... (diff truncated due to size limit)\n"

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

        # 最低限の条件: diffヘッダーまたはファイルヘッダーが存在
        return has_file_header or has_diff_header

    def _cached_format_diff(self, diff_hash: str, diff: str) -> str:
        """
        自前LRUキャッシュを使用した差分フォーマット処理

        Args:
            diff_hash: 差分のハッシュ値（キャッシュキーとして使用）
            diff: 差分内容

        Returns:
            フォーマットされた差分
        """
        with self._cache_lock:
            # キャッシュヒット確認
            if diff_hash in self._processing_cache:
                # LRU更新（最後に移動）
                value = self._processing_cache.pop(diff_hash)
                self._processing_cache[diff_hash] = value
                return value

            # キャッシュミス - 新しい値を計算
            result = self._format_diff_internal(diff)

            # キャッシュに保存
            self._processing_cache[diff_hash] = result

            # 容量制限チェック
            if len(self._processing_cache) > self._cache_maxsize:
                # 最古のエントリを削除
                self._processing_cache.popitem(last=False)

            return result

    def _format_diff_internal(self, diff: str) -> str:
        """
        内部的な差分フォーマット処理（キャッシュから呼び出される）

        Args:
            diff: 差分内容

        Returns:
            フォーマットされた差分
        """
        if not diff or not diff.strip():
            return "No changes detected"

        # 並行処理が有効な場合は並行フォーマットを使用
        executor = self._get_executor()
        if executor:
            return self._parallel_format_diff(diff)
        else:
            return self._sequential_format_diff(diff)

    def _sequential_format_diff(self, diff: str) -> str:
        """
        順次処理による差分フォーマット

        Args:
            diff: 差分内容

        Returns:
            フォーマットされた差分
        """
        diff_data = self._parse_diff(diff)
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

        # 実際の差分内容
        filtered_diff = self._filter_diff_content(diff)
        if filtered_diff:
            formatted_lines.append("Diff content:")
            formatted_lines.append(filtered_diff)

        return "\n".join(formatted_lines)

    def _parallel_format_diff(self, diff: str) -> str:
        """
        並行処理による差分フォーマット

        Args:
            diff: 差分内容

        Returns:
            フォーマットされた差分
        """
        # 大きな差分の場合のみ並行処理を使用
        if len(diff) < 10000:  # 10KB未満の場合は順次処理
            return self._sequential_format_diff(diff)

        # 差分解析とフィルタリングを並行実行
        executor = self._get_executor()
        future_parse = executor.submit(self._parse_diff, diff)
        future_filter = executor.submit(self._filter_diff_content, diff)

        try:
            # 結果を取得
            diff_data = future_parse.result(timeout=5.0)
            filtered_diff = future_filter.result(timeout=5.0)

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

            # 実際の差分内容
            if filtered_diff:
                formatted_lines.append("Diff content:")
                formatted_lines.append(filtered_diff)

            return "\n".join(formatted_lines)

        except Exception as e:
            logger.warning(f"並行処理エラー、順次処理にフォールバック: {e}")
            return self._sequential_format_diff(diff)

    def clear_cache(self):
        """
        キャッシュをクリア
        """
        with self._cache_lock:
            self._processing_cache.clear()
        logger.debug("キャッシュをクリアしました")

    def get_cache_info(self) -> Dict[str, Any]:
        """
        キャッシュ情報を取得

        Returns:
            キャッシュ統計情報
        """
        with self._cache_lock:
            return {
                'cache_size': len(self._processing_cache),
                'cache_maxsize': self._cache_maxsize,
            }

    def optimize_for_performance(self, diff: str) -> str:
        """
        パフォーマンス最適化された差分処理

        Args:
            diff: 差分内容

        Returns:
            最適化処理された差分
        """
        # 入力サイズに応じて処理方法を選択
        diff_size = len(diff.encode('utf-8'))

        if diff_size == 0:
            return "No changes detected"

        # 小さな差分は単純処理
        if diff_size < 1000:  # 1KB未満
            return self._sequential_format_diff(diff)

        # 中程度の差分はキャッシュを使用
        if diff_size < 50000:  # 50KB未満
            import hashlib
            diff_hash = hashlib.sha256(diff.encode('utf-8')).hexdigest()
            return self._cached_format_diff(diff_hash, diff)

        # 大きな差分は並行処理と切り詰めを使用
        truncated_diff = self._truncate_diff(diff)
        if self.enable_parallel_processing:
            return self._parallel_format_diff(truncated_diff)
        else:
            return self._sequential_format_diff(truncated_diff)

    def __del__(self):
        """
        デストラクタ - リソースクリーンアップ
        """
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=True)
