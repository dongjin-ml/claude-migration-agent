"""
Sample application using Claude Haiku 4.5.
Migrated from claude-3-haiku-20240307 → claude-haiku-4-5-20251001.
"""

import os
import anthropic

client = anthropic.Anthropic()

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r") as f:
        return f.read().strip()


def analyze_document(document: str) -> str:
    """Analyze a document using Claude Haiku 4.5."""
    system_prompt = load_prompt("system_prompt.txt")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Item 1: Updated model ID
        max_tokens=4096,
        temperature=0.7,
        # top_p removed — cannot use both temperature and top_p with Claude 4+
        system=system_prompt,
        messages=[
            {"role": "user", "content": document}
        ],
    )
    return response.content[0].text


def run_with_tools(user_message: str) -> str:
    """Run a tool-use workflow."""
    tool_prompt = load_prompt("tool_use_prompt.txt")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Item 1: Updated model ID
        max_tokens=4096,
        system=tool_prompt,
        tools=[
            {
                "type": "text_editor_20250728",        # Item 3: Updated tool version
                "name": "str_replace_based_edit_tool", # Item 3: Updated tool name
            }
        ],
        messages=[
            {"role": "user", "content": user_message}
        ],
    )
    return response


def process_response(response) -> str:
    """Process the API response."""
    if response.stop_reason == "end_turn":
        return response.content[0].text
    elif response.stop_reason == "max_tokens":
        return "Response truncated due to max tokens."
    elif response.stop_reason == "stop_sequence":
        return response.content[0].text
    elif response.stop_reason == "refusal":
        # Item 4: New in Claude 4+ — model declined the request
        raise ValueError("Request was refused by the model.")
    elif response.stop_reason == "model_context_window_exceeded":
        # Item 5: New in Claude 4.5+ — context window exhausted (distinct from max_tokens)
        return "Response stopped: context window exceeded."
    else:
        raise ValueError(f"Unexpected stop reason: {response.stop_reason}")


def match_tool_output(tool_result: str, expected: str) -> bool:
    """Check if tool output matches expected value."""
    # Item 6: Strip trailing newlines — Claude 4.5+ preserves them in tool call parameters
    return tool_result.strip() == expected.strip()


def get_cost_estimate(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost estimate based on Haiku 4.5 pricing."""
    # Item 8: Updated to Haiku 4.5 pricing ($1.00/M input, $5.00/M output — 4x Haiku 3)
    input_cost = (input_tokens / 1_000_000) * 1.00   # Haiku 4.5: $1.00/M input
    output_cost = (output_tokens / 1_000_000) * 5.00  # Haiku 4.5: $5.00/M output
    return input_cost + output_cost


if __name__ == "__main__":
    result = analyze_document("This is a test document for analysis.")
    print(result)
