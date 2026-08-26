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


def test_contract_assets_trigger_dashboard_web_workflows() -> None:
    root = Path(__file__).resolve().parents[1]
    shared_paths = {
        "schemas/**",
        "tests/fixtures/research_snapshot/**",
    }

    for workflow_name in ("web-unit.yml", "web-browser.yml"):
        workflow = (root / ".github" / "workflows" / workflow_name).read_text(encoding="utf-8")
        required_paths = shared_paths | {f".github/workflows/{workflow_name}"}
        for required_path in required_paths:
            assert required_path in workflow, f"{workflow_name} missing {required_path}"
