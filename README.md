# plugin-integrator-duckdb

DuckDB for [Liminal](https://github.com/pcxmac-dev/liminal-charts): each feed's closed months of bars as an
instance of their own, with new DuckDB files and files elsewhere beside it.

## What a database plugin is

A Liminal plugin of the integrator's (plugin API 2.3, `liminal_libs.storage.databases`): one engine's. It holds
**instances**. An instance is a database the plugin made, or a connection to one that exists, and each has its own
configuration: what it holds, where it is, the method it is reached by, its port, who else may attach and how far,
and on a server the role used there. The integrator's Databases view lists them, tests them and changes them.

- **With nothing set, nothing changes.** The plugin's own instance is what the app keeps in this engine today, where
  it is and opened as it is.
- **What you add is kept through the plugin's login**, as one value under `DUCKDB_INSTANCES`: never in a file of this
  software's. A sign-in is two more pairs through the login, never in that value and never shown.
- **A change is made by the system that holds the data alone.** The suite on another system (the one inside WSL) reads
  what is kept there and changes nothing of it.
- **Forgetting an instance removes nothing**: what it holds stays where it is. Only you remove data.

## Installing

The app finds it through the entry point group `liminal.providers` and lists it as `package:
plugin-integrator-duckdb`, with this package's version; a checkout in the workspace's `plugins/` folder is loaded
from there. It needs `liminal-libs` 1.61.0 or newer and `duckdb`.

```
python -m pip install -e ".[dev]"
python -m pytest -q
```

The tests open only files of their own (real DuckDB files in a temporary folder); one of them reads the makers' documentation pages, and only with
`LIMINAL_VENDOR_PAGES=1`.

## Its instances

- **`history`, its own**: each feed's closed months of bars, a file a month
  (`history/<feed>/<YYYY-MM>.<n>.duckdb`), copied from the feed's SQLite file once a month has closed and read by
  column from then on. Test lists the months by name and size (nothing opened), then opens the newest one for
  reading and says which DuckDB answered and its tables. A data folder no month has closed in yet is empty, not at
  fault.
- **New database**: a file in the data folder's `instances/` (or at a whole path, in a folder that is there), never
  over a file that is there. It says which DuckDB wrote it (an older DuckDB may not read a newer one's file) and what
  it is in a small table (`liminal_instance`).
- **Connect**: a file that exists, kept only when it is a DuckDB database.

## Its method

**`file`**: the file opened directly, for reading unless asked otherwise, with one thread and 64 MB. DuckDB lets one
process read and write a file, or several read it and none write. A closed month is written once and only read
after, so the suite on another system reads the same files through its mount and needs no helper; a file is written
from the system that holds it alone.

## Sharing

The plugin keeps no shares, and says so: who reads a file is whoever sees its folder.

## Its API

Its page in every app shows what it attaches to (`DATABASE.apis`): the maker's pages, every part of the engine with what the plugin does with it, and the calls it makes among the rest; and what it knows of the engine here without asking anything (`DATABASE.api_facts()`).
