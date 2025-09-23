"""
メッセージフォーマッターモジュール

LLMが生成したコミットメッセージをLazyGit用に整形する。
"""

import re
import logging

logger = logging.getLogger(__name__)


class MessageFormatter:
    """メッセージフォーマッタークラス"""

    def __init__(self, max_length: int = 500, default_message: str = "chore: update files"):
        """
        フォーマッターを初期化

        Args:
            max_length: 最大メッセージ長
            default_message: 空入力の場合のデフォルトメッセージ

        Raises:
            ValueError: max_lengthが無効な値の場合
        """
        if not isinstance(max_length, int) or max_length < 1:
            raise ValueError("max_length must be an integer >= 1")

        self.max_length = max_length
        self.default_message = default_message

    def format_response(self, raw_message: str) -> str:
        """
        LLMの生成メッセージをフォーマットする

        Args:
            raw_message: LLMが生成した生メッセージ

        Returns:
            フォーマット済みのコミットメッセージ
        """
        if not raw_message or not raw_message.strip():
            logger.warning("空のメッセージを受信しました")
            return self._apply_length_limit(self.default_message)

        # 基本的なクリーニング
        cleaned = self._clean_message(raw_message)

        # コミットメッセージの抽出
        commit_message = self._extract_commit_message(cleaned)

        # 抽出後に空の場合はデフォルトへフォールバック
        if not commit_message or not commit_message.strip():
            logger.warning("抽出後のメッセージが空のためデフォルトにフォールバックします")
            return self._apply_length_limit(self.default_message)

        # 長さ制限の適用
        final_message = self._apply_length_limit(commit_message)

        logger.debug("メッセージをフォーマットしました: '%s'", final_message)
        return final_message

    def _clean_message(self, message: str) -> str:
        """
        メッセージの基本的なクリーニングを行う

        Args:
            message: 元のメッセージ

        Returns:
            クリーニング済みメッセージ
        """
        # 先頭・末尾の空白を削除
        cleaned = message.strip()

        # 改行をLFに正規化
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

        # 複数の改行を単一の改行に変換
        cleaned = re.sub(r'\n+', '\n', cleaned)

        # タブを空白に変換
        cleaned = cleaned.replace('\t', ' ')

        # 複数の空白を単一の空白に変換
        cleaned = re.sub(r' +', ' ', cleaned)

        return cleaned

    def _extract_commit_message(self, message: str) -> str:
        """
        メッセージからコミットメッセージ部分を抽出する

        Args:
            message: クリーニング済みメッセージ

        Returns:
            抽出されたコミットメッセージ
        """
        # マークダウンのコードブロックを除去
        message = re.sub(r'```[\s\S]*?```', '', message)

        # 代表的な前置き文言を包括的に除去（英日・表記ゆれ対応）
        prefix_pattern = re.compile(
            r'^\s*(?:'
            r'git\s+commit\s+-m|'
            r'(?:suggested\s+)?commit\s+(?:message|messages|msg)\s*[:\-]|'
            r'commit\s*[:\-]|'
            r'(?:here\s+is\s+the\s+)?commit\s+message\s*[:\-]|'
            r'コミット(?:メッセージ)?\s*[:\-]'
            r')\s*',
            re.IGNORECASE,
        )
        message = prefix_pattern.sub('', message, count=1)

        # 引用符（ASCII/Unicode/日本語）を除去
        message = message.strip().strip('"\u201C\u201D\'\u2018\u2019`\u300C\u300D\u300E\u300F')

        # 最初の行を取得(複数行の場合)
        first_line = message.split('\n')[0].strip()

        if first_line:
            return first_line

        # フォールバック: 全体から最初の文を抽出
        sentences = re.split(r'[.!?]\s+', message)
        if sentences and sentences[0].strip():
            return sentences[0].strip()

        return message.strip()

    def _apply_length_limit(self, message: str) -> str:
        """
        メッセージに長さ制限を適用する

        Args:
            message: フォーマット済みメッセージ

        Returns:
            長さ制限が適用されたメッセージ
        """
        if len(message) <= self.max_length:
            return message

        # 省略記号分を確保（上限3未満はそのまま切り取り）
        if self.max_length <= 3:
            return message[:self.max_length]
        limit = self.max_length - 3
        truncated = message[:limit]
        last_space = truncated.rfind(' ')

        if last_space > int(limit * 0.7):  # 70%以上の位置に空白がある場合
            truncated = truncated[:last_space]

        # 末尾の句読点を除去して省略記号を追加(最終長は必ず self.max_length 以下)
        truncated = truncated.rstrip('.,!?;:').rstrip() + '...'

        logger.warning("メッセージが長すぎるため切り詰めました: %d -> %d文字",
                      len(message), len(truncated))

        return truncated

    def validate_message(self, message: str) -> bool:
        """
        コミットメッセージの妥当性を検証する

        Args:
            message: 検証するメッセージ

        Returns:
            メッセージが有効な場合True
        """
        if not message or not message.strip():
            return False

        # 最小長チェック
        if len(message.strip()) < 3:
            return False

        # 最大長チェック（任意）
        if len(message) > self.max_length:
            return False

        # 不正な文字のチェック(制御文字)
        if any(ord(c) < 0x20 and c not in '\n\t' for c in message):
            return False

        return True
