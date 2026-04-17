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

AGENT_MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-5-20250929")
EVAL_MODEL = os.getenv("EVAL_MODEL", "claude-sonnet-4-5-20250929")
MAX_EVAL_ITERATIONS = int(os.getenv("MAX_EVAL_ITERATIONS", "3"))


BACKEND = os.getenv("BACKEND", "api").strip().lower()


def use_vertex() -> bool:
    return BACKEND == "vertex"


if use_vertex():
    os.environ["CLAUDE_CODE_USE_VERTEX"] = "1"


def require_credentials() -> None:
    if BACKEND not in ("api", "vertex"):
        print(f"\n[ERROR] BACKEND must be 'api' or 'vertex', got '{BACKEND}'.")
        print("Edit .env and set BACKEND=api or BACKEND=vertex.")
        raise SystemExit(1)
    if use_vertex():
        missing = [
            v for v in ("ANTHROPIC_VERTEX_PROJECT_ID", "CLOUD_ML_REGION")
            if not os.getenv(v)
        ]
        if missing:
            print(f"\n[ERROR] BACKEND=vertex requires: {', '.join(missing)}")
            print("Set these in .env. See .env.example.")
            raise SystemExit(1)
        return
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[ERROR] BACKEND=api requires ANTHROPIC_API_KEY.")
        print("Set it in .env, or switch to BACKEND=vertex. See .env.example.")
        raise SystemExit(1)


def make_anthropic_client():
    if use_vertex():
        from anthropic import AnthropicVertex
        return AnthropicVertex(
            region=os.getenv("CLOUD_ML_REGION"),
            project_id=os.getenv("ANTHROPIC_VERTEX_PROJECT_ID"),
        )
    return anthropic.Anthropic()


def check_eval_backend_match(source_model: str, target_model: str) -> None:
    """Abort if eval_cases.json model IDs don't match the agent's BACKEND.

    eval must run on the customer's actual backend (FSI customers on Vertex
    may have no direct API access). A format mismatch means .env is wrong.
    """
    looks_vertex = "@" in source_model or "@" in target_model
    if looks_vertex and not use_vertex():
        print(
            "\n[ERROR] eval_cases.json uses Vertex model IDs (e.g. "
            f"'{source_model}') but .env has BACKEND=api.\n"
            "Set BACKEND=vertex (and ANTHROPIC_VERTEX_PROJECT_ID / "
            "CLOUD_ML_REGION / ANTHROPIC_VERTEX_BASE_URL) so eval runs on "
            "the customer's backend."
        )
        sys.exit(1)
    if not looks_vertex and use_vertex():
        print(
            "\n[ERROR] eval_cases.json uses Anthropic API model IDs (e.g. "
            f"'{source_model}') but .env has BACKEND=vertex.\n"
            "Either set BACKEND=api, or rewrite eval_cases.json model IDs "
            "in Vertex format (claude-...@YYYYMMDD)."
        )
        sys.exit(1)

TARGET_TO_SKILL = {
    "haiku-4.5": "migrate-to-haiku-45",
    "sonnet-4.5": "migrate-to-sonnet-45",
    "sonnet-4.6": "migrate-to-sonnet-46",
    "opus-4.6": "migrate-to-opus-46",
}

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


ANSI = {
    'blue': '\033[94m',
    'green': '\033[92m',
    'yellow': '\033[93m',
    'red': '\033[91m',
    'purple': '\033[95m',
    'cyan': '\033[96m',
    'white': '\033[97m',
    'bold': '\033[1m',
    'reset': '\033[0m',
}


def print_banner(title: str, subtitle: str = "", color: str = 'cyan') -> None:
    c = ANSI[color]
    b = ANSI['bold']
    r = ANSI['reset']
    bar = "=" * 60
    print(f"\n{c}{b}{bar}{r}")
    print(f"{c}{b}  {title}{r}")
    if subtitle:
        print(f"{c}  {subtitle}{r}")
    print(f"{c}{b}{bar}{r}\n")


def print_step(label: str, color: str = 'purple') -> None:
    c = ANSI[color]
    b = ANSI['bold']
    r = ANSI['reset']
    print(f"\n{c}{b}▶ {label}{r}\n")


class Spinner:
    FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

    def __init__(self, message: str = "Working", color: str = 'cyan'):
        self.message = message
        self.color = ANSI[color]
        self.reset = ANSI['reset']
        self._task = None
        self._paused = False
        self._stopped = False

    async def _run(self):
        i = 0
        while not self._stopped:
            if not self._paused:
                frame = self.FRAMES[i % len(self.FRAMES)]
                sys.stdout.write(f"\r{self.color}{frame} {self.message}...{self.reset}")
                sys.stdout.flush()
                i += 1
            await asyncio.sleep(0.1)

    def start(self):
        self._task = asyncio.create_task(self._run())

    def _clear_line(self):
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

    def pause(self):
        if not self._paused:
            self._paused = True
            self._clear_line()

    def resume(self):
        self._paused = False

    async def stop(self):
        self._stopped = True
        if self._task:
            await self._task
        self._clear_line()


async def stream_query(prompt: str, options: ClaudeAgentOptions) -> str | None:
    """Run query() with real-time streaming output. Returns the final result text."""
    options.include_partial_messages = True
    result_text = None
    in_text_block = False

    callback_text = ColoredStreamingCallback('white')
    spinner = Spinner("Working")
    spinner.start()

    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, StreamEvent):
                event = msg.event
                etype = event.get("type", "")

                if etype == "content_block_start":
                    block = event.get("content_block", {})
                    if block.get("type") == "text":
                        spinner.pause()
                        in_text_block = True

                elif etype == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        callback_text.on_llm_new_token(delta.get("text", ""))

                elif etype == "content_block_stop":
                    if in_text_block:
                        print(flush=True)
                        in_text_block = False
                        spinner.resume()

            elif isinstance(msg, ResultMessage):
                if in_text_block:
                    print(flush=True)
                result_text = msg.result
    finally:
        await spinner.stop()

    return result_text


