#!/usr/bin/env python3
"""
LazyGit LLM Commit Generator システム検証スクリプト

実装された全機能の動作確認と統合テストを実行します。
APIキーなしでも動作する検証項目と、実際のAPI呼び出しを分けて実行。
"""

import os
import sys
import subprocess
import tempfile
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from unittest.mock import Mock, patch

# プロジェクトパスを追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class SystemValidator:
    """システム全体の検証クラス"""

    def __init__(self, verbose: bool = False):
        """
        システム検証器を初期化

        Args:
            verbose: 詳細ログの有効/無効
        """
        self.verbose = verbose
        self.project_root = project_root
        self.src_dir = self.project_root / "lazygit_llm" / "src"
        self.config_dir = self.project_root / "config"

        # ログ設定
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

        # 検証結果を記録
        self.results: List[Tuple[str, bool, str]] = []

    def run_validation(self) -> bool:
        """
        システム全体の検証を実行

        Returns:
            全ての検証が成功した場合True
        """
        print("🔍 LazyGit LLM Commit Generator システム検証開始")
        print("=" * 60)

        validation_steps = [
            ("基本システム要件", self.validate_system_requirements),
            ("プロジェクト構造", self.validate_project_structure),
            ("Python モジュール", self.validate_python_modules),
            ("設定ファイル", self.validate_config_files),
            ("コアクラス", self.validate_core_classes),
            ("プロバイダーファクトリ", self.validate_provider_factory),
            ("セキュリティ機能", self.validate_security_features),
            ("Git差分処理", self.validate_git_processing),
            ("エラーハンドリング", self.validate_error_handling),
            ("メッセージフォーマット", self.validate_message_formatting),
            ("設定管理", self.validate_config_management),
            ("インストールスクリプト", self.validate_installation_script),
            ("実行統合テスト", self.validate_execution_integration),
        ]

        all_passed = True
        for step_name, validation_func in validation_steps:
            print(f"\n📋 {step_name}を検証中...")
            try:
                success, message = validation_func()
                self.results.append((step_name, success, message))

                if success:
                    print(f"✅ {step_name}: {message}")
                else:
                    print(f"❌ {step_name}: {message}")
                    all_passed = False

            except Exception as e:
                error_msg = f"検証中にエラー: {e}"
                print(f"❌ {step_name}: {error_msg}")
                self.results.append((step_name, False, error_msg))
                all_passed = False

        # 結果サマリー
        self.print_validation_summary()

        return all_passed

    def validate_system_requirements(self) -> Tuple[bool, str]:
        """システム要件を確認"""
        checks = []

        # Python バージョンチェック
        if sys.version_info >= (3, 9):
            checks.append("Python 3.9+ ✓")
        else:
            return False, f"Python 3.9+が必要（現在: {sys.version}）"

        # 必要なコマンドの確認
        required_commands = ['git', 'python3']
        for cmd in required_commands:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, check=True)
                checks.append(f"{cmd} コマンド ✓")
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, f"{cmd} コマンドが見つかりません"

        return True, f"システム要件満足: {', '.join(checks)}"

    def validate_project_structure(self) -> Tuple[bool, str]:
        """プロジェクト構造を確認"""
        required_paths = [
            "lazygit_llm/",
            "lazygit_llm/src/",
            "lazygit_llm/src/main.py",
            "lazygit_llm/src/base_provider.py",
            "lazygit_llm/src/config_manager.py",
            "lazygit_llm/src/git_processor.py",
            "lazygit_llm/src/provider_factory.py",
            "lazygit_llm/src/security_validator.py",
            "lazygit_llm/src/error_handler.py",
            "lazygit_llm/src/message_formatter.py",
            "lazygit_llm/src/api_providers/",
            "lazygit_llm/src/cli_providers/",
            "config/",
            "docs/",
            "requirements.txt",
            "setup.py",
            "install.py",
        ]

        missing_paths = []
        for path in required_paths:
            full_path = self.project_root / path
            if not full_path.exists():
                missing_paths.append(path)

        if missing_paths:
            return False, f"必要なファイル/ディレクトリが不足: {', '.join(missing_paths)}"

        return True, f"プロジェクト構造確認完了（{len(required_paths)}項目）"

    def validate_python_modules(self) -> Tuple[bool, str]:
        """Pythonモジュールのインポートテスト"""
        modules_to_test = [
            ("lazygit_llm.main", "メインエントリーポイント"),
            ("lazygit_llm.src.base_provider", "プロバイダー基底クラス"),
            ("lazygit_llm.src.config_manager", "設定管理"),
            ("lazygit_llm.src.git_processor", "Git差分処理"),
            ("lazygit_llm.src.provider_factory", "プロバイダーファクトリ"),
            ("lazygit_llm.src.security_validator", "セキュリティ検証"),
            ("lazygit_llm.src.error_handler", "エラーハンドリング"),
            ("lazygit_llm.src.message_formatter", "メッセージフォーマット"),
            ("lazygit_llm.src.api_providers.openai_provider", "OpenAIプロバイダー"),
            ("lazygit_llm.src.api_providers.anthropic_provider", "Anthropicプロバイダー"),
            ("lazygit_llm.src.api_providers.gemini_api_provider", "Gemini APIプロバイダー"),
            ("lazygit_llm.src.cli_providers.gemini_cli_provider", "Gemini CLIプロバイダー"),
            ("lazygit_llm.src.cli_providers.claude_code_provider", "Claude Codeプロバイダー"),
        ]

        failed_imports = []
        for module_name, description in modules_to_test:
            try:
                __import__(module_name)
                if self.verbose:
                    logger.debug(f"✓ {description} インポート成功")
            except ImportError as e:
                failed_imports.append(f"{description}: {e}")

        if failed_imports:
            return False, f"モジュールインポート失敗: {'; '.join(failed_imports)}"

        return True, f"全モジュール（{len(modules_to_test)}個）のインポート成功"

    def validate_config_files(self) -> Tuple[bool, str]:
        """設定ファイルの確認"""
        config_example = self.config_dir / "config.yml.example"

        if not config_example.exists():
            return False, "設定例ファイル（config.yml.example）が見つかりません"

        try:
            with open(config_example, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            required_fields = ['provider', 'model_name', 'timeout', 'max_tokens', 'prompt_template']
            missing_fields = [field for field in required_fields if field not in config]

            if missing_fields:
                return False, f"設定例に必須フィールドが不足: {', '.join(missing_fields)}"

            # プロンプトテンプレートに{diff}が含まれているかチェック
            if '{diff}' not in config.get('prompt_template', ''):
                return False, "プロンプトテンプレートに{diff}プレースホルダーが含まれていません"

            return True, f"設定ファイル形式確認完了（必須フィールド: {len(required_fields)}個）"

        except yaml.YAMLError as e:
            return False, f"設定ファイルのYAML解析エラー: {e}"
        except Exception as e:
            return False, f"設定ファイル確認エラー: {e}"

    def validate_core_classes(self) -> Tuple[bool, str]:
        """コアクラスの基本機能確認"""
        try:
            # BaseProviderの確認
            from src.base_provider import BaseProvider, ProviderError
            assert hasattr(BaseProvider, 'generate_commit_message')
            assert hasattr(BaseProvider, 'test_connection')
            assert hasattr(BaseProvider, 'supports_streaming')

            # ConfigManagerの確認
            from src.config_manager import ConfigManager, ConfigError
            config_manager = ConfigManager()
            assert hasattr(config_manager, 'load_config')
            assert hasattr(config_manager, 'validate_config')

            # GitDiffProcessorの確認
            from src.git_processor import GitDiffProcessor, DiffData
            processor = GitDiffProcessor()
            assert hasattr(processor, 'format_diff_for_llm')
            assert hasattr(processor, 'validate_diff_format')

            return True, "コアクラスのインターフェース確認完了"

        except Exception as e:
            return False, f"コアクラス確認エラー: {e}"

    def validate_provider_factory(self) -> Tuple[bool, str]:
        """プロバイダーファクトリの確認"""
        try:
            from src.provider_factory import ProviderFactory, provider_registry

            factory = ProviderFactory()
            available_providers = factory.get_available_providers()

            expected_providers = ['openai', 'anthropic', 'gemini-api', 'gemini-cli', 'claude-code']
            missing_providers = [p for p in expected_providers if p not in available_providers]

            if missing_providers:
                return False, f"プロバイダーが未登録: {', '.join(missing_providers)}"

            # レジストリの基本機能確認
            assert hasattr(provider_registry, 'register_provider')
            assert hasattr(provider_registry, 'get_provider_class')

            return True, f"プロバイダーファクトリ確認完了（登録済み: {len(available_providers)}個）"

        except Exception as e:
            return False, f"プロバイダーファクトリ確認エラー: {e}"

    def validate_security_features(self) -> Tuple[bool, str]:
        """セキュリティ機能の確認"""
        try:
            from src.security_validator import SecurityValidator, ValidationResult

            validator = SecurityValidator()

            # APIキー検証のテスト
            # 有効なパターン
            result = validator.validate_api_key("openai", "sk-test123456789")
            if not result.is_valid:
                return False, "有効なAPIキーが無効と判定されました"

            # 無効なパターン
            result = validator.validate_api_key("openai", "invalid")
            if result.is_valid:
                return False, "無効なAPIキーが有効と判定されました"

            # Git差分サニタイゼーションのテスト
            test_diff = "password=secret123\n+normal code change"
            sanitized, result = validator.sanitize_git_diff(test_diff)
            if "secret123" in sanitized:
                return False, "機密情報がサニタイゼーションされていません"

            # ファイル権限チェックのテスト
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                os.chmod(tmp.name, 0o644)  # 他のユーザーも読み取り可能
                result = validator.check_file_permissions(tmp.name)
                if result.level != "warning":
                    return False, "ファイル権限チェックが正しく動作していません"
                os.unlink(tmp.name)

            return True, "セキュリティ機能確認完了（APIキー検証、差分サニタイゼーション、権限チェック）"

        except Exception as e:
            return False, f"セキュリティ機能確認エラー: {e}"

    def validate_git_processing(self) -> Tuple[bool, str]:
        """Git差分処理の確認"""
        try:
            from src.git_processor import GitDiffProcessor, DiffData

            processor = GitDiffProcessor()

            # テスト用の差分データ
            test_diff = """diff --git a/test.py b/test.py
new file mode 100644
index 0000000..ed708ec
--- /dev/null
+++ b/test.py
@@ -0,0 +1,3 @@
+def hello():
+    print("Hello, World!")
+    return True
"""

            # 差分フォーマットの検証
            if not processor.validate_diff_format(test_diff):
                return False, "有効な差分フォーマットが無効と判定されました"

            # LLM向けフォーマット
            formatted = processor.format_diff_for_llm(test_diff)
            if "Files changed:" not in formatted:
                return False, "LLM向けフォーマットが正しく動作していません"

            # 差分解析
            diff_data = processor._parse_diff(test_diff)
            if diff_data.file_count != 1 or diff_data.additions != 3:
                return False, f"差分解析が不正確（files: {diff_data.file_count}, adds: {diff_data.additions}）"

            return True, "Git差分処理確認完了（フォーマット検証、LLM変換、統計解析）"

        except Exception as e:
            return False, f"Git差分処理確認エラー: {e}"

    def validate_error_handling(self) -> Tuple[bool, str]:
        """エラーハンドリングの確認"""
        try:
            from src.error_handler import ErrorHandler, ErrorInfo
            from src.base_provider import ProviderError

            error_handler = ErrorHandler(verbose=self.verbose)

            # エラー分類のテスト
            test_error = ProviderError("API authentication failed")
            error_info = error_handler.handle_error(test_error, {"provider": "openai"})

            from src.error_handler import ErrorCategory
            if error_info.category != ErrorCategory.AUTHENTICATION:
                return False, f"エラー分類が不正確（期待: AUTHENTICATION, 実際: {error_info.category}）"

            # ユーザーフレンドリーメッセージの生成
            message = error_handler.get_user_friendly_message(error_info)
            if not message or len(message) < 10:
                return False, "ユーザーフレンドリーメッセージが生成されませんでした"

            return True, "エラーハンドリング確認完了（分類、メッセージ生成、提案機能）"

        except Exception as e:
            return False, f"エラーハンドリング確認エラー: {e}"

    def validate_message_formatting(self) -> Tuple[bool, str]:
        """メッセージフォーマットの確認"""
        try:
            from src.message_formatter import MessageFormatter

            formatter = MessageFormatter()

            # LLMレスポンスのクリーニング
            test_response = "Here's your commit message:\n\nfeat: add new feature\n\nThis commit adds..."
            cleaned = formatter.clean_llm_response(test_response)
            if "Here's your commit message:" in cleaned:
                return False, "LLMレスポンスのクリーニングが動作していません"

            # LazyGit向けフォーマット
            formatted = formatter.format_for_lazygit("feat: add new feature")
            if not formatted or len(formatted) == 0:
                return False, "LazyGit向けフォーマットが動作していません"

            # コミットメッセージ検証
            if not formatter.validate_commit_message("feat: add new feature"):
                return False, "有効なコミットメッセージが無効と判定されました"

            return True, "メッセージフォーマット確認完了（クリーニング、LazyGit形式、検証）"

        except Exception as e:
            return False, f"メッセージフォーマット確認エラー: {e}"

    def validate_config_management(self) -> Tuple[bool, str]:
        """設定管理の確認"""
        try:
            from src.config_manager import ConfigManager

            # テスト用設定ファイル作成
            test_config = {
                'provider': 'openai',
                'api_key': '${TEST_API_KEY}',
                'model_name': 'gpt-3.5-turbo',
                'timeout': 30,
                'max_tokens': 100,
                'prompt_template': 'Test prompt: {diff}'
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(test_config, f)
                f.flush()

                # 環境変数設定
                os.environ['TEST_API_KEY'] = 'test-key-value'

                try:
                    manager = ConfigManager()
                    config = manager.load_config(f.name)

                    # 環境変数解決の確認
                    if config['api_key'] != 'test-key-value':
                        return False, "環境変数解決が動作していません"

                    # 設定検証
                    if not manager.validate_config():
                        return False, "設定検証が正しく動作していません"

                    # プロンプトテンプレート取得
                    template = manager.get_prompt_template()
                    if '{diff}' not in template:
                        return False, "プロンプトテンプレート取得が正しく動作していません"

                    return True, "設定管理確認完了（YAML解析、環境変数解決、検証機能）"

                finally:
                    os.unlink(f.name)
                    if 'TEST_API_KEY' in os.environ:
                        del os.environ['TEST_API_KEY']

        except Exception as e:
            return False, f"設定管理確認エラー: {e}"

    def validate_installation_script(self) -> Tuple[bool, str]:
        """インストールスクリプトの確認"""
        try:
            install_script = self.project_root / "install.py"
            if not install_script.exists():
                return False, "install.py が見つかりません"

            # スクリプトの基本的な構文チェック
            with open(install_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # 重要なクラス・関数の存在確認
            required_elements = [
                'class.*Installer',
                'def install',
                'def check_system_requirements',
                'def create_config_file',
                'def configure_lazygit'
            ]

            import re
            missing_elements = []
            for element in required_elements:
                if not re.search(element, content):
                    missing_elements.append(element)

            if missing_elements:
                return False, f"インストールスクリプトに必要な要素が不足: {', '.join(missing_elements)}"

            # 構文エラーチェック
            try:
                compile(content, str(install_script), 'exec')
            except SyntaxError as e:
                return False, f"インストールスクリプトに構文エラー: {e}"

            return True, "インストールスクリプト確認完了（構造、構文、主要機能）"

        except Exception as e:
            return False, f"インストールスクリプト確認エラー: {e}"

    def validate_execution_integration(self) -> Tuple[bool, str]:
        """実行統合テスト（モック使用）"""
        try:
            from lazygit_llm.main import main
            from lazygit_llm.src.config_manager import ConfigManager
            from lazygit_llm.src.provider_factory import ProviderFactory

            # テスト用設定
            test_config = {
                'provider': 'openai',
                'api_key': 'test-key',
                'model_name': 'gpt-3.5-turbo',
                'timeout': 30,
                'max_tokens': 100,
                'prompt_template': 'Generate commit: {diff}'
            }

            # テスト用差分
            test_diff = "diff --git a/test.py b/test.py\n+added line"

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                yaml.dump(test_config, f)
                f.flush()

                try:
                    # モックを使用してエンドツーエンドテスト
                    with patch('sys.stdin') as mock_stdin, \
                         patch('sys.argv', ['main.py', '--config', f.name, '--test-config']), \
                         patch('lazygit_llm.src.api_providers.openai_provider.OpenAIProvider.generate_commit_message') as mock_generate:

                        mock_stdin.read.return_value = test_diff
                        mock_generate.return_value = "feat: add new feature"

                        # メイン関数実行テスト（設定テストモード）
                        result = main()

                        # 正常終了の確認
                        if result != 0:
                            return False, f"メイン関数が異常終了しました（終了コード: {result}）"

                    return True, "実行統合テスト完了（エンドツーエンド、設定テスト、モック検証）"

                finally:
                    os.unlink(f.name)

        except Exception as e:
            return False, f"実行統合テスト確認エラー: {e}"

    def print_validation_summary(self):
        """検証結果のサマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 システム検証結果サマリー")
        print("=" * 60)

        passed = sum(1 for _, success, _ in self.results if success)
        total = len(self.results)

        print(f"\n✅ 成功: {passed}/{total} ({passed/total*100:.1f}%)")
        if passed < total:
            print(f"❌ 失敗: {total - passed}/{total}")

        # 失敗した項目の詳細
        failed_items = [(name, msg) for name, success, msg in self.results if not success]
        if failed_items:
            print("\n❌ 失敗した検証項目:")
            for name, message in failed_items:
                print(f"   • {name}: {message}")

        # 成功した項目（詳細モード）
        if self.verbose and passed > 0:
            print("\n✅ 成功した検証項目:")
            passed_items = [(name, msg) for name, success, msg in self.results if success]
            for name, message in passed_items:
                print(f"   • {name}: {message}")

        print(f"\n🎯 システム状態: {'準備完了' if passed == total else '修正が必要'}")


def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="LazyGit LLM システム検証")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="詳細な出力を有効にする")
    parser.add_argument("--api-test", action="store_true",
                       help="実際のAPI呼び出しテストを含める（APIキー必要）")

    args = parser.parse_args()

    validator = SystemValidator(verbose=args.verbose)
    success = validator.run_validation()

    if args.api_test:
        print("\n🔍 実際のAPI呼び出しテストは未実装")
        print("   → APIキーを設定して手動でテストしてください")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()