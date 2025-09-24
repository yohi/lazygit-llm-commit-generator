# セキュリティとエラーハンドリング

## 概要

LazyGit LLM Commit Generatorは、セキュリティを最優先に設計されており、包括的なエラーハンドリングシステムを実装しています。このドキュメントでは、セキュリティ機能、エラーハンドリング戦略、および安全な開発プラクティスについて詳述します。

## セキュリティアーキテクチャ

### 多層防御アプローチ

```text
┌─────────────────────────────────────┐
│        入力検証レイヤー             │ ← 入力サニタイゼーション
├─────────────────────────────────────┤
│      認証・認可レイヤー             │ ← APIキー検証、権限チェック
├─────────────────────────────────────┤
│     プロセス分離レイヤー            │ ← subprocess安全実行
├─────────────────────────────────────┤
│       データ保護レイヤー            │ ← 機密情報のマスキング
├─────────────────────────────────────┤
│        監査ログレイヤー             │ ← セキュリティイベント記録
└─────────────────────────────────────┘
```

### セキュリティ設計原則

1. **最小権限の原則**: 必要最小限の権限でプロセス実行
2. **デフォルト拒否**: 明示的に許可されていないものは全て拒否
3. **深層防御**: 複数のセキュリティ層による保護
4. **機密情報の分離**: APIキー等の機密情報を環境変数で外部化
5. **監査可能性**: 全セキュリティイベントをログに記録

## 入力検証とサニタイゼーション

### SecurityValidator (`src/security_validator.py`)

```python
class SecurityValidator:
    """入力データのセキュリティ検証"""

    # 機密情報パターン
    SENSITIVE_PATTERNS = [
        r'(?i)api[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',
        r'(?i)password["\s]*[:=]["\s]*[^\s]{6,}',
        r'(?i)secret["\s]*[:=]["\s]*[a-zA-Z0-9]{10,}',
        r'(?i)token["\s]*[:=]["\s]*[a-zA-Z0-9]{20,}',
        r'-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----',
    ]

    # 危険な文字パターン
    DANGEROUS_PATTERNS = [
        r'[;&|`$(){}[\]\\]',      # シェルメタ文字
        r'\.\./',                 # ディレクトリトラバーサル
        r'<script[^>]*>',         # スクリプトタグ
        r'javascript:',           # JavaScript URI
        r'data:',                 # Data URI
    ]

    @staticmethod
    def validate_diff(diff_content: str) -> bool:
        """Git差分の安全性検証"""
        if not diff_content or not isinstance(diff_content, str):
            return False

        # サイズ制限
        if len(diff_content) > 50 * 1024:  # 50KB
            logger.warning("差分サイズが制限を超過")
            return False

        # 機密情報の検出
        if SecurityValidator._contains_sensitive_data(diff_content):
            logger.warning("差分に機密情報を検出")
            return False

        # 危険なパターンの検出
        if SecurityValidator._contains_dangerous_patterns(diff_content):
            logger.warning("差分に危険なパターンを検出")
            return False

        return True

    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """プロンプトの安全化"""
        if not prompt:
            return ""

        # 基本的なサニタイゼーション
        sanitized = prompt.strip()

        # 制御文字の除去
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32 or char in '\n\r\t')

        # NULL文字の除去
        sanitized = sanitized.replace('\x00', '')

        # 長さ制限
        if len(sanitized) > 10000:  # 10KB
            sanitized = sanitized[:10000]
            logger.warning("プロンプトを長さ制限により切り詰め")

        return sanitized

    @staticmethod
    def mask_sensitive_data(content: str) -> str:
        """機密情報のマスキング"""
        masked_content = content

        for pattern in SecurityValidator.SENSITIVE_PATTERNS:
            masked_content = re.sub(pattern, '[MASKED]', masked_content, flags=re.MULTILINE | re.IGNORECASE)

        return masked_content

    @staticmethod
    def _contains_sensitive_data(content: str) -> bool:
        """機密情報の検出"""
        for pattern in SecurityValidator.SENSITIVE_PATTERNS:
            if re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _contains_dangerous_patterns(content: str) -> bool:
        """危険なパターンの検出"""
        for pattern in SecurityValidator.DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.MULTILINE):
                return True
        return False
