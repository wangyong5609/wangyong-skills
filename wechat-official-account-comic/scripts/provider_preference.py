#!/usr/bin/env python3
"""Read and write the persisted image-provider preference for this Skill."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROVIDERS = {"codex-imagegen", "agnes", "seedream", "pojuwenwen"}
ALIASES = {
    "codex": "codex-imagegen",
    "imagegen": "codex-imagegen",
    "codex-imagegen": "codex-imagegen",
    "agnes": "agnes",
    "seedream": "seedream",
    "doubao": "seedream",
    "ark": "seedream",
    "破局问问": "pojuwenwen",
    "pojuwenwen": "pojuwenwen",
    "breakout": "pojuwenwen",
}


def normalize_provider(value: str) -> str:
    provider = ALIASES.get(value.strip().lower())
    if provider not in PROVIDERS:
        allowed = ", ".join(sorted(PROVIDERS))
        raise ValueError(f"unsupported provider {value!r}; choose one of: {allowed}")
    return provider


def preference_path(runtime: str, store: str | None = None) -> Path:
    if store:
        return Path(store).expanduser()
    home = Path.home()
    if runtime == "codex":
        root = Path(os.environ.get("CODEX_HOME", home / ".codex"))
    elif runtime == "workbuddy":
        root = Path(os.environ.get("WORKBUDDY_HOME", home / ".workbuddy"))
    elif runtime == "generic":
        return home / ".config" / "wechat-official-account-comic" / "preferences.json"
    else:
        raise ValueError(f"unsupported runtime: {runtime}")
    return root / "preferences" / "wechat-official-account-comic.json"


def load_preference(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("preference file must contain a JSON object")
    provider = normalize_provider(str(data.get("provider", "")))
    return {
        "version": int(data.get("version", 1)),
        "provider": provider,
        "updated_at": str(data.get("updated_at", "")),
    }


def save_preference(path: Path, provider: str) -> dict[str, Any]:
    payload = {
        "version": 1,
        "provider": normalize_provider(provider),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        required=True,
        choices=("codex", "workbuddy", "generic"),
        help="runtime whose user-level preference should be used",
    )
    parser.add_argument("--store", help="override preference path, mainly for tests")
    subparsers = parser.add_subparsers(dest="command", required=True)
    get_parser = subparsers.add_parser("get", help="print the saved provider")
    get_parser.add_argument("--json", action="store_true", help="print the full JSON object")
    set_parser = subparsers.add_parser("set", help="save the provider")
    set_parser.add_argument("provider")
    subparsers.add_parser("clear", help="remove the saved preference")
    subparsers.add_parser("path", help="print the preference file path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    path = preference_path(args.runtime, args.store)

    if args.command == "path":
        print(path)
        return 0
    if args.command == "clear":
        path.unlink(missing_ok=True)
        return 0
    if args.command == "set":
        payload = save_preference(path, args.provider)
        print(payload["provider"])
        return 0

    payload = load_preference(path)
    if payload is None:
        return 3
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(payload["provider"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
