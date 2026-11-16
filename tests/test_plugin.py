"""The DuckDB plugin on real DuckDB files of the test's own (nothing of the app's is opened, no process started): its
own instance is the closed months' folder, read by name and size until one file is opened for reading; a new database
is made and says what it is; one that exists is connected only when it is a DuckDB file; a file is opened for reading
unless asked otherwise, and written from the system that holds it alone; it keeps no shares and says who reads it."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

duckdb = pytest.importorskip("duckdb")

from liminal_libs import mounts  # noqa: E402
from liminal_libs.apps import EnvironmentLogin  # noqa: E402
from liminal_libs.storage.databases import Instance, Refusal  # noqa: E402
from plugin_integrator_duckdb import DATABASE, MARKER, DuckdbPlugin, __version__, library, months, size  # noqa: E402


def month(path, rows=3) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = duckdb.connect(str(path))
    db.execute("CREATE TABLE bars (ticker VARCHAR, ts BIGINT, c DOUBLE)")
    db.execute("CREATE TABLE built_bars (ticker VARCHAR, ts BIGINT, c DOUBLE)")
    db.executemany("INSERT INTO bars VALUES (?, ?, ?)", [["AAPL", i, float(i)] for i in range(rows)])
    db.close()


@pytest.fixture
def ducks(tmp_path):
    """The plugin attached to an app whose data folder is the test's: two feeds' closed months, one copied twice."""
    data = tmp_path / "data"
    for name in ("massive/2026-09.1.duckdb", "massive/2026-10.1.duckdb", "massive/2026-10.2.duckdb", "tiingo/2026-09.1.duckdb"):
        month(data / "history" / name)
    (data / "history" / "massive" / "2026-11.1.duckdb.part").write_bytes(b"a copy going on")
    (data / "history" / "notes.txt").write_text("not a feed's folder", encoding="utf-8")
    env: dict = {}
    plugin = DuckdbPlugin()
    plugin.attach(SimpleNamespace(db_path=data / "liminal.db"), EnvironmentLogin(env=env))
    return plugin, data, env


def test_its_own_instance_is_the_closed_months_read_by_name_until_one_is_opened(ducks):
    plugin, data, env = ducks
    assert DATABASE.name == "duckdb" and isinstance(DATABASE, DuckdbPlugin) and plugin.driver() == (True, "")
    assert library() == duckdb.__version__ and plugin.api_facts() == {"DuckDB": {"DuckDB in this Python": duckdb.__version__}}
    (own,) = plugin.instances()
    assert (own.name, own.where, own.method, own.holds, own.builtin, own.folder) == ("history", "history/", "file", ("history",), True, True)
    assert plugin.path_of(own) == data / "history" and plugin.state(own)["state"] == "ready" and plugin.effective_method(own) == "file"
    found = months(data / "history")
    assert [(feed, file) for feed, file, _ in found] == [("massive", "2026-09.1.duckdb"), ("tiingo", "2026-09.1.duckdb"),
                                                         ("massive", "2026-10.1.duckdb"), ("massive", "2026-10.2.duckdb")]
    tested = plugin.test("history")
    assert tested["ok"] and tested["said"].startswith("history answers (file, ")
    assert tested["lines"] == [f"DuckDB {duckdb.__version__}, opened here",
                               f"4 closed months of 2 feeds, {size(sum(n for _, _, n in found))}",
                               "massive/2026-10.2.duckdb: 2 tables (the newest, opened for reading)"]
    # a month by its path in it; for reading unless asked otherwise
    db = plugin.open(own, "massive/2026-09.1.duckdb")
    assert db.execute("SELECT count(*) FROM bars").fetchone() == (3,)
    with pytest.raises(duckdb.Error, match="read-only"):
        db.execute("INSERT INTO bars VALUES ('MSFT', 9, 9.0)")
    db.close()
    for part in ("", "massive", "../x.duckdb", "massive/2026-09.1.duckdb.part", "massive/notes.txt", "C:/x.duckdb"):
        with pytest.raises(Refusal, match="is not a DuckDB file of history"):
            plugin.open(own, part)
    with pytest.raises(FileNotFoundError, match="no such database"):
        plugin.open(own, "massive/2031-01.1.duckdb", read_only=False)
    assert not (data / "history" / "massive" / "2031-01.1.duckdb").exists() and env == {}
    status = plugin.status()
    assert (status["engine"], status["shares"], status["can"]["share"], status["can"]["new"]) == ("duckdb", False, False, True)
    assert status["instances"][0]["sharedWords"].startswith("its files are opened directly")
    with pytest.raises(Refusal, match="its files are opened directly"):
        plugin.share("history", "linux::Ubuntu", "read")
    assert size(512) == "512 bytes" and size(2048) == "2.0 KB" and size(5 * 1024**3) == "5.0 GB"


def test_a_data_folder_with_no_closed_month_yet_is_empty_not_at_fault(tmp_path):
    plugin = DuckdbPlugin()
    (tmp_path / "data").mkdir()
    plugin.attach(SimpleNamespace(db_path=tmp_path / "data" / "liminal.db"), EnvironmentLogin(env={}))
    (own,) = plugin.instances()
    assert plugin.state(own)["state"] == "empty" and plugin.state(own)["why"] == "no closed month has been copied yet"
    assert plugin.test("history")["lines"] == [f"DuckDB {duckdb.__version__}, opened here", "no closed month has been copied yet"]
    (tmp_path / "data" / "history").mkdir()
    assert plugin.state(own)["state"] == "ready" and plugin.test("history")["lines"][1] == "no closed month has been copied yet"
    assert months(tmp_path / "nowhere") == []


def test_a_new_database_says_which_duckdb_wrote_it_and_what_it_is(ducks, tmp_path, monkeypatch):
    plugin, data, env = ducks
    made = plugin.new_database("research", holds="history", title="Research")
    path = data / "instances" / "research.duckdb"
    assert made["ok"] and made["said"] == f"research made: {path}"
    assert made["lines"][:2] == [f"research.duckdb made in {path.parent}",
                                 f"written by DuckDB {duckdb.__version__}: a DuckDB older than the one that wrote a file may not read it"]
    db = duckdb.connect(str(path), read_only=True)
    said = dict(db.execute(f"SELECT key, value FROM {MARKER}").fetchall())
    db.close()
    assert said == {"name": "research", "made": plugin.instance("research").at, "holds": "history",
                    "by": f"plugin-integrator-duckdb {__version__}"}
    assert plugin.test("research")["lines"] == [f"DuckDB {duckdb.__version__}, opened here", "research.duckdb: 1 table",
                                                f"made here on {said['made'][:10]} to hold history"]
    assert plugin.state(plugin.instance("research"))["bytes"] == path.stat().st_size
    # written through an open that asks for it; one file has no parts
    db = plugin.open(plugin.instance("research"), read_only=False)
    db.execute("CREATE TABLE notes (x INTEGER)")
    db.close()
    assert plugin.test("research")["lines"][1] == "research.duckdb: 2 tables"
    with pytest.raises(Refusal, match="research is one file"):
        plugin.open(plugin.instance("research"), "massive/2026-09.1.duckdb")
    other = tmp_path / "disk2"
    other.mkdir()
    assert plugin.new_database("second", where=str(other / "second.duckdb"))["ok"]
    for args, why in ((("x", "instances/x.db"), "a DuckDB file ends in .duckdb"), (("x", "history/x.duckdb"), "goes in its instances/ folder"),
                      (("x", str(other / "second.duckdb")), "is there already"), (("x", "", "bars"), "cannot hold bars")):
        with pytest.raises(Refusal, match=why):
            plugin.new_database(*args)
    assert [i["name"] for i in json.loads(env["DUCKDB_INSTANCES"])["instances"]] == ["research", "second"]
    # one that fails while it is made leaves no half-made file: the next try starts clean
    monkeypatch.setattr("plugin_integrator_duckdb.now_iso", lambda: 1 / 0)
    with pytest.raises(ZeroDivisionError):
        plugin.make(Instance("half", where="instances/half.duckdb"), data)
    assert not list((data / "instances").glob("half.duckdb*"))
    monkeypatch.undo()
    assert plugin.forget("research")["ok"] and path.is_file()


def test_a_file_that_exists_is_connected_only_when_it_is_a_duckdb_file(ducks, tmp_path):
    plugin, data, env = ducks
    elsewhere = tmp_path / "old" / "bars.duckdb"
    month(elsewhere, rows=5)
    got = plugin.connect_to("old", str(elsewhere), holds="history")
    assert got["ok"] and got["lines"][:2] == [f"DuckDB {duckdb.__version__}, opened here", "bars.duckdb: 2 tables"]
    notes = tmp_path / "notes.duckdb"
    notes.write_text("these are not the blocks of a database, however the file is named\n" * 40, encoding="utf-8")
    with pytest.raises(Refusal, match="did not answer, so it is not kept"):
        plugin.connect_to("notes", str(notes))
    for where, why in (("history/massive/2026-09.1.duckdb", "holds it already"), ("backups/gone.duckdb", "is no file here"),
                       (str(elsewhere.with_suffix(".db")), "a DuckDB file ends in .duckdb")):
        with pytest.raises(Refusal, match=why):
            plugin.connect_to("x", where)
    assert sorted(i.name for i in plugin.instances()) == ["history", "old"]


def test_another_systems_files_are_read_directly_and_written_from_that_system_alone(ducks, monkeypatch):
    plugin, data, env = ducks
    plugin.new_database("research")
    monkeypatch.setattr(mounts, "foreign", lambda path, mounts=None: True)
    monkeypatch.setattr("liminal_libs.config.UserEnvironment.saved", lambda self: {"DUCKDB_INSTANCES": env["DUCKDB_INSTANCES"]})
    assert [(i.name, plugin.effective_method(i)) for i in plugin.instances()] == [("history", "file"), ("research", "file")]
    db = plugin.open(plugin.instance("history"), "tiingo/2026-09.1.duckdb")  # read through the mount: no helper
    assert db.execute("SELECT count(*) FROM bars").fetchone() == (3,)
    db.close()
    assert plugin.test("history")["ok"] and plugin.test("research")["ok"]
    with pytest.raises(mounts.NotHere, match="writing a DuckDB file"):
        plugin.open(plugin.instance("research"), read_only=False)
    with pytest.raises(mounts.NotHere, match="done from that system"):
        plugin.new_database("x")
    assert plugin.status()["can"]["new"] is False and "changed from that system" in plugin.status()["can"]["why"]