```

### 入力検証の実装例

```python
class InputValidator:
    """入力データの検証"""

    @staticmethod
    def validate_config_path(path: str) -> bool:
        """設定ファイルパスの検証"""
        if not path or not isinstance(path, str):
            return False

        # パス正規化（実体パス解決）
        normalized_path = os.path.normpath(os.path.expanduser(path))
        resolved_path = os.path.realpath(normalized_path)

        # 許可されたディレクトリのみ（厳密な包含関係チェック）
        allowed_dirs = [
            os.path.expanduser('~/.config/lazygit-llm'),
            os.getcwd(),
        ]

        if not any(os.path.commonpath([resolved_path, os.path.realpath(allowed_dir)]) 
                   == os.path.realpath(allowed_dir) for allowed_dir in allowed_dirs):
            logger.warning(f"許可されていないディレクトリ: {path}")
            return False

        return True

    @staticmethod
    def validate_model_name(model_name: str) -> bool:
        """モデル名の検証"""
        if not model_name or not isinstance(model_name, str):
            return False

        # 英数字、ハイフン、ドット、アンダースコアのみ許可
        if not re.match(r'^[a-zA-Z0-9\-_.]+$', model_name):
            return False

        # 長さ制限
        if len(model_name) > 100:
            return False

        return True
```

## APIキー管理

### 環境変数による外部化

```python
class SecureKeyManager:
    """APIキーの安全な管理"""

    @staticmethod
    def get_api_key(provider_name: str) -> Optional[str]:
        """環境変数からAPIキーを安全に取得"""
        key_mappings = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'gemini': 'GOOGLE_API_KEY',
        }

        env_var = key_mappings.get(provider_name)
        if not env_var:
            logger.error(f"未知のプロバイダー: {provider_name}")
            return None

        api_key = os.getenv(env_var)
        if not api_key:
            logger.error(f"環境変数 {env_var} が設定されていません")
            return None

        # APIキーの基本的な形式検証
        if not SecureKeyManager._validate_api_key_format(api_key):
            logger.error("APIキーの形式が無効です")
            return None

        return api_key

    @staticmethod
    def _validate_api_key_format(api_key: str) -> bool:
        """APIキー形式の基本検証"""
        if not api_key or len(api_key) < 10:
            return False

        # 制御文字が含まれていないか確認
        if any(ord(char) < 32 for char in api_key if char not in '\n\r\t'):
            return False

        return True

    @staticmethod
    def mask_api_key(api_key: str) -> str:
        """APIキーのマスキング（ログ出力用）"""
        if not api_key or len(api_key) < 8:
            return '[MASKED]'

        return f"{api_key[:4]}...{api_key[-4:]}"
```

### 設定ファイルでの環境変数展開

```python
class ConfigExpander:
    """設定ファイル内の環境変数展開"""

    @staticmethod
    def expand_environment_variables(value: str) -> str:
        """環境変数の安全な展開"""
        if not isinstance(value, str):
            return value

        # ${VAR_NAME} または ${VAR_NAME:default} 形式をサポート
        pattern = r'\$\{([A-Za-z_][A-Za-z0-9_]*)(?::([^}]*))?\}'

        def replace_var(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) else ''

            # 環境変数名の検証
            if not ConfigExpander._is_safe_env_var(var_name):
                logger.warning(f"危険な環境変数名: {var_name}")
                return default_value

            return os.getenv(var_name, default_value)

        return re.sub(pattern, replace_var, value)

    @staticmethod
    def _is_safe_env_var(var_name: str) -> bool:
        """安全な環境変数名かチェック"""
        # 許可された環境変数のホワイトリスト
        allowed_vars = {
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GOOGLE_API_KEY',
            'CLAUDE_API_KEY', 'HOME', 'USER', 'PATH'
        }

        # プレフィックスによる許可
        allowed_prefixes = ('LAZYGIT_LLM_', 'LLM_')

        return (var_name in allowed_vars or
                any(var_name.startswith(prefix) for prefix in allowed_prefixes))
