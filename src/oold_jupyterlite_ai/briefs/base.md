Run Python with the `jupyterlab-ai-commands:execute-in-kernel` command. There is one kernel
per notebook and it keeps its state between calls, so import once and reuse.

## Start of a session

```python
import oold_agent
await oold_agent.setup()
```

Import `oold_agent` before anything touches `oold`: it sets `OOLD_DESCRIPTOR_BINDING` at
import time and the binding is chosen when `oold.model` is first imported. `setup` is the
only coroutine in the module; everything else is an ordinary call.

## Installing something else

`setup()` installs the readers and validators listed below from wheels shipped with the
site, with no network. Anything beyond them you install yourself:

```python
import piplite
await piplite.install("humanize")
```

Pure python only, unless the name is one the Pyodide distribution carries as a compiled
wheel, which `piplite.install` picks up the same way. Everything else resolves against
PyPI over the network, so it fails where the site is opened offline and it is slow on a
large dependency set. Reach for it when the task needs a library, not to replace what
`setup()` already installed.

## Pyodide trap

The kernel loads a distribution package only when the literal import statement appears in the
cell source it is about to run. An import inside a module on the drive is invisible to that
scan. If you need a package, write the import in the cell you execute.
