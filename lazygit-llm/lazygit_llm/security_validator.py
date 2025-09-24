# ruff: noqa: RUF002, RUF003
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
import threading
from typing import Dict, Any, Optional, List, Tuple, ClassVar
from pathlib import Path
from dataclasses import dataclass
# from functools import lru_cache  # インスタンスメソッドのメモリリーク回避のため削除

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
            'pattern': r'^sk-[A-Za-z0-9_-]{20,}$',
            'min_length': 24,
            'max_length': 200,
            'description': 'OpenAI API key (sk-...)'
        },
        'anthropic': {
            'pattern': r'^sk-ant-[A-Za-z0-9\-_]{20,}$',
            'min_length': 24,
            'max_length': 200,
            'description': 'Anthropic API key (sk-ant-...)'
        },
        'gemini': {
            'pattern': r'^AIza[A-Za-z0-9\-_]{34,36}$',
            'min_length': 38,
            'max_length': 40,
            'description': 'Google API key (AIza...)'
        }
    }

    # 危険な文字パターン
    DANGEROUS_PATTERNS: ClassVar[List[str]] = [
        r'\.\./',                                  # パストラバーサル
        r'(?i)\bjavascript:',                      # JS URI
        r'(?i)\bdata:(?:text|application)/\w+',    # Data URI(限定)
        r'(?is)<script\b[^>]*>.*?</script>',       # 明示的な script タグ
        r'[\x00-\x08\x0B\x0C\x0E-\x1F]',           # 制御文字(改行/タブ除外)
    ]

    # 機密情報パターン（全て大文字小文字区別なし）
    SENSITIVE_PATTERNS: ClassVar[List[str]] = [
        r'(?i)(password|passwd|pwd)\s*[:=]\s*[\'"]?([^\s\'"]{8,})',
        r'(?i)(secret|token|key)\s*[:=]\s*[\'"]?([^\s\'"]{16,})',
        r'(?i)(api[_-]?key)\s*[:=]\s*[\'"]?([^\s\'"]{20,})',
        r'(?i)[A-Z0-9+/]{64,}={0,2}',  # Base64エンコード（大文字小文字区別なし）
        r'(?i)[0-9A-F]{32,}',          # Hexエンコード（大文字小文字区別なし）
        r'(?i)(bearer|authorization)\s*[:=]\s*[\'"]?([^\s\'"]{20,})',  # 認証トークン
        r'(?i)(private[_-]?key|secret[_-]?key)\s*[:=]\s*[\'"]?([^\s\'"]{40,})',  # 秘密鍵
    ]

    def __init__(self, enable_caching: bool = True):
        """セキュリティバリデーターを初期化

        Args:
            enable_caching: キャッシュを有効にするかどうか
        """
        self.max_input_size = 1024 * 1024  # 1MB
        self.max_diff_size = 500 * 1024    # 500KB
        self.enable_caching = enable_caching
        self._cache_lock = threading.Lock()
        self.enable_parallel_processing = False
        self._processing_stats = {
            'total_validations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_key_validations': 0,
            'diff_sanitizations': 0
        }

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
        logger.debug(f"APIキー検証成功: provider={provider}, hash={key_hash}")

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

        original_size = len(diff_content.encode("utf-8"))

        # サイズ制限チェック
        if original_size > self.max_diff_size:
            truncated = diff_content.encode("utf-8")[: self.max_diff_size]
            diff_content = truncated.decode("utf-8", errors="ignore")
            logger.warning(
                f"差分サイズが制限を超過、切り詰めました: {original_size} -> {len(diff_content.encode('utf-8'))} bytes"
            )

        # 機密情報の検出とマスキング
        diff_content, sensitive_check = self._redact_sensitive_content(diff_content)

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

        # 最も深刻なレベルを選択
        final_level = "safe"
        all_recommendations = []

        if sensitive_check.level == "warning":
            final_level = "warning"
            all_recommendations.extend(sensitive_check.recommendations)

        if danger_check.level in ["warning", "danger"]:
            if final_level == "safe" or danger_check.level == "danger":
                final_level = danger_check.level
            all_recommendations.extend(danger_check.recommendations)

        messages = []
        if sensitive_check.level == "warning":
            messages.append(sensitive_check.message)
        messages.append(f"差分のサニタイゼーション完了 ({len(sanitized_diff)}文字)")

        final_check_result = SecurityCheckResult(
            is_valid=True,
            level=final_level,
            message=" / ".join(messages),
            recommendations=list(set(all_recommendations))  # 重複除去
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

        except (OSError, PermissionError, FileNotFoundError):
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

    def _redact_sensitive_content(self, content: str) -> Tuple[str, SecurityCheckResult]:
        """
        機密情報の検出とマスキング

        Args:
            content: チェック対象のコンテンツ

        Returns:
            (マスキング済みコンテンツ, セキュリティチェック結果)
        """
        detected_patterns = []
        masked_content = content

        for pattern in self.SENSITIVE_PATTERNS:
            matches = list(re.finditer(pattern, masked_content))
            if matches:
                detected_patterns.append("機密情報らしきパターン")
                # 機密情報をマスキング
                for match in reversed(matches):  # 後ろから置換して位置がずれないように
                    masked_content = (
                        masked_content[:match.start()] +
                        "[REDACTED]" +
                        masked_content[match.end():]
                    )

        if detected_patterns:
            return masked_content, SecurityCheckResult(
                is_valid=True,  # 継続処理可能
                level="warning",  # dangerからwarningに変更
                message="機密情報らしきパターンをマスキングしました",
                recommendations=[
                    "マスキング前の内容にパスワードやAPIキーが含まれていないか確認してください",
                    "機密情報をコミットしないでください",
                    ".gitignore で機密ファイルを除外してください"
                ]
            )
        else:
            return content, SecurityCheckResult(
                is_valid=True,
                level="safe",
                message="機密情報は検出されませんでした",
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

    # (重複定義は削除。末尾の定義を採用)

    @staticmethod
    def _cached_validate_api_key(provider: str, key_length: int) -> SecurityCheckResult:
        """
        静的なAPIキー形式検証（メモリリーク回避版）

        Args:
            provider: プロバイダー名
            key_length: APIキーの長さ

        Returns:
            セキュリティチェック結果
        """
        # 定数パターンを使用（インスタンス非依存）
        api_key_patterns = {
            'openai': {'min_length': 48, 'max_length': 56, 'pattern': r'^sk-(proj-)?[A-Za-z0-9]{20,}$'},
            'anthropic': {'min_length': 25, 'max_length': 100, 'pattern': r'^sk-ant-api[0-9]{2}-[A-Za-z0-9_-]{95}$'},
            'gemini': {'min_length': 39, 'max_length': 39, 'pattern': r'^AIza[A-Za-z0-9_-]{35}$'},
        }

        pattern_info = api_key_patterns.get(provider.lower())
        if pattern_info:
            if not (pattern_info['min_length'] <= key_length <= pattern_info['max_length']):
                return SecurityCheckResult(
                    is_valid=False,
                    level="warning",
                    message="APIキーの長さが期待値と異なります",
                    recommendations=[
                        "APIキーが完全にコピーされているか確認してください",
                        "APIキーに余分な文字が含まれていないか確認してください"
                    ]
                )

        return SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="APIキーの形式は有効です",
            recommendations=[]
        )

    @staticmethod
    def _cached_sanitize_diff(diff_length: int, max_diff_size: int) -> Tuple[str, SecurityCheckResult]:
        """
        静的な差分サイズ検証（メモリリーク回避版）

        Args:
            diff_length: 差分の長さ
            max_diff_size: 最大許可サイズ

        Returns:
            (サニタイゼーション済み差分の状態, セキュリティチェック結果)
        """
        # 基本的なサイズチェック
        if diff_length > max_diff_size:
            return "truncated", SecurityCheckResult(
                is_valid=True,
                level="warning",
                message="差分サイズが制限を超過、切り詰めました",
                recommendations=["大きなファイルの変更は分割することを検討してください"]
            )

        return "clean", SecurityCheckResult(
            is_valid=True,
            level="safe",
            message="差分のサニタイゼーション完了",
            recommendations=[]
        )

    def optimize_for_performance(self, operation_type: str, *args, **kwargs) -> Any:
        """
        パフォーマンス最適化されたセキュリティ検証

        Args:
            operation_type: 操作タイプ（'api_key', 'diff_sanitize', 'bulk_validate'）
            *args: 位置引数
            **kwargs: キーワード引数

        Returns:
            最適化処理された結果
        """
        with self._cache_lock:
            self._processing_stats['total_validations'] += 1

        if operation_type == 'api_key':
            return self._optimize_api_key_validation(*args, **kwargs)
        elif operation_type == 'diff_sanitize':
            return self._optimize_diff_sanitization(*args, **kwargs)
        elif operation_type == 'bulk_validate':
            return self._optimize_bulk_validation(*args, **kwargs)
        else:
            raise ValueError(f"Unknown operation type: {operation_type}")

    def _optimize_api_key_validation(self, provider: str, api_key: str, expose_details: bool = False) -> SecurityCheckResult:
        """
        パフォーマンス最適化されたAPIキー検証

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
                recommendations=["設定ファイルでAPIキーを設定してください"]
            )

        # キャッシュ使用の判定（ただし実際の検証は必ず実行）
        if self.enable_caching and len(api_key) > 20:
            # 早期判定にキャッシュ統計のみ利用（判定自体は必ずフル検証へ）
            with self._cache_lock:
                self._processing_stats['cache_hits'] += 1

        # 通常の検証処理（必ず実行）
        with self._cache_lock:
            self._processing_stats['api_key_validations'] += 1

        return self.validate_api_key(provider, api_key, expose_details)

    def _optimize_diff_sanitization(self, diff_content: str) -> Tuple[str, SecurityCheckResult]:
        """
        パフォーマンス最適化されたGit差分サニタイゼーション

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

        diff_size = len(diff_content)

        # 小さな差分は高速処理
        if diff_size < 1000:
            return self.sanitize_git_diff(diff_content)

        # 中程度の差分はキャッシュを使用
        if diff_size < 50000 and self.enable_caching:
            try:
                cached_status, _cached_result = self._cached_sanitize_diff(diff_size, self.max_diff_size)
                with self._cache_lock:
                    self._processing_stats['cache_hits'] += 1

                if cached_status == "clean":
                    sanitized_content, sanitized_result = self.sanitize_git_diff(diff_content)
                    return sanitized_content, sanitized_result
                elif cached_status == "truncated":
                    truncated = diff_content[:self.max_diff_size]
                    sanitized_content, sanitized_result = self.sanitize_git_diff(truncated)
                    return sanitized_content, sanitized_result
            except Exception:
                with self._cache_lock:
                    self._processing_stats['cache_misses'] += 1

        # 大きな差分は段階的処理
        with self._cache_lock:
            self._processing_stats['diff_sanitizations'] += 1

        # 早期切り詰め（必要な場合）
        if diff_size > self.max_diff_size * 2:
            diff_content = diff_content[:self.max_diff_size * 2]

        return self.sanitize_git_diff(diff_content)

    def _optimize_bulk_validation(self, validation_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        複数の検証タスクを一括処理（最適化版）

        Args:
            validation_tasks: 検証タスクのリスト

        Returns:
            検証結果のリスト
        """
        if not validation_tasks:
            return []

        results = []

        # 小さなバッチはシーケンシャル処理
        if len(validation_tasks) < 5 or not self.enable_parallel_processing:
            for task in validation_tasks:
                try:
                    task_type = task.get('type', 'unknown')
                    if task_type == 'api_key':
                        result = self._optimize_api_key_validation(
                            task['provider'],
                            task['api_key'],
                            task.get('expose_details', False)
                        )
                    elif task_type == 'diff_sanitize':
                        sanitized, result = self._optimize_diff_sanitization(task['diff_content'])
                        result = {'sanitized_content': sanitized, 'check_result': result}
                    else:
                        result = SecurityCheckResult(
                            is_valid=False,
                            level="warning",
                            message=f"Unknown task type: {task_type}",
                            recommendations=[]
                        )

                    results.append({
                        'task_id': task.get('task_id', len(results)),
                        'result': result
                    })
                except Exception as e:
                    logger.warning(f"バルク検証エラー: {e}")
                    results.append({
                        'task_id': task.get('task_id', len(results)),
                        'result': SecurityCheckResult(
                            is_valid=False,
                            level="warning",
                            message="検証エラー",
                            recommendations=["再度検証を実行してください"]
                        )
                    })

            return results

        # 大きなバッチは並行処理（簡略版）
        # 実際の並行処理は複雑なため、ここでは効率的なシーケンシャル処理
        return self._optimize_bulk_validation(validation_tasks[:5]) + \
               self._optimize_bulk_validation(validation_tasks[5:])

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        パフォーマンス統計情報を取得

        Returns:
            パフォーマンス統計情報
        """
        with self._cache_lock:
            stats = self._processing_stats.copy()

        # 静的メソッド化によりキャッシュ統計は内部統計のみ利用

        return stats

    def clear_cache(self):
        """
        キャッシュをクリア
        """
        # 静的メソッド化により個別キャッシュクリアは不要

        with self._cache_lock:
            self._processing_stats = {
                'total_validations': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'api_key_validations': 0,
                'diff_sanitizations': 0
            }

        logger.debug("セキュリティバリデーターのキャッシュをクリアしました")

    def optimize_memory_usage(self):
        """
        メモリ使用量を最適化
        """
        # 静的メソッド化により個別キャッシュ管理は不要

        # 統計情報のリセット
        with self._cache_lock:
            if self._processing_stats['total_validations'] > 5000:
                self._processing_stats = {
                    'total_validations': 0,
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'api_key_validations': 0,
                    'diff_sanitizations': 0
                }

    def __del__(self):
        """
        デストラクタ: リソースのクリーンアップ
        """
        pass

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
