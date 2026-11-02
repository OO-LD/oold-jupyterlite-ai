"""Read a flavour's `oold-lite.toml` into a :class:`~oold_jupyterlite_ai.site.Site`.

Every key is optional and every path is resolved against the file's own directory, so a
config can be read from anywhere. Anything this cannot express is a reason to import
:class:`Site` directly rather than to grow a key here.

    [site]
    contents = ["contents"]
    apps     = ["lab"]
    skills   = "skills"

    [agent]
    capabilities = ["validation", "tabular", "rdf"]
    framing      = "brief/framing.md"
    closing      = "brief/closing.md"
    extra        = ["brief/house-rules.md"]

    [wheels]
    oold         = "oold>=2.3"        # downloaded from PyPI unless OOLD_SRC is set
    oold_src     = "../oold-python"   # optional; OOLD_SRC in the environment wins
    requirements = "piplite-requirements.txt"

    [extension]
    path = "../oold-jupyterlite-ai/extension"
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from . import SITE, briefs
from .site import Site

FILENAME = "oold-lite.toml"


#: What a value has to look like to be read as a file rather than used as prompt text.
#: Without this test a renamed `brief/closing.md` would silently become the closing
#: paragraph of the deployed prompt, with the literal string in place of the file.
_LOOKS_LIKE_PATH = (".md", ".txt")


def _text(root: Path, value: str | None) -> str:
    """A key is a path when it is spelled like one, and literal text otherwise."""
    if value is None:
        return ""
    if "\n" not in value and value.endswith(_LOOKS_LIKE_PATH):
        candidate = root / value
        if not candidate.is_file():
            raise SystemExit(f"{value!r} looks like a file but there is nothing at {candidate}")
        return candidate.read_text(encoding="utf-8")
    return value


def _oold_src(root: Path, wheels_cfg: dict) -> Path | None:
    """Where the oold wheel comes from: the environment, then the file, then PyPI.

    OOLD_SRC wins so one export switches a build onto a branch without editing a config
    that is checked in. Unset and unconfigured means the released wheel is downloaded,
    which is what a clone of this repo alone can do.
    """
    from_env = os.environ.get("OOLD_SRC", "").strip()
    if from_env:
        return Path(from_env).expanduser()
    if "oold_src" in wheels_cfg:
        return root / wheels_cfg["oold_src"]
    return None


def load(path: Path) -> Site:
    path = Path(path).resolve()
    root = path.parent
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    site_cfg = data.get("site", {})
    agent_cfg = data.get("agent", {})
    wheels_cfg = data.get("wheels", {})
    ext_cfg = data.get("extension", {})

    capabilities = list(agent_cfg.get("capabilities", briefs.ALL))

    brief = None
    # Any of the three composes a brief. Keying only on `framing` meant a config that set
    # just `closing` wrote no overrides at all and shipped the stock Jupyternaut prompt.
    if agent_cfg.keys() & {"framing", "closing", "extra"}:
        brief = briefs.compose(
            framing=_text(root, agent_cfg.get("framing")),
            capabilities=capabilities,
            closing=_text(root, agent_cfg.get("closing")),
            extra=[_text(root, item) for item in agent_cfg.get("extra", [])],
        )
    elif "prompt" in agent_cfg:
        # Whole-file replacement, for a flavour that wants nothing this package documents.
        brief = root / agent_cfg["prompt"]

    skills = agent_cfg.get("skills") or site_cfg.get("skills")

    return Site(
        contents=[root / c for c in site_cfg.get("contents", ["contents"])],
        apps=list(site_cfg.get("apps", ["lab"])),
        capabilities=capabilities,
        brief=brief,
        skills=(root / skills) if skills else None,
        lite_config=(root / site_cfg["lite_config"]) if "lite_config" in site_cfg else SITE / "jupyter-lite.json",
        piplite_requirements=(
            (root / wheels_cfg["requirements"])
            if "requirements" in wheels_cfg
            else SITE / "piplite-requirements.txt"
        ),
        oold_src=_oold_src(root, wheels_cfg),
        oold_requirement=wheels_cfg.get("oold", "oold"),
        assert_wheel_contains=list(
            wheels_cfg.get("assert_contains", ["oold/cli.py", "oold/validation/formats.py"])
        ),
        extension=(root / ext_cfg["path"]) if "path" in ext_cfg else None,
        rebuild_extension=ext_cfg.get("rebuild", "auto"),
        work=root / site_cfg.get("work", ".build"),
        wheels=root / wheels_cfg.get("dir", "wheels"),
    )


def find(start: Path | None = None) -> Path | None:
    start = Path(start or Path.cwd()).resolve()
    for folder in (start, *start.parents):
        candidate = folder / FILENAME
        if candidate.is_file():
            return candidate
    return None
