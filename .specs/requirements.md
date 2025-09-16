# Requirements Document

## Introduction

This feature adds LLM-powered automatic commit message generation to LazyGit, a terminal-based Git client. The system will analyze staged code differences and use Large Language Models to suggest appropriate commit messages, reducing cognitive load on developers and helping maintain consistent, high-quality commit logs.

## Requirements

### Requirement 1

**User Story:** As a developer using LazyGit, I want to automatically generate commit messages from staged changes, so that I can save time and maintain consistent commit message quality.

#### Acceptance Criteria

1. WHEN the user presses a specific key (e.g., <c-g>) in LazyGit's Files panel THEN the system SHALL analyze all staged file differences and generate a commit message using LLM
2. WHEN the LLM generates a commit message THEN the system SHALL automatically insert it into LazyGit's commit message panel
3. WHEN there are no staged files THEN the system SHALL display "No staged files found" message without making API calls
4. WHEN the commit message generation is complete THEN the process SHALL take no more than 10 seconds under normal network conditions

### Requirement 2

**User Story:** As a developer, I want to configure LLM settings through a configuration file, so that I can customize the API keys, models, and prompts according to my preferences.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL read configuration from a config.yml file containing API_KEY, MODEL_NAME, and PROMPT_TEMPLATE
2. WHEN the configuration file is missing or unreadable THEN the system SHALL display an appropriate error message
3. WHEN an invalid API key is provided THEN the system SHALL display an authentication error message
4. IF the configuration file permissions are not restricted to user-only THEN the documentation SHALL recommend setting permissions to 600

### Requirement 3

**User Story:** As a developer, I want to customize the prompt template, so that I can control the format and language of generated commit messages.

#### Acceptance Criteria

1. WHEN the user modifies PROMPT_TEMPLATE in the configuration THEN the system SHALL use the custom template for message generation
2. WHEN the prompt template contains a {diff} placeholder THEN the system SHALL replace it with the actual staged differences
3. WHEN the user wants Conventional Commits format THEN the system SHALL support this through template customization
4. WHEN the user prefers Japanese or English messages THEN the system SHALL support both languages through template configuration

### Requirement 4

**User Story:** As a developer, I want secure API key management, so that my credentials are not exposed in the codebase.

#### Acceptance Criteria

1. WHEN storing API keys THEN the system SHALL NOT hardcode them in the script files
2. WHEN reading API keys THEN the system SHALL load them from environment variables or dedicated configuration files
3. WHEN accessing configuration files THEN the system SHALL recommend user-only permissions (600) in documentation
4. WHEN API requests fail due to authentication THEN the system SHALL display clear error messages without exposing sensitive information

### Requirement 5

**User Story:** As a developer, I want clear installation and setup instructions, so that I can easily integrate this feature into my workflow.

#### Acceptance Criteria

1. WHEN installing the feature THEN the documentation SHALL provide step-by-step setup instructions for users with basic Python knowledge
2. WHEN configuring LazyGit THEN the documentation SHALL include custom command configuration examples
3. WHEN setting up the configuration file THEN the documentation SHALL provide config.yml examples
4. WHEN troubleshooting issues THEN the documentation SHALL include common problems and solutions

### Requirement 6

**User Story:** As a developer, I want robust error handling, so that I can understand and resolve issues when they occur.

#### Acceptance Criteria

1. WHEN API requests fail THEN the system SHALL display descriptive error messages indicating the failure reason
2. WHEN the configuration file has syntax errors THEN the system SHALL display specific parsing error information
3. WHEN network connectivity issues occur THEN the system SHALL provide appropriate timeout and connection error messages
4. WHEN the LLM API returns unexpected responses THEN the system SHALL handle gracefully and inform the user

### Requirement 7

**User Story:** As a developer, I want support for multiple LLM providers and interfaces, so that I can choose the most suitable model and access method for my needs.

#### Acceptance Criteria

1. WHEN configuring the system THEN it SHALL support OpenAI API, Anthropic Claude API, Google Gemini API, Gemini CLI, and Claude Code
2. WHEN using API-based providers THEN the system SHALL use the appropriate client library for each API
3. WHEN using CLI-based providers (Gemini CLI, Claude Code) THEN the system SHALL execute the appropriate command-line interface
4. WHEN switching between providers THEN the system SHALL automatically detect the provider type and use the correct interface method
5. WHEN a provider is unavailable THEN the system SHALL display provider-specific error messages
6. IF streaming output is supported THEN the system SHALL display real-time generation progress to reduce perceived wait time