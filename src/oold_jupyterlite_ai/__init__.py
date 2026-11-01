"""Build an OO-LD schema agent into a static JupyterLite site.

The two modules the kernel imports, :mod:`oold_agent` and :mod:`oold_git`, are shipped
as top-level modules rather than as submodules of this package. Their names are published
API: they appear in the system prompt the agent is given, in the hint strings it reads back
when something is not installed, and in the notebooks a visitor opens. A rename would be a
breaking change to a text file no compiler checks.

This package is the build side, and nothing in it runs under Pyodide.
"""

__all__ = ["SITE"]

from pathlib import Path

#: The reference site: contents, lite config and the pinned vendored wheel set. Resolved
#: from the installed location, so an editable install picks up an edit without reinstalling.
SITE = Path(__file__).parent / "site"
