"""
GeminiApiProviderのユニットテスト

Google Gemini APIを使用したコミットメッセージ生成機能をテスト。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from lazygit_llm.src.api_providers.gemini_api_provider import GeminiApiProvider
from lazygit_llm.src.base_provider import ProviderError, AuthenticationError, TimeoutError, ResponseError


class TestGeminiApiProvider:
    """GeminiApiProviderのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行"""
        self.config = {
            'api_key': 'AIza1234567890abcdef1234567890abcdef123',  # gitleaks:allow - test only
            'model_name': 'gemini-1.5-pro',
            'timeout': 30,
            'max_tokens': 100,
            'prompt_template': 'Generate commit message: {diff}',
            'additional_params': {
                'temperature': 0.3,
                'top_p': 0.9,
                'top_k': 40
            }
        }

    def test_initialization_success(self):
        """正常初期化テスト"""
        provider = GeminiApiProvider(self.config)

        assert provider.api_key == 'AIza1234567890abcdef1234567890abcdef123'  # gitleaks:allow - test only
        assert provider.model_name == 'gemini-1.5-pro'
        assert provider.timeout == 30
        assert provider.max_tokens == 100
        assert provider.base_url == 'https://generativelanguage.googleapis.com/v1beta/models'

    def test_initialization_missing_api_key(self):
        """APIキー不足時の初期化エラーテスト"""
        config_without_key = self.config.copy()
        del config_without_key['api_key']

        with pytest.raises(ProviderError, match="APIキーが設定されていません"):
            GeminiApiProvider(config_without_key)

    def test_initialization_missing_model(self):
        """モデル名不足時の初期化エラーテスト"""
        config_without_model = self.config.copy()
        del config_without_model['model_name']

        with pytest.raises(ProviderError, match="モデル名が設定されていません"):
            GeminiApiProvider(config_without_model)

    def test_generate_commit_message_success(self, sample_git_diff):
        """コミットメッセージ生成成功テスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'feat: add new feature'}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)
            result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add new feature"

    def test_generate_commit_message_empty_diff(self):
        """空の差分でのエラーテスト"""
        provider = GeminiApiProvider(self.config)

        with pytest.raises(ProviderError, match="空の差分データです"):
            provider.generate_commit_message("")

    def test_generate_commit_message_authentication_error(self, sample_git_diff):
        """認証エラーテスト"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'error': {'message': 'Invalid API key'}
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(AuthenticationError, match="Gemini API認証エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_rate_limit_error(self, sample_git_diff):
        """レート制限エラーテスト"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            'error': {'message': 'Rate limit exceeded'}
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Gemini APIレート制限エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_timeout_error(self, sample_git_diff):
        """タイムアウトエラーテスト"""
        with patch('requests.post', side_effect=requests.exceptions.Timeout("Request timeout")):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(TimeoutError, match="Gemini APIタイムアウト"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_connection_error(self, sample_git_diff):
        """接続エラーテスト"""
        with patch('requests.post', side_effect=requests.exceptions.ConnectionError("Connection failed")):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Gemini API接続エラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_http_error(self, sample_git_diff):
        """HTTPエラーテスト"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            'error': {'message': 'Internal server error'}
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Gemini APIエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_unexpected_error(self, sample_git_diff):
        """予期しないエラーテスト"""
        with patch('requests.post', side_effect=Exception("Unexpected error")):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ProviderError, match="予期しないエラー"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_empty_response(self, sample_git_diff):
        """空のレスポンステスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': ''}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Geminiから空のレスポンス"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_no_candidates(self, sample_git_diff):
        """候補なしのレスポンステスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': []
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Geminiから無効なレスポンス形式"):
                provider.generate_commit_message(sample_git_diff)

    def test_generate_commit_message_malformed_response(self, sample_git_diff):
        """不正な形式のレスポンステスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'invalid': 'response'
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="Geminiから無効なレスポンス形式"):
                provider.generate_commit_message(sample_git_diff)

    def test_build_prompt(self, sample_git_diff):
        """プロンプト構築テスト"""
        provider = GeminiApiProvider(self.config)
        prompt = provider._build_prompt(sample_git_diff)

        assert sample_git_diff in prompt
        assert "Generate commit message:" in prompt

    def test_build_prompt_custom_template(self, sample_git_diff):
        """カスタムプロンプトテンプレートテスト"""
        custom_config = self.config.copy()
        custom_config['prompt_template'] = "Custom template: {diff}\nGenerate a message."

        provider = GeminiApiProvider(custom_config)
        prompt = provider._build_prompt(sample_git_diff)

        assert "Custom template:" in prompt
        assert sample_git_diff in prompt
        assert "Generate a message." in prompt

    def test_build_request_payload(self, sample_git_diff):
        """リクエストペイロード構築テスト"""
        provider = GeminiApiProvider(self.config)
        payload = provider._build_request_payload(sample_git_diff)

        assert 'contents' in payload
        assert 'generationConfig' in payload
        assert payload['generationConfig']['temperature'] == 0.3
        assert payload['generationConfig']['topP'] == 0.9
        assert payload['generationConfig']['topK'] == 40
        assert payload['generationConfig']['maxOutputTokens'] == 100

    def test_extract_response_content_success(self):
        """レスポンス内容抽出成功テスト"""
        provider = GeminiApiProvider(self.config)

        response_data = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'fix: resolve issue'}]
                }
            }]
        }

        result = provider._extract_response_content(response_data)
        assert result == "fix: resolve issue"

    def test_test_connection_success(self):
        """接続テスト成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'test response'}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)
            result = provider.test_connection()

            assert result is True

    def test_test_connection_failure(self):
        """接続テスト失敗"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {
            'error': {'message': 'Invalid API key'}
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)
            result = provider.test_connection()

            assert result is False

    def test_supports_streaming(self):
        """ストリーミング対応確認テスト"""
        provider = GeminiApiProvider(self.config)
        assert provider.supports_streaming() is False

    def test_retry_logic(self, sample_git_diff):
        """リトライロジックテスト"""
        # 最初の2回は失敗、3回目は成功
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'feat: add retry logic'}]
                }
            }]
        }

        failure_response = Mock()
        failure_response.status_code = 500

        with patch('requests.post', side_effect=[
            failure_response,
            requests.exceptions.Timeout("Timeout"),
            success_response
        ]):
            provider = GeminiApiProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                result = provider.generate_commit_message(sample_git_diff)

            assert result == "feat: add retry logic"

    def test_max_retries_exceeded(self, sample_git_diff):
        """最大リトライ回数超過テスト"""
        failure_response = Mock()
        failure_response.status_code = 500

        with patch('requests.post', return_value=failure_response):
            provider = GeminiApiProvider(self.config)

            with patch('time.sleep'):  # リトライ待機をスキップ
                with pytest.raises(ResponseError, match="最大リトライ回数"):
                    provider.generate_commit_message(sample_git_diff)

    @pytest.mark.parametrize("model_name", [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
    ])
    def test_different_models(self, model_name):
        """異なるモデルでの動作テスト"""
        config = self.config.copy()
        config['model_name'] = model_name

        provider = GeminiApiProvider(config)
        assert provider.model_name == model_name

    def test_additional_params_application(self, sample_git_diff):
        """追加パラメータの適用テスト"""
        config_with_params = self.config.copy()
        config_with_params['additional_params'] = {
            'temperature': 0.5,
            'top_p': 0.8,
            'top_k': 20,
            'candidate_count': 1,
            'stop_sequences': ['\n\n']
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'test: commit message'}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = GeminiApiProvider(config_with_params)
            provider.generate_commit_message(sample_git_diff)

            # パラメータが正しく適用されていることを確認
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            generation_config = payload['generationConfig']

            assert generation_config['temperature'] == 0.5
            assert generation_config['topP'] == 0.8
            assert generation_config['topK'] == 20
            assert generation_config['candidateCount'] == 1
            assert generation_config['stopSequences'] == ['\n\n']

    def test_safety_settings_application(self, sample_git_diff):
        """安全設定の適用テスト"""
        config_with_safety = self.config.copy()
        config_with_safety['safety_settings'] = [
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'test: commit message'}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = GeminiApiProvider(config_with_safety)
            provider.generate_commit_message(sample_git_diff)

            # 安全設定が適用されていることを確認
            call_args = mock_post.call_args
            payload = call_args[1]['json']

            assert 'safetySettings' in payload
            assert len(payload['safetySettings']) == 2

    def test_request_headers(self, sample_git_diff):
        """リクエストヘッダーのテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{'text': 'test: commit message'}]
                }
            }]
        }

        with patch('requests.post', return_value=mock_response) as mock_post:
            provider = GeminiApiProvider(self.config)
            provider.generate_commit_message(sample_git_diff)

            # ヘッダーが正しく設定されていることを確認
            call_args = mock_post.call_args
            headers = call_args[1]['headers']

            assert headers['Content-Type'] == 'application/json'
            assert 'User-Agent' in headers

    def test_api_endpoint_construction(self):
        """APIエンドポイント構築テスト"""
        provider = GeminiApiProvider(self.config)
        endpoint = provider._build_api_endpoint()

        expected_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
        assert endpoint == expected_url

    def test_error_response_parsing(self, sample_git_diff):
        """エラーレスポンス解析テスト"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {
                'message': 'Invalid request format',
                'code': 400,
                'status': 'INVALID_ARGUMENT',
                'details': [
                    {
                        'reason': 'INVALID_FORMAT',
                        'domain': 'googleapis.com',
                        'metadata': {}
                    }
                ]
            }
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError) as exc_info:
                provider.generate_commit_message(sample_git_diff)

            assert "Invalid request format" in str(exc_info.value)

    def test_json_decode_error_handling(self, sample_git_diff):
        """JSONデコードエラーハンドリングテスト"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(ResponseError, match="レスポンスの解析に失敗しました"):
                provider.generate_commit_message(sample_git_diff)

    @pytest.mark.parametrize("status_code,expected_error", [
        (400, ResponseError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (429, ResponseError),
        (500, ResponseError),
        (502, ResponseError),
        (503, ResponseError),
    ])
    def test_status_code_error_mapping(self, sample_git_diff, status_code, expected_error):
        """ステータスコードとエラーのマッピングテスト"""
        mock_response = Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = {
            'error': {'message': 'Test error'}
        }

        with patch('requests.post', return_value=mock_response):
            provider = GeminiApiProvider(self.config)

            with pytest.raises(expected_error):
                provider.generate_commit_message(sample_git_diff)
