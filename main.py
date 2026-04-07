import os
import sys
import json
import asyncio
import argparse
from datetime import datetime
from dotenv import load_dotenv
import anthropic
from claude_agent_sdk import query, ClaudeAgentOptions
from claude_agent_sdk.types import ResultMessage, StreamEvent
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from src.prompts.template import apply_prompt_template

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(PROJECT_ROOT, "report")

TARGET_TO_SKILL = {
    "haiku-4.5": "migrate-to-haiku-45",
    "sonnet-4.5": "migrate-to-sonnet-45",
    "sonnet-4.6": "migrate-to-sonnet-46",
    "opus-4.6": "migrate-to-opus-46",
}

TARGET_MODELS = list(TARGET_TO_SKILL.keys())

class ColoredStreamingCallback(StreamingStdOutCallbackHandler):
    COLORS = {
        'blue': '\033[94m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'purple': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
    }

    def __init__(self, color='blue'):
        super().__init__()
        self.color_code = self.COLORS.get(color, '\033[94m')
        self.reset_code = '\033[0m'

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        print(f"{self.color_code}{token}{self.reset_code}", end="", flush=True)


TOOL_LABELS = {
    "Read": "Reading",
    "Write": "Writing",
    "Edit": "Editing",
    "Glob": "Searching files",
    "Grep": "Searching code",
    "Bash": "Running command",
    "Skill": "Loading skill",
}


def _tool_detail(name: str, inp: dict) -> str:
    if name in ("Read", "Write", "Edit") and "file_path" in inp:
        return f" {os.path.basename(inp['file_path'])}"
    elif name == "Bash" and "command" in inp:
        cmd = inp["command"]
        if len(cmd) > 60:
            cmd = cmd[:60] + "..."
        return f" `{cmd}`"
    elif name == "Grep" and "pattern" in inp:
        return f" '{inp['pattern']}'"
    elif name == "Glob" and "pattern" in inp:
        return f" {inp['pattern']}"
    elif name == "Skill" and "skill" in inp:
        return f" {inp['skill']}"
    return ""


async def stream_query(prompt: str, options: ClaudeAgentOptions) -> str | None:
    """Run query() with real-time streaming output. Returns the final result text."""
    options.include_partial_messages = True
    result_text = None
    in_text_block = False
    current_tool_name = None
    tool_input_json = ""

    callback_text = ColoredStreamingCallback('white')
    callback_tool = ColoredStreamingCallback('yellow')

    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, StreamEvent):
            event = msg.event
            etype = event.get("type", "")

            if etype == "content_block_start":
                block = event.get("content_block", {})
                if block.get("type") == "tool_use":
                    if in_text_block:
                        print(flush=True)
                        in_text_block = False
                    current_tool_name = block.get("name", "")
                    tool_input_json = ""
                elif block.get("type") == "text":
                    in_text_block = True

            elif etype == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    callback_text.on_llm_new_token(delta.get("text", ""))
                elif delta.get("type") == "input_json_delta" and current_tool_name:
                    tool_input_json += delta.get("partial_json", "")

            elif etype == "content_block_stop":
                if current_tool_name:
                    label = TOOL_LABELS.get(current_tool_name, current_tool_name)
                    detail = ""
                    try:
                        inp = json.loads(tool_input_json)
                        detail = _tool_detail(current_tool_name, inp)
                    except (json.JSONDecodeError, KeyError):
                        pass
                    callback_tool.on_llm_new_token(f"\n  [tool-use] {label}{detail}\n")
                    current_tool_name = None
                    tool_input_json = ""
                elif in_text_block:
                    in_text_block = False

        elif isinstance(msg, ResultMessage):
            if in_text_block:
                print(flush=True)
            result_text = msg.result

    return result_text


def get_report_path(prefix: str, target_model: str) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = target_model.replace(".", "")
    return os.path.join(REPORT_DIR, f"{prefix}_{model_slug}_{timestamp}.md")


