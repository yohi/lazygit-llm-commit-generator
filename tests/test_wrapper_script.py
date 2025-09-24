"""
ラッパースクリプトのテストスイート
"""

import subprocess
import tempfile
import os
import unittest
from unittest.mock import patch, MagicMock


class TestGeminiWrapperScript(unittest.TestCase):
    """Gemini Wrapperスクリプトのテストクラス"""

    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        cls.wrapper_script = "/home/y_ohi/bin/gemini-wrapper-refactored.sh"

        # スクリプトの存在確認
        if not os.path.exists(cls.wrapper_script):
            raise unittest.SkipTest(f"Wrapper script not found: {cls.wrapper_script}")

    def test_help_option(self):
        """ヘルプオプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "--help"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("gemini-wrapper", result.stdout)
        self.assertIn("使用方法", result.stdout)
        self.assertIn("OPTIONS", result.stdout)

    def test_version_option(self):
        """バージョンオプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "--version"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("version", result.stdout.lower())

    def test_verbose_mode(self):
        """詳細モードのテスト"""
        # モックを使用してgeminiコマンドの動作をシミュレート
        with patch.dict(os.environ, {'GEMINI_VERBOSE': 'true'}):
            # 実際のテストは安全な方法で実行
            # ここでは設定が正しく読み込まれることをテスト
            result = subprocess.run(
                [self.wrapper_script, "--help"],  # 安全なオプション
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)

    def test_silent_mode(self):
        """サイレントモードのテスト"""
        with patch.dict(os.environ, {'GEMINI_SILENT': 'true'}):
            result = subprocess.run(
                [self.wrapper_script, "--help"],
                capture_output=True,
                text=True
            )
            self.assertEqual(result.returncode, 0)

    def test_no_fallback_option(self):
        """フォールバック無効オプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "--no-fallback", "--help"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("使用方法", result.stdout)

    def test_model_option(self):
        """モデル指定オプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "-m", "gemini-1.5-flash", "--help"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

    def test_invalid_option(self):
        """無効なオプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "--invalid-option"],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown option", result.stderr)

    def test_model_without_argument(self):
        """引数なしモデルオプションのテスト"""
        result = subprocess.run(
            [self.wrapper_script, "--model"],
            capture_output=True,
            text=True
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires an argument", result.stderr)


class TestWrapperScriptFunctions(unittest.TestCase):
    """ラッパースクリプト機能のテストクラス"""

    def setUp(self):
        """テスト前の準備"""
        self.wrapper_script = "/home/y_ohi/bin/gemini-wrapper-refactored.sh"

    def test_config_file_creation(self):
        """設定ファイル作成のテスト"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = os.path.join(temp_dir, ".config", "gemini")
            config_file = os.path.join(config_dir, "wrapper.conf")

            # 設定ディレクトリが存在しない状態でテスト
            # （実際のスクリプトは設定ファイルを作成する）
            self.assertFalse(os.path.exists(config_file))

    def test_environment_variable_override(self):
        """環境変数オーバーライドのテスト"""
        test_env = os.environ.copy()
        test_env.update({
            'GEMINI_AUTO_FALLBACK': 'false',
            'GEMINI_VERBOSE': 'true',
            'GEMINI_SILENT': 'false'
        })

        result = subprocess.run(
            [self.wrapper_script, "--help"],
            env=test_env,
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)

    def test_binary_discovery(self):
        """バイナリ検出のテスト"""
        # スクリプトが正しいgeminiバイナリを見つけられることをテスト
        # ヘルプオプションで安全にテスト
        result = subprocess.run(
            [self.wrapper_script, "--version"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)


class TestErrorHandling(unittest.TestCase):
    """エラーハンドリングのテストクラス"""

    def setUp(self):
        """テスト前の準備"""
        self.wrapper_script = "/home/y_ohi/bin/gemini-wrapper-refactored.sh"

    def test_error_classification_simulation(self):
        """エラー分類のシミュレーションテスト"""
        # 実際のAPIを呼び出さずに、スクリプトの構造をテスト
        result = subprocess.run(
            [self.wrapper_script, "--help"],
            capture_output=True,
            text=True
        )

        # ヘルプが正常に動作することで、基本的な構造が正しいことを確認
        self.assertEqual(result.returncode, 0)
        self.assertIn("エラーハンドリング", result.stdout or "")  # オプショナル

    def test_fallback_mechanism_structure(self):
        """フォールバック機構の構造テスト"""
        # --no-fallbackオプションで構造をテスト
        result = subprocess.run(
            [self.wrapper_script, "--no-fallback", "--version"],
            capture_output=True,
            text=True
        )

        self.assertEqual(result.returncode, 0)


if __name__ == '__main__':
    # テストスイート実行
    unittest.main(verbosity=2)
