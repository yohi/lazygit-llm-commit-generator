# Implementation Plan

- [x] 1. Set up project structure and core interfaces
  - ✅ LazyGit LLM専用ディレクトリ構造作成完了 (lazygit-llm/)
  - ✅ ベースプロバイダーインターフェース定義完了 (base_provider.py)
  - ✅ メインエントリーポイント作成完了 (main.py)
  - ✅ API/CLIプロバイダーディレクトリとレジストリ作成完了
  - ✅ 設定ファイル例・setup.py・requirements.txt作成完了
  - _Requirements: 1.1, 2.1, 5.1_

- [x] 2. Implement configuration management system
  - ✅ ConfigManager class with YAML parsing capabilities実装完了
  - ✅ 環境変数解決機能実装完了（${VAR_NAME}形式対応）
  - ✅ 包括的な設定検証とエラーハンドリング実装完了
  - ✅ 全5プロバイダー対応の設定例ファイル作成完了
  - ✅ セキュリティ機能（ファイル権限チェック、APIキー保護）実装完了
  - _Requirements: 2.1, 2.2, 2.3, 4.1, 4.2_

- [x] 3. Implement Git diff processing
  - ✅ GitDiffProcessor class実装完了
  - ✅ 標準入力からの差分読み取り機能実装完了
  - ✅ ステージされた変更の検証機能実装完了
  - ✅ LLM向け差分フォーマット機能実装完了
  - ✅ 空の差分および大容量差分の適切な処理実装完了
  - ✅ DiffDataクラスによる構造化解析実装完了
  - _Requirements: 1.1, 1.4_

- [ ] 4. Create provider factory and base classes
  - Implement ProviderFactory with provider type detection
  - Create BaseProvider abstract class with common interface
  - Add provider registration and instantiation logic
  - Implement connection testing interface for all providers
  - _Requirements: 7.1, 7.4_

- [ ] 5. Implement OpenAI API provider
  - Create OpenAIProvider class with API client integration
  - Add prompt template processing and API request handling
  - Implement error handling for authentication and rate limiting
  - Add streaming support if available
  - _Requirements: 7.1, 7.2, 6.1, 6.4_

- [ ] 6. Implement Anthropic Claude API provider
  - Create AnthropicProvider class with Claude API integration
  - Add model-specific configuration and request formatting
  - Implement Claude-specific error handling and response parsing
  - Add timeout and retry logic for API calls
  - _Requirements: 7.1, 7.2, 6.1, 6.4_

- [ ] 7. Implement Google Gemini API provider
  - Create GeminiAPIProvider class with Gemini API client
  - Add Gemini-specific prompt formatting and safety settings
  - Implement response parsing and error handling
  - Add support for different Gemini model variants
  - _Requirements: 7.1, 7.2, 6.1, 6.4_

- [ ] 8. Implement Gemini CLI provider
  - Create GeminiCLIProvider class with subprocess execution
  - **CLI Requirements:**
    - Binary: `gcloud` from Google Cloud SDK (cloud.google.com)
    - Supported OS: Linux/macOS/Windows, versions 420.0.0+
    - Verification: SHA256 checksums, Apache 2.0 license
    - Installation: Official installer or package managers (apt/brew/choco)
  - **Security Implementation:**
    - Use `subprocess.run()` with `shell=False` and argument lists only
    - Parse external strings with `shlex.split()` before argument construction
    - Mandatory input validation/sanitization for all user-provided data
    - Resource limits: 30s timeout, 1MB stdout/stderr buffer with truncation
    - PATH search policy: Prefer explicit binary paths over PATH resolution
  - **Error Handling:**
    - Map exit codes to user-friendly messages with retry/installation guidance
    - Log only safe metadata (command name, exit code) - exclude raw output
    - Handle CLI absence, permission errors, timeouts, oversized output
  - **Testing Requirements:**
    - Automated tests for normal/error scenarios including binary unavailability
  - _Requirements: 7.1, 7.3, 6.1, 6.4_

- [ ] 9. Implement Claude Code CLI provider
  - Create ClaudeCodeProvider class with CLI integration
  - **CLI Requirements:**
    - Binary: `claude-code` from Anthropic Claude Code (claude.ai/code)
    - Supported OS: Linux/macOS/Windows, versions 1.0.0+
    - Verification: Official installer signatures, proprietary license
    - Installation: Official installer from Anthropic website
  - **Security Implementation:**
    - Use `subprocess.run()` with `shell=False` and argument lists only
    - Parse external strings with `shlex.split()` before argument construction
    - Mandatory input validation/sanitization for all user-provided data
    - Resource limits: 45s timeout, 2MB stdout/stderr buffer with streaming rotation
    - PATH search policy: Require explicit binary path verification
  - **Error Handling:**
    - Map exit codes to user-friendly messages with authentication/installation guidance
    - Log only safe metadata (command name, exit code) - exclude raw output/prompts
    - Handle CLI absence, auth failures, rate limits, timeouts, oversized output
  - **Testing Requirements:**
    - Automated tests for auth/error scenarios including missing binary/credentials
  - _Requirements: 7.1, 7.3, 6.1, 6.4_

- [ ] 10. Create message formatting and output handling
  - Implement MessageFormatter class for response cleaning
  - Add output validation and format standardization
  - Create LazyGit-compatible output formatting
  - Implement message length and content validation
  - _Requirements: 1.2, 3.1, 3.2_

- [ ] 11. Implement comprehensive error handling
  - Create ErrorHandler class with categorized error processing
  - Add user-friendly error messages for each error type
  - Implement logging system for debugging purposes
  - Create error recovery mechanisms where possible
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 12. Add security and validation features
  - Implement API key validation without exposure
  - Add input sanitization for git diff content
  - Create configuration file permission checking
  - Implement secure temporary file handling if needed
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 13. Create comprehensive unit tests
  - Write tests for ConfigManager with various YAML scenarios
  - Create tests for GitDiffProcessor with different diff formats
  - Implement mock tests for all API providers
  - Add tests for CLI providers with subprocess mocking
  - _Requirements: All requirements validation_

- [ ] 14. Create integration tests and LazyGit compatibility
  - Write end-to-end tests simulating LazyGit integration
  - Test provider switching and configuration changes
  - Create tests for error scenarios and recovery
  - Validate streaming output functionality
  - _Requirements: 1.1, 1.2, 7.4, 7.6_

- [ ] 15. Implement performance optimizations
  - Add connection pooling for API providers
  - Implement caching for provider instances and configuration
  - Add diff size limiting and chunking for large changes
  - Optimize startup time and memory usage
  - _Requirements: 1.4, Performance targets_

- [ ] 16. Create installation and setup scripts
  - Write setup.py for package installation
  - Create requirements.txt with all dependencies
  - Add installation validation script
  - Create LazyGit configuration helper script
  - _Requirements: 5.1, 5.2, 5.3_

- [ ] 17. Write comprehensive documentation
  - Create detailed README.md with installation instructions
  - Add configuration examples for all supported providers
  - Write troubleshooting guide with common issues
  - Create LazyGit integration setup guide
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 18. Final integration testing and validation
  - Test complete workflow with real LazyGit installation
  - Validate all provider types with actual API keys
  - Test error scenarios and user experience
  - Perform security audit of API key handling
  - _Requirements: All requirements final validation_