"""CP-02 · FS-CM-03 JSON-schema export and golden snapshot."""

import json
from pathlib import Path

import pytest

from cocok_core.schema_export import SCHEMA_DIALECT, build_schema, main, render

pytestmark = pytest.mark.cp02

REPO_ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = REPO_ROOT / "schemas" / "extracted_document.schema.json"


def test_render_is_deterministic() -> None:
    assert render() == render()


def test_render_is_sorted_and_ends_with_newline() -> None:
    text = render()
    assert text.endswith("}\n")
    assert text == json.dumps(json.loads(text), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_schema_shape() -> None:
    schema = build_schema()
    assert schema["$schema"] == SCHEMA_DIALECT
    assert schema["required"] == ["doc_type"]
    assert schema["additionalProperties"] is False
    defs = schema["$defs"]
    assert defs["Money"]["properties"]["amount_idr"]["type"] == "integer"
    assert defs["Money"]["additionalProperties"] is False
    assert defs["LineItem"]["properties"]["qty"]["anyOf"][0]["type"] == "string"


def test_schema_has_no_long_docstrings() -> None:
    # The schema is sent to LLMs: descriptions must be short labels, not developer docs.
    def walk(node: object) -> None:
        if isinstance(node, dict):
            desc = node.get("description")
            if isinstance(desc, str):
                assert len(desc) <= 120, desc
                assert "Args:" not in desc
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(build_schema())


def test_committed_snapshot_is_up_to_date() -> None:
    assert SNAPSHOT.read_text(encoding="utf-8") == render(), (
        "Snapshot is stale. Review the model change, then run: "
        "uv run python -m cocok_core.schema_export --write schemas/extracted_document.schema.json"
    )


def test_cli_check_and_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "schema.json"
    assert main(["--check", str(target)]) == 1  # missing file is stale
    assert main(["--write", str(target)]) == 0
    assert main(["--check", str(target)]) == 0
    target.write_text("{}\n", encoding="utf-8")
    assert main(["--check", str(target)]) == 1
    capsys.readouterr()
    assert main([]) == 0
    assert capsys.readouterr().out == render()
