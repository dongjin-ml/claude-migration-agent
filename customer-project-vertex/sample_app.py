"""
Sample application using Claude Haiku 3 on Google Vertex AI.
This code intentionally contains migration issues for testing the scanner.
The scanner must detect the Vertex backend (from config.py + the AnthropicVertex
import) and preserve it: client class, project/region, proxy base URL must NOT
change. Only the model ID and call parameters should be migrated.
"""

import os
from anthropic import AnthropicVertex

import config

# base_url routes through the internal proxy (ANTHROPIC_VERTEX_BASE_URL in .env)
# instead of the public Vertex endpoint. The migration fixer must preserve this.
client = AnthropicVertex(
    project_id=config.VERTEX_PROJECT_ID,
    region=config.VERTEX_REGION,
    base_url=config.VERTEX_BASE_URL,
)

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def load_prompt(filename: str) -> str:
    with open(os.path.join(PROMPT_DIR, filename), "r") as f:
        return f.read().strip()


def analyze_document(document: str) -> str:
    """Analyze a document using Claude Haiku 3 on Vertex."""
    system_prompt = load_prompt("system_prompt.txt")
    response = client.messages.create(
        model="claude-3-haiku@20240307",  # Issue 1: Old model ID (Vertex format)
        max_tokens=4096,
        temperature=0.7,
        top_p=0.9,  # Issue 2: Cannot use both temperature and top_p
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
        model="claude-3-haiku@20240307",
        max_tokens=4096,
        system=tool_prompt,
        tools=[
            {
                "type": "text_editor_20250124",  # Issue 3: Old tool version
                "name": "str_replace_editor",
            }
        ],
        messages=[
            {"role": "user", "content": user_message}
        ],
    )
    return response


def process_response(response) -> str:
    """Process the API response."""
    # Issue 4 & 5: Missing handling for new stop reasons
    if response.stop_reason == "end_turn":
        return response.content[0].text
    elif response.stop_reason == "max_tokens":
        return "Response truncated due to max tokens."
    elif response.stop_reason == "stop_sequence":
        return response.content[0].text
    else:
        raise ValueError(f"Unexpected stop reason: {response.stop_reason}")


def match_tool_output(tool_result: str, expected: str) -> bool:
    """Check if tool output matches expected value."""
    # Issue 6: Exact string matching without handling trailing newlines
    return tool_result == expected


def get_cost_estimate(input_tokens: int, output_tokens: int) -> float:
    """Calculate cost estimate based on Haiku 3 pricing."""
    # Issue 8: Using Haiku 3 pricing
    input_cost = (input_tokens / 1_000_000) * 0.25
    output_cost = (output_tokens / 1_000_000) * 1.25
    return input_cost + output_cost


if __name__ == "__main__":
    result = analyze_document("This is a test document for analysis.")
    print(result)
