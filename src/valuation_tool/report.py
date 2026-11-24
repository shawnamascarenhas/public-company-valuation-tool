"""Downloadable Excel valuation report generation."""

from io import BytesIO

import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from valuation_tool.data_loader import InputBundle
from valuation_tool.dcf import DCFAnalysis
from valuation_tool.multiples import CompsAnalysis
from valuation_tool.sensitivity import SensitivityAnalysis


def _format_workbook(workbook: object) -> None:
    """Apply compact professional formatting to every worksheet."""
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    for worksheet in workbook.worksheets:
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
        for column_cells in worksheet.columns:
            max_length = max(
                len(str(cell.value)) if cell.value is not None else 0
                for cell in column_cells
            )
            width = min(max(max_length + 2, 10), 28)
            worksheet.column_dimensions[
                get_column_letter(column_cells[0].column)
            ].width = width


def build_excel_report(
    bundle: InputBundle,
    comps: CompsAnalysis,
    dcf: DCFAnalysis,
    sensitivity: SensitivityAnalysis,
) -> bytes:
    """Return a formatted workbook containing inputs and valuation outputs."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        bundle.companies.to_excel(writer, sheet_name="Companies", index=False)
        bundle.historicals.to_excel(
            writer, sheet_name="Historical Financials", index=False
        )
        bundle.forecast_assumptions.to_excel(
            writer, sheet_name="DCF Assumptions", index=False
        )
        bundle.valuation_assumptions.to_excel(
            writer, sheet_name="Terminal Assumptions", index=False
        )
        comps.company_multiples.to_excel(
            writer, sheet_name="Trading Multiples", index=False
        )
        comps.summary_statistics.to_excel(writer, sheet_name="Peer Statistics")
        comps.implied_valuation.to_excel(
            writer, sheet_name="Comps Valuation", index=False
        )
        dcf.forecast.to_excel(writer, sheet_name="DCF Forecast", index=False)
        dcf.valuation_summary.to_excel(writer, sheet_name="DCF Valuation", index=False)
        sensitivity.perpetuity_growth.to_excel(
            writer, sheet_name="Perpetuity Sensitivity"
        )
        sensitivity.exit_multiple.to_excel(
            writer, sheet_name="Exit Multiple Sensitivity"
        )
        sensitivity.football_field.to_excel(
            writer, sheet_name="Football Field", index=False
        )
        _format_workbook(writer.book)
    return output.getvalue()
