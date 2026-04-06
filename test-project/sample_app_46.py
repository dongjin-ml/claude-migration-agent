"""
Sample application using Claude Sonnet 4.5 / Opus 4.5.
This code intentionally contains 4.6 migration issues for testing the scanner.
"""

import os
import anthropic

client = anthropic.Anthropic()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r") as f:
        return f.read().strip()


def analyze_with_prefill(document: str) -> str:
    """Analyze a document with prefilled assistant response."""
    analysis_prompt = load_prompt("analysis_prompt.txt")
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",  # Issue: Old model ID for 4.6 target
        max_tokens=4096,
        system=analysis_prompt,
        messages=[
            {"role": "user", "content": f"Analyze this document: {document}"},
            {"role": "assistant", "content": "{\"analysis\": "},  # Issue: Prefill deprecated in 4.6
        ],
    )
    return response.content[0].text


def run_with_thinking(query: str) -> str:
    """Run a query with extended thinking."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16384,
        thinking={  # Issue: Should migrate to adaptive thinking for 4.6
            "type": "enabled",
            "budget_tokens": 8192,
        },
        messages=[
            {"role": "user", "content": query}
        ],
    )
    return response.content[0].text


def run_with_output_format(query: str) -> str:
    """Run a query with structured output."""
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
        output_format={  # Issue: Should use output_config.format in 4.6
            "type": "json",
            "schema": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string"},
                    "score": {"type": "number"},
                },
            },
        },
        messages=[
            {"role": "user", "content": query}
        ],
    )
    return response.content[0].text


def run_agent_task(task: str) -> str:
    """Run an agentic task with thorough instructions."""
    agent_prompt = load_prompt("agent_system_prompt.txt")  # Issue: Anti-laziness prompts cause runaway thinking in 4.6
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=16384,
        system=agent_prompt,
        extra_headers={
            "anthropic-beta": "token-efficient-tools-2025-02-19,output-128k-2025-02-19",  # Issue: Legacy beta headers
        },
        messages=[
            {"role": "user", "content": task}
        ],
    )
    return response.content[0].text


def process_response(response) -> str:
    """Process the API response."""
    if response.stop_reason == "end_turn":
        return response.content[0].text
    elif response.stop_reason == "max_tokens":
        return "Response truncated."
    else:
        raise ValueError(f"Unexpected stop reason: {response.stop_reason}")


if __name__ == "__main__":
    result = analyze_with_prefill("This is a test document.")
    print(result)