async def run_scan(target_model: str, project_path: str):
    report_path = get_report_path("scan", target_model)
    system_prompt = apply_prompt_template("scanner", {
        "TARGET_MODEL": target_model,
        "REPORT_PATH": report_path,
    })
    scan_options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Skill", "Write"],
        system_prompt=system_prompt,
        setting_sources=["project"],
        permission_mode="acceptEdits",
        cwd=project_path,
    )
    skill_name = TARGET_TO_SKILL[target_model]
    prompt = (
        f"Scan this project for migration issues when upgrading to {target_model}. "
        f"Use the {skill_name} skill for the checklist."
    )
    await stream_query(prompt=prompt, options=scan_options)

    if os.path.exists(report_path):
        print(f"\nReport saved to: {report_path}")
    else:
        print("\nWarning: report was not generated.")
        return

    confirm = input("\nApply fixes? (y/n): ").strip().lower()
    if confirm != "y":
        print("Fixes not applied. You can review the report and re-run later.")
        return

    print("\nApplying fixes...")
    fix_prompt = apply_prompt_template("fixer", {
        "TARGET_MODEL": target_model
    })
    fix_options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Skill", "Edit", "Write", "Bash"],
        system_prompt=fix_prompt,
        setting_sources=["project"],
        permission_mode="acceptEdits",
        cwd=project_path,
    )
    skill_name = TARGET_TO_SKILL[target_model]
    fix_command = (
        f"Read {report_path} and apply all the fixes described in it. "
        f"Use the {skill_name} skill for reference. "
        f"Backup each file with _prev suffix before modifying."
    )
    await stream_query(prompt=fix_command, options=fix_options)


async def run_guide(target_model: str):
    skill_name = TARGET_TO_SKILL[target_model]
    system_prompt = apply_prompt_template("guide", {
        "TARGET_MODEL": target_model,
        "SKILL_NAME": skill_name,
    })
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Glob", "Grep", "Skill"],
        system_prompt=system_prompt,
        setting_sources=["project"],
        permission_mode="acceptEdits",
        cwd=PROJECT_ROOT,
    )
    print(f"Claude Migration Guide - Target: {target_model} (type 'exit' to quit)")
    while True:
        user_input = input("\n> ")
        if user_input.lower() == "exit":
            break
        await stream_query(prompt=user_input, options=options)


async def run_eval(target_model: str, project_path: str):
    eval_path = os.path.join(project_path, "eval_cases.json")
    if not os.path.exists(eval_path):
        print(f"\n[ERROR] eval_cases.json not found in {project_path}")
        print("Create an eval_cases.json file with your test cases. See README.md for format.")
        raise SystemExit(1)

    with open(eval_path, 'r') as f:
        eval_data = json.load(f)

    source_model = eval_data["source_model"]
    target_model_id = eval_data["target_model"]
    system_prompt = eval_data.get("system_prompt", "")
    cases = eval_data["cases"]

    print(f"\nRunning {len(cases)} eval cases...")
    print(f"Source: {source_model}")
    print(f"Target: {target_model_id}")
    print()

    client = anthropic.Anthropic()
    results = []

    for case in cases:
        print(f"  [{case['id']}] {case['name']}... ", end="", flush=True)

        messages = [{"role": "user", "content": case["input"]}]
        kwargs = {"max_tokens": 4096, "messages": messages}
        if system_prompt:
            kwargs["system"] = system_prompt

        source_resp = client.messages.create(model=source_model, **kwargs)
        source_output = source_resp.content[0].text

        target_resp = client.messages.create(model=target_model_id, **kwargs)
        target_output = target_resp.content[0].text

        results.append({
            "id": case["id"],
            "name": case["name"],
            "input": case["input"],
            "expected_output": case.get("expected_output", ""),
            "criteria": case.get("criteria", ""),
            "source_output": source_output,
            "target_output": target_output,
        })
        print("done")

    print("\nAll cases collected. Running LLM-as-Judge evaluation...")

    report_path = get_report_path("eval", target_model)
    eval_prompt = apply_prompt_template("evaluator", {
        "TARGET_MODEL": target_model,
        "REPORT_PATH": report_path,
    })
    eval_options = ClaudeAgentOptions(
        allowed_tools=["Write"],
        system_prompt=eval_prompt,
        setting_sources=["project"],
        permission_mode="acceptEdits",
        cwd=PROJECT_ROOT,
    )

    judge_input = json.dumps(results, indent=2, ensure_ascii=False)
    judge_prompt = (
        f"Evaluate these {len(results)} migration test results. "
        f"Source model: {source_model}, Target model: {target_model_id}.\n\n"
        f"Results:\n{judge_input}"
    )

    await stream_query(prompt=judge_prompt, options=eval_options)

    if os.path.exists(report_path):
        print(f"\nEval report saved to: {report_path}")
    else:
        print("\nWarning: eval report was not generated.")


