"""Compose a system prompt out of capability fragments.

A flavour supplies its own framing, the part that says what the agent is for and how it
should answer, and selects which capabilities to document. Everything in between is shipped
here and moves with the kernel API it describes, so a flavour never re-documents a function
signature it does not own and cannot drift when one changes.

The file listing is generated from the contents actually being built. A brief that names a
fixture the site does not ship sends the agent looking for a file that is not there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

FRAGMENTS = Path(__file__).parent / "briefs"

#: Fragment order in the composed prompt. `base` is not optional: it is what says how to
#: reach the kernel at all.
ORDER = ("base", "validation", "tabular", "documents", "rdf", "git")

ALL = tuple(name for name in ORDER if name != "base")


def fragment(name: str) -> str:
    path = FRAGMENTS / f"{name}.md"
    if not path.is_file():
        known = ", ".join(sorted(p.stem for p in FRAGMENTS.glob("*.md")))
        raise SystemExit(f"no brief fragment named {name!r}; have: {known}")
    return path.read_text(encoding="utf-8").strip()


#: Staged by the build and of no use to the agent. Naming them in the prompt only invites
#: it to open a file that tells it nothing about the data.
HIDDEN = {"oold-capabilities.json"}


def listing(contents: Path, limit: int = 40) -> str:
    """One line naming what is on the drive, so the agent can open it without guessing."""
    names = sorted(
        p.name
        for p in contents.iterdir()
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix != ".py"
        and p.name not in HIDDEN
    )
    if not names:
        return ""
    shown = names[:limit]
    tail = "" if len(names) == len(shown) else f", and {len(names) - len(shown)} more"
    return "On the drive: " + ", ".join(f"`{n}`" for n in shown) + tail + "."


@dataclass
class Brief:
    """What becomes the `systemPrompt` setting.

    ``framing`` is the flavour's own text and leads the document, so its first line is the
    prompt's heading. ``closing`` lands after the capability fragments, which is where an
    instruction about how to answer belongs: it is the last thing the model reads.
    """

    framing: str
    capabilities: tuple[str, ...] = ALL
    closing: str = ""
    extra: tuple[str, ...] = field(default_factory=tuple)

    def render(self, contents: Path | None = None) -> str:
        parts = [self.framing.strip(), fragment("base")]
        parts += [fragment(name) for name in ORDER[1:] if name in self.capabilities]
        parts += [text.strip() for text in self.extra if text.strip()]
        if contents is not None:
            found = listing(contents)
            if found:
                parts.append(found)
        if self.closing.strip():
            parts.append(self.closing.strip())
        return "\n\n".join(p for p in parts if p) + "\n"


def compose(framing: str, capabilities=ALL, closing: str = "", extra=()) -> Brief:
    return Brief(framing=framing, capabilities=tuple(capabilities), closing=closing, extra=tuple(extra))
