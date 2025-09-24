# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LazyGit LLM Commit Generator is a Python tool that integrates with LazyGit to automatically generate commit messages using Large Language Models (LLMs). The tool supports multiple LLM providers through both API and CLI interfaces.

## Development Commands

### Setup and Installation
```bash
# Initialize UV project with all dependencies
uv sync --extra dev

# Install project in development mode
uv pip install -e .

# Run the automated installation script (recommended for new setups)
uv run python install.py
# This script handles: dependency installation, config directory creation,
# LazyGit integration setup, and binary linking

# Manual installation for advanced users
./lazygit-llm-generate --test-config
```

### Testing
```bash
# Run all tests
uv run pytest tests/

# Run specific test categories (defined in pyproject.toml)
uv run pytest tests/ -m unit          # Unit tests - Individual component testing
uv run pytest tests/ -m integration   # Integration tests - End-to-end provider testing  
uv run pytest tests/ -m performance   # Performance tests - Response time and resource usage
uv run pytest tests/ -m "not slow"    # Exclude slow tests - Fast test execution

# Run single test file
uv run pytest tests/test_config_manager.py

# Run with coverage
uv run pytest tests/ --cov=lazygit_llm --cov-report=html

# Run tests from specific directories
uv run pytest tests/integration/      # Integration tests only
uv run pytest tests/performance/      # Performance tests only
```

### Code Quality
```bash
# Format code
uv run black lazygit-llm/lazygit_llm/

# Lint code
uv run flake8 lazygit-llm/lazygit_llm/

# Type checking
uv run mypy lazygit-llm/lazygit_llm/
```

### Configuration Testing
```bash
# Test configuration
uv run python lazygit-llm/lazygit_llm/main.py --test-config

# Run with verbose logging
uv run python lazygit-llm/lazygit_llm/main.py --verbose

# Run using installed command
uv run lazygit-llm-generate --test-config
```

### Packaging
```bash
# Build package using UV
uv build

# Install package locally for testing
uv pip install dist/*.whl

# Create development environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Add new dependencies
uv add package_name

# Add development dependencies
uv add --dev package_name
```

## Architecture Overview

### Core Architecture
The project follows a plugin-based architecture with clear separation between API and CLI providers:

```
lazygit-llm/                 # Project root directory
├── lazygit_llm/             # Core application package
│   ├── main.py              # Entry point and CLI interface
│   ├── config_manager.py    # YAML configuration and env var management
│   ├── git_processor.py     # Git operations and diff processing
│   ├── provider_factory.py  # Factory for creating LLM providers
│   ├── message_formatter.py # Output formatting and cleanup
│   ├── base_provider.py     # Abstract base class for all providers
│   ├── api_providers/       # (legacy) API provider imports
│   └── cli_providers/       # CLI provider implementations
│       ├── claude_code_provider.py # Claude Code CLI integration
│       └── gemini_cli_provider.py  # Google Gemini CLI integration
├── src/                     # Provider implementations
│   ├── api_providers/       # REST API-based providers
│   │   ├── openai_provider.py   # OpenAI GPT integration
│   │   ├── anthropic_provider.py # Anthropic Claude integration
│   │   └── gemini_api_provider.py # Google Gemini API integration
│   ├── cli_providers/       # Additional CLI provider implementations
│   ├── error_handler.py     # Centralized error handling
│   └── security_validator.py # Input validation and security
└── tests/                   # Comprehensive test suite
    ├── integration/         # End-to-end integration tests
    ├── performance/         # Performance and load testing
    └── test_*.py           # Unit tests for each component
```

### Provider System
All LLM providers inherit from `BaseProvider` and implement:
- `generate_commit_message(diff: str, prompt_template: str) -> str`
- `test_connection() -> bool`

The `ProviderFactory` dynamically loads providers based on configuration:
- API providers require API keys and HTTP client setup
- CLI providers interface with external command-line tools
- Configuration validates provider availability and settings

### Data Flow
1. **Input**: Git diff from `git diff --staged` via `GitDiffProcessor`
2. **Configuration**: YAML config loaded via `ConfigManager` with environment variable expansion
3. **Provider Selection**: `ProviderFactory` creates appropriate provider instance
4. **Generation**: Provider processes diff with prompt template
5. **Output**: `MessageFormatter` cleans and formats the generated message
6. **LazyGit Integration**: Output displayed in LazyGit for user confirmation

### Configuration Management
- YAML-based configuration with environment variable substitution (`${VAR_NAME}`)
- Secure API key management through environment variables
- Provider-specific parameters and prompt templates
- Validation and fallback mechanisms

### Security Considerations
- API keys stored in environment variables, never in code/config files
- Input sanitization via `SecurityValidator`
- Subprocess execution with `shell=False` for CLI providers
- Temporary file handling for secure logging

### Testing Strategy
- **Unit tests**: Individual component testing with mocking
- **Integration tests**: End-to-end provider testing
- **Performance tests**: Response time and resource usage
- Mock implementations for external APIs during testing

## Configuration File Locations
- **Main config**: `~/.config/lazygit-llm/config.yml`
- **LazyGit integration**: `~/.config/lazygit/config.yml`
- **Example configs**: 
  - `config/config.yml.example` (project root)
  - `lazygit-llm/config/config.yml.example` (package level)
- **Development config**: `lazygit-llm/config/config.yml` (local testing)

## Important Implementation Notes

### Package Structure
- The `lazygit-llm/` directory contains the actual package source code
- Provider modules are dynamically imported by the factory pattern
- Both `src/` and `lazygit_llm/` contain provider implementations (legacy structure)

### Development Workflow  
- Use `install.py` for automated setup of new development environments
- The tool integrates with LazyGit as a custom command (`Ctrl+G` by default)
- All external API calls include configurable timeout and retry mechanisms
- Error handling provides user-friendly messages while logging technical details

### Design Principles
- Fail gracefully and never break the user's Git workflow
- Security-first approach with input sanitization and safe subprocess execution
- Plugin-based architecture allows easy addition of new LLM providers
- Environment variable-based configuration for secure API key management