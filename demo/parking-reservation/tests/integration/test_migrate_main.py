import json

import pytest

from parking_reservation.migrate_main import main

pytestmark = pytest.mark.integration


def test_missing_database_url_exits_2(monkeypatch, restore_root_logging) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main() == 2


def test_unreachable_database_exits_1_with_one_json_error_line(
    monkeypatch, capsys, restore_root_logging
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:x@127.0.0.1:1/none?connect_timeout=1")
    assert main() == 1
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [line["severity"] for line in lines] == ["ERROR"]
    assert lines[0]["message"] == "migration failed"


def test_up_to_date_database_exits_0(monkeypatch, database_url: str, restore_root_logging) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    assert main() == 0
