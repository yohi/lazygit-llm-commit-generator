# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LazyGit LLM Commit Generator is a Python tool that integrates with LazyGit to automatically generate commit messages using Large Language Models (LLMs). The tool supports multiple LLM providers through both API and CLI interfaces.

## Development Commands

### Setup and Installation
```bash
# Install in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt

# Run the installation script
python3 install.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/ -m unit          # Unit tests only
python -m pytest tests/ -m integration   # Integration tests only
python -m pytest tests/ -m performance   # Performance tests only
python -m pytest tests/ -m "not slow"    # Exclude slow tests

# Run single test file
python -m pytest tests/test_config_manager.py

# Run with coverage
python -m pytest tests/ --cov=lazygit_llm --cov-report=html
```

### Code Quality
```bash
# Format code
black lazygit-llm/lazygit_llm/

# Lint code
flake8 lazygit-llm/lazygit_llm/

# Type checking
mypy lazygit-llm/lazygit_llm/
```

### Configuration Testing
```bash
# Test configuration
python3 lazygit-llm/lazygit_llm/main.py --test-config

# Run with verbose logging
python3 lazygit-llm/lazygit_llm/main.py --verbose
```

### Packaging
```bash
# Test packaging
./test_packaging.sh

# Verify packaging
python3 verify_packaging.py

# Build distribution
python setup.py sdist bdist_wheel
```

## Architecture Overview

### Core Architecture
The project follows a plugin-based architecture with clear separation between API and CLI providers:

```
lazygit_llm/                 # Core application package
├── main.py                  # Entry point and CLI interface
├── config_manager.py        # YAML configuration and env var management
├── git_processor.py         # Git operations and diff processing
├── provider_factory.py      # Factory for creating LLM providers
├── message_formatter.py     # Output formatting and cleanup
└── base_provider.py         # Abstract base class for all providers

src/                         # Provider implementations
├── api_providers/           # REST API-based providers
│   ├── openai_provider.py   # OpenAI GPT integration
│   ├── anthropic_provider.py # Anthropic Claude integration
│   └── gemini_api_provider.py # Google Gemini API integration
├── cli_providers/           # CLI-based providers
│   ├── claude_code_provider.py # Claude Code CLI integration
│   └── gemini_cli_provider.py  # Google Gemini CLI integration
├── error_handler.py         # Centralized error handling
└── security_validator.py   # Input validation and security
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
- Main config: `~/.config/lazygit-llm/config.yml`
- LazyGit integration: `~/.config/lazygit/config.yml`
- Example config: `lazygit-llm/config/config.yml.example`

## Important Implementation Notes
- The `lazygit-llm/` directory contains the actual package source
- Provider modules are dynamically imported by the factory
- All external API calls include timeout and retry mechanisms
- Error handling provides user-friendly messages while logging technical details
- The tool is designed to fail gracefully and never break the user's Git workflow