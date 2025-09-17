"""
メッセージフォーマッターシステム

LLMからの生のレスポンスをクリーンアップし、LazyGitとの統合に適した形式にフォーマットする。
"""

import re
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
import threading

logger = logging.getLogger(__name__)


class MessageFormatter:
    """
    メッセージフォーマッタークラス

    LLMからの生のレスポンスをクリーンアップし、
    LazyGitで表示するのに適した形式に整形する。
    """

    def __init__(self, max_message_length: int = 500, enable_caching: bool = True):
        """
        メッセージフォーマッターを初期化

        Args:
            max_message_length: メッセージの最大長（文字数）
            enable_caching: キャッシュを有効にするかどうか
        """
        self.max_message_length = max_message_length
        self.enable_caching = enable_caching
        self._cache_lock = threading.Lock()
        self._processing_stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    def format_response(self, raw_response: str) -> str:
        """
        LLMからの生レスポンスをフォーマット

        Args:
            raw_response: LLMからの生レスポンス

        Returns:
            フォーマット済みのコミットメッセージ

        Raises:
            ValueError: レスポンスが空または無効な場合
        """
        if not raw_response:
            raise ValueError("空のレスポンスです")

        try:
            # 基本的なクリーニング
            cleaned_message = self.clean_message(raw_response)

            # メッセージの妥当性検証
            if not self.validate_message_format(cleaned_message):
                logger.warning("生成されたメッセージの形式が無効です")
                # 無効な場合でも使用可能な形に修正を試行
                cleaned_message = self._fix_invalid_message(cleaned_message)

            # 最終フォーマット
            formatted_message = self._apply_final_formatting(cleaned_message)

            logger.debug(f"メッセージフォーマット完了: {len(formatted_message)}文字")
            return formatted_message

        except Exception as e:
            logger.error(f"メッセージフォーマットエラー: {e}")
            # エラー時はクリーンアップのみ適用
            return self.clean_message(raw_response)

    def clean_message(self, message: str) -> str:
        """
        メッセージの基本的なクリーニング

        Args:
            message: クリーニング対象のメッセージ

        Returns:
            クリーンアップされたメッセージ
        """
        if not message:
            return ""

        # 前後の空白を除去
        cleaned = message.strip()

        # 複数の連続する空白行を単一の空白行に
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)

        # 行末の空白を除去
        lines = [line.rstrip() for line in cleaned.split('\n')]
        cleaned = '\n'.join(lines)

        # LLM特有の不要なテキストを除去
        cleaned = self._remove_llm_artifacts(cleaned)

        # 引用符で囲まれている場合は除去
        cleaned = self._remove_quotes(cleaned)

        # 長すぎる場合は切り詰め
        if len(cleaned) > self.max_message_length:
            cleaned = self._truncate_message(cleaned)

        return cleaned.strip()

    def validate_message_format(self, message: str) -> bool:
        """
        コミットメッセージの形式を検証

        Args:
            message: 検証するメッセージ

        Returns:
            形式が有効な場合True
        """
        if not message or not message.strip():
            return False

        # 基本的な長さチェック
        if len(message) > self.max_message_length:
            return False

        # 極端に短いメッセージもチェック
        if len(message.strip()) < 3:
            return False

        # 改行が多すぎる場合は無効
        line_count = len(message.split('\n'))
        if line_count > 5:
            return False

        # 特殊文字のチェック（制御文字など）
        if any(ord(char) < 32 and char not in '\n\t' for char in message):
            return False

        return True

    def _remove_llm_artifacts(self, message: str) -> str:
        """
        LLM特有の不要なテキストを除去

        Args:
            message: 処理対象のメッセージ

        Returns:
            アーティファクトが除去されたメッセージ
        """
        # よくあるLLMの前置き・後置きテキストのパターン
        artifacts_patterns = [
            r'^(Here is|Here\'s|Based on|Looking at|Analyzing|I would suggest|I recommend).*?:?\s*',
            r'^(commit message|コミットメッセージ):\s*',
            r'\s*(no additional text|以上です|以下の通りです|以下のようになります)\.?\s*$',
            r'```[a-zA-Z]*\n?',  # コードブロック記法
            r'^git commit -m\s*["\']?|["\']?\s*$',  # git commit コマンド
        ]

        cleaned = message
        for pattern in artifacts_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)

        return cleaned.strip()

    def _remove_quotes(self, message: str) -> str:
        """
        メッセージを囲む引用符を除去

        Args:
            message: 処理対象のメッセージ

        Returns:
            引用符が除去されたメッセージ
        """
        # 全体を囲む引用符を除去
        if len(message) >= 2:
            # ダブルクォート
            if message.startswith('"') and message.endswith('"'):
                message = message[1:-1]
            # シングルクォート
            elif message.startswith("'") and message.endswith("'"):
                message = message[1:-1]
            # バッククォート
            elif message.startswith("`") and message.endswith("`"):
                message = message[1:-1]

        return message.strip()

    def _truncate_message(self, message: str) -> str:
        """
        長すぎるメッセージを切り詰め

        Args:
            message: 切り詰め対象のメッセージ

        Returns:
            切り詰められたメッセージ
        """
        if len(message) <= self.max_message_length:
            return message

        # 最初の行（コミットメッセージのタイトル）を優先的に保持
        lines = message.split('\n')
        first_line = lines[0]

        # 最初の行が既に長すぎる場合
        if len(first_line) > self.max_message_length - 3:
            return first_line[:self.max_message_length - 3] + "..."

        # 最初の行 + 可能な限りの追加行
        result_lines = [first_line]
        remaining_length = self.max_message_length - len(first_line) - 3  # "..."分

        for line in lines[1:]:
            if len('\n'.join(result_lines + [line])) <= remaining_length:
                result_lines.append(line)
            else:
                break

        # 切り詰めた場合は"..."を追加
        if len(result_lines) < len(lines):
            return '\n'.join(result_lines) + "\n..."
        else:
            return '\n'.join(result_lines)

    def _fix_invalid_message(self, message: str) -> str:
        """
        無効なメッセージを可能な限り修正

        Args:
            message: 修正対象のメッセージ

        Returns:
            修正されたメッセージ
        """
        if not message or not message.strip():
            return "Update files"  # デフォルトメッセージ

        # 制御文字を除去（改行とタブ以外）
        fixed = ''.join(char for char in message if ord(char) >= 32 or char in '\n\t')

        # 極端に短い場合は補完
        if len(fixed.strip()) < 3:
            if 'fix' in fixed.lower():
                return "Fix issues"
            elif 'add' in fixed.lower():
                return "Add features"
            elif 'update' in fixed.lower():
                return "Update files"
            else:
                return "Update code"

        return fixed

    def _apply_final_formatting(self, message: str) -> str:
        """
        最終フォーマットを適用

        Args:
            message: フォーマット対象のメッセージ

        Returns:
            最終フォーマット済みメッセージ
        """
        # 最終的な空白の正規化
        formatted = re.sub(r'\s+', ' ', message.replace('\n', ' ').strip())

        # 最初の文字を大文字に（英語の場合）
        if formatted and formatted[0].islower() and formatted[0].isalpha():
            formatted = formatted[0].upper() + formatted[1:]

        # 末尾のピリオドを除去（コミットメッセージの慣習）
        if formatted.endswith('.'):
            formatted = formatted[:-1]

        return formatted

    def extract_commit_message(self, response: str) -> str:
        """
        レスポンスからコミットメッセージ部分のみを抽出

        Args:
            response: LLMからのレスポンス

        Returns:
            抽出されたコミットメッセージ
        """
        # 複数行の場合、最初の有効な行を抽出
        lines = [line.strip() for line in response.split('\n') if line.strip()]

        if not lines:
            return "Update files"

        # 最初の意味のある行を返す
        for line in lines:
            # コメント行や説明行をスキップ
            if (not line.startswith('#') and
                not line.startswith('//') and
                not line.lower().startswith('commit message:') and
                len(line) >= 3):
                return line

        # 適切な行が見つからない場合は最初の行を返す
        return lines[0] if lines else "Update files"

    @lru_cache(maxsize=256)
    def _cached_clean_message(self, message_hash: str, message: str) -> str:
        """
        LRUキャッシュを使用したメッセージクリーニング

        Args:
            message_hash: メッセージのハッシュ値（キャッシュキーとして使用）
            message: クリーニング対象のメッセージ

        Returns:
            クリーニング済みメッセージ
        """
        with self._cache_lock:
            self._processing_stats['total_processed'] += 1

        return self._clean_message_internal(message)

    def _clean_message_internal(self, message: str) -> str:
        """
        内部的なメッセージクリーニング処理

        Args:
            message: クリーニング対象のメッセージ

        Returns:
            クリーニング済みメッセージ
        """
        # 基本的なクリーニング
        cleaned = self.clean_llm_response(message)

        # LLMアーティファクトの除去
        cleaned = self._remove_llm_artifacts(cleaned)

        # サイズ制限の適用
        if len(cleaned) > self.max_message_length:
            cleaned = self._truncate_message(cleaned)

        return cleaned

    def optimize_for_performance(self, raw_response: str) -> str:
        """
        パフォーマンス最適化されたメッセージフォーマット

        Args:
            raw_response: LLMからの生レスポンス

        Returns:
            最適化処理されたメッセージ
        """
        if not raw_response:
            raise ValueError("空のレスポンスです")

        # メッセージサイズに応じて処理方法を選択
        message_size = len(raw_response)

        # 小さなメッセージは単純処理
        if message_size < 100:
            return self._clean_message_internal(raw_response)

        # 中程度のメッセージはキャッシュを使用
        if message_size < 2000 and self.enable_caching:
            import hashlib
            message_hash = hashlib.md5(raw_response.encode('utf-8')).hexdigest()
            with self._cache_lock:
                self._processing_stats['cache_hits'] += 1
            return self._cached_clean_message(message_hash, raw_response)

        # 大きなメッセージは段階的処理
        with self._cache_lock:
            self._processing_stats['cache_misses'] += 1

        # 段階的クリーニング
        # 1. 基本的なクリーニング
        cleaned = self.clean_llm_response(raw_response)

        # 2. 早期切り詰め（必要な場合）
        if len(cleaned) > self.max_message_length * 2:
            cleaned = cleaned[:self.max_message_length * 2]

        # 3. LLMアーティファクトの除去
        cleaned = self._remove_llm_artifacts(cleaned)

        # 4. 最終的なサイズ調整
        if len(cleaned) > self.max_message_length:
            cleaned = self._truncate_message(cleaned)

        return cleaned

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        処理統計情報を取得

        Returns:
            処理統計情報
        """
        with self._cache_lock:
            stats = self._processing_stats.copy()

        if self.enable_caching:
            cache_info = self._cached_clean_message.cache_info()
            stats.update({
                'cache_hits': cache_info.hits,
                'cache_misses': cache_info.misses,
                'cache_size': cache_info.currsize,
                'cache_maxsize': cache_info.maxsize
            })

        return stats

    def clear_cache(self):
        """
        キャッシュをクリア
        """
        if self.enable_caching:
            self._cached_clean_message.cache_clear()

        with self._cache_lock:
            self._processing_stats = {
                'total_processed': 0,
                'cache_hits': 0,
                'cache_misses': 0
            }

        logger.debug("メッセージフォーマッターのキャッシュをクリアしました")

    def bulk_format_messages(self, messages: List[str]) -> List[str]:
        """
        複数メッセージの一括フォーマット（最適化版）

        Args:
            messages: フォーマット対象のメッセージリスト

        Returns:
            フォーマット済みメッセージリスト
        """
        if not messages:
            return []

        formatted_messages = []

        # 小さなバッチはシーケンシャル処理
        if len(messages) < 10:
            for message in messages:
                formatted_messages.append(self.optimize_for_performance(message))
            return formatted_messages

        # 大きなバッチは効率的な処理
        for message in messages:
            try:
                formatted = self.optimize_for_performance(message)
                formatted_messages.append(formatted)
            except Exception as e:
                logger.warning(f"メッセージフォーマットエラー: {e}")
                formatted_messages.append("Update files")  # フォールバック

        return formatted_messages

    def optimize_memory_usage(self):
        """
        メモリ使用量を最適化
        """
        # キャッシュサイズを調整
        if self.enable_caching:
            cache_info = self._cached_clean_message.cache_info()
            if cache_info.currsize > cache_info.maxsize * 0.8:
                # キャッシュが80%以上埋まっている場合は部分的にクリア
                self._cached_clean_message.cache_clear()
                logger.debug("メモリ最適化のためキャッシュを部分的にクリアしました")

        # 統計情報のリセット
        with self._cache_lock:
            if self._processing_stats['total_processed'] > 10000:
                self._processing_stats = {
                    'total_processed': 0,
                    'cache_hits': 0,
                    'cache_misses': 0
                }