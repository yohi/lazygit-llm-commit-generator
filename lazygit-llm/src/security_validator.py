"""
セキュリティ・バリデーション機能

APIキー検証、入力サニタイゼーション、セキュリティポリシー確認を提供。
機密情報の保護とシステムの安全性を確保。
"""

import re
import hashlib
import logging
import os
import stat
from typing import Dict, Any, Optional, List, Tuple, ClassVar
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SecurityCheckResult:
    """セキュリティチェック結果"""
    is_valid: bool
    level: str  # "safe", "warning", "danger"
    message: str
    recommendations: List[str]


class SecurityValidator:
    """
    セキュリティバリデータークラス

    APIキー検証、入力サニタイゼーション、ファイル権限チェック等の
    セキュリティ機能を統合的に提供。
    """

    # APIキーのパターン定義
    API_KEY_PATTERNS: ClassVar[Dict[str, Dict[str, Any]]] = {
        'openai': {
            'pattern': r'^sk-[A-Za-z0-9]{48}$',
            'min_length': 51,
            'max_length': 51,
            'description': 'OpenAI API key (sk-...)'
        },
        'anthropic': {
            'pattern': r'^sk-ant-[A-Za-z0-9\-_]{95,}$',
            'min_length': 100,
            'max_length': 200,
            'description': 'Anthropic API key (sk-ant-...)'
        },
        'gemini': {
            'pattern': r'^AIza[A-Za-z0-9\-_]{35}$',
            'min_length': 39,
            'max_length': 39,
            'description': 'Google API key (AIza...)'
        }
    }

    # 危険な文字パターン
    DANGEROUS_PATTERNS: ClassVar[List[str]] = [
        r'[`$\\|&;()<>]',  # シェルインジェクション
        r'[{}[\]]',        # コードインジェクション
        r'["\']',          # クォートインジェクション
        r'[\x00-\x1f]',    # 制御文字
        r'\.\./',          # パストラバーサル
        r'<script',        # XSS
        r'javascript:',    # JavaScript URI
        r'data:',          # Data URI
    ]

    # 機密情報パターン
    SENSITIVE_PATTERNS: ClassVar[List[str]] = [
        r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]?([^\s\'"]{8,})',
        r'(?i)(secret|token|key)\s*[:=]\s*[\'"]?([^\s\'"]{16,})',
        r'(?i)(api[_-]?key)\s*[:=]\s*[\'"]?([^\s\'"]{20,})',
        r'[A-Za-z0-9+/]{64,}={0,2}',  # Base64エンコード
        r'[0-9a-fA-F]{32,}',          # Hexエンコード
    ]

    def __init__(self):
        """セキュリティバリデーターを初期化"""
        self.max_input_size = 1024 * 1024  # 1MB
        self.max_diff_size = 500 * 1024    # 500KB

    def validate_api_key(self, provider: str, api_key: str, expose_details: bool = False) -> SecurityCheckResult:
        """
        APIキーを安全に検証（キー内容を露出しない）

        Args:
            provider: プロバイダー名
            api_key: 検証するAPIキー
            expose_details: 詳細情報を公開するかどうか

        Returns:
            セキュリティチェック結果
        """
        if not api_key:
            return SecurityCheckResult(
                is_valid=False,
                level="danger",
                message="APIキーが設定されていません",
                recommendations=[
                    "設定ファイルでAPIキーを設定してください",
                    f"{provider.upper()}_API_KEY 環境変数を設定してください"
                ]
            )

        # 基本的な長さチェック
        if len(api_key) < 10:
            return SecurityCheckResult(
                is_valid=False,
                level="danger",
                message="APIキーが短すぎます",
                recommendations=[
                    "正しいAPIキーが設定されているか確認してください",
                    "APIキーに不正な文字が含まれていないか確認してください"
                ]
            )

        # プロバイダー固有の検証
        pattern_info = self.API_KEY_PATTERNS.get(provider.lower())
        if pattern_info:
            # パターンマッチング
            if not re.match(pattern_info['pattern'], api_key):
                return SecurityCheckResult(
                    is_valid=False,
                    level="warning",
                    message=f"{pattern_info['description']}の形式に一致しません",
                    recommendations=[
                        f"正しい{provider} APIキーを設定してください",
                        "APIキーをコピー&ペーストする際の文字化けを確認してください"
                    ]
                )

            # 長さチェック
            if not (pattern_info['min_length'] <= len(api_key) <= pattern_info['max_length']):
                return SecurityCheckResult(
                    is_valid=False,
                    level="warning",
                    message="APIキーの長さが期待値と異なります",
                    recommendations=[
                        "APIキーが完全にコピーされているか確認してください",
                        "APIキーに余分な文字が含まれていないか確認してください"
                    ]
                )

        # セキュリティ強度チェック
        strength_result = self._check_api_key_strength(api_key, expose_details)
        if not strength_result.is_valid:
            return strength_result

        # APIキーハッシュを生成（ログ用、元のキーは記録しない）
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
        logger.info(f"APIキー検証成功: provider={provider}, hash={key_hash}")

        return SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="APIキーの形式は有効です",
            recommendations=[]
        )

    def sanitize_git_diff(self, diff_content: str) -> Tuple[str, SecurityCheckResult]:
        """
        Git差分内容をサニタイゼーション

        Args:
            diff_content: サニタイゼーション対象の差分

        Returns:
            (サニタイゼーション済み差分, セキュリティチェック結果)
        """
        if not diff_content:
            return "", SecurityCheckResult(
                is_valid=True,
                level="safe",
                message="空の差分",
                recommendations=[]
            )

        original_size = len(diff_content)

        # サイズ制限チェック
        if original_size > self.max_diff_size:
            diff_content = diff_content[:self.max_diff_size]
            logger.warning(f"差分サイズが制限を超過、切り詰めました: {original_size} -> {len(diff_content)}")

        # 機密情報の検出
        sensitive_check = self._detect_sensitive_content(diff_content)
        if not sensitive_check.is_valid:
            return "", sensitive_check

        # 危険なパターンの検出と除去
        sanitized_diff, danger_check = self._remove_dangerous_patterns(diff_content)

        # バイナリコンテンツの検出
        if self._contains_binary_content(sanitized_diff):
            return "(Binary content detected and filtered)", SecurityCheckResult(
                is_valid=True,
                level="safe",
                message="バイナリコンテンツを検出し、フィルタリングしました",
                recommendations=[]
            )

        final_check_result = SecurityCheckResult(
            is_valid=True,
            level=danger_check.level,
            message=f"差分のサニタイゼーション完了 ({len(sanitized_diff)}文字)",
            recommendations=danger_check.recommendations
        )

        logger.debug(f"Git差分サニタイゼーション完了: {original_size} -> {len(sanitized_diff)} 文字")
        return sanitized_diff, final_check_result

    def check_file_permissions(self, file_path: str) -> SecurityCheckResult:
        """
        ファイル権限をチェック

        Args:
            file_path: チェック対象ファイルのパス

        Returns:
            セキュリティチェック結果
        """
        path = Path(file_path)

        if not path.exists():
            return SecurityCheckResult(
                is_valid=False,
                level="danger",
                message="ファイルが存在しません",
                recommendations=[f"ファイルを作成してください: {file_path}"]
            )

        try:
            # ファイル権限を取得
            file_stat = path.stat()
            permissions = oct(file_stat.st_mode)[-3:]

            # 理想的な権限（600: 所有者のみ読み書き）
            if permissions == '600':
                return SecurityCheckResult(
                    is_valid=True,
                    level="safe",
                    message="ファイル権限は安全です",
                    recommendations=[]
                )

            # 警告レベルの権限
            elif permissions in ['644', '640']:
                return SecurityCheckResult(
                    is_valid=True,
                    level="warning",
                    message=f"ファイル権限が緩いです: {permissions}",
                    recommendations=[
                        f"chmod 600 {file_path} で権限を制限することをお勧めします",
                        "機密情報を含むファイルは所有者のみアクセス可能にしてください"
                    ]
                )

            # 危険レベルの権限
            else:
                return SecurityCheckResult(
                    is_valid=False,
                    level="danger",
                    message=f"ファイル権限が危険です: {permissions}",
                    recommendations=[
                        f"chmod 600 {file_path} で権限を制限してください",
                        "機密情報へのアクセスを制限してください"
                    ]
                )

        except (OSError, PermissionError, FileNotFoundError) as e:
            logger.exception("ファイル権限チェックエラー")
            return SecurityCheckResult(
                is_valid=False,
                level="warning",
                message="ファイル権限を確認できませんでした",
                recommendations=[
                    "ファイルのアクセス権限を手動で確認してください",
                    "ls -la コマンドでファイル権限を確認してください"
                ]
            )

    def validate_input_size(self, input_data: str, input_type: str = "general") -> SecurityCheckResult:
        """
        入力データのサイズを検証

        Args:
            input_data: 検証対象のデータ
            input_type: 入力タイプ（"general", "diff", "prompt"）

        Returns:
            セキュリティチェック結果
        """
        if not input_data:
            return SecurityCheckResult(
                is_valid=True,
                level="safe",
                message="空の入力",
                recommendations=[]
            )

        data_size = len(input_data.encode('utf-8'))

        # タイプ別のサイズ制限
        size_limits = {
            "general": 1024 * 1024,     # 1MB
            "diff": 500 * 1024,        # 500KB
            "prompt": 100 * 1024       # 100KB
        }

        max_size = size_limits.get(input_type, self.max_input_size)

        if data_size > max_size:
            return SecurityCheckResult(
                is_valid=False,
                level="warning",
                message=f"入力サイズが制限を超過: {data_size} > {max_size} bytes",
                recommendations=[
                    "入力データを小さくしてください",
                    "必要に応じてデータを分割してください",
                    "バイナリデータが含まれていないか確認してください"
                ]
            )

        return SecurityCheckResult(
            is_valid=True,
            level="safe",
            message=f"入力サイズは適切です: {data_size} bytes",
            recommendations=[]
        )

    def _check_api_key_strength(self, api_key: str, expose_details: bool) -> SecurityCheckResult:
        """
        APIキーの強度をチェック

        Args:
            api_key: チェック対象のAPIキー
            expose_details: 詳細を公開するかどうか

        Returns:
            セキュリティチェック結果
        """
        issues = []

        # 文字種の多様性チェック
        has_upper = any(c.isupper() for c in api_key)
        has_lower = any(c.islower() for c in api_key)
        has_digit = any(c.isdigit() for c in api_key)

        if not (has_upper and has_lower and has_digit):
            issues.append("文字種の多様性が不足")

        # 繰り返しパターンのチェック
        if self._has_repetitive_pattern(api_key):
            issues.append("繰り返しパターンを検出")

        # 明らかに無効なキーのチェック
        if api_key.lower() in ['test', 'example', 'sample', 'demo', 'placeholder']:
            issues.append("テスト用キーまたはプレースホルダー")

        if issues:
            return SecurityCheckResult(
                is_valid=False,
                level="warning",
                message="APIキーの強度に問題があります",
                recommendations=[
                    "正しいAPIキーが設定されているか確認してください",
                    "テスト用の値になっていないか確認してください"
                ] + (issues if expose_details else [])
            )

        return SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="APIキーの強度は適切です",
            recommendations=[]
        )

    def _detect_sensitive_content(self, content: str) -> SecurityCheckResult:
        """
        機密情報の検出

        Args:
            content: チェック対象のコンテンツ

        Returns:
            セキュリティチェック結果
        """
        detected_patterns = []

        for pattern in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                detected_patterns.append("機密情報らしきパターン")

        if detected_patterns:
            return SecurityCheckResult(
                is_valid=False,
                level="danger",
                message="機密情報が含まれている可能性があります",
                recommendations=[
                    "パスワードやAPIキーが含まれていないか確認してください",
                    "機密情報をコミットしないでください",
                    ".gitignore で機密ファイルを除外してください"
                ]
            )

        return SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="機密情報は検出されませんでした",
            recommendations=[]
        )

    def _remove_dangerous_patterns(self, content: str) -> Tuple[str, SecurityCheckResult]:
        """
        危険なパターンを除去

        Args:
            content: 処理対象のコンテンツ

        Returns:
            (クリーンなコンテンツ, セキュリティチェック結果)
        """
        removed_patterns = []

        # 危険なパターンを順次除去
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, content):
                content = re.sub(pattern, '', content)
                removed_patterns.append("危険な文字")

        if removed_patterns:
            return content, SecurityCheckResult(
                is_valid=True,
                level="warning",
                message=f"危険なパターンを除去しました: {len(removed_patterns)}個",
                recommendations=[
                    "入力に特殊文字が含まれていました",
                    "セキュリティのため一部文字を除去しました"
                ]
            )

        return content, SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="危険なパターンは検出されませんでした",
            recommendations=[]
        )

    def _contains_binary_content(self, content: str) -> bool:
        """
        バイナリコンテンツが含まれているかチェック

        Args:
            content: チェック対象のコンテンツ

        Returns:
            バイナリコンテンツが含まれている場合True
        """
        # NULL文字の検出
        if '\x00' in content:
            return True

        # 非印刷文字の割合をチェック
        non_printable = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
        if len(content) > 0 and non_printable / len(content) > 0.3:
            return True

        return False

    def _has_repetitive_pattern(self, text: str) -> bool:
        """
        繰り返しパターンの検出

        Args:
            text: チェック対象のテキスト

        Returns:
            繰り返しパターンがある場合True
        """
        # 同じ文字の連続（3文字以上）
        if re.search(r'(.)\1{2,}', text):
            return True

        # 短いパターンの繰り返し
        for i in range(2, min(6, len(text) // 3)):
            pattern = text[:i]
            if text.startswith(pattern * 3):
                return True

        return False

    def get_security_recommendations(self) -> List[str]:
        """
        一般的なセキュリティ推奨事項を取得

        Returns:
            セキュリティ推奨事項のリスト
        """
        return [
            "設定ファイルの権限を 600 に設定してください",
            "APIキーを環境変数で管理してください",
            "機密情報をGitリポジトリにコミットしないでください",
            ".gitignore で設定ファイルを除外してください",
            "定期的にAPIキーをローテーションしてください",
            "ログに機密情報が含まれていないか確認してください"
        ]