def validate_eval_cases(eval_path: str):
    if not os.path.exists(eval_path):
        print(f"\n[ERROR] eval_cases.json not found in {os.path.dirname(eval_path)}")
        print("Create an eval_cases.json file with your test cases. See README.md for format.")
        raise SystemExit(1)

    with open(eval_path, 'r') as f:
        eval_data = json.load(f)

    cases = eval_data.get("cases", [])
    if not cases:
        print("\n[ERROR] eval_cases.json has no test cases.")
        raise SystemExit(1)

    types = [c.get("type", "none") for c in cases]
    if "regression" not in types:
        print("\n[WARNING] No regression test cases found in eval_cases.json.")
        print("Regression cases are critical to ensure existing functionality is not broken.")
        print('Add cases with "type": "regression" for features that must continue working.')
        confirm = input("Continue without regression cases? (y/n): ").strip().lower()
        if confirm != "y":
            raise SystemExit(1)

    return eval_data


async def run_autopilot(target_model: str, project_path: str, max_iterations: int = 3):
    eval_path = os.path.join(project_path, "eval_cases.json")
    eval_data = validate_eval_cases(eval_path)

    print(f"\n=== Autopilot Mode ===")
    print(f"Target: {target_model}")
    print(f"Max iterations: {max_iterations}")
    print(f"Eval cases: {len(eval_data['cases'])}")
    regression_count = sum(1 for c in eval_data['cases'] if c.get('type') == 'regression')
    print(f"Regression cases: {regression_count}")
    print()

    skill_name = TARGET_TO_SKILL[target_model]

    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration}/{max_iterations} ---")

        # Step 1: Scan
        print(f"\n[{iteration}/{max_iterations}] Scanning...")
        report_path = get_report_path(f"autopilot_scan_iter{iteration}", target_model)
        scan_prompt = apply_prompt_template("scanner", {
            "TARGET_MODEL": target_model,
            "REPORT_PATH": report_path,
        })
        scan_options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Skill", "Write"],
            system_prompt=scan_prompt,
            setting_sources=["project"],
            permission_mode="acceptEdits",
            cwd=project_path,
        )
        await stream_query(
            prompt=f"Scan this project for migration issues when upgrading to {target_model}. Use the {skill_name} skill for the checklist.",
            options=scan_options,
        )

        # Step 2: Fix
        print(f"\n[{iteration}/{max_iterations}] Applying fixes...")
        fix_prompt = apply_prompt_template("fixer", {
            "TARGET_MODEL": target_model
        })
        fix_options = ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep", "Skill", "Edit", "Write", "Bash"],
            system_prompt=fix_prompt,
            setting_sources=["project"],
            permission_mode="acceptEdits",
            cwd=project_path,
        )
        fix_command = (
            f"Read {report_path} and apply all the fixes described in it. "
            f"Use the {skill_name} skill for reference. "
            f"Backup each file with _prev suffix before modifying."
        )
        await stream_query(prompt=fix_command, options=fix_options)

        # Step 3: Eval
        print(f"\n[{iteration}/{max_iterations}] Evaluating...")
        source_model = eval_data["source_model"]
        target_model_id = eval_data["target_model"]
        system_prompt = eval_data.get("system_prompt", "")
        cases = eval_data["cases"]

        client = anthropic.Anthropic()
        results = []
        for case in cases:
            print(f"  [{case['id']}] {case['name']}... ", end="", flush=True)
            messages = [{"role": "user", "content": case["input"]}]
            kwargs = {"max_tokens": 4096, "messages": messages}
            if system_prompt:
                kwargs["system"] = system_prompt

            source_resp = client.messages.create(model=source_model, **kwargs)
            target_resp = client.messages.create(model=target_model_id, **kwargs)

            results.append({
                "id": case["id"],
                "name": case["name"],
                "type": case.get("type", "improvement"),
                "input": case["input"],
                "expected_output": case.get("expected_output", ""),
                "criteria": case.get("criteria", ""),
                "source_output": source_resp.content[0].text,
                "target_output": target_resp.content[0].text,
            })
            print("done")

        eval_report_path = get_report_path(f"autopilot_eval_iter{iteration}", target_model)
        eval_prompt = apply_prompt_template("evaluator", {
            "TARGET_MODEL": target_model,
            "REPORT_PATH": eval_report_path,
        })
        eval_options = ClaudeAgentOptions(
            allowed_tools=["Write"],
            system_prompt=eval_prompt,
            setting_sources=["project"],
            permission_mode="acceptEdits",
            cwd=PROJECT_ROOT,
        )

        judge_input = json.dumps(results, indent=2, ensure_ascii=False)
        judge_prompt = (
            f"Evaluate these {len(results)} migration test results. "
            f"Source model: {source_model}, Target model: {target_model_id}. "
            f"Pay special attention to cases with type 'regression' - these MUST pass.\n\n"
            f"At the end, output exactly one line: VERDICT: PASS or VERDICT: FAIL\n\n"
            f"Results:\n{judge_input}"
        )

        verdict = "FAIL"
        result_text = await stream_query(prompt=judge_prompt, options=eval_options)
        if result_text and "VERDICT: PASS" in result_text:
            verdict = "PASS"

        if verdict == "PASS":
            print(f"\n=== Autopilot Complete (iteration {iteration}/{max_iterations}) ===")
            print("All eval cases passed. Migration is ready.")
            if os.path.exists(eval_report_path):
                print(f"Final eval report: {eval_report_path}")
            return

        if iteration < max_iterations:
            print(f"\nEval failed. Starting iteration {iteration + 1}...")
        else:
            print(f"\n=== Autopilot stopped after {max_iterations} iterations ===")
            print("Some eval cases still failing. Review the latest report and fix manually.")
            if os.path.exists(eval_report_path):
                print(f"Latest eval report: {eval_report_path}")


