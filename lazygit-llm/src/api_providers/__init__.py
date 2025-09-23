"""
API Providers Package

LLM APIプロバイダーの実装モジュール群
"""

from typing import TYPE_CHECKING, Any

# Sorted __all__ list as required by RUF022
__all__ = [
    'AnthropicProvider',
    'GeminiAPIProvider',
    'OpenAIProvider'
]

# Provider name to submodule path mapping for lazy loading
_PROVIDER_MAPPING = {
    'AnthropicProvider': 'anthropic_provider',
    'GeminiAPIProvider': 'gemini_api_provider',
    'OpenAIProvider': 'openai_provider'
}

# Cache for imported providers
_provider_cache = {}

if TYPE_CHECKING:
    # Static typing imports - only available during type checking
    from .anthropic_provider import AnthropicProvider
    from .gemini_api_provider import GeminiAPIProvider
    from .openai_provider import OpenAIProvider


def __getattr__(name: str) -> Any:
    """
    PEP 562 lazy import implementation.

    Import providers on first access to avoid loading dependencies
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
                    f"Required dependencies may not be installed. "
                    f"Original error: {e}"
                ) from e

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    """
    Return the list of available exports for interactive use.
    """
    return __all__
