"""What the DuckDB plugin attaches to (plugin API 2.2, liminal_libs.sources.apis; the user, 2026-11-11: "each plugin
should reflect the the API its attached to, and present links that provide documentation ... it should also expose more
of what the API is about"): DuckDB itself, through its Python client. Local only: nothing is sent anywhere.

Every address is one of DuckDB's own pages (duckdb.org, and its repository on GitHub), each read on 2026-11-16
(`VERIFIED`). The documentation's `stable` addresses led to the pages of 2.0 that day (2.0.0 LTS, released
2026-10-21, the newest on the release calendar): the documentation's home, Python API, Concurrency, Connect, ATTACH
and DETACH Statements, DuckDB_% Metadata Functions, Storage Versions and Format, Configuration and Pragmas.

Two of those pages decide how the plugin works. Concurrency: one process may read and write a database file, or
several may read it and none write; so a closed month, written once and only read after, is read by every system
that sees its folder, and the plugin needs no helper and keeps no shares. Storage Versions and Format: a newer DuckDB
reads the files of an older one, the other way round is not promised, and a DuckDB before 2.0 cannot read the format
2.0 writes by default; so a database made here says which DuckDB wrote it."""
from __future__ import annotations

from liminal_libs.sources.apis import Api, Area, Call, Link

VERIFIED = "2026-11-16"
DOCS = "https://duckdb.org/docs/stable/"
PYTHON = DOCS + "clients/python/overview"
CONCURRENCY = DOCS + "connect/concurrency"
CONNECT = DOCS + "connect/overview"
ATTACH = DOCS + "sql/statements/attach"
META = DOCS + "sql/meta/duckdb_table_functions"
STORAGE = DOCS + "internals/storage"
CONFIGURATION = DOCS + "configuration/overview"
PRAGMAS = DOCS + "configuration/pragmas"
RELEASES = "https://duckdb.org/release_calendar"
SOURCE = "https://github.com/duckdb/duckdb"

DUCKDB = Api(
    name="DuckDB",
    maker="The DuckDB project (duckdb.org)",
    about=("An analytical database engine in a library: a database is one file, read by column, with no server. The app "
           "keeps each feed's closed months of bars in such files, a file a month, written once a month has closed and "
           "only read after. The plugin reaches them through DuckDB's Python client, each file opened directly."),
    kind="sdk",
    base="history/<feed>/<YYYY-MM>.<n>.duckdb in the data folder, instances/, and wherever an instance is",
    version="DuckDB 2.0 (written against 2.0.0 LTS of 2026-10-21, this Python's)",
    auth="none of its own: a file's rights on its system",
    limits="one process reads and writes a file, or several read it and none writes",
    costs="",
    links=(
        Link("DuckDB Documentation", DOCS, "docs"),
        Link("Python API", PYTHON, "reference"),
        Link("Concurrency", CONCURRENCY, "guide"),
        Link("Connect", CONNECT, "guide"),
        Link("Storage Versions and Format", STORAGE, "spec"),
        Link("Release Calendar", RELEASES, "changelog"),
        Link("duckdb/duckdb on GitHub (MIT license)", SOURCE, "source"),
    ),
    areas=(
        Area("Database files", "a persistent database is one file, made or opened by its path; without a path it is "
             "in memory and gone with the process", CONNECT,
             covered="a feed's closed months are its own instance; a new file is made; one that exists is connected"),
        Area("Concurrency", "one process may read and write a file, or several may read it and none write", CONCURRENCY,
             covered="a file is opened for reading unless asked otherwise, and written from the system that holds it "
                     "alone: a closed month is read by every system that sees its folder, with no helper"),
        Area("Storage versions", "a newer DuckDB reads an older one's files; an older one may not read a newer one's, and "
             "one before 2.0 cannot read the format 2.0 writes by default", STORAGE,
             covered="a database made here says which DuckDB wrote it"),
        Area("The Python client", "duckdb.connect(database, read_only, config) and the connection it gives", PYTHON,
             covered="every connection it opens"),
        Area("Configuration", "a connection's settings, its threads and its memory limit among them", CONFIGURATION,
             covered="one thread and 64 MB for every connection it opens"),
        Area("Metadata functions", "the duckdb_% table functions: a database's tables, their estimated rows, their "
             "columns and indexes", META,
             covered="Test counts a file's tables with duckdb_tables()"),
        Area("Pragmas", "statements about the engine itself, its version among them", PRAGMAS,
             covered="Test: the DuckDB that answers (pragma_version())"),
        Area("ATTACH and DETACH", "another database file attached to a connection, read-only when asked", ATTACH),
        Area("Several processes writing", "what the Concurrency page sends writers in several processes to instead of "
             "one file", CONCURRENCY),
        Area("The SQL dialect", "DuckDB's SQL: its statements, functions and types"),
        Area("The other clients", "its command line and its clients for other languages"),
    ),
    calls=(
        Call("duckdb.connect(database, read_only=, config=)", "a connection to a database file", "The Python client",
             used="every open of an instance: read_only unless asked otherwise", docs=PYTHON),
        Call("config={'threads': 1, 'memory_limit': '64MB'}", "a connection's threads and memory", "Configuration",
             used="every connection it opens", docs=CONFIGURATION),
        Call("SELECT library_version FROM pragma_version()", "the engine's version", "Pragmas",
             used="Test: the DuckDB that answers", docs=PRAGMAS),
        Call("SELECT count(*) FROM duckdb_tables() WHERE NOT internal", "a database's own tables", "Metadata functions",
             used="Test: how many tables a file has", docs=META),
        Call("CREATE TABLE liminal_instance (key VARCHAR PRIMARY KEY, value VARCHAR)", "a table made", "The SQL dialect",
             used="a database made here says what it is in it: its name, the day, what it is to hold", writes=True),
        Call("ATTACH 'file' AS name (READ_ONLY)", "another file attached for reading", "ATTACH and DETACH", docs=ATTACH),
        Call("SET access_mode = 'READ_ONLY'", "a database several processes may read", "Concurrency", docs=CONCURRENCY),
    ),
    verified=VERIFIED,
)

APIS = (DUCKDB,)
