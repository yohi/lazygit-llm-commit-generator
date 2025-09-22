"""
設定管理モジュール

YAML設定ファイルの読み込み、検証、環境変数展開を行う。
"""

import os
import re
import yaml
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        """設定マネージャーを初期化"""
        self.config: Dict[str, Any] = {}
    
    def load_config(self, config_path: str) -> None:
        """
        設定ファイルを読み込む
        
        Args:
            config_path: 設定ファイルのパス
            
        Raises:
            FileNotFoundError: 設定ファイルが見つからない
            yaml.YAMLError: YAML解析エラー
            ValueError: 設定ファイルの構造が不正
        """
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            # ルートは辞書である必要がある(空ファイルなどは {} とみなす)
            if raw_config is None:
                raw_config = {}
            elif not isinstance(raw_config, dict):
                logger.error("設定ファイルのルートは辞書である必要があります")
                raise ValueError("設定ファイルのルートは辞書である必要があります")
            
            # 環境変数を展開
            self.config = self._expand_environment_variables(raw_config)
            logger.info("設定ファイルを読み込みました: %s", config_path)
            
        except yaml.YAMLError:
            logger.exception("YAML解析エラー")
            raise
    
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
    
    def validate_config(self) -> bool:
        """
        設定の妥当性を検証する
        
        Returns:
            設定が有効な場合True
        """
        required_fields = ['provider', 'prompt_template']
        
        for field in required_fields:
            if field not in self.config:
                logger.error("必須設定項目が不足: %s", field)
                return False
        
        # プロバイダー設定の検証
        provider_config = self.config.get('provider', {})
        if not isinstance(provider_config, dict):
            logger.error("provider設定が不正です")
            return False
        
        provider_type = provider_config.get('type')
        if not provider_type:
            logger.error("provider.type が設定されていません")
            return False
        
        if not provider_config.get('name'):
            logger.error("provider.name が設定されていません")
            return False
        
        return True
    
    def get_prompt_template(self) -> str:
        """
        プロンプトテンプレートを取得する
        
        Returns:
            プロンプトテンプレート文字列
        """
        return self.config.get(
            'prompt_template',
            'Generate a commit message for the following changes:\n\n$diff',
        )
    
    def get_provider_config(self) -> Dict[str, Any]:
        """
        プロバイダー設定を取得する
        
        Returns:
            プロバイダー設定辞書
        """
        return self.config.get('provider', {})
