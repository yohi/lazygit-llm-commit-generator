"""
LazyGit LLM Commit Message Generator セットアップスクリプト
"""

from setuptools import setup, find_packages
from pathlib import Path

# README.mdの内容を読み込み
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8') if (this_directory / "README.md").exists() else ""

setup(
    name="lazygit-llm-commit-generator",
    version="1.0.0",
    author="LazyGit LLM Team",
    author_email="team@lazygit-llm.example.com",
    description="LLM-powered commit message generator for LazyGit",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yohi/lazygit-llm-commit-generator",
    packages=find_packages(where="lazygit-llm"),
    package_dir={"": "lazygit-llm"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Version Control :: Git",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "PyYAML>=6.0.1",
        "requests>=2.31.0",
        "openai>=1.3.0",
        "anthropic>=0.7.0",
        "google-generativeai>=0.3.0",
        "cryptography>=41.0.0",
        "colorlog>=6.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-mock>=3.11.1",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "psutil>=5.9.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "lazygit-llm-generate=lazygit_llm.main:main",
        ],
    },
    include_package_data=True,
    # MANIFEST.in を使用してファイルを含めるため、package_data は不要
    zip_safe=False,
)
