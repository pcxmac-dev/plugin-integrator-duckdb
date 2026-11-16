"""DuckDB for Liminal: each feed's closed months of bars as an instance of their own, new DuckDB files and files
elsewhere beside it (a database plugin, plugin API 2.3: liminal_libs.storage.databases).

The user, 2026-11-15: "for the integrator i need plugins for each type of database and in each plugin can setup either
new databases or connections to existing databases using many different types of IP or IPC methods. each instance in
the plugin has it's own configuration how it's shared, ports, permissions etc".

Its own instance, `history`, is what the app keeps in DuckDB today: a feed's closed months of bars, a file a month
(history/<feed>/<YYYY-MM>.<n>.duckdb), copied from the feed's SQLite file once a month has closed and read by column
from then on (liminal-libs' storage/history.py). With nothing set, nothing changes. Beside it you may make a new
DuckDB database (a file in the data folder's instances/, or at a whole path) or connect one that exists.

One method, `file`: the file opened directly. DuckDB lets one process read and write a file, or several read it and
none write; a closed month is written once by the system that holds it and only read after, so the suite on another
system (the one inside WSL) reads the same files through its mount and needs no helper. That is also why the plugin
keeps no shares: who reads a file is whoever sees its folder, and it says so. A file is written from the system that
holds it alone.

Every connection it opens has one thread and 64 MB, as the Databases view's reads have. A database it makes says what
it is in a small table (`liminal_instance`)."""
from __future__ import annotations

import os
import re
from importlib import metadata
from pathlib import Path

from liminal_libs import layout, mounts
from liminal_libs.storage.databases import SUFFIXES, DatabasePlugin, Instance, Refusal, now_iso, variable_of

from .apis import APIS, DUCKDB

__version__ = "0.1.0"
HISTORY = "history"  # its own instance: the closed months
MARKER = "liminal_instance"  # the table a database made here says what it is in
THREADS, MEMORY = 1, "64MB"  # a connection it opens: small, as every read of the app's
MONTH_FILE = re.compile(r"^(\d{4}-\d{2})\.(\d+)\.duckdb$")  # a closed month's file: <YYYY-MM>.<version>.duckdb
ENDS = SUFFIXES["duckdb"]


def library() -> str:
    """The DuckDB this Python carries, by its package's word (nothing is loaded to say it); "" when it has none."""
    try:
        return metadata.version("duckdb")
    except metadata.PackageNotFoundError:
        return ""


def months(folder: Path) -> list[tuple[str, str, int]]:
    """The closed months in a history folder: (feed, file, bytes) each, in the order of their months (a month's
    later copy after its earlier one). Names and sizes alone: nothing is opened."""
    out: list[tuple[str, str, int]] = []
    try:
        feeds = sorted(e.name for e in os.scandir(folder) if e.is_dir())
    except OSError:
        return out
    for feed in feeds:
        try:
            with os.scandir(folder / feed) as it:
                out += [(feed, e.name, e.stat().st_size) for e in it if MONTH_FILE.match(e.name) and e.is_file()]
        except OSError:
            continue
    key = lambda row: (MONTH_FILE.match(row[1]).group(1), int(MONTH_FILE.match(row[1]).group(2)), row[0])  # noqa: E731
    return sorted(out, key=key)


def size(n: int) -> str:
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:,.0f} {unit}" if unit == "bytes" else f"{n:,.1f} {unit}"
        n /= 1024
    return f"{n:,.1f} TB"


