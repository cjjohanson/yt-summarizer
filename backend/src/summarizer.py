"""LLM summarization — supports Anthropic Claude and OpenAI GPT."""

import os
import time


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
# When running as a module from /app, prompts are at /app/prompts
if not os.path.isdir(PROMPTS_DIR):
    PROMPTS_DIR = os.path.join(os.getcwd(), "prompts")
if not os.path.isdir(PROMPTS_DIR):
    PROMPTS_DIR = "/app/prompts"


def _load_prompt(filename: str) -> str:
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path) as f:
        return f.read()


def _format_duration(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _build_user_message(transcript: str, metadata: dict) -> str:
    duration = _format_duration(metadata.get("duration", 0))
    return (
        f"Here is the video information:\n\n"
        f"Title: {metadata.get('title', 'Unknown')}\n"
        f"Channel: {metadata.get('channel', 'Unknown')}\n"
        f"Duration: {duration}\n"
        f"Upload Date: {metadata.get('upload_date', 'Unknown')}\n\n"
        f"Here is the full transcript:\n\n{transcript}"
    )


class Summarizer:
    def __init__(self, config):
        self.provider = config.llm_provider
        self.model = config.llm_model
        self.config = config

    def summarize(self, transcript: str, metadata: dict) -> dict:
        """
        Generate detailed and executive summaries from a transcript.

        Returns dict with keys "detailed" and "executive".
        """
        word_count = len(transcript.split())
        if word_count > 100_000:
            print(
                f"      WARNING: Transcript is very long ({word_count:,} words). "
                f"LLM API call may fail if context window is exceeded."
            )

        user_message = _build_user_message(transcript, metadata)

        detailed_prompt = _load_prompt("detailed_summary.txt")
        executive_prompt = _load_prompt("executive_summary.txt")

        if self.provider == "anthropic":
            detailed = self._call_anthropic(detailed_prompt, user_message, max_tokens=4096)
            executive = self._call_anthropic(executive_prompt, user_message, max_tokens=1024)
        elif self.provider == "openai":
            detailed = self._call_openai(detailed_prompt, user_message, max_tokens=4096)
            executive = self._call_openai(executive_prompt, user_message, max_tokens=1024)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

        return {"detailed": detailed, "executive": executive}

    def _call_anthropic(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Anthropic API authentication failed.\n"
                "  → Check that your ANTHROPIC_API_KEY is valid."
            )
        except anthropic.RateLimitError:
            print("      Rate limited by Anthropic API. Waiting 30s and retrying...")
            time.sleep(30)
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                raise RuntimeError(
                    "Anthropic API rate limit exceeded even after retry.\n"
                    "  → Wait a few minutes and try again."
                )
        except anthropic.BadRequestError as e:
            if "context" in str(e).lower() or "token" in str(e).lower():
                raise RuntimeError(
                    f"Transcript may be too long for model {self.model}.\n"
                    f"  → Try a model with a larger context window."
                )
            raise

    def _call_openai(self, system_prompt: str, user_message: str, max_tokens: int) -> str:
        from openai import OpenAI, AuthenticationError, RateLimitError

        client = OpenAI(api_key=self.config.openai_api_key)

        try:
            response = client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            return response.choices[0].message.content
        except AuthenticationError:
            raise RuntimeError(
                "OpenAI API authentication failed.\n"
                "  → Check that your OPENAI_API_KEY is valid."
            )
        except RateLimitError:
            print("      Rate limited by OpenAI API. Waiting 30s and retrying...")
            time.sleep(30)
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                )
                return response.choices[0].message.content
            except RateLimitError:
                raise RuntimeError(
                    "OpenAI API rate limit exceeded even after retry.\n"
                    "  → Wait a few minutes and try again."
                )
