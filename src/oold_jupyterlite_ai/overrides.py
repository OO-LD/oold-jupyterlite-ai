"""Write the settings overrides a site ships with.

The agent brief is authored as markdown and is also the default system prompt. Generating
the override from that file keeps one source: pasting the markdown into JSON by hand would
drift the moment either is edited.

Without this, a visitor gets the stock Jupyternaut prompt and has to paste the brief into
AI Settings before the agent knows anything about OO-LD.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

#: Where jupyterlite-ai keeps the system prompt. Patched over the schema default by the
#: settings addon, which reads overrides.json from the lite directory.
SETTINGS_MODEL = "@jupyternaut/persona:settings-model"

#: No default heading. The prompt is a flavour's to write, and pinning a string here would
#: make every flavour inherit this one's. A flavour that wants the check passes
#: --require-heading; the OO-LD reference site does not, because Site.build composes its
#: prompt rather than reading a file that could silently stop being one.
DEFAULT_HEADING = ""


def write(brief_path: Path, out_path: Path, heading: str = DEFAULT_HEADING) -> int:
    if not brief_path.is_file():
        raise SystemExit(f"agent brief not found: {brief_path}")

    brief = brief_path.read_text(encoding="utf-8").strip()
    if heading and not brief.startswith(heading):
        raise SystemExit(
            f"{brief_path.name} no longer starts with {heading!r}, which the tests pin; "
            "update tests/agent-loop.mjs with it rather than loosening this check"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({SETTINGS_MODEL: {"systemPrompt": brief}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(brief)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--brief", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--require-heading",
        default=DEFAULT_HEADING,
        help="first line the brief has to start with; empty string disables the check",
    )


def main(args: argparse.Namespace) -> None:
    chars = write(args.brief, args.out, args.require_heading)
    print(f"wrote {args.out}, systemPrompt {chars} chars")
