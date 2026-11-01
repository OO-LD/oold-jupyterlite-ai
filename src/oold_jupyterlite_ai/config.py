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
    oold_src     = "../oold-python"
    requirements = "piplite-requirements.txt"

    [extension]
    path = "../oold-jupyterlite-ai/extension"
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from . import SITE, briefs
from .site import Site

FILENAME = "oold-lite.toml"


def _text(root: Path, value: str | None) -> str:
    """A key is a path when it resolves to a file, and literal text otherwise."""
    if value is None:
        return ""
    candidate = root / value
    return candidate.read_text(encoding="utf-8") if candidate.is_file() else value


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
    if "framing" in agent_cfg:
        brief = briefs.compose(
            framing=_text(root, agent_cfg["framing"]),
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
        oold_src=(root / wheels_cfg["oold_src"]) if "oold_src" in wheels_cfg else None,
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
