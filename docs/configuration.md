# ⚙️ 設定ガイド

LazyGit LLM Commit Generatorの詳細な設定方法を説明します。

## 📁 設定ファイルの場所

### デフォルトパス

```
~/.config/lazygit-llm/config.yml
```

### 環境変数での指定

```bash
export LAZYGIT_LLM_CONFIG="/path/to/your/config.yml"
```

### コマンドライン引数での指定

```bash
python3 lazygit-llm/src/main.py --config /path/to/config.yml
```

## 🔧 基本設定

### 最小構成

```yaml
# 必須項目のみ
provider: "openai"
api_key: "${OPENAI_API_KEY}"
model_name: "gpt-4"
```

### 完全な設定例

```yaml
# ===========================================
# LazyGit LLM Commit Generator 設定ファイル
# ===========================================

# プロバイダー設定
provider: "openai"  # openai, anthropic, gemini, gcloud, gemini-cli, claude-code

# APIキー（環境変数推奨）
api_key: "${OPENAI_API_KEY}"

# モデル設定
model_name: "gpt-4"

# タイムアウト設定（秒）
timeout: 30

# 最大トークン数
max_tokens: 100

# プロンプトテンプレート
prompt_template: |
  Based on the following git diff, generate a concise commit message
  that follows conventional commits format:

  {diff}

  Generate only the commit message, no additional text.

# プロバイダー固有の追加パラメータ
additional_params:
  temperature: 0.3
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0
```

## 🤖 プロバイダー別設定

### OpenAI GPT

```yaml
provider: "openai"
api_key: "${OPENAI_API_KEY}"
model_name: "gpt-4"  # gpt-4, gpt-3.5-turbo
timeout: 30
max_tokens: 100

additional_params:
  temperature: 0.3        # 0.0-2.0（創造性）
  top_p: 0.9             # 0.0-1.0（多様性）
  frequency_penalty: 0.0  # -2.0-2.0（重複回避）
  presence_penalty: 0.0   # -2.0-2.0（トピック多様性）
  max_tokens: 100        # レスポンスの最大トークン数
```

### Anthropic Claude

```yaml
provider: "anthropic"
api_key: "${ANTHROPIC_API_KEY}"
model_name: "claude-3-5-sonnet-20241022"  # claude-3-5-sonnet-20241022, claude-3-opus-20240229, claude-3-haiku-20240307
timeout: 45
max_tokens: 100

additional_params:
  temperature: 0.3           # 0.0-1.0
  top_p: 0.9                # 0.0-1.0
  top_k: 40                 # トップK制限
```

### Google Gemini API

```yaml
provider: "gemini"
api_key: "${GOOGLE_API_KEY}"
model_name: "gemini-1.5-pro"  # gemini-1.5-pro, gemini-1.5-flash
timeout: 30
max_tokens: 100

additional_params:
  temperature: 0.3              # 0.0-1.0
  top_p: 0.9                   # 0.0-1.0
  top_k: 40                    # 1-40
  candidate_count: 1           # 生成候補数
  max_output_tokens: 100       # 出力の最大トークン数

  # 安全設定
  safety_settings:
    - category: "HARM_CATEGORY_HARASSMENT"
      threshold: "BLOCK_MEDIUM_AND_ABOVE"
    - category: "HARM_CATEGORY_HATE_SPEECH"
      threshold: "BLOCK_MEDIUM_AND_ABOVE"
```

### Google Gemini CLI

```yaml
provider: "gcloud"
model_name: "gemini-1.5-pro"
timeout: 45
max_tokens: 100

# CLI固有設定
additional_params:
  temperature: 0.3
  top_p: 0.9
  top_k: 40

  # gcloud CLI設定
  project_id: "your-gcp-project-id"  # オプション
  location: "us-central1"            # オプション
```

### Claude Code CLI

```yaml
provider: "claude-code"
model_name: "claude-3-5-sonnet-20241022"
timeout: 60
max_tokens: 100

additional_params:
  temperature: 0.3
  # Claude Code固有の設定は自動的に管理されます
```

## 📝 プロンプトテンプレート

### テンプレートの基本構造

