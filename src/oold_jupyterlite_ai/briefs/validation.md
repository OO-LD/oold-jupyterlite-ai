## Command line

`!oold ...` does not work. Emscripten has no subprocess. Use

```python
oold_agent.oold_cli("validate", "Thing.schema.json")
```

It returns everything the CLI printed plus a final `exit code N` line, and never raises.
`--offline` is appended for you, because the kernel reaches only the origin serving the site.

## Reasoning about results

Use the wrappers, not the CLI text, when you have to act on a finding:
`validate_schema`, `validate_instance`, `validate`. Each returns a `Report` with `.passed`,
`.counts`, `.failures()` and `.to_dict()`. Read `check.id` and `check.rule`, never prose.

Ids you will see: `schema.meta`, `schema.refs`, `context.predicates`, `context.coverage`,
`instance.schema`, `roundtrip.generated`, `roundtrip.instance`, `generate.satisfiable`,
`lint.*`, `rule.*`.

Status vocabulary:

- `fail` is a problem in the document.
- `warn` is a SHOULD and does not fail the document.
- `skip` means the check could not run.
- `fault` is a bug in oold: the question was never answered, so do not read the result as
  a pass or a failure of the document.

`passed` is false on `fail` or `fault`, never on `warn`.

All four validate entry points take a dict as well as a path, so validate a draft before
you write it to disk.
