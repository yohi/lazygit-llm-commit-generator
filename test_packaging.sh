#!/bin/bash
# LazyGit LLM パッケージングテストスクリプト

echo "🚀 LazyGit LLM パッケージングテスト"
echo "=================================="

# 仮想環境でのテスト
echo "📦 1. 仮想環境セットアップ"
python3 -m venv test_packaging_env
source test_packaging_env/bin/activate

echo "📦 2. ビルドツールインストール"
pip install --upgrade pip setuptools wheel build

echo "📦 3. ソース配布物ビルド"
python setup.py sdist

echo "📦 4. wheel配布物ビルド"
python setup.py bdist_wheel

echo "📦 5. 配布物内容確認"
echo "--- sdist 内容 ---"
tar -tzf dist/*.tar.gz | head -20

echo "--- wheel 内容 ---"
unzip -l dist/*.whl | head -20

echo "📦 6. テストインストール"
pip install dist/*.whl

echo "📦 7. インストール確認"
python -c "import lazygit_llm; print('✅ パッケージインポート成功')"

echo "📦 8. クリーンアップ"
deactivate
rm -rf test_packaging_env

echo "✅ パッケージングテスト完了"
