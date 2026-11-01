## Tabular data

- `csv_profile(path)` returns columns with type, examples, nulls, distinct and unique, plus
  `rows`, `identifier` and `problems`. It never raises; a traceback out of it is a bug worth
  reporting rather than working around.
- `xlsx_profile(path, sheet=None)` returns that same shape for one sheet of a spreadsheet,
  plus `sheet` and `sheets`. `sheets(path)` lists the sheet names alone. On a workbook with
  more than one sheet, `xlsx_profile` profiles the first and says so in `problems`; read the
  `sheets` list, then call it again with `sheet=` per sheet you need.
- `xlsx`, `xlsm`, `xlsb`, `ods` and legacy `xls` all open, through `python-calamine`. Do not
  use `xlrd`: it is in the distribution but 2.x reads `.xls` only and never `.xlsx`. Writing
  a workbook needs `openpyxl`, which `setup()` installs; it is what `DataFrame.to_excel` uses.
- A number in a sheet is a double, so `22` and `22.0` are the same cell. The profiler renders
  it as the sheet shows it, which types a column of whole numbers `integer`.
