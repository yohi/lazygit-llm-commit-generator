"""
パフォーマンステストパッケージ

LazyGit LLM Commit Generator のパフォーマンステストを提供します。

このパッケージには以下のテストが含まれています：
- 実行時間の測定
- メモリ使用量の監視
- CPU使用率の最適化
- 並行処理のパフォーマンス
- ストレステスト
- リソースクリーンアップテスト

使用方法:
    pytest tests/performance/ -m performance
    pytest tests/performance/ -m slow  # 時間のかかるテスト
"""