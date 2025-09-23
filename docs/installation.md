# 📦 インストールガイド

LazyGit LLM Commit Generatorの詳細なインストール手順を説明します。

## 🚀 クイックインストール

### 自動インストーラー使用（推奨）

```bash
# 1. リポジトリをクローン
git clone <repository-url>
cd lazygit-llm-commit-generator

# 2. 自動インストール実行
python3 install.py

# 3. 対話形式で設定を完了
# - プロバイダー選択
# - APIキー入力
# - LazyGit統合設定
```

## 📋 システム要件

### 必須要件

- **Python**: 3.9以上
- **Git**: 2.0以上
- **pip**: Pythonパッケージマネージャー

### 推奨要件

- **LazyGit**: 0.35以上
- **OS**: Linux, macOS, Windows 10以上

### 確認コマンド

```bash
# Python バージョン確認
python3 --version

# Git バージョン確認
git --version

# LazyGit インストール確認
lazygit --version

# pip 確認
pip3 --version
```

## 🔧 手動インストール

### 1. 依存関係のインストール

```bash
# requirements.txtから一括インストール
pip3 install -r requirements.txt

# または個別インストール
pip3 install openai anthropic google-generativeai PyYAML
```

### 2. 設定ファイル作成

```bash
# 設定ディレクトリ作成
mkdir -p ~/.config/lazygit-llm

# 設定例ファイルをコピー
cp config/config.yml.example ~/.config/lazygit-llm/config.yml

# セキュリティのため権限を設定
chmod 600 ~/.config/lazygit-llm/config.yml
```

### 3. 設定ファイル編集

```bash
# お好みのエディタで編集
nano ~/.config/lazygit-llm/config.yml
```

基本設定例：

```yaml
# プロバイダー選択
provider: "openai"

# APIキー（環境変数推奨）
api_key: "${OPENAI_API_KEY}"

# モデル設定
model_name: "gpt-4"

# タイムアウト設定
timeout: 30

# 最大トークン数
max_tokens: 100

# プロンプトテンプレート
prompt_template: |
  Based on the following git diff, generate a concise commit message
  that follows conventional commits format:

  {diff}

  Generate only the commit message, no additional text.
```

### 4. 実行可能スクリプト作成

```bash
# スクリプト作成
cat > ~/.local/bin/lazygit-llm << 'EOF'
#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# プロジェクトパスを追加
project_path = Path(__file__).parent.parent / "path/to/lazygit-llm-commit-generator"
sys.path.insert(0, str(project_path / "lazygit-llm"))

# 設定ファイルパスを環境変数で設定
os.environ.setdefault('LAZYGIT_LLM_CONFIG', str(Path.home() / ".config/lazygit-llm/config.yml"))

if __name__ == "__main__":
    from src.main import main
    sys.exit(main())
EOF

# 実行権限を付与
chmod +x ~/.local/bin/lazygit-llm
```

### 5. LazyGit統合設定

LazyGitの設定ファイル（`~/.config/lazygit/config.yml`）に以下を追加：

```yaml
customCommands:
  - key: '<c-g>'
    command: 'git diff --staged | ~/.local/bin/lazygit-llm'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

## 🌍 プラットフォーム別設定

### Linux

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip git

# Arch Linux
sudo pacman -S python python-pip git

# LazyGit インストール（Snap）
sudo snap install lazygit

# または AppImage
wget https://github.com/jesseduffield/lazygit/releases/latest/download/lazygit_Linux_x86_64.tar.gz
tar xf lazygit_Linux_x86_64.tar.gz
sudo mv lazygit /usr/local/bin/
```

### macOS

```bash
# Homebrew使用
brew install python git lazygit

# MacPorts使用
sudo port install python39 git lazygit
```

### Windows

```powershell
# Chocolatey使用
choco install python git lazygit

# Scoop使用
scoop install python git lazygit

# または手動インストール
# 1. Python: https://www.python.org/downloads/
# 2. Git: https://git-scm.com/download/win
# 3. LazyGit: https://github.com/jesseduffield/lazygit/releases
```

## 🔑 APIキー設定

### 環境変数での設定（推奨）