プロンプトテンプレートには必ず `{diff}` プレースホルダーを含める必要があります。

```yaml
prompt_template: |
  あなたのプロンプト内容

  {diff}

  追加の指示
```

### 日本語コミットメッセージ

```yaml
prompt_template: |
  以下のGit差分に基づいて、簡潔で分かりやすい日本語のコミットメッセージを生成してください：

  {diff}

  形式: [種類] 簡潔な説明
  種類の例:
  - feat: 新機能
  - fix: バグ修正
  - docs: ドキュメント
  - style: スタイル修正
  - refactor: リファクタリング
  - test: テスト
  - chore: その他

  コミットメッセージのみを出力してください。
```

### Conventional Commits形式

```yaml
prompt_template: |
  Generate a commit message following the Conventional Commits specification based on this git diff:

  {diff}

  Format: <type>[optional scope]: <description>

  Types:
  - feat: A new feature
  - fix: A bug fix
  - docs: Documentation only changes
  - style: Changes that do not affect the meaning of the code
  - refactor: A code change that neither fixes a bug nor adds a feature
  - perf: A code change that improves performance
  - test: Adding missing tests or correcting existing tests
  - chore: Changes to the build process or auxiliary tools

  Generate only the commit message, no additional text.
```

### 詳細コミットメッセージ

```yaml
prompt_template: |
  Generate a detailed commit message based on this git diff:

  {diff}

  Format:
  <type>(<scope>): <subject>

  <body>

  Guidelines:
  - Subject line: 50 characters or less
  - Use imperative mood in the subject line
  - Body: Explain what and why vs. how
  - Wrap body at 72 characters
  - Focus on the motivation for the change

  Generate the complete commit message with subject and body.
```

### コードレビュー用

```yaml
prompt_template: |
  Analyze this git diff and generate a commit message that would be helpful for code reviewers:

  {diff}

  Include:
  - What was changed
  - Why it was changed
  - Any potential impact or side effects
  - Testing considerations

  Format as a conventional commit with detailed body.
```

## 🔐 セキュリティ設定

### APIキーの安全な管理

#### 環境変数（推奨）

```bash
# ~/.bashrc または ~/.zshrc
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AI..."
```

設定ファイル：
```yaml
api_key: "${OPENAI_API_KEY}"
```

#### .env ファイル

```bash
# .env ファイル（プロジェクトルート）
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AI...
```

#### ファイル権限

```bash
# 設定ファイルを自分のみ読み書き可能に
chmod 600 ~/.config/lazygit-llm/config.yml

# .envファイルも同様に
chmod 600 .env
```

### 入力サニタイゼーション設定

システムが自動的に以下を検出・除去します：

- APIキー、アクセストークン
- パスワード、機密情報
- 個人情報（メールアドレス、電話番号）
- データベース接続文字列

追加の除外パターンが必要な場合は、GitHubでIssueを作成してください。

## 🚀 パフォーマンス設定

### 高速化設定

```yaml
# 高速レスポンス重視
provider: "openai"
model_name: "gpt-3.5-turbo"  # より高速
timeout: 15                  # タイムアウト短縮
max_tokens: 50               # トークン数制限

additional_params:
  temperature: 0.1           # 一貫性重視
  top_p: 0.8                # 選択肢を絞る
```

### 品質重視設定

```yaml
# 高品質コミットメッセージ重視
provider: "anthropic"
model_name: "claude-3-5-sonnet-20241022"
timeout: 60                  # 余裕のあるタイムアウト
max_tokens: 200              # 詳細なメッセージ許可

additional_params:
  temperature: 0.3           # バランスの取れた創造性
  top_p: 0.95               # 多様性を確保
```

### ストリーミング設定

```yaml
# リアルタイム出力
additional_params:
  stream: true               # ストリーミング有効

# LazyGit設定でも有効化
customCommands:
  - key: '<c-g>'
    command: '...'
    stream: true             # LazyGit側でもストリーミング有効
```

## 🔧 詳細設定オプション

### ログ設定

```yaml
# ログレベル設定
log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR

# ログファイル指定
log_file: "/tmp/lazygit-llm.log"

# 詳細ログ
verbose: false
```

