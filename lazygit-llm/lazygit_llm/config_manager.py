"""
設定管理モジュール

YAML設定ファイルの読み込み、検証、環境変数展開を行う。
セキュリティ要件に従いAPIキーの安全な管理を実装。
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field

from .security_validator import SecurityValidator

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """プロバイダー設定データクラス"""
    name: str
    type: str  # "api" or "cli"
    model: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_tokens: int = 100
    additional_params: Dict[str, Any] = field(default_factory=dict)


class ConfigError(Exception):
    """設定関連のエラー"""
    pass


class ConfigManager:
    """
    設定管理クラス

    YAML設定ファイルの読み込み、環境変数解決、設定検証を行う。
    セキュリティ要件に従いAPIキーの安全な取り扱いを実装。
    """

    def __init__(self):
        """設定マネージャーを初期化"""
        self.config: Dict[str, Any] = {}
        self._config_path: Optional[str] = None
        self.security_validator = SecurityValidator()

        # サポートされているプロバイダーの定義
        self.supported_providers = {
            'openai': {'type': 'api', 'required_fields': ['api_key', 'model_name']},
            'anthropic': {'type': 'api', 'required_fields': ['api_key', 'model_name']},
            'gemini-api': {'type': 'api', 'required_fields': ['api_key', 'model_name']},
            'gemini-cli': {'type': 'cli', 'required_fields': ['model_name']},
            'claude-code': {'type': 'cli', 'required_fields': ['model_name']},
        }

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        設定ファイルを読み込み

        Args:
            config_path: 設定ファイルのパス

        Returns:
            読み込まれた設定データ

        Raises:
            ConfigError: 設定ファイルの読み込みまたは解析に失敗した場合
        """
        self._config_path = config_path
        config_file = Path(config_path)

        if not config_file.exists():
            raise ConfigError(f"設定ファイルが見つかりません: {config_path}")

        # ファイル権限をチェック（セキュリティ要件）
        permission_result = self.security_validator.check_file_permissions(str(config_file))
        if permission_result.level == "warning":
            logger.warning(f"設定ファイル権限警告: {permission_result.message}")
            for rec in permission_result.recommendations:
                logger.warning(f"推奨: {rec}")
        elif permission_result.level == "danger":
            logger.error(f"設定ファイル権限エラー: {permission_result.message}")
            raise ConfigError(f"セキュリティエラー: {permission_result.message}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            # ルートは辞書である必要がある(空ファイルなどは {} とみなす)
            if raw_config is None:
                raw_config = {}
            elif not isinstance(raw_config, dict):
                raise ConfigError("設定ファイルのルートは辞書である必要があります")

            # 環境変数を解決
            self.config = self._expand_environment_variables(raw_config)

            # 設定を検証
            if not self.validate_config():
                raise ConfigError("設定の検証に失敗しました")

            logger.info(f"設定ファイルを正常に読み込みました: {config_path}")
            return self.config

        except yaml.YAMLError as e:
            raise ConfigError(f"YAML解析エラー: {e}")
        except Exception as e:
            raise ConfigError(f"設定ファイル読み込みエラー: {e}")

    def get_api_key(self, provider: str) -> str:
        """
        指定されたプロバイダーのAPIキーを取得

        Args:
            provider: プロバイダー名

        Returns:
            APIキー

        Raises:
            ConfigError: APIキーが見つからない、または空の場合
        """
        # まず設定ファイルから取得を試行
        api_key = self.config.get('api_key')

        # 設定ファイルにない場合は、環境変数名を推測
        if not api_key:
            env_var_name = f"{provider.upper().replace('-', '_')}_API_KEY"
            api_key = os.getenv(env_var_name)

        if not api_key:
            raise ConfigError(f"APIキーが見つかりません（プロバイダー: {provider}）")

        # セキュリティバリデーターでAPIキーを検証
        validation_result = self.security_validator.validate_api_key(provider, api_key.strip())
        if not validation_result.is_valid:
            raise ConfigError(f"APIキー検証エラー（{provider}）: {validation_result.message}")

        if validation_result.level == "warning":
            logger.warning(f"APIキー警告（{provider}）: {validation_result.message}")
            for rec in validation_result.recommendations:
                logger.warning(f"推奨: {rec}")

        return api_key.strip()

    def get_model_name(self, provider: str) -> str:
        """
        指定されたプロバイダーのモデル名を取得

        Args:
            provider: プロバイダー名

        Returns:
            モデル名

        Raises:
            ConfigError: モデル名が見つからない場合
        """
        model_name = self.config.get('model_name')
        if not model_name:
            raise ConfigError(f"モデル名が設定されていません（プロバイダー: {provider}）")

        return model_name

    def get_prompt_template(self) -> str:
        """
        プロンプトテンプレートを取得

        Returns:
            プロンプトテンプレート

        Raises:
            ConfigError: プロンプトテンプレートが見つからない場合
        """
        template = self.config.get('prompt_template')
        if not template:
            # デフォルトのプロンプトテンプレートを提供
            template = (
                "Based on the following git diff, generate a concise commit message "
                "that follows conventional commits format:\n\n$diff\n\n"
                "Generate only the commit message, no additional text."
            )
            logger.warning("プロンプトテンプレートが設定されていません。デフォルトを使用します。")

        # $diffプレースホルダーが含まれているかチェック
        if '$diff' not in template:
            raise ConfigError("プロンプトテンプレートに$diffプレースホルダーが含まれていません")

        return template

    def get_provider_config(self) -> ProviderConfig:
        """
        現在の設定からプロバイダー設定を生成

        Returns:
            プロバイダー設定オブジェクト

        Raises:
            ConfigError: 必須設定が不足している場合
        """
        provider_name = self.config.get('provider')
        if not provider_name:
            raise ConfigError("プロバイダー名が設定されていません")

        if provider_name not in self.supported_providers:
            raise ConfigError(f"サポートされていないプロバイダー: {provider_name}")

        provider_info = self.supported_providers[provider_name]

        # APIキーの取得（API型プロバイダーのみ）
        api_key = None
        if provider_info['type'] == 'api':
            api_key = self.get_api_key(provider_name)

        return ProviderConfig(
            name=provider_name,
            type=provider_info['type'],
            model=self.get_model_name(provider_name),
            api_key=api_key,
            timeout=self.config.get('timeout', 30),
            max_tokens=self.config.get('max_tokens', 100),
            additional_params=self.config.get('additional_params', {})
        )

    def validate_config(self) -> bool:
        """
        設定を検証

        Returns:
            設定が有効な場合True、無効な場合False
        """
        try:
            # 必須フィールドの存在確認
            required_fields = ['provider']
            for field in required_fields:
                if field not in self.config:
                    logger.error(f"必須設定項目が不足: {field}")
                    return False

            # プロバイダーの有効性確認
            provider = self.config['provider']
            if provider not in self.supported_providers:
                logger.error(f"サポートされていないプロバイダー: {provider}")
                return False

            # プロバイダー固有の設定検証
            provider_info = self.supported_providers[provider]
            for field in provider_info['required_fields']:
                # APIキーは別途チェック（セキュリティのため）
                if field == 'api_key':
                    if provider_info['type'] == 'api':
                        try:
                            self.get_api_key(provider)
                        except ConfigError:
                            logger.error(f"APIキーの取得に失敗: {provider}")
                            return False
                elif field not in self.config:
                    logger.error(f"必須設定項目が不足（{provider}）: {field}")
                    return False

            # 数値設定の範囲チェック
            timeout = self.config.get('timeout', 30)
            if not isinstance(timeout, int) or timeout <= 0 or timeout > 300:
                logger.error(f"タイムアウト値が無効: {timeout}")
                return False

            max_tokens = self.config.get('max_tokens', 100)
            if not isinstance(max_tokens, int) or max_tokens <= 0 or max_tokens > 4000:
                logger.error(f"最大トークン数が無効: {max_tokens}")
                return False

            # プロンプトテンプレートの検証
            try:
                self.get_prompt_template()
            except ConfigError as e:
                logger.error(f"プロンプトテンプレートエラー: {e}")
                return False

            logger.info("設定の検証が完了しました")
            return True

        except Exception as e:
            logger.error(f"設定検証中にエラー: {e}")
            return False

    def _expand_environment_variables(self, config: Any) -> Any:
        """
        設定内の環境変数を再帰的に展開する

        Args:
            config: 設定の一部 (dict, list, strなど)

        Returns:
            環境変数が展開された設定
        """
        if isinstance(config, dict):
            return {
                key: self._expand_environment_variables(value)
                for key, value in config.items()
            }
        elif isinstance(config, list):
            return [self._expand_environment_variables(item) for item in config]
        elif isinstance(config, str):
            # ${VAR} または ${VAR:default} を文字列中の任意位置で展開
            pattern = re.compile(r'\${([^}:]+)(?::([^}]*))?}')
            def repl(m: re.Match) -> str:
                key = m.group(1)
                default = m.group(2)
                return os.environ.get(key, default if default is not None else m.group(0))
            return pattern.sub(repl, config)
        else:
            return config

    def _check_file_permissions(self, config_file: Path) -> None:
        """
        設定ファイルの権限をチェック（セキュリティ要件）

        Args:
            config_file: 設定ファイルのパス

        Raises:
            ConfigError: ファイル権限が安全でない場合
        """
        try:
            stat_info = config_file.stat()

            # Unix系システムでの権限チェック
            if hasattr(stat_info, 'st_mode'):
                # ファイル権限を8進数で取得
                permissions = oct(stat_info.st_mode)[-3:]

                # 他のユーザーが読み取り可能な場合は警告
                if permissions[2] != '0':
                    logger.warning(
                        f"設定ファイルが他のユーザーからアクセス可能です: {config_file}\n"
                        f"セキュリティのため権限を600に設定することをお勧めします:\n"
                        f"chmod 600 {config_file}"
                    )

        except Exception as e:
            logger.debug(f"ファイル権限チェック中にエラー（処理続行）: {e}")

    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        サポートされているプロバイダーの一覧を取得

        Returns:
            プロバイダー情報の辞書
        """
        return self.supported_providers.copy()

    def __str__(self) -> str:
        """設定の文字列表現（APIキーを除く）"""
        safe_config = self.config.copy()
        if 'api_key' in safe_config:
            safe_config['api_key'] = '*' * 8  # APIキーをマスク
        return f"ConfigManager(provider={safe_config.get('provider')}, config_path={self._config_path})"