```bash
# ~/.bashrc または ~/.zshrc に追加
export OPENAI_API_KEY="your-openai-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GOOGLE_API_KEY="your-google-api-key"

# 設定を再読み込み
source ~/.bashrc  # または ~/.zshrc
```

### 設定ファイルでの設定

```yaml
# ~/.config/lazygit-llm/config.yml
api_key: "your-actual-api-key"  # 非推奨：セキュリティリスク
```

### APIキー取得方法

#### OpenAI
1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. API Keys セクションで新しいキーを生成
3. 使用量制限を設定（推奨）

#### Anthropic
1. [Anthropic Console](https://console.anthropic.com/) にアクセス
2. API Keys でキーを生成
3. 利用規約を確認

#### Google Gemini
1. [Google AI Studio](https://makersuite.google.com/) にアクセス
2. API キーを取得
3. 利用制限を確認

## 🧪 インストール確認

### 基本動作テスト

```bash
# 設定テスト
python3 lazygit-llm/src/main.py --test-config

# ヘルプ表示
python3 lazygit-llm/src/main.py --help

# 詳細ログでテスト
python3 lazygit-llm/src/main.py --verbose --test-config
```

### LazyGit統合テスト

```bash
# テストリポジトリ作成
mkdir test-repo && cd test-repo
git init

# テストファイル作成
echo "Hello World" > test.txt
git add test.txt

# LazyGitを起動してCtrl+Gをテスト
lazygit
```

### 期待される出力

```
✅ 設定ファイル読み込み成功
✅ プロバイダー初期化成功
✅ API接続テスト成功
✅ Git差分処理テスト成功
```

## 🐛 インストール時のトラブルシューティング

### よくある問題

#### 1. Python バージョンエラー
```
Python 3.8 は対応していません
```
**解決策：**
```bash
# Python 3.9+ をインストール
# Ubuntu
sudo apt install python3.9

# macOS
brew install python@3.9
```

#### 2. pip インストールエラー
```
pip: command not found
```
**解決策：**
```bash
# pip インストール
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
```

#### 3. 権限エラー
```
Permission denied: ~/.config/lazygit-llm/config.yml
```
**解決策：**
```bash
# 権限修正
chmod 600 ~/.config/lazygit-llm/config.yml
sudo chown $USER:$USER ~/.config/lazygit-llm/config.yml
```

#### 4. LazyGit設定エラー
```
LazyGit設定ファイルが見つかりません
```
**解決策：**
```bash
# LazyGit設定ディレクトリ作成
mkdir -p ~/.config/lazygit

# 初期設定ファイル作成
touch ~/.config/lazygit/config.yml
```

### デバッグ手順

1. **詳細ログの有効化**
   ```bash
   python3 lazygit-llm/src/main.py --verbose
   ```

2. **設定ファイルの確認**
   ```bash
   cat ~/.config/lazygit-llm/config.yml
   ```

3. **依存関係の確認**
   ```bash
   pip3 list | grep -E "(openai|anthropic|google-generativeai|PyYAML)"
   ```

4. **環境変数の確認**
   ```bash
   env | grep -E "(OPENAI|ANTHROPIC|GOOGLE)_API_KEY"
   ```

## 🔄 アップデート

### 自動アップデート

```bash
# プロジェクトディレクトリで
git pull origin main
python3 install.py
```

### 手動アップデート

```bash
# 依存関係の更新
pip3 install -r requirements.txt --upgrade

# 設定ファイルの確認
# 新しい設定項目があれば追加
```

## 🗑️ アンインストール

### 完全削除

```bash
# 設定ファイル削除
rm -rf ~/.config/lazygit-llm

# 実行スクリプト削除
rm -f ~/.local/bin/lazygit-llm

# LazyGit設定から削除
# ~/.config/lazygit/config.yml の customCommands から該当行を削除

# プロジェクトディレクトリ削除
rm -rf /path/to/lazygit-llm-commit-generator
```

### LazyGit統合のみ削除

LazyGitの設定ファイルから以下の部分を削除：

```yaml
customCommands:
  - key: '<c-g>'
    command: '...'
    # この部分を削除
```

---

インストールに関してご質問がありましたら、GitHubのIssuesでお気軽にお尋ねください。