```

## プロセス分離とsubprocess安全性

### CLIプロバイダーのセキュリティ

```python
class SecureSubprocess:
    """安全なsubprocess実行"""

    @staticmethod
    def safe_run(cmd_args: List[str], input_data: str = None,
                timeout: int = 30, env: Dict[str, str] = None) -> subprocess.CompletedProcess:
        """安全なsubprocess実行"""

        # コマンド引数の検証
        if not SecureSubprocess._validate_command_args(cmd_args):
            raise SecurityError("危険なコマンド引数")

        # 環境変数の検証
        safe_env = SecureSubprocess._create_safe_environment(env)

        # 入力データのサニタイゼーション
        safe_input = SecurityValidator.sanitize_prompt(input_data) if input_data else None

        try:
            result = subprocess.run(
                cmd_args,
                input=safe_input,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=timeout,
                env=safe_env,
                shell=False,  # 重要: shell=False を強制
                check=False,
                cwd=None,     # カレントディレクトリを固定
            )

            # 出力のサニタイゼーション
            result.stdout = SecureSubprocess._sanitize_output(result.stdout)
            result.stderr = SecureSubprocess._sanitize_output(result.stderr)

            return result

        except subprocess.TimeoutExpired as e:
            logger.warning(f"コマンド実行タイムアウト: {cmd_args[0]}")
            raise
        except Exception as e:
            logger.error(f"コマンド実行エラー: {e}")
            raise

    @staticmethod
    def _validate_command_args(cmd_args: List[str]) -> bool:
        """コマンド引数の検証"""
        if not cmd_args or not isinstance(cmd_args, list):
            return False

        # 空の引数がないかチェック
        if any(not arg or not isinstance(arg, str) for arg in cmd_args):
            return False

        # 危険な文字の検出
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '{', '}', '<', '>']
        for arg in cmd_args:
            if any(char in arg for char in dangerous_chars):
                logger.warning(f"危険な文字を含む引数: {arg}")
                return False

        return True

    @staticmethod
    def _create_safe_environment(custom_env: Dict[str, str] = None) -> Dict[str, str]:
        """安全な環境変数の作成"""
        # 基本的な環境変数のみを継承
        safe_vars = ['PATH', 'HOME', 'USER', 'LANG', 'LC_ALL', 'TERM']
        safe_env = {}

        for var in safe_vars:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        # カスタム環境変数の追加（検証済み）
        if custom_env:
            for key, value in custom_env.items():
                if ConfigExpander._is_safe_env_var(key):
                    safe_env[key] = value
                else:
                    logger.warning(f"安全でない環境変数をスキップ: {key}")

        return safe_env

    @staticmethod
    def _sanitize_output(output: str) -> str:
        """出力のサニタイゼーション"""
        if not output:
            return ""

        # 制御文字の除去（改行、タブ、復帰文字以外）
        sanitized = ''.join(
            char for char in output
            if ord(char) >= 32 or char in '\n\r\t'
        )

        # サイズ制限
        max_size = 1024 * 1024  # 1MB
        if len(sanitized) > max_size:
            sanitized = sanitized[:max_size]
            logger.warning("出力をサイズ制限により切り詰め")

        return sanitized
```

### バイナリ検証

```python
class BinaryValidator:
    """実行バイナリの検証"""

    ALLOWED_BINARIES = {
        'claude-code': ['/usr/local/bin/claude-code', '/usr/bin/claude-code'],
        'claude': ['/usr/local/bin/claude', '/usr/bin/claude'],
        'gcloud': ['/usr/local/bin/gcloud', '/usr/bin/gcloud'],
    }

    @staticmethod
    def verify_binary(binary_path: str, expected_name: str) -> bool:
        """バイナリの安全性検証"""
        try:
            # パスの正規化
            resolved_path = Path(binary_path).resolve()

            # 存在確認
            if not resolved_path.exists():
                logger.error(f"バイナリが存在しません: {binary_path}")
                return False

            # 実行権限確認
            if not os.access(resolved_path, os.X_OK):
                logger.error(f"実行権限がありません: {binary_path}")
                return False

            # 許可されたバイナリ名か確認
            if resolved_path.name not in BinaryValidator.ALLOWED_BINARIES:
                logger.error(f"許可されていないバイナリ: {resolved_path.name}")
                return False

            # 許可されたパスか確認
            allowed_paths = BinaryValidator.ALLOWED_BINARIES.get(expected_name, [])
            if str(resolved_path) not in allowed_paths and not any(
                str(resolved_path).startswith(path) for path in ['/usr/local/bin/', '/usr/bin/']
            ):
                logger.error(f"許可されていないパス: {resolved_path}")
                return False

            # 危険なパスの検出
            dangerous_paths = ['/tmp/', '/var/tmp/', '/dev/shm/']
            if any(dangerous_path in str(resolved_path) for dangerous_path in dangerous_paths):
                logger.error(f"危険なパス: {resolved_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"バイナリ検証エラー: {e}")
            return False
```

## エラーハンドリングシステム

### 例外階層

```python
# lazygit_llm/base_provider.py

class ProviderError(Exception):
    """プロバイダー関連エラーの基底クラス"""

    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message)
        self.details = details or {}
        self.timestamp = time.time()

