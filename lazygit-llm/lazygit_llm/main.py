#!/usr/bin/env python3
"""
LazyGit LLM Commit Message Generator - メインエントリーポイント

LazyGitのカスタムコマンドから呼び出される主要スクリプト。
ステージ済みのGit差分を内部コマンドで取得し、LLMでコミットメッセージを生成する。

使用方法:
    lazygit-llm-generate

LazyGit設定例:
    customCommands:
      - key: '<c-g>'
        command: 'lazygit-llm-generate'
        context: 'files'
        description: 'Generate commit message with LLM'
        stream: true
"""

import sys
import argparse
import logging
import tempfile
from pathlib import Path
from typing import Optional

from lazygit_llm.config_manager import ConfigManager
from lazygit_llm.git_processor import GitDiffProcessor
from lazygit_llm.provider_factory import ProviderFactory
from lazygit_llm.message_formatter import MessageFormatter
from lazygit_llm.base_provider import ProviderError, AuthenticationError, ProviderTimeoutError

def setup_logging(verbose: bool = False) -> None:
    """
    ロギング設定を初期化

    Args:
        verbose: 詳細ログを有効にする場合True
    """
    level = logging.DEBUG if verbose else logging.INFO
    log_file = Path(tempfile.gettempdir()) / 'lazygit-llm.log'
    handlers = [logging.FileHandler(str(log_file), encoding='utf-8')]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stderr))
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
    )


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数を解析

    Returns:
        解析された引数
    """
    parser = argparse.ArgumentParser(
        description='LazyGit LLM Commit Message Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config/config.yml',
        help='設定ファイルのパス (default: config/config.yml)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを有効にする'
    )

    parser.add_argument(
        '--test-config',
        action='store_true',
        help='設定をテストして終了'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    return parser.parse_args()


def test_configuration(config_manager: ConfigManager) -> bool:
    """
    設定をテストして結果を表示

    Args:
        config_manager: 設定マネージャー

    Returns:
        設定が有効な場合True
    """
    logger = logging.getLogger(__name__)

    try:
        # 設定の基本検証
        if not config_manager.validate_config():
            print("❌ 設定ファイルの検証に失敗しました")
            return False

        # プロバイダーの接続テスト
        provider_factory = ProviderFactory()
        provider = provider_factory.create_provider(config_manager.config)

        if provider.test_connection():
            print("✅ 設定とプロバイダー接続は正常です")
            return True
        else:
            print("❌ プロバイダーへの接続に失敗しました")
            return False

    except (ProviderError, AuthenticationError, ProviderTimeoutError) as e:
        logger.exception("設定テスト中にエラー")
        print(f"❌ 設定テストエラー: {e}")
        return False


def main() -> int:
    """
    メイン処理

    Returns:
        終了コード (0: 成功, 1: エラー)
    """
    args = parse_arguments()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # 設定を読み込み
        config_manager = ConfigManager()
        config_path = Path(args.config)

        if not config_path.exists():
            print(f"❌ 設定ファイルが見つかりません: {config_path}")
            return 1

        config_manager.load_config(str(config_path))

        # 設定テストモード
        if args.test_config:
            return 0 if test_configuration(config_manager) else 1

        # Git差分を処理
        git_processor = GitDiffProcessor()
        if not git_processor.has_staged_changes():
            print("ステージ済みの変更が見つかりません")
            return 0
        diff_data = git_processor.read_staged_diff()

        # LLMプロバイダーを作成
        provider_factory = ProviderFactory()
        provider = provider_factory.create_provider(config_manager.config)

        # コミットメッセージを生成
        prompt_template = config_manager.get_prompt_template()
        raw_message = provider.generate_commit_message(diff_data, prompt_template)

        # メッセージをフォーマット
        formatter = MessageFormatter()
        formatted_message = formatter.format_response(raw_message)

        # LazyGitに出力
        print(formatted_message)

        logger.info("コミットメッセージ生成完了")
        return 0

    except AuthenticationError as e:
        logger.exception("認証エラー")
        print("❌ 認証エラー: APIキーを確認してください")
        return 1

    except ProviderTimeoutError as e:
        logger.exception("タイムアウトエラー")
        print("❌ タイムアウト: ネットワーク接続を確認してください")
        return 1

    except ProviderError as e:
        logger.exception("プロバイダーエラー")
        print(f"❌ プロバイダーエラー: {e}")
        return 1

    except KeyboardInterrupt:
        print("⛔ 操作が中断されました")
        return 130
    except Exception as e:
        logger.exception("予期しないエラー")
        print(f"❌ エラー: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
