## Documents

- `doc_profile(path, table=None)` returns that same column shape for one table of a `docx`
  or a `pptx`, plus `format`, `table`, `where` and `tables`. `tables(path)` lists the
  tables alone, each with `index`, `where` it sits and its size. `table=` takes an index,
  never a name; a document has nothing to name its tables by. More than one and
  `doc_profile` takes the first and says so in `problems`.
- `doc_text(path)` returns the prose: `headings` for the outline, `blocks` for the text per
  paragraph, slide or page, and `text` for all of it. Read it before proposing terms. A data
  dictionary or a methods section is usually what says what a column means, and the table
  alone never does.
- The suffix is not trusted. The format is read from the bytes, and a file whose name
  disagrees is still extracted, with the mismatch in `problems`. A spreadsheet handed to
  `doc_profile` is turned away rather than parsed.
- A pdf has no table extraction: `pypdf` reads text and nothing else, so `tables` and
  `doc_profile` come back empty for one and say so. Call `doc_text` instead and read the
  columns off the page text yourself. That text keeps the reading order of the page, so a
  row arrives as a line; decide the column boundaries from the header line and check them
  against a few rows before proposing terms.