class AuthenticationError(ProviderError):
    """認証失敗エラー"""
    pass

class ProviderTimeoutError(ProviderError):
    """タイムアウトエラー"""
    pass

class ResponseError(ProviderError):
    """レスポンス処理エラー"""
    pass

class RateLimitError(ProviderError):
    """レート制限エラー"""

    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after

class ConfigError(Exception):
    """設定関連エラー"""
    pass

class GitError(Exception):
    """Git操作エラー"""
    pass

class SecurityError(Exception):
    """セキュリティ関連エラー"""
    pass
```

### ErrorHandler実装

```python
# src/error_handler.py

class ErrorHandler:
    """統一的なエラーハンドリング"""

    @staticmethod
    def handle_provider_error(error: Exception, context: Dict[str, Any] = None) -> str:
        """プロバイダーエラーの統一処理"""
        context = context or {}

        # エラーの分類と処理
        if isinstance(error, AuthenticationError):
            return ErrorHandler._handle_authentication_error(error, context)
        elif isinstance(error, RateLimitError):
            return ErrorHandler._handle_rate_limit_error(error, context)
        elif isinstance(error, ProviderTimeoutError):
            return ErrorHandler._handle_timeout_error(error, context)
        elif isinstance(error, ResponseError):
            return ErrorHandler._handle_response_error(error, context)
        elif isinstance(error, SecurityError):
            return ErrorHandler._handle_security_error(error, context)
        else:
            return ErrorHandler._handle_generic_error(error, context)

    @staticmethod
    def _handle_authentication_error(error: AuthenticationError, context: Dict) -> str:
        """認証エラーの処理"""
        provider = context.get('provider', 'unknown')

        # セキュリティイベントとしてログ記録
        SecurityLogger.log_authentication_failure(provider, str(error))

        # ユーザーフレンドリーなメッセージ
        return f"認証に失敗しました。{provider}のAPIキーを確認してください。"

    @staticmethod
    def _handle_rate_limit_error(error: RateLimitError, context: Dict) -> str:
        """レート制限エラーの処理"""
        provider = context.get('provider', 'unknown')
        retry_after = getattr(error, 'retry_after', 60)

        logger.warning(f"レート制限: {provider}, retry_after={retry_after}")

        return f"APIの利用制限に達しました。{retry_after}秒後に再試行してください。"

    @staticmethod
    def _handle_timeout_error(error: ProviderTimeoutError, context: Dict) -> str:
        """タイムアウトエラーの処理"""
        provider = context.get('provider', 'unknown')

        logger.warning(f"タイムアウト: {provider}")

        return "リクエストがタイムアウトしました。ネットワーク接続を確認してください。"

    @staticmethod
    def _handle_security_error(error: SecurityError, context: Dict) -> str:
        """セキュリティエラーの処理"""
        # セキュリティインシデントとしてログ記録
        SecurityLogger.log_security_incident(str(error), context)

        return "セキュリティ上の問題が検出されました。操作を中止しました。"

    @staticmethod
    def log_error_with_context(error: Exception, context: Dict[str, Any]) -> None:
        """コンテキスト付きエラーログ"""
        # 機密情報のマスキング（error_info構築前に実施）
        safe_context = SecurityValidator.mask_sensitive_data(str(context))
        safe_message = SecurityValidator.mask_sensitive_data(str(error))

        error_info = {
            'error_type': type(error).__name__,
            'error_message': safe_message,
            'context': safe_context,
            'timestamp': time.time(),
        }

        logger.error(f"エラー発生: {error_info}", extra={'context': safe_context})
