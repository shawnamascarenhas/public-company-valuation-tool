"""Tests for the downloadable valuation workbook."""

from io import BytesIO

from openpyxl import load_workbook

from valuation_tool.config import RAW_DATA_DIR
from valuation_tool.data_loader import load_input_bundle
from valuation_tool.dcf import run_dcf_analysis
from valuation_tool.multiples import run_comps_analysis
from valuation_tool.report import build_excel_report
from valuation_tool.sensitivity import run_sensitivity_analysis


def test_excel_report_contains_complete_model() -> None:
    bundle = load_input_bundle(RAW_DATA_DIR / "example")
    comps = run_comps_analysis(bundle)
    dcf = run_dcf_analysis(bundle)
    sensitivity = run_sensitivity_analysis(bundle, comps)

    report = build_excel_report(bundle, comps, dcf, sensitivity)
    workbook = load_workbook(BytesIO(report), data_only=False)

    assert len(report) > 10_000
    assert workbook.sheetnames == [
        "Companies",
        "Historical Financials",
        "DCF Assumptions",
        "Terminal Assumptions",
        "Trading Multiples",
        "Peer Statistics",
        "Comps Valuation",
        "DCF Forecast",
        "DCF Valuation",
        "Perpetuity Sensitivity",
        "Exit Multiple Sensitivity",
        "Football Field",
    ]
    assert workbook["Companies"]["A1"].value == "ticker"
    assert workbook["DCF Forecast"].max_row == 6
