# Changelog

## 0.1.0 (2026-11-16)

The first release: DuckDB as a database plugin (plugin API 2.3, liminal-libs 1.61.0; the user, 2026-11-15: "for the
integrator i need plugins for each type of database and in each plugin can setup either new databases or connections
to existing databases").

- Its own instance `history`: each feed's closed months of bars, a file a month, read by name and size until one is
  opened for reading. With nothing set, nothing changes.
- New database (a file in `instances/` or at a whole path, saying which DuckDB wrote it and what it is) and Connect (a
  file that exists, kept only when it is a DuckDB database).
- One method, `file`: read by every system that sees the folder, written from the system that holds it alone; no
  shares, said in words.
- Its API card: DuckDB through its Python client, every address one of duckdb.org's own pages (and its repository),
  read on 2026-11-16, with the two pages that decide how it works (Concurrency, Storage Versions and Format).
