# LazyGit LLM Commit Generator - ユーザーガイド

## 🚀 クイックスタート

### 1. インストール

```bash
# プロジェクトをクローン
git clone https://github.com/yohi/lazygit-llm-commit-generator.git
cd lazygit-llm-commit-generator

# インストールスクリプトを実行
python3 install.py
```

### 2. 基本設定

```bash
# 設定ファイルをコピー
cp lazygit-llm/config/config.yml.example ~/.config/lazygit-llm/config.yml

# 設定を編集
vi ~/.config/lazygit-llm/config.yml
```

### 3. 環境変数設定

```bash
# 使用するLLMサービスのAPIキーを設定
export OPENAI_API_KEY="sk-..."        # OpenAI使用時
export ANTHROPIC_API_KEY="sk-ant-..."  # Claude使用時
export GOOGLE_API_KEY="AI..."          # Gemini使用時
```

### 4. LazyGit統合

LazyGitの設定ファイル (`~/.config/lazygit/config.yml`) に以下を追加：

```yaml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

## 💡 基本的な使い方

### LazyGitでの使用

1. LazyGitを起動: `lazygit`
2. ファイルをステージング: `Space`キー
3. **Ctrl+G**を押してLLMコミットメッセージ生成
4. 生成されたメッセージを確認・編集
5. コミット実行

### コマンドラインでの使用

```bash
# 基本使用法
git add .
lazygit-llm-generate

# 設定ファイル指定
lazygit-llm-generate --config /path/to/config.yml

# 詳細ログ出力
lazygit-llm-generate --verbose

# 設定テスト
lazygit-llm-generate --test-config
```

## ⚙️ 設定詳細

### プロバイダー設定

#### OpenAI GPT

```yaml
provider: "openai"
model_name: "gpt-4"  # 推奨: gpt-4, 代替: gpt-3.5-turbo
api_key: "${OPENAI_API_KEY}"
additional_params:
  temperature: 0.3    # 創造性 (0.0-1.0)
  top_p: 1.0         # 多様性制御
```

**特徴**:
- 高品質なコミットメッセージ生成
- 複雑なdiffも適切に理解
- レスポンス速度: 2-5秒

#### Anthropic Claude

```yaml
provider: "anthropic"
model_name: "claude-3-5-sonnet-20241022"  # 最新推奨
api_key: "${ANTHROPIC_API_KEY}"
additional_params:
  max_tokens_to_sample: 100
```

**特徴**:
- 非常に高精度な分析
- 適切なConventional Commits形式
- レスポンス速度: 3-7秒

#### Google Gemini API

```yaml
provider: "gemini-api"
model_name: "gemini-1.5-pro"  # 推奨
api_key: "${GOOGLE_API_KEY}"
additional_params:
  safety_settings:
    - category: "HARM_CATEGORY_DANGEROUS_CONTENT"
      threshold: "BLOCK_MEDIUM_AND_ABOVE"
```

#### Claude Code CLI

```yaml
provider: "claude-code"
model_name: "claude-3-5-sonnet-20241022"
# CLIプロバイダーではapi_key不要
```

**前提条件**: Claude Codeがインストール・認証済み

#### Gemini CLI (gcloud)

```yaml
provider: "gemini-cli"
model_name: "gemini-1.5-pro"
additional_params:
  project_id: "your-gcp-project-id"
  location: "us-central1"
```

**前提条件**: gcloud CLIがインストール・認証済み

### プロンプトテンプレート

#### 基本的な英語コミット

```yaml
prompt_template: |
  Based on the following git diff, generate a concise commit message:

  {diff}

  Generate only the commit message, no additional text.
```

#### Conventional Commits形式

```yaml
prompt_template: |
  Based on the following git diff, generate a commit message following the Conventional Commits specification:

  Format: <type>[optional scope]: <description>
  Types: feat, fix, docs, style, refactor, test, chore

  {diff}

  Generate only the commit message, no additional text.
```

#### 日本語コミット

```yaml
prompt_template: |
  以下のgit diffに基づいて、簡潔で分かりやすいコミットメッセージを日本語で生成してください：

  {diff}

  コミットメッセージのみを出力してください。
```

#### Gitmoji + Conventional Commits

```yaml
prompt_template: |
  Based on the following git diff, generate a commit message with gitmoji and conventional commits format:

  Format: <gitmoji> <type>[optional scope]: <description>

  {diff}

  Generate only the commit message with appropriate emoji, no additional text.
```

## 🔧 高度な設定

### パフォーマンス調整

```yaml
# レスポンス時間優先
timeout: 15           # タイムアウト短縮
max_tokens: 50        # トークン数制限
additional_params:
  temperature: 0.1    # 一貫性重視
  stream: true        # ストリーミング有効

# 品質優先
timeout: 60
max_tokens: 200
additional_params:
  temperature: 0.3
```

### セキュリティ設定

```bash
# 設定ファイルのパーミッション設定
chmod 600 ~/.config/lazygit-llm/config.yml

# 実行ファイルのパーミッション
chmod +x ~/.local/bin/lazygit-llm-generate
```

### 複数プロファイル

```bash
# プロファイル別設定
~/.config/lazygit-llm/
├── config.yml          # デフォルト
├── config-work.yml     # 仕事用
└── config-personal.yml # 個人用

