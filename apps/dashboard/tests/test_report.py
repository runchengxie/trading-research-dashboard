import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path('.').resolve()))


def test_report_builds_html(tmp_path):
    import report

    results = [
        {"股票代码": "sh600199", "股票名称": "金种子酒", "指标/参数": "最新收盘价",
         "计算值": "10.00 元", "使用说明": "T+0交易的核心中轴。"},
    ]
    out = str(tmp_path)
    index = report.build_report(results, [], "2024-09-30", out)

    assert os.path.exists(index)
    with open(index, encoding="utf-8") as f:
        content = f.read()
    assert "T+0 交易仪表盘" in content
    assert "金种子酒" in content
    assert "最新收盘价" in content


def test_report_copies_charts(tmp_path):
    import report

    # 造一个假的图表文件
    charts_dir = tmp_path / "charts"
    charts_dir.mkdir()
    fake = charts_dir / "sh600199_20240930.png"
    fake.write_bytes(b"fakepng")

    out = str(tmp_path / "site")
    index = report.build_report([], [str(fake)], "2024-09-30", out)

    assert os.path.exists(os.path.join(out, "charts", "sh600199_20240930.png"))
    with open(index, encoding="utf-8") as f:
        content = f.read()
    assert "sh600199" in content
