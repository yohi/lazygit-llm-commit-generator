"""
CLI Providers Package

CLIベースのLLMプロバイダーの実装モジュール群
"""

from typing import TYPE_CHECKING, Any

# Sorted __all__ list as required by RUF022
__all__ = [
    'ClaudeCodeProvider',
    'GeminiCLIProvider'
]

# Provider name to submodule path mapping for lazy loading
_PROVIDER_MAPPING = {
    'ClaudeCodeProvider': 'claude_code_provider',
    'GeminiCLIProvider': 'gemini_cli_provider'
}

# Cache for imported providers
_provider_cache = {}

if TYPE_CHECKING:
    # Static typing imports - only available during type checking
    from .claude_code_provider import ClaudeCodeProvider
    from .gemini_cli_provider import GeminiCLIProvider


def __getattr__(name: str) -> Any:
    """
    PEP 562 lazy import implementation.

    Import CLI providers on first access to avoid loading dependencies
    until they are actually needed.
    """
    if name in __all__:
        if name in _provider_cache:
            return _provider_cache[name]

        submodule_name = _PROVIDER_MAPPING.get(name)
        if submodule_name:
            try:
                # Import the submodule
                from importlib import import_module
                submodule = import_module(f".{submodule_name}", package=__name__)

                # Get the provider class from the submodule
                provider_class = getattr(submodule, name)

                # Cache the imported class
                _provider_cache[name] = provider_class
                globals()[name] = provider_class

                return provider_class

            except (ModuleNotFoundError, ImportError) as e:
                raise ImportError(
                    f"Failed to import {name}. "
                    f"Required CLI dependencies may not be installed. "
                    f"Original error: {e}"
                ) from e

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """
    Return the list of available exports for interactive use.
    """
    return __all__