# 使用時
lazygit-llm-generate --config ~/.config/lazygit-llm/config-work.yml
```

## 🛠 トラブルシューティング

### よくある問題と解決方法

#### 1. 設定ファイルが見つからない

```text
❌ 設定ファイルが見つかりません: config/config.yml
```

**解決方法**:
```bash
# 設定ファイルを作成
mkdir -p ~/.config/lazygit-llm
cp lazygit-llm/config/config.yml.example ~/.config/lazygit-llm/config.yml
```

#### 2. APIキー認証エラー

```text
❌ 認証エラー: APIキーを確認してください
```

**解決方法**:
```bash
# 環境変数を確認
echo $OPENAI_API_KEY  # 空の場合は設定が必要

# 環境変数を設定
export OPENAI_API_KEY="sk-..."

# 永続化 (.bashrc/.zshrcに追加)
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.bashrc
```

#### 3. Pythonモジュールエラー

```text
ModuleNotFoundError: No module named 'openai'
```

**解決方法**:
```bash
# 依存関係をインストール
pip install -r requirements.txt

# または個別インストール
pip install openai anthropic google-generativeai PyYAML
```

#### 4. LazyGitでCtrl+Gが動かない

**解決方法**:
```bash
# LazyGit設定を確認
cat ~/.config/lazygit/config.yml

# パスを確認
which lazygit-llm-generate

# 実行権限を確認
ls -la ~/.local/bin/lazygit-llm-generate
```

#### 5. タイムアウトエラー

```text
❌ タイムアウト: ネットワーク接続を確認してください
```

**解決方法**:
```yaml
# 設定ファイルでタイムアウトを延長
timeout: 60  # 60秒に延長
```

#### 6. レート制限エラー

```text
❌ プロバイダーエラー: 利用制限に達しました
```

**解決方法**:
- APIの利用制限を確認
- 別のプロバイダーに切り替え
- 時間をおいて再実行

### デバッグ手順

#### 1. 詳細ログ確認

```bash
# 詳細ログで実行
lazygit-llm-generate --verbose

# ログファイルの場所が表示される
# 例: ログファイル: /tmp/lazygit-llm-xyz.log
```

#### 2. 設定テスト

```bash
# 設定とプロバイダー接続をテスト
lazygit-llm-generate --test-config
```

#### 3. Git状態確認

```bash
# ステージ済み変更を確認
git diff --staged

# 変更がない場合は何かをステージ
echo "test" > test.txt
git add test.txt
```

## 📊 使用統計とモニタリング

### パフォーマンス指標

| プロバイダー | 平均レスポンス時間 | 品質スコア | コスト |
|------------|-----------------|-----------|-------|
| GPT-4 | 3-5秒 | ⭐⭐⭐⭐⭐ | 高 |
| Claude 3.5 | 4-7秒 | ⭐⭐⭐⭐⭐ | 中 |
| Gemini Pro | 2-4秒 | ⭐⭐⭐⭐ | 低 |

### 使用量制限

- **OpenAI**: RPM制限に注意
- **Anthropic**: 月間トークン制限
- **Google**: 1日あたりのリクエスト制限
- **CLI**: ローカル制限なし（認証済み）

### ログ分析

```bash
# ログからエラーパターンを確認
grep "ERROR" /tmp/lazygit-llm-*.log

# 使用頻度を確認
grep "コミットメッセージ生成完了" /tmp/lazygit-llm-*.log | wc -l
```

## 🎯 ベストプラクティス

### 効果的なプロンプト設計

1. **明確な指示**: 求める形式を具体的に指定
2. **制約設定**: 文字数や形式の制限を明記
3. **例示**: 期待する出力例を含める
4. **言語指定**: 日本語/英語を明確に指定

### プロバイダー選択基準

- **品質重視**: Claude 3.5 Sonnet
- **速度重視**: Gemini Pro
- **コスト重視**: GPT-3.5-turbo
- **オフライン**: CLI系プロバイダー

### セキュリティベストプラクティス

1. **APIキー管理**: 環境変数を使用、平文保存を避ける
2. **権限設定**: 設定ファイルは600権限
3. **ログ管理**: 機密情報の自動マスキング
4. **アクセス制御**: 必要最小限の権限で実行

### チーム利用

```bash
# チーム共通設定の配布
mkdir -p team-configs/
cp ~/.config/lazygit-llm/config.yml team-configs/config-standard.yml

# チームメンバーは設定をコピー
cp team-configs/config-standard.yml ~/.config/lazygit-llm/config.yml
```

## 🔄 アップデート

### ツールの更新

```bash
# プロジェクトを更新
cd lazygit-llm-commit-generator
git pull origin master

# 再インストール
python3 install.py
```

### 設定の移行

新しいバージョンで設定形式が変更された場合：

```bash
# 現在の設定をバックアップ
cp ~/.config/lazygit-llm/config.yml ~/.config/lazygit-llm/config.yml.backup

# 新しい設定例を確認
cat lazygit-llm/config/config.yml.example

# 必要に応じて設定を更新
```

## 🤝 サポート

### 質問・要望

- **Issues**: GitHub Issuesで報告
- **Discussions**: 一般的な質問
- **Wiki**: 詳細ドキュメント

### 設定サンプル集

よく使われる設定パターンは [GitHub Wiki](https://github.com/yohi/lazygit-llm-commit-generator/wiki) で公開しています。

---

**Happy coding with AI-powered commit messages! 🚀**
