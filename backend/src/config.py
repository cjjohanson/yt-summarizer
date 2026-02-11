"""Centralized configuration management. All settings from environment variables."""

import os
import sys


class Config:
    def __init__(self, overrides: dict | None = None):
        overrides = overrides or {}

        self.transcriber = overrides.get("transcriber") or os.getenv("TRANSCRIBER", "groq")
        self.llm_provider = overrides.get("llm_provider") or os.getenv("LLM_PROVIDER", "anthropic")
        self.llm_model = overrides.get("llm_model") or os.getenv("LLM_MODEL")
        self.output_dir = overrides.get("output_dir") or os.getenv("OUTPUT_DIR", "/app/output")

        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")

        self.whisper_server_url = os.getenv(
            "WHISPER_SERVER_URL", "http://host.docker.internal:8080"
        )
        self.whisper_timeout = int(os.getenv("WHISPER_TIMEOUT", "600"))

        # Resolve default model based on provider
        if not self.llm_model:
            if self.llm_provider == "anthropic":
                self.llm_model = "claude-sonnet-4-20250514"
            else:
                self.llm_model = "gpt-4o"

    def validate(self):
        """Validate that required API keys are present. Exits with a clear message if not."""
        errors = []

        if self.transcriber == "groq" and not self.groq_api_key:
            errors.append(
                "GROQ_API_KEY is not set.\n"
                "  → The default transcriber (Groq Whisper) requires a Groq API key.\n"
                "  → Add your Groq API key to the .env file.\n"
                "  → Or use --transcriber openai for OpenAI Whisper, or --transcriber local for local whisper-server."
            )

        if self.transcriber == "openai" and not self.openai_api_key:
            errors.append(
                "OPENAI_API_KEY is not set.\n"
                "  → OpenAI Whisper transcription requires an OpenAI API key.\n"
                "  → Add your OpenAI API key to the .env file.\n"
                "  → Or use --transcriber groq (default) or --transcriber local instead."
            )

        if self.llm_provider == "openai" and not self.openai_api_key:
            errors.append(
                "OPENAI_API_KEY is not set.\n"
                "  → LLM provider 'openai' requires an OpenAI API key.\n"
                "  → Add your OpenAI API key to the .env file."
            )

        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            errors.append(
                "ANTHROPIC_API_KEY is not set.\n"
                "  → Add your Anthropic API key to the .env file.\n"
                "  → Or use --llm openai to use OpenAI for summarization instead."
            )

        if errors:
            for error in errors:
                print(f"\nERROR: {error}", file=sys.stderr)
            sys.exit(1)

    def validate_for_api(self):
        """Validate config for API mode — raises ValueError instead of sys.exit."""
        errors = []

        if self.transcriber == "groq" and not self.groq_api_key:
            errors.append("GROQ_API_KEY is required for Groq Whisper transcription.")

        if self.transcriber == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required for OpenAI Whisper transcription.")

        if self.llm_provider == "openai" and not self.openai_api_key:
            errors.append("OPENAI_API_KEY is required for OpenAI LLM provider.")

        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required for Anthropic LLM provider.")

        if errors:
            raise ValueError(" ".join(errors))
