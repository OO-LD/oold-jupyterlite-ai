## GitHub

```python
import piplite
await piplite.install(["requests", "pyodide-http"])
import oold_git
```

The module is already on the drive and the working directory is `/drive`.

Nothing in `oold_git` raises. Check `result["ok"]` on every call; on a failure read `reason`,
`message` and `hint`. Do not wrap these calls in try/except.

- `pull(repo, ref, into, paths)`. Always pass `paths`. Without it the whole tree is fetched
  at one request per file, and unauthenticated GitHub allows 60 per hour. Read `rate` before
  a second pull.
- Reads need no token. Writes need a fine-grained PAT with Contents read and write, plus
  Pull requests read and write for `open_pr`. Never print the token and never write it into
  a cell.
- `commit` and `push` are two steps. `status()` between them reports `pending` and
  `remote_head`, and adds `stale` when the remote moved under the staged commit.
- `open_pr` needs `head` to exist on the remote already. This module cannot create a branch.
- There is no local history, no merge and no diff. A `conflict` reason means re-read the file
  and redo the change.
