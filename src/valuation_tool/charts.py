"""Interactive Plotly charts for valuation outputs."""

import pandas as pd
import plotly.graph_objects as go


def create_sensitivity_heatmap(
    table: pd.DataFrame,
    *,
    title: str,
    column_format: str,
) -> go.Figure:
    """Create an implied-share-price sensitivity heatmap."""
    x_labels = [format(float(value), column_format) for value in table.columns]
    y_labels = [f"{float(value):.1%}" for value in table.index]
    figure = go.Figure(
        data=go.Heatmap(
            z=table.to_numpy(),
            x=x_labels,
            y=y_labels,
            colorscale="RdYlGn",
            text=[[f"${value:,.2f}" for value in row] for row in table.to_numpy()],
            texttemplate="%{text}",
            hovertemplate="Column: %{x}<br>WACC: %{y}<br>Value: %{text}<extra></extra>",
            colorbar={"title": "Share price"},
        )
    )
    figure.update_layout(
        title=title,
        xaxis_title=table.columns.name.replace("_", " ").title(),
        yaxis_title="WACC",
        template="plotly_white",
    )
    return figure


def create_football_field(
    ranges: pd.DataFrame, current_share_price: float
) -> go.Figure:
    """Create a horizontal valuation football field."""
    figure = go.Figure()
    for row in ranges.itertuples(index=False):
        figure.add_trace(
            go.Scatter(
                x=[row.low, row.high],
                y=[row.method, row.method],
                mode="lines+markers",
                line={"width": 10, "color": "#1F4E78"},
                marker={"size": 10, "color": "#1F4E78"},
                name=row.method,
                text=[f"Low: ${row.low:,.2f}", f"High: ${row.high:,.2f}"],
                hovertemplate="%{text}<extra></extra>",
                showlegend=False,
            )
        )
    figure.add_vline(
        x=current_share_price,
        line_width=2,
        line_dash="dash",
        line_color="#C00000",
        annotation_text=f"Current price ${current_share_price:,.2f}",
        annotation_position="top",
    )
    figure.update_layout(
        title="Valuation Football Field",
        xaxis_title="Implied share price",
        yaxis_title="",
        template="plotly_white",
        height=450,
        margin={"l": 170, "r": 40, "t": 80, "b": 50},
    )
    return figure


def create_forecast_chart(forecast: pd.DataFrame) -> go.Figure:
    """Create a revenue and EBITDA forecast chart."""
    figure = go.Figure()
    figure.add_bar(
        x=forecast["forecast_year"],
        y=forecast["revenue"],
        name="Revenue",
        marker_color="#8FB8DE",
    )
    figure.add_bar(
        x=forecast["forecast_year"],
        y=forecast["ebitda"],
        name="EBITDA",
        marker_color="#1F4E78",
    )
    figure.update_layout(
        title="Five-Year Operating Forecast",
        xaxis_title="Forecast year",
        yaxis_title="USD millions",
        barmode="group",
        template="plotly_white",
    )
    return figure
