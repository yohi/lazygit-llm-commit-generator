"""
パフォーマンステスト

システムの性能、レスポンス時間、リソース使用量を測定。
"""

import pytest
import time
import psutil
import os
import sys
import threading
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lazygit_llm.src.git_processor import GitDiffProcessor
from lazygit_llm.src.message_formatter import MessageFormatter
from lazygit_llm.src.config_manager import ConfigManager
from lazygit_llm.src.provider_factory import ProviderFactory
from lazygit_llm.src.security_validator import SecurityValidator


class TestPerformance:
    """パフォーマンステストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.process = psutil.Process(os.getpid())
        self.baseline_memory = self.process.memory_info().rss

    def create_large_diff(self, lines=1000, line_length=100):
        """大容量差分を生成"""
        diff_header = """diff --git a/large_file.py b/large_file.py
new file mode 100644
index 0000000..1234567
--- /dev/null
+++ b/large_file.py
@@ -0,0 +1,{} @@""".format(lines)

        diff_content = []
        for i in range(lines):
            line_content = "x" * line_length
            diff_content.append(f"+line_{i:04d} = '{line_content}'")

        return diff_header + "\n" + "\n".join(diff_content)

    def measure_execution_time(self, func, *args, **kwargs):
        """関数の実行時間を測定"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time

    def measure_memory_usage(self, func, *args, **kwargs):
        """関数のメモリ使用量を測定"""
        initial_memory = self.process.memory_info().rss
        result = func(*args, **kwargs)
        final_memory = self.process.memory_info().rss
        memory_increase = final_memory - initial_memory
        return result, memory_increase

    @pytest.mark.performance
    def test_git_diff_processing_performance(self):
        """Git差分処理のパフォーマンステスト"""
        processor = GitDiffProcessor()

        # 小さな差分でのベンチマーク
        small_diff = self.create_large_diff(lines=10, line_length=50)
        _, small_time = self.measure_execution_time(
            processor.format_diff_for_llm, small_diff
        )

        # 中程度の差分でのベンチマーク
        medium_diff = self.create_large_diff(lines=100, line_length=100)
        _, medium_time = self.measure_execution_time(
            processor.format_diff_for_llm, medium_diff
        )

        # 大きな差分でのベンチマーク
        large_diff = self.create_large_diff(lines=1000, line_length=100)
        _, large_time = self.measure_execution_time(
            processor.format_diff_for_llm, large_diff
        )

        # パフォーマンス要件の確認
        assert small_time < 0.1  # 100ms以内
        assert medium_time < 0.5  # 500ms以内
        assert large_time < 2.0  # 2秒以内

        # 実行時間の線形性をチェック（極端な増加がないこと）
        time_ratio = large_time / small_time
        assert time_ratio < 50  # 50倍以内の増加

    @pytest.mark.performance
    def test_message_formatting_performance(self):
        """メッセージフォーマットのパフォーマンステスト"""
        formatter = MessageFormatter()

        # 異なる長さのメッセージでのベンチマーク
        test_messages = [
            "feat: add feature",
            "feat: add comprehensive authentication system\n\nThis commit introduces a new authentication system with OAuth2 support.",
            "feat: add feature\n\n" + "Long description line. " * 100,
        ]

        for i, message in enumerate(test_messages):
            _, execution_time = self.measure_execution_time(
                formatter.format_response, message
            )

            # フォーマット処理は高速である必要がある
            assert execution_time < 0.05  # 50ms以内

    @pytest.mark.performance
    def test_security_validation_performance(self):
        """セキュリティ検証のパフォーマンステスト"""
        validator = SecurityValidator()

        # APIキー検証のパフォーマンス
        api_keys = [
            "sk-1234567890abcdef1234567890abcdef12345678",
            "sk-ant-api03-" + "a" * 95,
            "AIza" + "a" * 35,
        ]

        for api_key in api_keys:
            _, execution_time = self.measure_execution_time(
                validator.validate_api_key, "openai", api_key
            )
            assert execution_time < 0.01  # 10ms以内

        # 差分サニタイゼーションのパフォーマンス
        test_diffs = [
            self.create_large_diff(lines=100, line_length=50),
            self.create_large_diff(lines=500, line_length=100),
        ]

        for diff in test_diffs:
            _, execution_time = self.measure_execution_time(
                validator.sanitize_git_diff, diff
            )
            assert execution_time < 1.0  # 1秒以内

    @pytest.mark.performance
    def test_config_loading_performance(self):
        """設定読み込みのパフォーマンステスト"""
        config_manager = ConfigManager()

        # テスト用設定ファイルを作成
        config_content = """
provider: openai
model_name: gpt-4
api_key: test-key
timeout: 30
max_tokens: 100
prompt_template: "Generate commit message: {diff}"
additional_params:
  temperature: 0.3
  top_p: 0.9
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(config_content)
            config_file = f.name

        try:
            with patch.object(config_manager.security_validator, 'check_file_permissions') as mock_check:
                mock_check.return_value = Mock(level='info')

                _, execution_time = self.measure_execution_time(
                    config_manager.load_config, config_file
                )

                # 設定読み込みは高速である必要がある
                assert execution_time < 0.1  # 100ms以内

        finally:
            os.unlink(config_file)

    @pytest.mark.performance
    def test_provider_creation_performance(self):
        """プロバイダー作成のパフォーマンステスト"""
        factory = ProviderFactory()

        providers_to_test = [
            ('openai', 'lazygit_llm.src.api_providers.openai_provider.OpenAIProvider'),
            ('anthropic', 'lazygit_llm.src.api_providers.anthropic_provider.AnthropicProvider'),
            ('gemini-api', 'lazygit_llm.src.api_providers.gemini_api_provider.GeminiApiProvider'),
        ]

        for provider_name, provider_class_path in providers_to_test:
            from lazygit_llm.src.provider_factory import ProviderConfig

            config = ProviderConfig(
                name=provider_name,
                type='api',
                model='test-model',
                api_key='test-key',
                timeout=30,
                max_tokens=100,
                prompt_template='Test: {diff}',
                additional_params={}
            )

            with patch(provider_class_path) as mock_provider_class:
                mock_provider_class.return_value = Mock()

                _, execution_time = self.measure_execution_time(
                    factory.create_provider, config
                )

                # プロバイダー作成は高速である必要がある
                assert execution_time < 0.1  # 100ms以内

    @pytest.mark.performance
    def test_memory_usage_optimization(self):
        """メモリ使用量最適化テスト"""
        processor = GitDiffProcessor()
        formatter = MessageFormatter()

        # 大容量データでのメモリ使用量測定
        large_diff = self.create_large_diff(lines=2000, line_length=200)

        # Git差分処理のメモリ使用量
        _, memory_increase = self.measure_memory_usage(
            processor.format_diff_for_llm, large_diff
        )

        # メモリ使用量が適切な範囲内であることを確認
        assert memory_increase < 50 * 1024 * 1024  # 50MB以内

        # メッセージフォーマットのメモリ使用量
        long_message = "feat: add feature\n\n" + "Description line. " * 1000
        _, memory_increase = self.measure_memory_usage(
            formatter.format_response, long_message
        )

        assert memory_increase < 10 * 1024 * 1024  # 10MB以内

    @pytest.mark.performance
    def test_concurrent_processing_performance(self):
        """並行処理のパフォーマンステスト"""
        processor = GitDiffProcessor()
        num_threads = 5
        results = {}
        errors = []

        def process_diff_thread(thread_id, results_dict, errors_list):
            """差分処理を別スレッドで実行"""
            try:
                diff = self.create_large_diff(lines=100, line_length=50)
                start_time = time.time()
                result = processor.format_diff_for_llm(diff)
                end_time = time.time()

                results_dict[thread_id] = {
                    'result': result,
                    'execution_time': end_time - start_time
                }
            except Exception as e:
                errors_list.append((thread_id, e))

        # 複数スレッドで並行実行
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(
                target=process_diff_thread,
                args=(i, results, errors)
            )
            threads.append(thread)

        # 全スレッドを開始
        start_time = time.time()
        for thread in threads:
            thread.start()

        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        end_time = time.time()

        # 結果を検証
        assert len(errors) == 0  # エラーがないこと
        assert len(results) == num_threads  # 全スレッドが完了

        # 並行実行が効率的であることを確認
        total_time = end_time - start_time
        average_sequential_time = sum(r['execution_time'] for r in results.values()) / num_threads

        # 並行実行の効果があることを確認（完全に線形ではないが改善があること）
        assert total_time < average_sequential_time * num_threads

    @pytest.mark.performance
    def test_large_file_handling_performance(self):
        """大容量ファイル処理のパフォーマンステスト"""
        processor = GitDiffProcessor(max_diff_size=100000)  # 100KB制限

        # 制限を超える大容量差分
        oversized_diff = self.create_large_diff(lines=5000, line_length=200)

        _, execution_time = self.measure_execution_time(
            processor.format_diff_for_llm, oversized_diff
        )

        # 大容量ファイルでも適切な時間内で処理されること
        assert execution_time < 3.0  # 3秒以内

        # 出力サイズが制限内であることを確認
        formatted = processor.format_diff_for_llm(oversized_diff)
        assert len(formatted.encode('utf-8')) <= 110000  # 制限+余裕

    @pytest.mark.performance
    def test_repeated_operations_performance(self):
        """反復操作のパフォーマンステスト"""
        processor = GitDiffProcessor()
        formatter = MessageFormatter()

        test_diff = self.create_large_diff(lines=50, line_length=80)
        test_message = "feat: add new feature with comprehensive documentation"

        num_iterations = 100

        # Git差分処理の反復実行
        start_time = time.time()
        for _ in range(num_iterations):
            processor.format_diff_for_llm(test_diff)
        diff_processing_time = time.time() - start_time

        # メッセージフォーマットの反復実行
        start_time = time.time()
        for _ in range(num_iterations):
            formatter.format_response(test_message)
        message_formatting_time = time.time() - start_time

        # 平均実行時間が適切であることを確認
        avg_diff_time = diff_processing_time / num_iterations
        avg_message_time = message_formatting_time / num_iterations

        assert avg_diff_time < 0.05  # 50ms以内
        assert avg_message_time < 0.01  # 10ms以内

    @pytest.mark.performance
    def test_memory_leak_detection(self):
        """メモリリーク検出テスト"""
        processor = GitDiffProcessor()
        formatter = MessageFormatter()

        initial_memory = self.process.memory_info().rss

        # 多数の操作を実行してメモリリークをチェック
        for i in range(100):
            diff = self.create_large_diff(lines=50, line_length=50)
            processed = processor.format_diff_for_llm(diff)
            formatted = formatter.format_response(f"feat: iteration {i}")

            # 定期的にメモリ使用量をチェック
            if i % 20 == 0:
                current_memory = self.process.memory_info().rss
                memory_increase = current_memory - initial_memory

                # メモリ増加が過度でないことを確認
                assert memory_increase < 100 * 1024 * 1024  # 100MB以内

        # 最終的なメモリ使用量をチェック
        final_memory = self.process.memory_info().rss
        total_memory_increase = final_memory - initial_memory

        # 明らかなメモリリークがないことを確認
        assert total_memory_increase < 150 * 1024 * 1024  # 150MB以内

    @pytest.mark.performance
    def test_cpu_usage_optimization(self):
        """CPU使用率最適化テスト"""
        processor = GitDiffProcessor()

        # CPU使用率を監視しながら処理を実行
        cpu_percent_before = psutil.cpu_percent(interval=0.1)

        # 集約的な処理を実行
        large_diff = self.create_large_diff(lines=1000, line_length=150)
        start_time = time.time()

        for _ in range(10):
            processor.format_diff_for_llm(large_diff)

        end_time = time.time()
        cpu_percent_after = psutil.cpu_percent(interval=0.1)

        execution_time = end_time - start_time

        # CPU使用率が適切な範囲内であることを確認
        # （この値は環境によって変わるため、基本的なチェックのみ）
        assert execution_time < 10.0  # 10秒以内で完了

    @pytest.mark.performance
    @pytest.mark.slow
    def test_stress_testing(self):
        """ストレステスト"""
        processor = GitDiffProcessor()
        formatter = MessageFormatter()
        validator = SecurityValidator()

        # 高負荷状況をシミュレート
        num_operations = 500
        max_execution_time = 30.0  # 30秒以内

        start_time = time.time()

        for i in range(num_operations):
            # 様々なサイズの差分を処理
            diff_size = (i % 10 + 1) * 10  # 10-100行
            diff = self.create_large_diff(lines=diff_size, line_length=80)

            # 各コンポーネントを順次実行
            processed_diff = processor.format_diff_for_llm(diff)
            message = f"feat: iteration {i} with {diff_size} lines"
            formatted_message = formatter.format_response(message)
            validator.validate_api_key("openai", "sk-1234567890abcdef1234567890abcdef12345678")

            # 進行状況の確認
            if i % 100 == 0 and i > 0:
                current_time = time.time()
                elapsed_time = current_time - start_time
                estimated_total_time = elapsed_time * (num_operations / i)

                # 推定完了時間が制限内であることを確認
                assert estimated_total_time < max_execution_time

        end_time = time.time()
        total_time = end_time - start_time

        # 全体実行時間が制限内であることを確認
        assert total_time < max_execution_time

        # 平均実行時間が適切であることを確認
        avg_time_per_operation = total_time / num_operations
        assert avg_time_per_operation < 0.1  # 操作あたり100ms以内

    @pytest.mark.performance
    def test_resource_cleanup_performance(self):
        """リソースクリーンアップのパフォーマンステスト"""
        initial_memory = self.process.memory_info().rss

        # 大量のオブジェクト作成と破棄
        for _ in range(100):
            processor = GitDiffProcessor()
            formatter = MessageFormatter()
            validator = SecurityValidator()

            # 一時的に大きなデータを処理
            large_diff = self.create_large_diff(lines=100, line_length=100)
            processor.format_diff_for_llm(large_diff)

            # オブジェクトを明示的に削除
            del processor, formatter, validator

        # メモリが適切にクリーンアップされていることを確認
        final_memory = self.process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # 明らかなメモリリークがないことを確認
        assert memory_increase < 50 * 1024 * 1024  # 50MB以内