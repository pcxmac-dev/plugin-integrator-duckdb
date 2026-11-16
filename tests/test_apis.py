"""What the DuckDB plugin attaches to (plugin API 2.2): its card is sound, every address one of DuckDB's own pages;
it names the statements the plugin itself runs; what it knows of DuckDB here asks nothing and loads nothing; and the
card's pages answer (LIMINAL_VENDOR_PAGES=1 only, the one test that reaches the network)."""
from __future__ import annotations

import inspect
import os
import sys

import pytest

import plugin_integrator_duckdb as module
from liminal_libs.sources.apis import dead_links, problems, urls
from plugin_integrator_duckdb import DATABASE
from plugin_integrator_duckdb import apis as cards


def test_the_card_is_sound_and_links_the_makers_own_pages():
    assert problems(DATABASE.apis) == [] and DATABASE.apis == cards.APIS == (cards.DUCKDB,)
    api = cards.DUCKDB
    assert (api.name, api.kind, api.verified, api.costs) == ("DuckDB", "sdk", "2026-11-16", "") and api.docs == cards.DOCS
    assert all(u.startswith(("https://duckdb.org/", "https://github.com/duckdb/duckdb")) for u in urls(DATABASE.apis))
    assert len(urls(DATABASE.apis)) == 11 and {x.kind for x in api.links} == {"docs", "reference", "guide", "spec", "changelog", "source"}
    assert len(api.areas) > len(api.covered) >= 6 and len(api.calls) > len(api.used) >= 4
    assert {c.area for c in api.calls} <= {a.name for a in api.areas}
    # the two pages that decide how it works are on the card
    assert "no helper" in next(a.covered for a in api.areas if a.name == "Concurrency")
    assert "which DuckDB wrote it" in next(a.covered for a in api.areas if a.name == "Storage versions")


def test_the_card_names_what_the_plugin_itself_runs():
    src = inspect.getsource(module)
    used = " ".join(c.name for c in cards.DUCKDB.used)
    for statement in ("SELECT library_version FROM pragma_version()", "SELECT count(*) FROM duckdb_tables() WHERE NOT internal"):
        assert statement in src and statement in used
    assert "duckdb.connect(" in src and "duckdb.connect(database, read_only=, config=)" in used
    assert '"threads": THREADS, "memory_limit": MEMORY' in src and (module.THREADS, module.MEMORY) == (1, "64MB")
    assert f"CREATE TABLE {module.MARKER} " in used and "CREATE TABLE {MARKER} " in src


def test_what_it_knows_of_duckdb_here_loads_nothing():
    was = sys.modules.pop("duckdb", None)
    try:
        facts = module.DuckdbPlugin().api_facts()
        assert list(facts) == ["DuckDB"] and facts["DuckDB"]["DuckDB in this Python"] and "duckdb" not in sys.modules
    finally:
        if was is not None:
            sys.modules["duckdb"] = was


@pytest.mark.skipif(os.environ.get("LIMINAL_VENDOR_PAGES") != "1", reason="reaches DuckDB's pages: LIMINAL_VENDOR_PAGES=1")
def test_the_cards_pages_answer():
    assert dead_links(DATABASE.apis) == []
