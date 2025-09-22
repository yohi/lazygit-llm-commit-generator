"""
Git差分処理モジュール

ステージ済みの変更を取得・処理する。
"""

import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GitDiffProcessor:
    """Git差分処理クラス"""
    
    def has_staged_changes(self) -> bool:
        """
        ステージ済みの変更があるかチェックする
        
        Returns:
            ステージ済みの変更がある場合True
        """
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached', '--quiet'],
                capture_output=True,
                text=True,
                timeout=10
            )
            # git diff --quiet は変更がある場合は1、ない場合は0を返す
            has_changes = result.returncode != 0
            logger.debug("ステージ済み変更チェック: %s", has_changes)
            return has_changes
            
        except subprocess.TimeoutExpired:
            logger.error("git diff --cached --quiet がタイムアウトしました")
            return False
        except FileNotFoundError:
            logger.error("gitコマンドが見つかりません")
            return False
        except Exception as e:
            logger.error("ステージ済み変更のチェックに失敗: %s", e)
            return False
    
    def read_staged_diff(self) -> str:
        """
        ステージ済みの差分を取得する
        
        Returns:
            Git差分の文字列
            
        Raises:
            subprocess.SubprocessError: gitコマンド実行エラー
        """
        try:
            result = subprocess.run(
                ['git', 'diff', '--cached'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = f"git diff --cached が失敗しました: {result.stderr}"
                logger.error(error_msg)
                raise subprocess.SubprocessError(error_msg)
            
            diff_output = result.stdout.strip()
            logger.debug("Git差分を取得しました (%d文字)", len(diff_output))
            
            return diff_output
            
        except subprocess.TimeoutExpired:
            error_msg = "git diff --cached がタイムアウトしました"
            logger.error(error_msg)
            raise subprocess.SubprocessError(error_msg)
        except FileNotFoundError:
            error_msg = "gitコマンドが見つかりません"
            logger.error(error_msg)
            raise subprocess.SubprocessError(error_msg)
    
    def get_repository_status(self) -> dict:
        """
        リポジトリの状態を取得する
        
        Returns:
            リポジトリの状態辞書
        """
        try:
            # ブランチ名を取得
            branch_result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=10
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            # ステージ済み/未ステージファイル数を取得
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            staged_files = 0
            unstaged_files = 0
            
            if status_result.returncode == 0:
                for line in status_result.stdout.split('\\n'):
                    if len(line.strip()) >= 2:
                        staged_char = line[0]
                        unstaged_char = line[1]
                        
                        if staged_char != ' ' and staged_char != '?':
                            staged_files += 1
                        if unstaged_char != ' ':
                            unstaged_files += 1
            
            return {
                'current_branch': current_branch,
                'staged_files': staged_files,
                'unstaged_files': unstaged_files
            }
            
        except Exception as e:
            logger.error("リポジトリ状態の取得に失敗: %s", e)
            return {
                'current_branch': "unknown",
                'staged_files': 0,
                'unstaged_files': 0
            }