def validate_target(target: str) -> str:
    if target not in TARGET_TO_SKILL:
        available = ", ".join(TARGET_TO_SKILL.keys())
        print(f"\n[ERROR] '{target}' is not a supported migration target.")
        print(f"Available targets: {available}")
        raise SystemExit(1)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Claude Migration Agent")
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="Scan code for migration issues")
    scan_p.add_argument("--target", required=True, type=validate_target,
                        help="Target model to migrate to")
    scan_p.add_argument("path", help="Path to project directory")

    guide_p = sub.add_parser("guide", help="Interactive migration guide")
    guide_p.add_argument("--target", required=True, type=validate_target,
                         help="Target model to migrate to")

    eval_p = sub.add_parser("eval", help="Run migration eval cases")
    eval_p.add_argument("--target", required=True, type=validate_target,
                        help="Target model to migrate to")
    eval_p.add_argument("path", help="Path to directory containing eval_cases.json")

    auto_p = sub.add_parser("autopilot", help="Scan, fix, eval in a loop until pass")
    auto_p.add_argument("--target", required=True, type=validate_target,
                        help="Target model to migrate to")
    auto_p.add_argument("--max-iterations", type=int, default=3,
                        help="Maximum scan-fix-eval iterations (default: 3)")
    auto_p.add_argument("path", help="Path to project directory (must contain eval_cases.json)")

    args = parser.parse_args()
    if args.command == "scan":
        asyncio.run(run_scan(args.target, args.path))
    elif args.command == "guide":
        asyncio.run(run_guide(args.target))
    elif args.command == "eval":
        asyncio.run(run_eval(args.target, args.path))
    elif args.command == "autopilot":
        asyncio.run(run_autopilot(args.target, args.path, args.max_iterations))
    else:
        parser.print_help()
