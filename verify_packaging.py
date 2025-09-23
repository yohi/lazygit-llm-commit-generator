#!/usr/bin/env python3
"""
LazyGit LLM パッケージング検証スクリプト
"""

import os
import sys
from pathlib import Path

def check_package_structure():
    """パッケージ構造を検証"""
    print("🔍 パッケージ構造検証")
    print("=" * 50)

    root = Path(__file__).parent

    # 重要なファイル・ディレクトリの存在確認
    critical_paths = [
        "setup.py",
        "MANIFEST.in",
        "README.md",
        "requirements.txt",
        "config/config.yml.example",
        "docs/",
        "lazygit-llm/",
        "lazygit-llm/lazygit_llm/",
        "lazygit-llm/config/config.yml.example",
    ]

    all_good = True
    for path_str in critical_paths:
        path = root / path_str
        if path.exists():
            print(f"✅ {path_str}")
        else:
            print(f"❌ {path_str} - 存在しません")
            all_good = False

    return all_good

def check_manifest_content():
    """MANIFEST.in の内容確認"""
    print("\n🔍 MANIFEST.in 内容確認")
    print("=" * 50)

    manifest_path = Path(__file__).parent / "MANIFEST.in"
    if not manifest_path.exists():
        print("❌ MANIFEST.in が存在しません")
        return False

    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 重要な包含設定の確認
    required_includes = [
        "recursive-include config",
        "recursive-include docs",
        "include README.md",
        "include requirements.txt"
    ]

    all_good = True
    for include in required_includes:
        if include in content:
            print(f"✅ {include}")
        else:
            print(f"❌ {include} - 設定されていません")
            all_good = False

    return all_good

def check_setup_py():
    """setup.py の設定確認"""
    print("\n🔍 setup.py 設定確認")
    print("=" * 50)

    setup_path = Path(__file__).parent / "setup.py"
    if not setup_path.exists():
        print("❌ setup.py が存在しません")
        return False

    with open(setup_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 重要な設定の確認
    required_settings = [
        'include_package_data=True',
        'packages=find_packages(where="lazygit-llm")',
        'package_dir={"": "lazygit-llm"}',
    ]

    all_good = True
    for setting in required_settings:
        if setting in content:
            print(f"✅ {setting}")
        else:
            print(f"❌ {setting} - 設定されていません")
            all_good = False

    # package_data の空設定確認（MANIFEST.in使用のため）
    if 'package_data=' in content and '{}' not in content and '"": [' not in content:
        print("⚠️  package_data が設定されています - MANIFEST.in使用時は不要です")
    else:
        print("✅ package_data設定は適切です（MANIFEST.in使用）")

    return all_good

def main():
    """メイン検証ロジック"""
    print("🚀 LazyGit LLM パッケージング検証")
    print("=" * 60)

    structure_ok = check_package_structure()
    manifest_ok = check_manifest_content()
    setup_ok = check_setup_py()

    print("\n📊 検証結果サマリー")
    print("=" * 50)

    if structure_ok and manifest_ok and setup_ok:
        print("✅ 全ての検証にパスしました！")
        print("📦 パッケージングの準備が完了しています")
        return 0
    else:
        print("❌ 一部の検証に失敗しました")
        print("🔧 上記の問題を修正してください")
        return 1

if __name__ == "__main__":
    sys.exit(main())