def get_report_path(prefix: str, target_model: str) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_slug = target_model.replace(".", "")
    return os.path.join(REPORT_DIR, f"{prefix}_{model_slug}_{timestamp}.md")


async def run_scan(target_model: str, project_path: str):
    print_banner(
        "SCAN MODE",
        f"Target: {target_model}  |  Agent model: {AGENT_MODEL}  |  Project: {project_path}",
        color='cyan',
    )
    print_step("Step 1/2: Scanning code for migration issues", color='purple')
    report_path = get_report_path("scan", target_model)
    system_prompt = apply_prompt_template("scanner", {
        "TARGET_MODEL": target_model,
        "REPORT_PATH": report_path,
    })
    scan_options = ClaudeAgentOptions(
        model=AGENT_MODEL,
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

    print_step("Step 2/2: Applying fixes to source code", color='purple')
    fix_prompt = apply_prompt_template("fixer", {
        "TARGET_MODEL": target_model
    })
    fix_options = ClaudeAgentOptions(
        model=AGENT_MODEL,
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


async def run_eval(target_model: str, project_path: str):
    eval_path = os.path.join(project_path, "eval_cases.json")
    eval_data = validate_eval_cases(eval_path)

    source_model = eval_data["source_model"]
    target_model_id = eval_data["target_model"]
    check_eval_backend_match(source_model, target_model_id)
    system_prompt = eval_data.get("system_prompt", "")
    cases = eval_data["cases"]

    print_banner(
        "EVAL MODE",
        f"Source: {source_model}  →  Target: {target_model_id}  |  Eval model: {EVAL_MODEL}",
        color='cyan',
    )
    print_step(f"Step 1/2: Running {len(cases)} eval cases on both models", color='purple')

    client = make_anthropic_client()
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

    print_step("Step 2/2: LLM-as-Judge evaluation", color='purple')

    report_path = get_report_path("eval", target_model)
    eval_prompt = apply_prompt_template("evaluator", {
        "TARGET_MODEL": target_model,
        "REPORT_PATH": report_path,
    })
    eval_options = ClaudeAgentOptions(
        model=EVAL_MODEL,
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
    check_eval_backend_match(eval_data["source_model"], eval_data["target_model"])

    regression_count = sum(1 for c in eval_data['cases'] if c.get('type') == 'regression')
    subtitle = (
        f"Target: {target_model}  |  Agent: {AGENT_MODEL}  |  Eval: {EVAL_MODEL}  |  "
        f"Max iterations: {max_iterations}  |  "
        f"Eval cases: {len(eval_data['cases'])} ({regression_count} regression)"
    )
    print_banner("AUTOPILOT MODE", subtitle, color='cyan')

    skill_name = TARGET_TO_SKILL[target_model]

    for iteration in range(1, max_iterations + 1):
        print_banner(f"Iteration {iteration}/{max_iterations}", "scan → fix → eval", color='blue')

        # Step 1: Scan
        print_step(f"[Iter {iteration}] Step 1/3: Scanning", color='purple')
        report_path = get_report_path(f"autopilot_scan_iter{iteration}", target_model)
        scan_prompt = apply_prompt_template("scanner", {
            "TARGET_MODEL": target_model,
            "REPORT_PATH": report_path,
        })
        scan_options = ClaudeAgentOptions(
            model=AGENT_MODEL,
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
        print_step(f"[Iter {iteration}] Step 2/3: Applying fixes", color='purple')
        fix_prompt = apply_prompt_template("fixer", {
            "TARGET_MODEL": target_model
        })
        fix_options = ClaudeAgentOptions(
            model=AGENT_MODEL,
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
        print_step(f"[Iter {iteration}] Step 3/3: Evaluating", color='purple')
        source_model = eval_data["source_model"]
        target_model_id = eval_data["target_model"]
        system_prompt = eval_data.get("system_prompt", "")
        cases = eval_data["cases"]

        client = make_anthropic_client()
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
            model=EVAL_MODEL,
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
    scan_p.add_argument("--project-path", required=True, help="Path to project directory")

    eval_p = sub.add_parser("eval", help="Run migration eval cases")
    eval_p.add_argument("--target", required=True, type=validate_target,
                        help="Target model to migrate to")
    eval_p.add_argument("--project-path", required=True, help="Path to directory containing eval_cases.json")

    auto_p = sub.add_parser("autopilot", help="Scan, fix, eval in a loop until pass")
    auto_p.add_argument("--target", required=True, type=validate_target,
                        help="Target model to migrate to")
    auto_p.add_argument("--max-iterations", type=int, default=MAX_EVAL_ITERATIONS,
                        help=f"Maximum scan-fix-eval iterations (default: {MAX_EVAL_ITERATIONS} from MAX_EVAL_ITERATIONS env)")
    auto_p.add_argument("--project-path", required=True, help="Path to project directory (must contain eval_cases.json)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        raise SystemExit(0)
    require_credentials()
    if args.command == "scan":
        asyncio.run(run_scan(args.target, args.project_path))
    elif args.command == "eval":
        asyncio.run(run_eval(args.target, args.project_path))
    elif args.command == "autopilot":
        asyncio.run(run_autopilot(args.target, args.project_path, args.max_iterations))
