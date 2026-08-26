from pathlib import Path


def test_dashboard_python_sources_do_not_import_niu_men_package() -> None:
    root = Path(__file__).resolve().parents[1]
    source_roots = [root / "src", root / "scripts", root / "backtest"]
    forbidden = "niu_men_line_strategy"
    offenders = [
        path
        for source_root in source_roots
        for path in source_root.rglob("*.py")
        if forbidden in path.read_text(encoding="utf-8")
    ]

    assert offenders == []


def test_contract_assets_are_retained_with_the_dashboard() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "schemas" / "research-snapshot.schema.json").is_file()
    assert (root / "tests" / "fixtures" / "research_snapshot" / "valid_v2.json").is_file()
