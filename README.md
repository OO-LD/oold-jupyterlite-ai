# oold-jupyterlite-ai

An OO-LD schema agent in a static JupyterLite site. Point a model at a folder of CSV files,
spreadsheets and documents and get validated OO-LD schemas back, with no server: the kernel,
the files and the validator all run in the browser.

This is the reusable half of the
[AI schema agent playground](https://playgrounds.oo-ld.org/ai/lab/index.html). Build your
own flavour of it, or build that one.

## What is in here

| | |
| --- | --- |
| `src/oold_agent.py` | the kernel API the agent calls: profiling, validation, RDF export, graph and term rendering |
| `src/oold_git.py` | a GitHub REST client for the kernel. Nothing in it raises; every call returns a dict |
| `src/oold_jupyterlite_ai/` | the build: `Site`, the TOML front end, wheel vendoring, prompt composition |
| `src/oold_jupyterlite_ai/briefs/` | the system prompt, one fragment per capability |
| `extension/` | `oold-azure-providers`, registering Azure OpenAI and Azure AI Foundry Anthropic with jupyterlite-ai |
| `tests/` | six deterministic Playwright suites, 504 checks, plus two opt-in live ones |

Two distributions on purpose. `oold-jupyterlite-ai` is pure python and declares no runtime
dependencies, because `oold_agent.setup()` installs them inside the kernel in an order wheel
metadata cannot express. `oold-azure-providers` carries the compiled labextension, which the
kernel has no use for.

## Build a site

```bash
python -m venv .venv
.venv/bin/python -m pip install -e .[build]
(cd extension && npm ci && npm run build)
.venv/bin/python -m pip install --no-deps ./extension
.venv/bin/python -m oold_jupyterlite_ai.cli build
.venv/bin/python -m oold_jupyterlite_ai.cli serve --port 8903
```

The `oold` wheel is downloaded from PyPI. Export `OOLD_SRC=/path/to/oold-python` to build it
from a checkout instead, which is how a branch ahead of the last release is tracked.

The labextension is built by npm, never by pip. `npm run build` shells out to
`jupyter-builder`, a console script from the build venv, and pip's subprocess does not
inherit it. `oold-lite build` rebuilds it when `extension/src` is newer.

## Make your own flavour

Nothing here is OO-LD specific except the reference site's own framing. A flavour declares
what it wants in `oold-lite.toml`:

```toml
[site]
contents = ["contents"]

[agent]
capabilities = ["validation", "tabular"]
framing = "brief/framing.md"
skills  = "skills"
```

`capabilities` picks which brief fragments are included, which packages `setup()` installs
and which wheels are vendored, together. A `["validation", "tabular"]` flavour vendors 14
packages instead of 17 and ships a 3.8 KB prompt instead of 7.9 KB, with no `pypdf` or
`oold_git` sections in it. The file listing in the prompt is generated from the contents
being built, so a brief cannot name a file the site does not ship.

Anything the TOML cannot express is a reason to use the API directly:

```python
from oold_jupyterlite_ai import Site, briefs

Site(
    contents=["contents"],
    capabilities=["validation", "tabular"],
    brief=briefs.compose(framing=my_framing, capabilities=["validation", "tabular"]),
).build(output="_output")
```

## Skills

`skills` in the config is staged into `.agents/skills`, where jupyterlite-ai looks. Skills
also load at runtime: write a `SKILL.md` into `_agents/skills/<name>/` on the contents drive
and run the `@jupyternaut/persona:refresh-skills` command. That is how a pack fetched from a
repository gets registered without a rebuild, and it is what `oold_git.pull` into that
directory is for.

## Test

```bash
.venv/bin/python -m oold_jupyterlite_ai.cli serve --port 8903 --dir _output &
for s in run offline kernel-api git providers agent-loop; do node tests/$s.mjs; done
```

`BASE` points a suite at any served site, which is how the playground's deployed subpath is
checked. `offline.mjs` is the one to watch in any change to vendoring: it blocks pypi.org and
files.pythonhosted.org and asserts that a cold start reaches neither.

`live-agent.mjs` and `live-git.mjs` need real credentials and are never required to merge.

## Pyodide constraints this inherits

- `OOLD_DESCRIPTOR_BINDING` is set when `oold_agent` is imported, before anything imports
  `oold.model`; the binding is chosen at that first import.
- No subprocess, so `!oold ...` does not work and the CLI is driven in-process.
- The kernel loads a distribution package only when the literal import appears in the cell
  source it is about to run, which is why `setup()` installs rather than imports.
- `pyodide_http.patch_all()` covers requests and urllib but never httpx.
- pdfs are read with `pypdf`, text only. `pymupdf` finds tables but is a 17.3 MB compiled
  wheel that could only come from a CDN, and column detection is the agent's job here.
