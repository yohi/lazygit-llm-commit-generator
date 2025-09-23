#!/usr/bin/env python3
"""
LazyGit LLM Commit Generator インストールスクリプト

依存関係のインストール、設定ファイル作成、LazyGit統合を自動化。
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InstallationError(Exception):
    """インストールエラー"""
    pass


class Installer:
    """
    LazyGit LLM Commit Generator インストーラー

    Python環境のチェック、依存関係のインストール、設定ファイル作成、
    LazyGit統合の自動設定を行う。
    """

    def __init__(self):
        """インストーラーを初期化"""
        self.script_dir = Path(__file__).parent
        self.project_dir = self.script_dir / "lazygit-llm"
        self.config_dir = self.project_dir / "config"
        self.src_dir = self.project_dir / "src"

        # システム要件
        self.min_python_version = (3, 9)
        self.required_commands = ['git', 'python3']
        self.recommended_commands = ['uv']  # UV は推奨

        # LazyGitの設定パス候補
        self.lazygit_config_paths = [
            Path.home() / ".config" / "lazygit" / "config.yml",
            Path.home() / ".lazygit.yml",
            Path.home() / "AppData" / "Local" / "lazygit" / "config.yml",  # Windows
        ]

    def install(self, interactive: bool = True) -> bool:
        """
        インストールプロセスを実行

        Args:
            interactive: 対話モードを有効にするかどうか

        Returns:
            インストールが成功した場合True
        """
        try:
            print("🚀 LazyGit LLM Commit Generator インストール開始")
            print("=" * 60)

            # システム要件チェック
            print("\n1️⃣ システム要件チェック")
            self.check_system_requirements()

            # Python環境チェック
            print("\n2️⃣ Python環境チェック")
            self.check_python_environment()

            # UV推奨とセットアップ
            print("\n3️⃣ パッケージ管理ツール確認")
            self.check_package_manager()

            # 依存関係インストール
            print("\n4️⃣ 依存関係インストール")
            self.install_dependencies()

            # 設定ファイル作成
            print("\n5️⃣ 設定ファイル作成")
            config_created = self.create_config_file(interactive)

            # LazyGit統合
            print("\n6️⃣ LazyGit統合設定")
            lazygit_configured = self.configure_lazygit(interactive)

            # 実行可能スクリプト作成
            print("\n7️⃣ 実行可能スクリプト作成")
            self.create_executable_script()

            # 動作確認
            print("\n8️⃣ 動作確認テスト")
            self.test_installation()

            # インストール完了
            print("\n✅ インストール完了!")
            self.print_success_message(config_created, lazygit_configured)

            return True

        except InstallationError as e:
            print(f"\n❌ インストールエラー: {e}")
            return False
        except KeyboardInterrupt:
            print("\n\n⚠️ インストールがキャンセルされました")
            return False
        except Exception as e:
            logger.error(f"予期しないエラー: {e}")
            print(f"\n❌ 予期しないエラー: {e}")
            return False

    def check_system_requirements(self) -> None:
        """システム要件をチェック"""
        print("   システム要件を確認中...")

        # 必要なコマンドの存在確認
        missing_commands = []
        for cmd in self.required_commands:
            if not shutil.which(cmd):
                missing_commands.append(cmd)

        if missing_commands:
            raise InstallationError(
                f"必要なコマンドが見つかりません: {', '.join(missing_commands)}\n"
                "インストール手順:\n"
                "- Git: https://git-scm.com/downloads\n"
                "- Python 3.9+: https://www.python.org/downloads/"
            )

        print("   ✅ 必要なコマンドが確認できました")

    def check_python_environment(self) -> None:
        """Python環境をチェック"""
        print("   Python環境を確認中...")

        # Pythonバージョンチェック
        current_version = sys.version_info[:2]
        if current_version < self.min_python_version:
            raise InstallationError(
                f"Python {self.min_python_version[0]}.{self.min_python_version[1]}+ が必要です。"
                f"現在のバージョン: {current_version[0]}.{current_version[1]}"
            )

        print(f"   ✅ Python {current_version[0]}.{current_version[1]} を確認")

        # pipの確認（UV環境では不要）
        uv_available = shutil.which('uv') is not None
        if not uv_available:
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                      capture_output=True, text=True, check=True)
                print(f"   ✅ pip を確認: {result.stdout.strip()}")
            except subprocess.CalledProcessError:
                raise InstallationError("pip が利用できません。Pythonの再インストールが必要な可能性があります。")
        else:
            print("   ✅ UV環境が利用可能なためpipチェックをスキップ")

    def check_package_manager(self) -> None:
        """パッケージ管理ツール（UV推奨）をチェック"""
        print("   パッケージ管理ツールを確認中...")

        # UVの確認
        uv_available = shutil.which('uv') is not None
        if uv_available:
            try:
                result = subprocess.run(['uv', '--version'], capture_output=True, text=True, check=True)
                print(f"   ✅ UV を確認: {result.stdout.strip()}")
                print("   💡 UV環境での高速セットアップが利用可能です")
                return
            except subprocess.CalledProcessError:
                pass

        # UVが利用できない場合はpipを使用
        print("   ⚠️ UV が見つかりません。pipを使用します")
        print("   💡 高速化のためUVの導入を推奨:")
        print("      https://docs.astral.sh/uv/getting-started/installation/")

        # pipの確認
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                  capture_output=True, text=True, check=True)
            print(f"   ✅ pip を確認: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            raise InstallationError("pip が利用できません。")

    def install_dependencies(self) -> None:
        """依存関係をインストール"""
        print("   依存関係をインストール中...")

        # pyproject.tomlの存在を確認
        pyproject_file = self.script_dir / "pyproject.toml"
        requirements_file = self.script_dir / "requirements.txt"

        uv_available = shutil.which('uv') is not None

        try:
            if uv_available and pyproject_file.exists():
                # UVを使用してインストール
                print("   📦 UV環境でセットアップ中...")
                cmd = ['uv', 'sync', '--extra', 'dev']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=self.script_dir)
                print("   ✅ UV環境でのセットアップ完了")

            elif requirements_file.exists():
                # pipを使用してインストール
                print("   📦 pip環境でセットアップ中...")
                cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print("   ✅ pip環境でのセットアップ完了")

            else:
                raise InstallationError("pyproject.toml または requirements.txt が見つかりません")

            # インストールされたパッケージを確認
            self.verify_installed_packages()

        except subprocess.CalledProcessError as e:
            logger.error(f"依存関係インストールエラー: {e.stderr}")
            raise InstallationError(f"依存関係のインストールに失敗しました: {e.stderr}")

    def verify_installed_packages(self) -> None:
        """インストールされたパッケージを確認"""
        required_packages = ['openai', 'anthropic', 'google-generativeai', 'PyYAML']

        import importlib
        name_map = {
            'google-generativeai': 'google.generativeai',
            'PyYAML': 'yaml',
        }

        for package in required_packages:
            try:
                module_name = name_map.get(package, package.replace('-', '_'))
                importlib.import_module(module_name)
                print(f"   ✅ {package}")
            except ImportError:
                print(f"   ⚠️ {package} のインポートに失敗（オプショナル）")

    def create_config_file(self, interactive: bool) -> bool:
        """設定ファイルを作成"""
        print("   設定ファイルを作成中...")

        config_file = self.config_dir / "config.yml"
        example_file = self.config_dir / "config.yml.example"

        if not example_file.exists():
            raise InstallationError(f"設定例ファイルが見つかりません: {example_file}")

        if config_file.exists():
            if interactive:
                response = input(f"   設定ファイルが既に存在します。上書きしますか？ [y/N]: ")
                if response.lower() != 'y':
                    print("   ⏭️ 設定ファイルの作成をスキップ")
                    return False
            else:
                print("   ⏭️ 設定ファイルが既に存在するためスキップ")
                return False

        # 設定例をコピー
        shutil.copy2(example_file, config_file)

        # 権限を設定（セキュリティ）
        try:
            os.chmod(config_file, 0o600)
            print(f"   ✅ 設定ファイル作成: {config_file}")
            print(f"   🔒 ファイル権限を600に設定")
        except OSError as e:
            logger.warning(f"ファイル権限設定に失敗: {e}")
            print(f"   ⚠️ ファイル権限を手動で設定してください: chmod 600 {config_file}")

        if interactive:
            self.interactive_config_setup(config_file)

        return True

    def interactive_config_setup(self, config_file: Path) -> None:
        """対話形式で設定をセットアップ"""
        print("\n   📝 対話形式で設定をセットアップします（Enter でスキップ）")

        # プロバイダーの選択
        providers = {
            '1': 'openai',
            '2': 'anthropic',
            '3': 'gemini-api',
            '4': 'gemini-cli',
            '5': 'claude-code'
        }

        print("\n   使用したいLLMプロバイダーを選択してください:")
        for key, value in providers.items():
            print(f"     {key}. {value}")

        provider_choice = input("\n   選択 [1]: ").strip() or '1'
        selected_provider = providers.get(provider_choice, 'openai')

        # APIキーの設定（API型プロバイダーの場合）
        api_key = ""
        if selected_provider in ['openai', 'anthropic', 'gemini-api']:
            api_key = input(f"\n   {selected_provider} のAPIキーを入力してください（空でスキップ）: ").strip()

        # 設定ファイルを更新
        if selected_provider != 'openai' or api_key:
            self.update_config_file(config_file, selected_provider, api_key)

    def update_config_file(self, config_file: Path, provider: str, api_key: str) -> None:
        """設定ファイルを更新"""
        try:
            import yaml

            # 既存設定を読み込み
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 設定を更新
            config['provider'] = provider

            if api_key:
                config['api_key'] = api_key

            # モデル名をプロバイダーに応じて設定
            model_defaults = {
                'openai': 'gpt-4',
                'anthropic': 'claude-3-5-sonnet-20241022',
                'gemini-api': 'gemini-1.5-pro',
                'gemini-cli': 'gemini-1.5-pro',
                'claude-code': 'claude-3-5-sonnet-20241022'
            }
            config['model_name'] = model_defaults.get(provider, 'gpt-4')

            # 設定を保存
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            print(f"   ✅ 設定を更新: provider={provider}")

        except Exception as e:
            logger.error(f"設定ファイル更新エラー: {e}")
            print(f"   ⚠️ 設定ファイルの更新に失敗: {e}")

    def configure_lazygit(self, interactive: bool) -> bool:
        """LazyGitの設定を行う"""
        print("   LazyGit統合設定を確認中...")

        # LazyGitの設定ファイルを検索
        lazygit_config = self.find_lazygit_config()
        if not lazygit_config:
            if interactive:
                manual_path = input("   LazyGit設定ファイルのパスを入力してください（空でスキップ）: ").strip()
                if manual_path:
                    lazygit_config = Path(manual_path)
                else:
                    print("   ⏭️ LazyGit統合設定をスキップ")
                    return False
            else:
                print("   ⏭️ LazyGit設定ファイルが見つからないためスキップ")
                return False

        # カスタムコマンドを追加
        try:
            self.add_lazygit_custom_command(lazygit_config)
            print(f"   ✅ LazyGit統合設定完了: {lazygit_config}")
            return True
        except Exception as e:
            logger.error(f"LazyGit設定エラー: {e}")
            print(f"   ⚠️ LazyGit設定の更新に失敗: {e}")
            print("   📋 手動設定用のコマンドを後で表示します")
            return False

    def find_lazygit_config(self) -> Optional[Path]:
        """LazyGitの設定ファイルを検索"""
        for config_path in self.lazygit_config_paths:
            if config_path.exists():
                return config_path
        return None

    def add_lazygit_custom_command(self, config_file: Path) -> None:
        """LazyGitにカスタムコマンドを追加"""
        import yaml

        launcher = str(self.script_dir / "lazygit-llm-generate")
        config_path = str(self.config_dir / "config.yml")
        custom_command = {
            'key': '<c-g>',
            'command': f'git diff --staged | "{launcher}" --config "{config_path}"',
            'context': 'files',
            'description': 'Generate commit message with LLM',
            'stream': True
        }

        # 既存設定を読み込み
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # customCommands を追加
        if 'customCommands' not in config:
            config['customCommands'] = []

        # 既存のコマンドをチェック
        existing_commands = config['customCommands']
        for cmd in existing_commands:
            if cmd.get('key') == '<c-g>' and 'LLM' in cmd.get('description', ''):
                print("   ℹ️ 既存のLLMコマンドを更新")
                cmd.update(custom_command)
                break
        else:
            # 新しいコマンドを追加
            existing_commands.append(custom_command)

        # 設定ディレクトリを作成
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # 設定を保存
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    def create_executable_script(self) -> None:
        """実行可能スクリプトを作成"""
        print("   実行可能スクリプトを作成中...")

        script_path = self.script_dir / "lazygit-llm-generate"

        # UVが利用可能かチェック
        uv_available = shutil.which('uv') is not None
        pyproject_exists = (self.script_dir / "pyproject.toml").exists()

        if uv_available and pyproject_exists:
            # UV環境用のスクリプト
            script_content = f"""#!/bin/bash