class DuckdbPlugin(DatabasePlugin):
    name = "duckdb"
    title = "DuckDB"
    about = ("Each feed's closed months of bars (a DuckDB file a month) as an instance of their own, with new DuckDB files "
             "and files elsewhere beside it")
    api = "2.3"
    order = 701
    options = (variable_of("duckdb"),)  # DUCKDB_INSTANCES: what you add, kept through the login
    apis = APIS
    ENGINE = "duckdb"
    METHODS = ("file",)
    HOLDS = ("history",)
    DRIVER = "duckdb"
    DRIVER_HINT = "duckdb is not installed in the app's Python (the app's own dependency: pip install duckdb)"
    SHARES = False
    SHARED = ("its files are opened directly: written by the system that holds them alone, read by any system that sees "
              "their folder (a closed month is written once, then only read)")

    # -- the hooks ---------------------------------------------------------------------------------------------------
    def builtin(self, data_dir: Path) -> tuple[Instance, ...]:
        return (Instance(HISTORY, "Closed months", where=layout.HISTORY + "/", holds=(HISTORY,),
                         note="each feed's closed months of bars, a file a month: history/<feed>/<YYYY-MM>.<n>.duckdb"),)

    def state(self, instance: Instance, data_dir: Path | None = None) -> dict:
        out = super().state(instance, data_dir)
        if instance.builtin and out.get("state") == "absent":  # a data folder no month has closed in yet: not a fault
            out.update(state="empty", why="no closed month has been copied yet")
        return out

    def file_of(self, instance: Instance, part: str = "", data_dir: Path | None = None) -> Path:
        """The file an instance is, or the one of a folder instance that `part` names (<feed>/<month file>). Refusal
        for a part that is no DuckDB file of it."""
        path = self.path_of(instance, data_dir)
        if path is None:
            raise mounts.NotHere(f"{instance.name} is at {instance.where}, on the system that holds the data: this one "
                                 "has no name for that path")
        if not instance.folder:
            if part:
                raise Refusal(f"{instance.name} is one file: there is no {str(part)[:60]!r} in it")
            return path
        named = str(part or "").replace("\\", "/")
        pieces = [p for p in named.split("/") if p not in ("", ".")]
        if not pieces or ".." in pieces or ":" in named or named.startswith("/") or not named.lower().endswith(ENDS):
            raise Refusal(f"{str(part)[:60]!r} is not a DuckDB file of {instance.name}: one is <feed>/<month>.<n>.duckdb")
        return path.joinpath(*pieces)

    def open(self, instance: Instance, part: str = "", read_only: bool = True, data_dir: Path | None = None):
        """A connection to the instance's file (a folder's: the file `part` names), for reading unless asked otherwise;
        written from the system that holds it alone. Never makes one."""
        import duckdb

        path = self.file_of(instance, part, data_dir)
        if not path.is_file():
            raise FileNotFoundError(f"{path}: no such database")
        if not read_only:
            mounts.owner_only(path, "writing a DuckDB file")
        return duckdb.connect(str(path), read_only=read_only, config={"threads": THREADS, "memory_limit": MEMORY})

    def probe(self, instance: Instance, data_dir: Path) -> list[str]:
        if instance.folder:
            folder = self.path_of(instance, data_dir)
            found = months(folder) if folder is not None else []
            lines = [f"DuckDB {library()}, opened here"]
            if not found:
                return [*lines, "no closed month has been copied yet"]
            feeds = len({feed for feed, _, _ in found})
            lines.append(f"{len(found)} closed month{'' if len(found) == 1 else 's'} of {feeds} feed"
                         f"{'' if feeds == 1 else 's'}, {size(sum(n for _, _, n in found))}")
            feed, file, _ = found[-1]
            tables, _made_ = self._asked(instance, f"{feed}/{file}", data_dir)[1:]
            return [*lines, f"{feed}/{file}: {tables} table{'' if tables == 1 else 's'} (the newest, opened for reading)"]
        version, tables, made = self._asked(instance, "", data_dir)
        path = self.file_of(instance, "", data_dir)
        lines = [f"DuckDB {version}, opened here", f"{path.name}: {tables} table{'' if tables == 1 else 's'}"]
        if made:
            lines.append(f"made here on {made.get('made', '?')[:10]} to hold {made.get('holds') or 'nothing yet'}")
        return lines

    def _asked(self, instance: Instance, part: str, data_dir: Path) -> tuple[str, int, dict | None]:
        """One file opened for reading and asked: the DuckDB that answers, its tables, what it says of itself."""
        db = self.open(instance, part, data_dir=data_dir)
        try:
            version = str(db.execute("SELECT library_version FROM pragma_version()").fetchone()[0]).removeprefix("v")
            tables = int(db.execute("SELECT count(*) FROM duckdb_tables() WHERE NOT internal").fetchone()[0])
            try:
                made = {str(k): str(v) for k, v in db.execute(f"SELECT key, value FROM {MARKER}").fetchall()}
            except Exception:  # noqa: BLE001 - no such table: a database not made here
                made = None
        finally:
            db.close()
        return version, tables, made

    def make(self, instance: Instance, data_dir: Path, **given) -> list[str]:
        import duckdb

        path = self.file_of(instance, "", data_dir)
        mounts.owner_only(path.parent if path.parent.exists() else data_dir, "making a DuckDB database")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise Refusal(f"{path} is there already: a new database is never made over a file")
        db = duckdb.connect(str(path), config={"threads": THREADS, "memory_limit": MEMORY})
        try:
            db.execute(f"CREATE TABLE {MARKER} (key VARCHAR PRIMARY KEY, value VARCHAR)")
            db.executemany(f"INSERT INTO {MARKER} VALUES (?, ?)", [
                ["name", instance.name], ["made", instance.at or now_iso()], ["holds", ",".join(instance.holds)],
                ["by", f"plugin-integrator-duckdb {__version__}"]])
        except Exception:
            db.close()
            for name in (path.name, path.name + ".wal"):  # no half-made file is left: the next try would find it there
                try:
                    path.with_name(name).unlink()
                except OSError:
                    pass
            raise
        db.close()
        return [f"{path.name} made in {path.parent}",
                f"written by DuckDB {library()}: a DuckDB older than the one that wrote a file may not read it"]

    def api_facts(self) -> dict:
        """What is known of DuckDB here without asking anything: the library this Python carries."""
        return {DUCKDB.name: {"DuckDB in this Python": library() or "not installed"}}


DATABASE = DuckdbPlugin()
