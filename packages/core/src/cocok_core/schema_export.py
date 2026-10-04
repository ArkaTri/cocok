"""Export the JSON schema of ``ExtractedDocument`` (FS-CM-03).

The file ``schemas/extracted_document.schema.json`` is a *golden snapshot*: it is committed,
reviewed like code,
and later sent to LLMs as their output format. Any model change that alters it must show up in a
diff.

Usage::

    uv run python -m cocok_core.schema_export               # print to stdout
    uv run python -m cocok_core.schema_export --write PATH  # (re)write the snapshot
    uv run python -m cocok_core.schema_export --check PATH  # exit 1 if PATH is stale (gate)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from cocok_core.models.document import ExtractedDocument

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"


def build_schema() -> dict[str, Any]:
    """Return the JSON schema of ``ExtractedDocument`` (validation mode) with the dialect declared.

    Returns:
        A JSON-serializable dict.
    """
    schema = ExtractedDocument.model_json_schema(mode="validation")
    return {"$schema": SCHEMA_DIALECT, **schema}


def render() -> str:
    """Return the schema as stable text: sorted keys, 2-space indent, trailing newline.

    Returns:
        The exact text of the snapshot file. Same models in → same bytes out.
    """
    return json.dumps(build_schema(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments without the program name; ``None`` means ``sys.argv[1:]``.

    Returns:
        Process exit code: 0 on success, 1 if ``--check`` found a stale snapshot.
    """
    parser = argparse.ArgumentParser(prog="python -m cocok_core.schema_export", description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--write", type=Path, metavar="PATH", help="write the schema to PATH")
    group.add_argument("--check", type=Path, metavar="PATH", help="fail if PATH is out of date")
    args = parser.parse_args(argv)

    text = render()
    if args.write is not None:
        args.write.write_text(text, encoding="utf-8")
        return 0
    if args.check is not None:
        current = args.check.read_text(encoding="utf-8") if args.check.exists() else ""
        if current != text:
            print(
                f"{args.check} is out of date. Review the model change, then run:\n"
                f"  uv run python -m cocok_core.schema_export --write {args.check}",
                file=sys.stderr,
            )
            return 1
        print(f"{args.check} is up to date.")
        return 0
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