# LazyGit LLM Commit Message Generator Launcher (UV version)

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

# UV環境でメインスクリプトを実行
uv run python lazygit-llm/lazygit_llm/main.py "$@"
"""
        else:
            # 従来のPython環境用スクリプト
            script_content = f"""#!/usr/bin/env python3
# LazyGit LLM Commit Message Generator Launcher

import sys
import os
from pathlib import Path

# プロジェクトディレクトリをPATHに追加
project_dir = Path(__file__).parent / "lazygit-llm"
sys.path.insert(0, str(project_dir))

# メインスクリプトを実行
if __name__ == "__main__":
    from lazygit_llm.main import main
    sys.exit(main())
"""

        # スクリプトを作成
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # 実行権限を付与
        try:
            os.chmod(script_path, 0o755)
            print(f"   ✅ 実行可能スクリプト作成: {script_path}")
        except OSError as e:
            logger.warning(f"実行権限設定に失敗: {e}")
            print(f"   ⚠️ 実行権限を手動で設定してください: chmod +x {script_path}")

    def test_installation(self) -> None:
        """インストールをテスト"""
        print("   動作確認中...")

        try:
            # UVが利用可能かチェック
            uv_available = shutil.which('uv') is not None
            pyproject_exists = (self.script_dir / "pyproject.toml").exists()

            if uv_available and pyproject_exists:
                # UV環境でテスト実行
                cmd = [
                    'uv', 'run', 'python',
                    str(self.project_dir / "lazygit_llm" / "main.py"),
                    "--config", str(self.config_dir / "config.yml"),
                    "--test-config"
                ]
            else:
                # 従来のPython環境でテスト実行
                cmd = [
                    sys.executable,
                    str(self.project_dir / "lazygit_llm" / "main.py"),
                    "--config", str(self.config_dir / "config.yml"),
                    "--test-config"
                ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=self.script_dir)

            if result.returncode == 0:
                print("   ✅ 動作確認テスト成功")
            else:
                print(f"   ⚠️ 設定テストで警告: {result.stderr}")
                print("   📝 APIキーの設定が必要な可能性があります")

        except subprocess.TimeoutExpired:
            print("   ⚠️ 設定テストがタイムアウト（正常な場合もあります）")
        except Exception as e:
            logger.warning(f"動作確認テストエラー: {e}")
            print(f"   ⚠️ 動作確認テストで問題が発生: {e}")

    def print_success_message(self, config_created: bool, lazygit_configured: bool) -> None:
        """成功メッセージを表示"""
        print("\n" + "=" * 60)
        print("🎉 インストールが完了しました！")
        print("=" * 60)

        print("\n📋 次のステップ:")

        if config_created:
            print(f"1. 設定ファイルを編集してAPIキーを設定:")
            print(f"   {self.config_dir / 'config.yml'}")
            print(f"   例: api_key: 'your-api-key-here'")

        if lazygit_configured:
            print("2. LazyGitで Ctrl+G を押してコミットメッセージを生成")
        else:
            print("2. LazyGitに以下の設定を手動で追加:")
            print("   customCommands:")
            print("     - key: '<c-g>'")
            print(f"       command: 'git diff --staged | \"{self.script_dir / 'lazygit-llm-generate'}\"'")
            print("       context: 'files'")
            print("       description: 'Generate commit message with LLM'")
            print("       stream: true")

        print("\n🔧 使用方法:")
        print("1. ファイルを変更してステージ (git add)")
        print("2. LazyGitを起動")
        print("3. Files画面で Ctrl+G を押す")
        print("4. LLMが生成したコミットメッセージを確認")

        print("\n📚 詳細情報:")
        print(f"- 設定ファイル: {self.config_dir / 'config.yml'}")
        print(f"- ログファイル: /tmp/lazygit-llm.log")
        print(f"- 実行スクリプト: {self.script_dir / 'lazygit-llm-generate'}")


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description='LazyGit LLM Commit Generator Installer')
    parser.add_argument('--non-interactive', action='store_true',
                       help='非対話モードで実行')
    args = parser.parse_args()

    installer = Installer()
    success = installer.install(interactive=not args.non_interactive)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()