# Testing Guide

## MessageFormatter Tests

MessageFormatterクラスの包括的なテストが実装されています。

### テスト実行方法

```bash
# プロジェクトルートから実行（推奨）
# UV環境を使用
uv run pytest lazygit-llm/tests/test_message_formatter.py -v

# 特定のテストクラスを実行
uv run pytest lazygit-llm/tests/test_message_formatter.py::TestMessageFormatter -v

# カバレッジ付きで実行
uv run pytest lazygit-llm/tests/test_message_formatter.py --cov=lazygit_llm.message_formatter

# 従来の方法（lazygit-llmディレクトリ内から）
cd lazygit-llm
python -m pytest tests/test_message_formatter.py -v

# 簡単なサンプル実行
uv run python lazygit-llm/tests/test_message_formatter.py
```

### テストカバレッジ

以下の機能を包括的にテストしています：

#### `format_response`メソッド
- ✅ 空入力/空白入力でデフォルトメッセージを返し警告をログ出力
- ✅ 正常なフローでの処理
- ✅ コードブロックを含む入力の処理

#### `_clean_message`メソッド
- ✅ 文字列のトリム
- ✅ 改行の統合
- ✅ タブから空白への変換
- ✅ 複数空白の統合
- ✅ CRLF正規化

#### `_extract_commit_message`メソッド
- ✅ コードブロックの削除
- ✅ 一般的なプレフィックスの大文字小文字無視での削除
- ✅ 周囲の引用符の削除
- ✅ 最初の行の選択
- ✅ フォールバックとして最初の文の選択

#### `_apply_length_limit`メソッド
- ✅ 最大長未満での無操作
- ✅ 境界/境界超過での切り詰め
- ✅ 単語境界での切り詰め動作
- ✅ 句読点の除去と省略記号の追加
- ✅ 警告ログの出力確認

#### `validate_message`メソッド
- ✅ 空/短すぎる入力の検証
- ✅ 不正な制御文字の検出
- ✅ 有効な制御文字（改行・タブ）の許可

### エッジケーステスト

パラメタ化テストにより以下のエッジケースをカバー：

- 空文字列・空白のみの入力
- 最小/最大長の境界値
- 特殊文字・制御文字
- 長すぎるメッセージ
- 複雑な組み合わせ入力

### モックとアサーション

- ロガーのモックによる警告出力の検証
- 文字列の内容・長さ・形式の検証
- 処理パイプライン全体の統合テスト

### 必要な依存関係

```bash
# UV環境を使用（推奨、開発依存関係含む）
uv sync --extra dev

# または従来のpipを使用
pip install pytest pytest-mock pytest-cov
```

### テスト品質

- **カバレッジ**: 全メソッドと分岐を網羅
- **エラーケース**: 異常入力に対する適切な処理
- **ログ検証**: 適切なログ出力の確認
- **統合テスト**: 複数処理ステップの組み合わせテスト
- **パラメータ化**: 同種のテストケースの効率的な実行