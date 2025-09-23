# LazyGit LLM Commit Generator

AI-powered commit message generator for LazyGit.

## Features

- Multi-LLM support (OpenAI, Anthropic, Google Gemini)
- LazyGit integration
- Secure API authentication
- YAML configuration

## Quick Start

### Installation

```bash
git clone https://github.com/yohi/lazygit-llm-commit-generator.git
cd lazygit-llm-commit-generator
python3 install.py
```

### Configuration

```bash
export OPENAI_API_KEY="your-key"
mkdir -p ~/.config/lazygit-llm
cp lazygit-llm/config/config.yml.example ~/.config/lazygit-llm/config.yml
```

### LazyGit Setup

Add to `~/.config/lazygit/config.yml`:

```yaml
customCommands:
  - key: '<c-g>'
    command: 'lazygit-llm-generate'
    context: 'files'
    description: 'Generate commit message with LLM'
    stream: true
```

## Usage

1. Stage files: `git add .`
2. Open LazyGit: `lazygit`
3. Press Ctrl+G to generate commit message

## Requirements

- Python 3.9+
- Git 2.0+
- LazyGit 0.35+

## Documentation

- [User Guide](docs/USER_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Developer Guide](docs/DEVELOPMENT.md)

## License

MIT License


