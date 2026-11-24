"""Headless smoke test for the complete Streamlit workflow."""

from streamlit.testing.v1 import AppTest

from valuation_tool.config import PROJECT_ROOT


def test_streamlit_example_workflow_renders_without_exception() -> None:
    app = AppTest.from_file(PROJECT_ROOT / "app.py", default_timeout=30).run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "Inputs",
        "Company Overview",
        "Comparable Companies",
        "DCF",
        "Sensitivity",
        "Valuation Summary",
    ]
    assert any("Validated: ALPH with 5 peers" in item.value for item in app.success)
    assert len(app.get("download_button")) == 1