### Git差分処理設定

```yaml
# 差分処理設定
git_diff:
  max_size: 50000           # 最大差分サイズ（バイト）
  max_lines: 1000           # 最大行数
  include_binary: false     # バイナリファイル変更を含めるか
  context_lines: 3          # コンテキスト行数
```

### エラーハンドリング設定

```yaml
# リトライ設定
retry:
  max_attempts: 3           # 最大リトライ回数
  backoff_factor: 2         # バックオフ係数
  timeout_multiplier: 1.5   # タイムアウト乗数
```

## 🔄 設定の検証とテスト

### 設定ファイルの検証

```bash
# 設定テスト
python3 lazygit-llm/src/main.py --test-config

# 詳細ログで検証
python3 lazygit-llm/src/main.py --test-config --verbose
```

### プロバイダー接続テスト

```bash
# 各プロバイダーで個別テスト
python3 lazygit-llm/src/main.py --test-provider openai
python3 lazygit-llm/src/main.py --test-provider anthropic
```

### 設定の環境変数展開確認

```bash
# 環境変数が正しく展開されるかテスト
python3 -c "
import yaml
with open('~/.config/lazygit-llm/config.yml') as f:
    config = yaml.safe_load(f)
    print(f'API Key: {config.get(\"api_key\", \"未設定\")}')
"
```

## 🏷️ 設定例集

### シンプルな設定（初心者向け）

```yaml
provider: "openai"
api_key: "${OPENAI_API_KEY}"
model_name: "gpt-3.5-turbo"
timeout: 30
max_tokens: 50
```

### バランス重視設定

```yaml
provider: "anthropic"
api_key: "${ANTHROPIC_API_KEY}"
model_name: "claude-3-5-sonnet-20241022"
timeout: 45
max_tokens: 100

additional_params:
  temperature: 0.3
  top_p: 0.9

prompt_template: |
  Generate a conventional commit message based on this diff:

  {diff}

  Format: type(scope): description
  Keep it concise and clear.
```

### 高度な設定（上級者向け）

```yaml
provider: "gemini"
api_key: "${GOOGLE_API_KEY}"
model_name: "gemini-1.5-pro"
timeout: 60
max_tokens: 200

additional_params:
  temperature: 0.4
  top_p: 0.95
  top_k: 50
  candidate_count: 1

  safety_settings:
    - category: "HARM_CATEGORY_HARASSMENT"
      threshold: "BLOCK_ONLY_HIGH"

prompt_template: |
  You are an expert software engineer. Analyze this git diff and create a comprehensive commit message:

  {diff}

  Requirements:
  1. Follow conventional commits format
  2. Include scope when applicable
  3. Write a detailed body explaining the rationale
  4. Mention any breaking changes
  5. Keep subject under 50 characters
  6. Wrap body at 72 characters

  Generate a professional commit message that would pass code review.

# 詳細ログ有効
verbose: true
log_level: "DEBUG"
```

## 🔍 トラブルシューティング

### 設定エラーの診断

```bash
# 設定ファイルの構文チェック
python3 -c "import yaml; yaml.safe_load(open('~/.config/lazygit-llm/config.yml'))"

# 設定項目の確認
python3 lazygit-llm/src/main.py --show-config

# 環境変数の確認
env | grep -E "(OPENAI|ANTHROPIC|GOOGLE)_API_KEY"
```

### よくある設定ミス

1. **YAMLインデントエラー**
   ```yaml
   # ❌ 間違い
   additional_params:
   temperature: 0.3

   # ✅ 正しい
   additional_params:
     temperature: 0.3
   ```

2. **プレースホルダー忘れ**
   ```yaml
   # ❌ 間違い
   prompt_template: "Generate a commit message from this diff"

   # ✅ 正しい
   prompt_template: "Generate a commit message from this diff: {diff}"
   ```

3. **環境変数の記法**
   ```yaml
   # ❌ 間違い
   api_key: "$OPENAI_API_KEY"

   # ✅ 正しい
   api_key: "${OPENAI_API_KEY}"
   ```

---

設定に関するご質問は、GitHubのDiscussionsでお気軽にお尋ねください。
