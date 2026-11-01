"""Assemble a JupyterLite site with an OO-LD agent in it.

`Site` is the interface. `oold-lite build` fills the same dataclass from a TOML file, so a
flavour that needs to compute something imports this module and one that does not never
sees Python.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import sysconfig
from dataclasses import dataclass, field
from pathlib import Path

from . import SITE, briefs, overrides
from .briefs import Brief

#: Where jupyterlite-ai looks for agent skills, relative to the contents root. The first
#: entry of the setting's default, so a flavour's skills are found without changing it.
SKILLS_DIR = ".agents/skills"


def _python() -> str:
    return sys.executable


def _run(args: list[str], **kwargs) -> None:
    subprocess.run(args, check=True, **kwargs)


@dataclass
class Site:
    """One flavour of the site.

    ``contents`` are copied in order, so a later tree overrides an earlier one by filename.
    ``oold_agent.py`` and ``oold_git.py`` are staged on top of all of them, because the kernel
    imports both from its working directory and a flavour must not be able to shadow them by
    accident.
    """

    contents: list[Path] = field(default_factory=list)
    apps: list[str] = field(default_factory=lambda: ["lab"])
    capabilities: list[str] = field(default_factory=lambda: list(briefs.ALL))
    brief: Brief | Path | str | None = None
    skills: Path | None = None
    lite_config: Path = SITE / "jupyter-lite.json"
    piplite_requirements: Path = SITE / "piplite-requirements.txt"
    #: Wheels built from a checkout rather than pulled from an index. oold tracks a branch,
    #: so the site is built against source rather than against a release.
    oold_src: Path | None = None
    #: Paths inside the oold wheel that have to exist. Emscripten has no subprocess, so the
    #: site drives the CLI in-process and validation imports its format checkers eagerly.
    assert_wheel_contains: list[str] = field(
        default_factory=lambda: ["oold/cli.py", "oold/validation/formats.py"]
    )
    extension: Path | None = None
    rebuild_extension: str = "auto"
    work: Path = Path(".build")
    wheels: Path = Path("wheels")

    def render_brief(self, contents_root: Path) -> str | None:
        if self.brief is None:
            return None
        if isinstance(self.brief, Brief):
            return self.brief.render(contents_root)
        text = Path(self.brief).read_text(encoding="utf-8") if isinstance(self.brief, Path) else self.brief
        return text.strip() + "\n"

    def build(self, output: Path = Path("_output"), debug: bool = True) -> Path:
        output = Path(output).resolve()
        work = Path(self.work).resolve()
        wheels = Path(self.wheels).resolve()
        py = _python()

        # jupyter_core dispatches `jupyter lite` to the first jupyter-lite script on PATH,
        # not to the interpreter running it. A sibling venv on PATH otherwise builds with
        # its own jupyterlite-core and without the labextensions installed here. Invoking
        # the module through sys.executable makes the dispatch interpreter-bound; the PATH
        # prefix covers the addons that shell out again.
        env = dict(os.environ)
        env["PATH"] = os.pathsep.join([str(Path(py).parent), sysconfig.get_path("scripts"), env.get("PATH", "")])

        self._build_extension(py, env)
        built = self._build_wheels(py, wheels)

        print("== staging contents ==")
        shutil.rmtree(work, ignore_errors=True)
        staged = work / "contents"
        staged.mkdir(parents=True)
        for tree in self.contents:
            shutil.copytree(tree, staged, dirs_exist_ok=True)

        # The kernel imports both from its working directory, which is the contents drive.
        # Staged rather than installed: making the first import go through micropip would
        # put the bootstrap behind an index, which is the one thing the offline suite exists
        # to rule out.
        for module in ("oold_agent.py", "oold_git.py"):
            shutil.copy(Path(__file__).parent.parent / module, staged / module)

        # Read back by oold_agent.setup(), so a narrowed build does not ask piplite for a
        # wheel this site never vendored.
        (staged / "oold-capabilities.json").write_text(
            json.dumps(sorted(self.capabilities), indent=2) + "\n", encoding="utf-8"
        )

        if self.skills is not None:
            target = staged / SKILLS_DIR
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(self.skills, target, dirs_exist_ok=True)
            print(f"staged skills from {self.skills}")

        shutil.copy(self.lite_config, work / "jupyter-lite.json")

        prompt = self.render_brief(staged)
        if prompt is not None:
            # The settings addon reads overrides.json from the lite dir and patches it into
            # the settingsOverrides of the built jupyter-lite.json. There is no flag for it:
            # jupyterlite-core still accepts --settings-overrides but no addon reads it.
            out = work / "overrides.json"
            # Stripped: a trailing newline on a system prompt is invisible in the settings
            # UI but shows up as an off-by-one against anything that compares the two.
            prompt = prompt.strip()
            out.write_text(
                json.dumps({overrides.SETTINGS_MODEL: {"systemPrompt": prompt}}, indent=2) + "\n",
                encoding="utf-8",
            )
            print(f"wrote {out.name}, systemPrompt {len(prompt)} chars")

        print("== jupyter lite build ==")
        # No working incremental mode; a stale doit db silently reuses old output.
        shutil.rmtree(output, ignore_errors=True)
        (work / ".jupyterlite.doit.db").unlink(missing_ok=True)

        args = [py, "-m", "jupyter", "lite", "build", "--contents", str(staged)]
        for wheel in built:
            args += ["--piplite-wheels", str(wheel)]
        args += ["--no-libarchive", "--no-unused-shared-packages", "--output-dir", str(output)]
        for app in self.apps:
            args += ["--apps", app]
        if debug:
            args.append("--debug")
        _run(args, cwd=work, env=env)

        print(f"== done: {output} ==")
        return output

    def _build_extension(self, py: str, env: dict[str, str]) -> None:
        if self.extension is None or self.rebuild_extension == "never":
            return
        ext = Path(self.extension).resolve()
        bundle = ext / "labextension"
        if not (ext / "node_modules").is_dir():
            if not bundle.is_dir():
                raise SystemExit(
                    f"{ext} has neither node_modules nor a built labextension. "
                    "Run `npm ci` there first: the bundle is not tracked and pip does not build it."
                )
            return
        # extension/pyproject.toml declares shared-data and no build hook, so pip copies
        # whatever labextension/ holds and never runs tsc. Nothing downstream rebuilds it,
        # which is why a missing bundle is built here rather than silently shipped empty.
        if self.rebuild_extension == "auto" and bundle.is_dir():
            newest = max(
                (p.stat().st_mtime for p in [*(ext / "src").rglob("*"), ext / "package.json"] if p.is_file()),
                default=0,
            )
            if newest <= max((p.stat().st_mtime for p in bundle.rglob("*") if p.is_file()), default=0):
                return
        print("== rebuilding the provider extension ==")
        # env carries the venv scripts dir, where `jupyter-builder` lives; npm run build
        # shells out to it and fails with a bare "command not found" without it.
        _run(["npm", "run", "build"], cwd=ext, env=env, shell=os.name == "nt")
        _run([py, "-m", "pip", "install", "--quiet", "--force-reinstall", "--no-deps", str(ext)], env=env)

    def _build_wheels(self, py: str, wheels: Path) -> list[Path]:
        built: list[Path] = []
        wheels.mkdir(parents=True, exist_ok=True)

        if self.oold_src is not None:
            src = Path(self.oold_src).resolve()
            print(f"== building oold wheel from {src} ==")
            for stale in wheels.glob("oold-*.whl"):
                stale.unlink()
            _run([py, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(wheels)], cwd=src)
            wheel = sorted(wheels.glob("oold-*.whl"))[0]
            self._assert_wheel(wheel)
            built.append(wheel)

        pyodide_version = subprocess.run(
            [py, "-c", "from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION; print(PYODIDE_VERSION)"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

        print(f"== vendoring piplite wheels for pyodide {pyodide_version} ==")
        vendor = wheels / "vendor"
        shutil.rmtree(vendor, ignore_errors=True)
        vendor.mkdir(parents=True)
        # --platform any with --only-binary rejects anything that is not pure python, which
        # is the point: a compiled artifact has to come from the Pyodide distribution.
        _run([
            py, "-m", "pip", "download", "-r", str(self.piplite_requirements),
            "--dest", str(vendor), "--no-deps", "--only-binary=:all:",
            "--platform", "any", "--python-version", "3.14", "--implementation", "py", "--quiet",
        ])

        # The kernel labextension ships ipykernel, pyodide-kernel and piplite but none of
        # their dependencies, so the closure has to start there too.
        bundled = Path(sys.prefix, "share/jupyter/labextensions/@jupyterlite/pyodide-kernel-extension/static/pypi")
        verify = [
            py, "-m", "oold_jupyterlite_ai.cli", "wheels", "verify",
            "--pyodide-version", pyodide_version,
            "--cache", ".cache",
            "--bundled", str(bundled),
            "--dir", str(wheels),
            "--dir", str(vendor),
        ]
        for capability in self.capabilities:
            verify += ["--capability", capability]
        _run(verify)

        built += sorted(vendor.glob("*.whl"))
        print(f"indexing {len(built)} wheels into the site")
        return built

    def _assert_wheel(self, wheel: Path) -> None:
        import zipfile

        names = zipfile.ZipFile(wheel).namelist()
        for required in self.assert_wheel_contains:
            if required not in names:
                raise SystemExit(f"{wheel.name} is missing {required}")
        print(f"wheel ok: {wheel}")
