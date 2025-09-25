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
        # 最初にマークダウンのコードブロックを除去
        message = re.sub(r'```[\s\S]*?```', '', message)

        # 前置き文言を引用符処理より先に除去
        prefix_patterns = [
            r'git\s+commit\s+-m',
            r'(?:suggested\s+)?commit\s+(?:message|messages|msg)\s*[:\-]',
            r'commit\s*[:\-]',
            r'(?:here\s+is\s+(?:the\s+)?)?commit\s+message\s*[:\-]',
            r'(?:here\s+is\s+your\s+)?commit\s+message\s*[:\-]',
            r'generated\s+commit\s+message\s*[:\-]',
            r'suggested\s+message\s*[:\-]',
            r'コミット(?:メッセージ)?\s*[:\-]'
        ]

        for pattern in prefix_patterns:
            message = re.sub(f'^\\s*{pattern}\\s*', '', message, count=1, flags=re.IGNORECASE)

        # インラインコードの除去は引用符処理後に実行
        # （バッククォート引用符との競合を避けるため）

        # 引用符の除去（前置き文言除去後に実施）
        message = message.strip()

        # 三重引用符の処理（最優先）
        triple_quotes = ['"""', "'''"]
        for quote in triple_quotes:
            if message.startswith(quote) and message.endswith(quote) and len(message) > len(quote) * 2:
                message = message[len(quote):-len(quote)].strip()
                break
        else:
            # 通常の引用符処理（対になったもの＋部分的な非対称引用符対応）
            quote_pairs = [
                ('"', '"'), ("'", "'"), ('`', '`'),
                ('「', '」'), ('『', '』')
            ]

            # 1. 完全対称引用符の処理
            for start_quote, end_quote in quote_pairs:
                if (message.startswith(start_quote) and message.endswith(end_quote)
                    and len(message) > len(start_quote) + len(end_quote)):
                    message = message[len(start_quote):-len(end_quote)].strip()
                    # 引用符内の改行とタブを空白に変換
                    message = message.replace('\n', ' ').replace('\t', ' ')
                    message = re.sub(r' +', ' ', message).strip()
                    break
            else:
                # 2. 非対称引用符の部分対応（開始引用符のみ除去）
                for start_quote, _ in quote_pairs:
                    if message.startswith(start_quote) and len(message) > len(start_quote):
                        # 開始引用符を除去し、末尾の異なる引用符もチェック
                        temp_message = message[len(start_quote):]
                        for _, end_quote in quote_pairs:
                            if temp_message.endswith(end_quote) and len(temp_message) > len(end_quote):
                                message = temp_message[:-len(end_quote)].strip()
                                # 非対称引用符処理でも改行とタブを空白に変換
                                message = message.replace('\n', ' ').replace('\t', ' ')
                                message = re.sub(r' +', ' ', message).strip()
                                break
                        else:
                            message = temp_message.strip()
                            # 非対称引用符処理でも改行とタブを空白に変換
                            message = message.replace('\n', ' ').replace('\t', ' ')
                            message = re.sub(r' +', ' ', message).strip()
                        break

        # 引用符処理後にインラインコードを除去
        message = re.sub(r'`[^`]*`', '', message)

        # 改行の正規化（行分割準備）
        message = re.sub(r'\n\s*\n', '\n', message)
        message = re.sub(r'\n+', '\n', message).strip()

        # 前置き文言の除去は既に上で実行済み

        # 改行で区切られた行を処理
        lines = [line.strip() for line in message.split('\n') if line.strip()]

        if not lines:
            # すべてのコンテンツが除去された場合は空文字を返す
            return ""

        # 最も意味のありそうな行を選択
        best_line = ""
        best_score = 0

        for line in lines:
            score = 0
            # プレフィックスが残っていないかチェック
            clean_line = line
            for pattern in prefix_patterns:
                old_line = clean_line
                clean_line = re.sub(f'^\\s*{pattern}\\s*', '', clean_line, count=1, flags=re.IGNORECASE)
                if clean_line != old_line:
                    score += 10  # プレフィックスが除去された行は高スコア

            # 長さによるスコアリング（短すぎず長すぎないものを優先）
            if len(clean_line) >= 10:
                score += 5
            elif len(clean_line) >= 5:
                score += 2

            # コロン文字を含む行は説明文である可能性が高いので減点
            if ':' in clean_line:
                score -= 3

            # 実際のコミットメッセージっぽい単語があるかチェック
            commit_words = ['add', 'fix', 'update', 'remove', 'refactor', 'feat', 'chore', 'docs']
            if any(word in clean_line.lower() for word in commit_words):
                score += 3

            if score > best_score:
                best_score = score
                best_line = clean_line

        # 最高スコアの行があれば、それが複数の文を含んでいるかチェック
        if best_line:
            # タブと空白の正規化を実行
            best_line = best_line.replace('\t', ' ')
            best_line = re.sub(r' +', ' ', best_line).strip()

            # 句読点で分割して最初の文を取得
            sentence_match = re.match(r'^([^.!?]*[.!?])', best_line)
            if sentence_match:
                result = sentence_match.group(1).strip()
                # タブと空白の正規化を再実行
                result = result.replace('\t', ' ')
                result = re.sub(r' +', ' ', result).strip()
                return result
            else:
                return best_line

        # フォールバック：最初の行
        if lines:
            first_line = lines[0]
            # タブと空白の正規化を実行
            first_line = first_line.replace('\t', ' ')
            first_line = re.sub(r' +', ' ', first_line).strip()

            # 句読点で分割して最初の文を取得
            sentence_match = re.match(r'^([^.!?]*[.!?])', first_line)
            if sentence_match:
                result = sentence_match.group(1).strip()
                # タブと空白の正規化を再実行
                result = result.replace('\t', ' ')
                result = re.sub(r' +', ' ', result).strip()
                return result
            else:
                return first_line

        # フォールバック: 全体から最初の文を抽出
        # 句読点で文を分割
        sentence_match = re.match(r'^([^.!?]*[.!?])', message)
        if sentence_match:
            return sentence_match.group(1).strip()

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

        limit = self.max_length - 3  # "..." 分を確保
        truncated = message[:limit]

        # 単語境界での切り詰めを試行
        last_space = truncated.rfind(' ')

        # 70%以上の位置に空白がある場合は単語境界で切り詰め
        if last_space > int(limit * 0.7):
            truncated = truncated[:last_space]
            # さらに確実に単語境界で終わることを保証
            truncated = truncated.rstrip()

        # 末尾の句読点と空白を除去（ただし単語境界を保持）
        original_truncated = truncated
        truncated = truncated.rstrip('.,!?;: ')

        # 句読点除去後に英数字で終わる場合は、前の空白まで戻す
        if truncated and truncated[-1].isalnum():
            # 最後の空白位置を探して、そこまで戻す
            last_space = original_truncated.rfind(' ')
            if last_space >= 0:  # 空白が見つかった場合
                # 空白位置で切って、末尾に空白を残す（rstripしない）
                truncated = original_truncated[:last_space + 1]
            else:
                # 空白が見つからない場合は、最初の非英数字文字まで戻す
                for i in range(len(original_truncated) - 1, -1, -1):
                    if not original_truncated[i].isalnum():
                        truncated = original_truncated[:i + 1]
                        break
                else:
                    # すべて英数字の場合は、安全な長さで切り詰め
                    safe_length = min(len(original_truncated) - 5, limit - 10)
                    truncated = original_truncated[:safe_length] + ' '

        truncated += '...'

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
