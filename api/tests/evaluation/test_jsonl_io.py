import json

import pytest

from app.evaluation.jsonl_io import read_jsonl_rows


def test_unicode_line_separators_inside_values_round_trip(tmp_path):
    path = tmp_path / "rows.jsonl"
    rows = [{"k": "a\u2028b\u0085c"}, {"k": "plain"}]
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                    encoding="utf-8")
    assert read_jsonl_rows(path) == rows


def test_missing_file_and_blank_lines(tmp_path):
    path = tmp_path / "rows.jsonl"
    assert read_jsonl_rows(path) == []
    path.write_text('{"a": 1}\n\n  \n{"a": 2}\n', encoding="utf-8")
    assert read_jsonl_rows(path) == [{"a": 1}, {"a": 2}]


def test_torn_last_line_is_dropped_and_file_rewritten(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n{"a": ', encoding="utf-8")
    assert read_jsonl_rows(path) == [{"a": 1}, {"a": 2}]
    assert path.read_bytes() == b'{"a": 1}\n{"a": 2}\n'
    assert not list(tmp_path.glob("*.tmp"))


def test_bad_middle_line_exits_naming_file_and_line(tmp_path):
    path = tmp_path / "rows.jsonl"
    path.write_text('{"a": 1}\n{oops\n{"a": 3}\n', encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        read_jsonl_rows(path)
    assert "rows.jsonl" in str(exc.value) and "line 2" in str(exc.value)