```

### セキュリティログ

```python
class SecurityLogger:
    """セキュリティイベントの専用ログ"""

    def __init__(self):
        self.security_logger = logging.getLogger('security')

        # セキュリティログの設定（重複追加防止＆ローテーション）
        if not self.security_logger.handlers:
            try:
                os.makedirs('/var/log/lazygit-llm', exist_ok=True)
                handler = logging.handlers.RotatingFileHandler(
                    '/var/log/lazygit-llm/security.log', maxBytes=5_000_000, backupCount=3, encoding='utf-8'
                )
            except Exception:
                # フォールバック（パス権限問題など）
                handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - SECURITY - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.security_logger.addHandler(handler)
            self.security_logger.setLevel(logging.WARNING)
            self.security_logger.propagate = False

    @staticmethod
    def log_authentication_failure(provider: str, error_details: str) -> None:
        """認証失敗のログ記録"""
        SecurityLogger().security_logger.warning(
            f"AUTHENTICATION_FAILURE: provider={provider}, details={error_details}"
        )

    @staticmethod
    def log_security_incident(incident_type: str, context: Dict) -> None:
        """セキュリティインシデントのログ記録"""
        safe_context = SecurityValidator.mask_sensitive_data(str(context))
        SecurityLogger().security_logger.error(
            f"SECURITY_INCIDENT: type={incident_type}, context={safe_context}"
        )

    @staticmethod
    def log_suspicious_activity(activity: str, details: Dict) -> None:
        """疑わしい活動のログ記録"""
        safe_details = SecurityValidator.mask_sensitive_data(str(details))
        SecurityLogger().security_logger.warning(
            f"SUSPICIOUS_ACTIVITY: {activity}, details={safe_details}"
        )
```

## 監査とモニタリング

### 監査ログの実装

```python
class AuditLogger:
    """監査ログ機能"""

    def __init__(self):
        self.audit_logger = logging.getLogger('audit')

        # 監査ログの設定（重複追加防止＆ローテーション）
        if not self.audit_logger.handlers:
            try:
                os.makedirs('/var/log/lazygit-llm', exist_ok=True)
                handler = logging.handlers.RotatingFileHandler(
                    '/var/log/lazygit-llm/audit.log', maxBytes=5_000_000, backupCount=3, encoding='utf-8'
                )
            except Exception:
                handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - AUDIT - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
            self.audit_logger.propagate = False

    def log_api_request(self, provider: str, model: str, request_size: int) -> None:
        """API リクエストの監査ログ"""
        self.audit_logger.info(
            f"API_REQUEST: provider={provider}, model={model}, "
            f"request_size={request_size}, user={os.getenv('USER', 'unknown')}"
        )

    def log_config_access(self, config_path: str, action: str) -> None:
        """設定ファイルアクセスの監査ログ"""
        self.audit_logger.info(
            f"CONFIG_ACCESS: path={config_path}, action={action}, "
            f"user={os.getenv('USER', 'unknown')}"
        )

    def log_binary_execution(self, binary_path: str, args: List[str]) -> None:
        """バイナリ実行の監査ログ"""
        safe_args = ' '.join(args[:3])  # 引数の最初の3つのみ記録
        self.audit_logger.info(
            f"BINARY_EXECUTION: binary={binary_path}, args={safe_args}, "
            f"user={os.getenv('USER', 'unknown')}"
        )
```

### パフォーマンス監視

```python
class PerformanceMonitor:
    """パフォーマンス監視"""

    @staticmethod
    def monitor_api_call(func):
        """API呼び出しの監視デコレータ"""
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss

            try:
                result = func(self, *args, **kwargs)

                # 成功時の監視データ記録
                elapsed_time = time.time() - start_time
                memory_used = psutil.Process().memory_info().rss - start_memory

                logger.info(
                    f"API呼び出し成功: {func.__name__}, "
                    f"elapsed={elapsed_time:.2f}s, memory={memory_used/1024/1024:.1f}MB"
                )

                return result

            except Exception as e:
                # エラー時の監視データ記録
                elapsed_time = time.time() - start_time
                logger.error(
                    f"API呼び出し失敗: {func.__name__}, "
                    f"elapsed={elapsed_time:.2f}s, error={type(e).__name__}"
                )
                raise

        return wrapper
