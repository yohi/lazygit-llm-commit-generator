# LazyGit LLM Commit Generator - ドキュメント索引

## 📚 ドキュメント一覧

このプロジェクトの包括的なドキュメントセットです。用途に応じて適切なドキュメントをご参照ください。

### 👥 ユーザー向けドキュメント

#### [📖 ユーザーガイド](USER_GUIDE.md)
**対象**: エンドユーザー・LazyGit利用者
**内容**: インストール、設定、基本的な使い方からトラブルシューティングまで

- ✅ クイックスタートガイド
- ⚙️ 詳細な設定方法
- 🔧 トラブルシューティング
- 💡 ベストプラクティス
- 🎯 プロバイダー別設定例

### 🔧 開発者向けドキュメント

#### [🛠 開発者ガイド](DEVELOPMENT.md)
**対象**: コントリビューター・拡張開発者
**内容**: 開発環境構築、アーキテクチャ、新機能の実装方法

- 🏗 開発環境セットアップ
- 📁 プロジェクト構造説明
- 🔌 新しいプロバイダーの追加方法
- 🧪 テスト戦略とガイドライン
- 🔒 セキュリティベストプラクティス
- 🚀 リリース管理プロセス

#### [📋 API仕様書](API_REFERENCE.md)
**対象**: 内部実装の理解・拡張開発者
**内容**: 全クラス・メソッドの詳細仕様

- 🏗️ アーキテクチャ概要
- 📝 全クラスのAPI仕様
- 🔌 プロバイダーシステム詳細
- ⚙️ 設定ファイル仕様
- 🛡️ エラーハンドリング
- 🔧 拡張ポイント

## 🎯 用途別ガイド

### 初回利用時
1. [ユーザーガイド - クイックスタート](USER_GUIDE.md#🚀-クイックスタート)
2. [ユーザーガイド - 基本的な使い方](USER_GUIDE.md#💡-基本的な使い方)

### 設定カスタマイズ
1. [ユーザーガイド - 設定詳細](USER_GUIDE.md#⚙️-設定詳細)
2. [API仕様書 - 設定ファイル仕様](API_REFERENCE.md#設定ファイル仕様)

### 新しいプロバイダー追加
1. [開発者ガイド - プロバイダー開発](DEVELOPMENT.md#🔌-プロバイダー開発)
2. [API仕様書 - BaseProvider](API_REFERENCE.md#baseprovider)

### トラブルシューティング
1. [ユーザーガイド - トラブルシューティング](USER_GUIDE.md#🛠-トラブルシューティング)
2. [開発者ガイド - デバッグガイド](DEVELOPMENT.md#🛠-デバッグガイド)

### コントリビューション
1. [開発者ガイド - コントリビューションガイド](DEVELOPMENT.md#🤝-コントリビューションガイド)
2. [開発者ガイド - 開発フロー](DEVELOPMENT.md#🎯-開発フロー)

## 📋 ドキュメント品質チェックリスト

### ✅ ユーザーガイド
- [x] インストール手順が明確
- [x] 設定例が豊富
- [x] トラブルシューティング充実
- [x] プロバイダー別説明

### ✅ 開発者ガイド
- [x] 開発環境構築手順
- [x] アーキテクチャ説明
- [x] 新機能実装ガイド
- [x] テスト戦略説明
- [x] セキュリティガイドライン

### ✅ API仕様書
- [x] 全クラス・メソッドを網羅
- [x] パラメータ・戻り値明記
- [x] 例外処理説明
- [x] 使用例提供

## 🔄 ドキュメント更新プロセス

### 1. 定期更新タイミング
- ✨ 新機能追加時
- 🐛 バグ修正時
- ⚙️ 設定変更時
- 🔧 API変更時

### 2. 更新チェックリスト
- [ ] 関連する全ドキュメントを確認
- [ ] コード例の動作確認
- [ ] リンク切れチェック
- [ ] 書式統一確認

### 3. レビュープロセス
- [ ] 技術的正確性の確認
- [ ] 可読性・理解しやすさの確認
- [ ] 網羅性の確認

## 🔗 外部リンク・参考資料

### プロジェクト関連
- [GitHub リポジトリ](https://github.com/yohi/lazygit-llm-commit-generator)
- [PyPI パッケージ](https://pypi.org/project/lazygit-llm-commit-generator/)
- [Issue トラッカー](https://github.com/yohi/lazygit-llm-commit-generator/issues)

### 依存プロジェクト
- [LazyGit](https://github.com/jesseduffield/lazygit) - Git UI ツール
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Google Generative AI Python SDK](https://github.com/google/generative-ai-python)

### 仕様・標準
- [Conventional Commits](https://www.conventionalcommits.org/) - コミットメッセージ規約
- [Semantic Versioning](https://semver.org/) - バージョニング規約
- [Python Packaging Guide](https://packaging.python.org/) - パッケージング

## 💡 ドキュメント改善提案

ドキュメントの改善提案は以下の方法で受け付けています：

1. **GitHub Issues**: [Documentation](https://github.com/yohi/lazygit-llm-commit-generator/issues?q=is%3Aissue+is%3Aopen+label%3Adocumentation)ラベルでIssue作成
2. **Pull Request**: ドキュメントの直接編集・改善
3. **Discussions**: 一般的な質問・提案

### 特に歓迎する改善
- 🌐 多言語対応（英語版の追加）
- 📝 チュートリアル動画・図解の追加
- 💡 実用的な使用例の追加
- 🔧 よくある質問（FAQ）の拡充

---

### 良いドキュメントは良いソフトウェアの基盤です 📚✨