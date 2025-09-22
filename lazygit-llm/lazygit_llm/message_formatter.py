"""
メッセージフォーマッターモジュール

LLMが生成したコミットメッセージをLazyGit用に整形する。
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class MessageFormatter:
    """メッセージフォーマッタークラス"""
    
    def __init__(self, max_length: int = 500):
        """
        フォーマッターを初期化
        
        Args:
            max_length: 最大メッセージ長
        """
        self.max_length = max_length
    
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
            return "chore: update files"
        
        # 基本的なクリーニング
        cleaned = self._clean_message(raw_message)
        
        # コミットメッセージの抽出
        commit_message = self._extract_commit_message(cleaned)
        
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
        
        # 説明的なテキストを除去
        prefixes_to_remove = [
            'commit message:',
            'git commit -m',
            'suggested commit message:',
            'here is the commit message:',
            'commit:',
        ]
        
        for prefix in prefixes_to_remove:
            pattern = re.compile(rf'^{re.escape(prefix)}\s*', re.IGNORECASE)
            message = pattern.sub('', message)
        
        # 引用符を除去
        message = message.strip().strip('"').strip("'").strip('`')
        
        # 最初の行を取得（複数行の場合）
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
        
        # 単語境界で切り詰め
        truncated = message[:self.max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > self.max_length * 0.7:  # 70%以上の位置に空白がある場合
            truncated = truncated[:last_space]
        
        # 末尾の句読点を除去して省略記号を追加
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
        
        # 不正な文字のチェック（制御文字）
        if any(ord(c) < 0x20 and c not in '\n\t' for c in message):
            return False
        
        return True