```

## セキュリティ設定のベストプラクティス

### 1. 設定ファイルのセキュリティ

```bash
# 設定ファイルの適切な権限設定
chmod 600 ~/.config/lazygit-llm/config.yml
chmod 700 ~/.config/lazygit-llm/

# 設定ディレクトリの所有者確認
chown $USER:$USER ~/.config/lazygit-llm/
```

### 2. 環境変数の設定

```bash
# ~/.bashrc または ~/.zshrc
export OPENAI_API_KEY="your-secure-api-key"
export ANTHROPIC_API_KEY="your-secure-api-key"

# 権限の確認
umask 0077  # 作成されるファイルを他のユーザーから隠す
```

### 3. ログファイルのセキュリティ

```bash
# ログディレクトリの作成と権限設定
sudo mkdir -p /var/log/lazygit-llm/
sudo chown $USER:$USER /var/log/lazygit-llm/
chmod 750 /var/log/lazygit-llm/
```

### 4. 定期的なセキュリティチェック

```python
class SecurityChecker:
    """定期的なセキュリティチェック"""

    @staticmethod
    def check_file_permissions(config_path: str) -> bool:
        """ファイル権限のチェック"""
        try:
            stat_info = os.stat(config_path)
            permissions = oct(stat_info.st_mode)[-3:]

            # 600 (所有者のみ読み書き) が推奨
            if permissions != '600':
                logger.warning(f"設定ファイルの権限が不適切: {permissions}")
                return False

            return True

        except Exception as e:
            logger.error(f"権限チェックエラー: {e}")
            return False

    @staticmethod
    def check_api_key_security() -> bool:
        """APIキーのセキュリティチェック"""
        issues = []

        # 環境変数からのAPIキー取得
        api_keys = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
            'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY'),
        }

        for key_name, key_value in api_keys.items():
            if key_value:
                # 長さチェック
                if len(key_value) < 20:
                    issues.append(f"{key_name}が短すぎます")

                # 形式チェック（基本的なパターン）
                if not re.match(r'^[a-zA-Z0-9\-_.]+$', key_value):
                    issues.append(f"{key_name}に不正な文字が含まれています")

        if issues:
            for issue in issues:
                logger.warning(f"APIキーセキュリティ問題: {issue}")
            return False

        return True
```

## トラブルシューティング

### よくあるセキュリティ問題

#### 1. 設定ファイル権限エラー

```text
ERROR: 設定ファイルの権限が不適切です
```

**解決方法**:
```bash
chmod 600 ~/.config/lazygit-llm/config.yml
```

#### 2. APIキー形式エラー

```text
ERROR: APIキーの形式が無効です
```

**解決方法**:
- 環境変数の値を確認
- APIキーの先頭・末尾に余分な文字がないか確認
- 引用符が含まれていないか確認

#### 3. バイナリ検証エラー

```text
ERROR: 許可されていないバイナリパス
```

**解決方法**:
- 正しいパスにバイナリがインストールされているか確認
- 実行権限があるか確認
- シンボリックリンクが正しく設定されているか確認

### デバッグ手順

1. **詳細ログの有効化**
```bash
export LAZYGIT_LLM_DEBUG=1
uv run lazygit-llm-generate --verbose
```

2. **セキュリティログの確認**
```bash
tail -f /var/log/lazygit-llm/security.log
```

3. **監査ログの確認**
```bash
tail -f /var/log/lazygit-llm/audit.log
```

---

## メタ情報

- **ドキュメント**: セキュリティとエラーハンドリング
- **バージョン**: 1.0.0
- **対象者**: 開発者・セキュリティ担当者
- **最終更新**: 2024年12月

このセキュリティとエラーハンドリングシステムにより、LazyGit LLM Commit Generatorは安全で信頼性の高い動作を実現しています。
