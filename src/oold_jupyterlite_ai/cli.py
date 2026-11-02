"""The ``oold-lite`` command.

One entry point with subcommands, so a site build is a single dependency rather than a
directory of scripts each consumer has to copy and keep in step.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="oold-lite", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    from . import overrides, serve, wheels

    p = sub.add_parser("build", help="build a site from oold-lite.toml")
    p.add_argument("--config", type=Path, default=None)
    p.add_argument("--output", type=Path, default=None)
    p.add_argument("--oold-src", type=Path, default=None)
    p.add_argument("--apps", action="append", default=None)
    p.add_argument("--capability", action="append", dest="capabilities", default=None)
    p.add_argument("--rebuild-extension", choices=["auto", "always", "never"], default=None)
    p.set_defaults(run=_build)

    p = sub.add_parser("overrides", help="write overrides.json from the agent brief")
    overrides.add_arguments(p)
    p.set_defaults(run=overrides.main)

    p = sub.add_parser("wheels", help="resolve or verify the vendored wheel set")
    wheels.add_arguments(p)
    p.set_defaults(run=wheels.main)

    p = sub.add_parser("serve", help="serve a built site")
    serve.add_arguments(p)
    p.set_defaults(run=serve.main)

    p = sub.add_parser("fixtures", help="regenerate the test fixtures")
    p.add_argument("kind", choices=["xlsx", "docs"])
    p.set_defaults(run=_fixtures)

    args = parser.parse_args(argv)
    return args.run(args) or 0


def _build(args: argparse.Namespace) -> int:
    from . import config
    from .briefs import Brief

    path = args.config or config.find()
    if path is None:
        raise SystemExit(
            f"no {config.FILENAME} here or above. Write one, or import Site and build in python."
        )
    site = config.load(path)

    # Flags win over the file, so a CI run can retarget a build without editing it.
    if args.oold_src is not None:
        site.oold_src = args.oold_src
    if args.apps:
        site.apps = args.apps
    if args.capabilities:
        site.capabilities = args.capabilities
        # config.load froze the list into the Brief, and render_brief reads the Brief, not
        # the Site. Without this the wheel check and oold-capabilities.json narrow while
        # the prompt still documents everything, telling the agent it can do things
        # setup() will not install.
        if isinstance(site.brief, Brief):
            site.brief.capabilities = tuple(args.capabilities)
    if args.rebuild_extension is not None:
        site.rebuild_extension = args.rebuild_extension

    site.build(output=args.output or (path.parent / "_output"))
    return 0


def _fixtures(args: argparse.Namespace) -> int:
    # Imported here, not at module scope: docs needs pymupdf, which only the `fixtures`
    # extra installs, and `oold-lite serve` should not fail because of it.
    if args.kind == "xlsx":
        from .fixtures import xlsx as module
    else:
        from .fixtures import docs as module
    module.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
