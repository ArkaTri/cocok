# Changelog

All notable changes to this project are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/). Checkpoint tags (`cp-NN`) mark build progress.

## [Unreleased]

### Added
- Project architecture: 93 folders and 373 placeholder files created by Arka in VS Code (docs/BLUEPRINT.md §7).
- CP-01: uv workspace (core, adapters, ml, api, worker), ruff/mypy/import-linter/pytest/pre-commit toolchain,
  Makefile, checkpoint gate scripts cp00/cp01, SHA-pinned GitHub workflows, Dependabot, project docs.
- CP-02: domain language in `cocok_core` — `Money` (strict whole rupiah), `ExtractedDocument`/`LineItem`/
  `FieldMeta` (Pydantic 2.13, frozen), `REQUIRED_FIELDS`, document state machine, error hierarchy with stable
  codes, 8 ports + port data types, JSON-schema export and golden snapshot, gate cp02.

### Changed
- CP-02 spec errata: `ValidationError` → `DomainValidationError`; ports take `PageImage` (not numpy arrays) and an
  opaque `Transaction` (not a psycopg connection); repository ports moved to CP-21/22.
