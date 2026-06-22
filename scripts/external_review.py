#!/usr/bin/env python3
"""Run independent reviewers through OpenAI-compatible chat-completions APIs."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
LOCAL_ENV_PATH = SKILL_ROOT / ".env.local"
DEFAULT_PROMPTS_PATH = SKILL_ROOT / "references" / "reviewer-prompts.md"


def load_local_env(path: Path = LOCAL_ENV_PATH) -> None:
    """Load simple KEY=VALUE entries without overriding process environment."""
    if not path.is_file():
        return
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number} must use KEY=VALUE format")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            raise ValueError(f"{path}:{line_number} has an empty key")
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        os.environ.setdefault(key, value)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def load_prompt_markdown(path: Path) -> dict[str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    sections = re.split(r"(?m)^## Prompt: ([a-z0-9-]+)\s*$", text)
    prompts: dict[str, dict[str, str]] = {}
    for index in range(1, len(sections), 2):
        prompt_id = sections[index]
        body = sections[index + 1]
        system_match = re.search(
            r"(?ms)^### System Prompt\s*\n+```text\s*\n(.*?)\n```\s*$",
            body,
        )
        user_match = re.search(
            r"(?ms)^### User Prompt Template\s*\n+```text\s*\n(.*?)\n```",
            body,
        )
        missing = []
        if not system_match:
            missing.append("System Prompt")
        if not user_match:
            missing.append("User Prompt Template")
        if missing:
            raise ValueError(
                f"{path} prompt {prompt_id} missing: {', '.join(missing)}"
            )
        prompts[prompt_id] = {
            "system_prompt": system_match.group(1).strip(),
            "user_prompt_template": user_match.group(1).strip(),
        }
    if not prompts:
        raise ValueError(f"{path} contains no '## Prompt: <prompt-id>' sections")
    return prompts


def validate_reviewer(
    value: Any,
    index: int,
    require_key: bool,
    prompts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"reviewers[{index}] must be an object")
    required = ("name", "endpoint", "model", "api_key_env", "prompt_id")
    missing = [key for key in required if not value.get(key)]
    if missing:
        raise ValueError(f"reviewers[{index}] missing: {', '.join(missing)}")
    if value["prompt_id"] not in prompts:
        raise ValueError(
            f"reviewers[{index}].prompt_id must be one of: {', '.join(prompts)}"
        )
    endpoint = str(value["endpoint"])
    if not endpoint.startswith("https://"):
        raise ValueError(f"reviewers[{index}].endpoint must use https")
    if require_key and not os.environ.get(str(value["api_key_env"])):
        raise ValueError(
            f"environment variable {value['api_key_env']} is not configured"
        )
    return value


def build_payload(
    reviewer: dict[str, Any],
    material: str,
    prompts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    prompt = prompts[reviewer["prompt_id"]]
    payload: dict[str, Any] = {
        "model": reviewer["model"],
        "messages": [
            {
                "role": "system",
                "content": prompt["system_prompt"],
            },
            {
                "role": "user",
                "content": prompt["user_prompt_template"].replace(
                    "{material}", material
                ),
            },
        ],
    }
    for key in ("thinking", "reasoning_effort", "max_tokens", "temperature"):
        if key in reviewer:
            payload[key] = reviewer[key]
    return payload


def parse_model_json(content: str) -> Any:
    candidate = content.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        first_newline = candidate.find("\n")
        if first_newline != -1:
            candidate = candidate[first_newline + 1 : -3].strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {
            "raw_text": content,
            "parse_error": "model returned non-JSON content",
        }


def request_reviewer(
    reviewer: dict[str, Any],
    material: str,
    prompts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    api_key = os.environ[str(reviewer["api_key_env"])]
    request = urllib.request.Request(
        str(reviewer["endpoint"]),
        data=json.dumps(build_payload(reviewer, material, prompts)).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    timeout = float(reviewer.get("timeout_seconds", 180))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:2000]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"request failed: {exc.reason}") from exc

    envelope = json.loads(response_body)
    content = envelope["choices"][0]["message"]["content"]
    parsed = parse_model_json(content)
    return {
        "reviewer": reviewer["name"],
        "provider_endpoint": reviewer["endpoint"],
        "model": reviewer["model"],
        "prompt_id": reviewer["prompt_id"],
        "result": parsed,
    }


async def run_one(
    reviewer: dict[str, Any],
    material: str,
    prompts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    try:
        return await asyncio.to_thread(
            request_reviewer, reviewer, material, prompts
        )
    except Exception as exc:  # Keep other independent reviewers running.
        return {
            "reviewer": reviewer["name"],
            "provider_endpoint": reviewer["endpoint"],
            "model": reviewer["model"],
            "prompt_id": reviewer["prompt_id"],
            "error": str(exc),
        }


async def run(args: argparse.Namespace) -> int:
    load_local_env()
    config = load_json(args.config)
    prompts = load_prompt_markdown(args.prompts)
    raw_reviewers = config.get("reviewers")
    if not isinstance(raw_reviewers, list) or not raw_reviewers:
        raise ValueError("config.reviewers must be a non-empty array")

    active = [
        validate_reviewer(
            value,
            index,
            require_key=not args.dry_run,
            prompts=prompts,
        )
        for index, value in enumerate(raw_reviewers)
        if not isinstance(value, dict) or value.get("enabled", True)
    ]
    if not active:
        raise ValueError("no external reviewers are enabled")

    material = args.input.read_text(encoding="utf-8")
    if args.dry_run:
        summary = {
            "status": "valid",
            "input_chars": len(material),
            "prompts": str(args.prompts),
            "reviewers": [
                {
                    "name": reviewer["name"],
                    "endpoint": reviewer["endpoint"],
                    "model": reviewer["model"],
                    "prompt_id": reviewer["prompt_id"],
                    "api_key_env": reviewer["api_key_env"],
                    "api_key_configured": bool(
                        os.environ.get(str(reviewer["api_key_env"]))
                    ),
                }
                for reviewer in active
            ],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    results = await asyncio.gather(
        *(run_one(reviewer, material, prompts) for reviewer in active)
    )
    output = {
        "review_packet": str(args.input),
        "reviewer_count": len(active),
        "results": results,
    }
    serialized = json.dumps(output, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 1 if all("error" in result for result in results) else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        return asyncio.run(run(parse_args()))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
